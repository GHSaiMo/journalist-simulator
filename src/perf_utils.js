import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

// =========================================================================
// Draw-call reduction: merge rigid meshes that share a material.
//
//  Tier A (fully static subtrees: walls, furniture, props): baked into world
//          space and merged per material -> a few dozen draw calls total.
//  Tier B (meshes rigidly attached to an animated/scripted node, e.g. a
//          character's torso or a door hinge): merged per (parent, material)
//          in the parent's local space, so they still follow the animation.
//
// Every shadow pass (point light = 6 passes) and the BokehPass depth pass
// re-issues all draw calls, so cutting ~1400 meshes down to a few hundred
// is the single biggest CPU/GPU saving.
// =========================================================================

// Nodes the game logic drives directly (guards, necks, doors, NPC flash anchor)
const SCRIPTED_ANCESTOR_RE = /^(Char_|EntryDoor)/;
const PROTECTED_NAME_RE = /(_Root|_Neck|_Torso|_Shoulder_[LR]|_Elbow_[LR])$|^Press_SLR_Flash$|^EntryDoor_Hinge/;

function attributeSignature(geometry) {
  const parts = [];
  for (const name of Object.keys(geometry.attributes).sort()) {
    const a = geometry.attributes[name];
    if (a.isInterleavedBufferAttribute) return null;
    parts.push(`${name}:${a.itemSize}:${a.array.constructor.name}:${a.normalized ? 1 : 0}`);
  }
  if (Object.keys(geometry.morphAttributes).length > 0) return null;
  parts.push(geometry.index ? 'idx' : 'noidx');
  return parts.join('|');
}

function isMergeCandidate(mesh) {
  return (
    mesh.isMesh &&
    !mesh.isSkinnedMesh &&
    !mesh.isInstancedMesh &&
    !Array.isArray(mesh.material) &&
    mesh.children.length === 0 &&
    !mesh.morphTargetInfluences
  );
}

/**
 * @param {THREE.Object3D} root      glTF scene root (not yet added to the scene)
 * @param {THREE.AnimationClip[]} clips
 * @returns {{ raycastTargets: THREE.Mesh[], before: number, after: number }}
 */
export function mergeStaticMeshes(root, clips = []) {
  root.updateMatrixWorld(true);
  const rootInv = new THREE.Matrix4().copy(root.matrixWorld).invert();

  // Objects targeted by animation tracks
  const animated = new Set();
  for (const clip of clips) {
    for (const track of clip.tracks) {
      const { nodeName } = THREE.PropertyBinding.parseTrackName(track.name);
      const obj = nodeName ? root.getObjectByName(nodeName) : null;
      if (obj) animated.add(obj);
    }
  }

  const hasDynamicAncestor = (obj) => {
    for (let o = obj; o && o !== root; o = o.parent) {
      if (animated.has(o) || SCRIPTED_ANCESTOR_RE.test(o.name || '')) return true;
    }
    return false;
  };

  const groups = new Map(); // key -> { parent, material, castShadow, receiveShadow, meshes: [], world }
  let before = 0;

  root.traverse((obj) => {
    if (!obj.isMesh) return;
    before++;
    if (!isMergeCandidate(obj)) return;
    if (animated.has(obj) || PROTECTED_NAME_RE.test(obj.name || '')) return;
    const sig = attributeSignature(obj.geometry);
    if (!sig) return;

    const world = !hasDynamicAncestor(obj);
    const matrix = world
      ? new THREE.Matrix4().multiplyMatrices(rootInv, obj.matrixWorld)
      : obj.matrix.clone();
    // Mirrored transforms would flip triangle winding when baked; leave them alone.
    if (matrix.determinant() < 0) return;

    const parent = world ? root : obj.parent;
    const key = [parent.uuid, obj.material.uuid, sig, obj.castShadow ? 1 : 0, obj.receiveShadow ? 1 : 0, obj.renderOrder].join('#');
    let g = groups.get(key);
    if (!g) {
      g = { parent, world, material: obj.material, castShadow: obj.castShadow, receiveShadow: obj.receiveShadow, renderOrder: obj.renderOrder, items: [] };
      groups.set(key, g);
    }
    g.items.push({ mesh: obj, matrix });
  });

  const raycastTargets = [];
  const mergedWorldMeshes = new Set();

  for (const g of groups.values()) {
    if (g.items.length < 2) continue;
    const geoms = g.items.map(({ mesh, matrix }) => mesh.geometry.clone().applyMatrix4(matrix));
    const merged = mergeGeometries(geoms, false);
    for (const geo of geoms) geo.dispose();
    if (!merged) continue;
    merged.computeBoundingBox();
    merged.computeBoundingSphere();

    const m = new THREE.Mesh(merged, g.material);
    m.name = `Merged_${g.material.name || 'mat'}_${g.items.length}`;
    m.castShadow = g.castShadow;
    m.receiveShadow = g.receiveShadow;
    m.renderOrder = g.renderOrder;
    g.parent.add(m);
    if (g.world) {
      m.matrixAutoUpdate = false;
      m.updateMatrix();
      mergedWorldMeshes.add(m);
    }

    for (const { mesh } of g.items) {
      mesh.removeFromParent();
      // Static originals keep their (frozen) matrixWorld and serve as cheap,
      // bounding-sphere-culled raycast proxies for the auto-focus ray.
      if (g.world) raycastTargets.push(mesh);
    }
  }

  // Remaining live meshes (dynamic + per-bone merged) are raycast directly.
  let after = 0;
  root.updateMatrixWorld(true);
  root.traverse((obj) => {
    if (!obj.isMesh) return;
    after++;
    if (!mergedWorldMeshes.has(obj)) raycastTargets.push(obj);
  });

  // Fully static subtrees never move: skip per-frame local matrix recomposition.
  root.traverse((obj) => {
    if (obj !== root && !hasDynamicAncestor(obj)) {
      obj.updateMatrix();
      obj.matrixAutoUpdate = false;
    }
  });

  return { raycastTargets, before, after };
}

// =========================================================================
// Adaptive render resolution: drops pixel ratio when the GPU can't hold the
// target frame rate, and cautiously raises it again when there is headroom.
// =========================================================================
export class AdaptiveResolution {
  constructor({ maxDpr, minDpr = 1.0, onChange }) {
    const steps = [2.0, 1.75, 1.5, 1.25, 1.0, 0.85, 0.75].filter((s) => s <= maxDpr + 1e-3 && s >= minDpr - 1e-3);
    if (steps.length === 0 || Math.abs(steps[0] - maxDpr) > 1e-3) steps.unshift(maxDpr);
    this.steps = steps;
    this.idx = 0;
    this.ceilingIdx = 0; // highest quality allowed (raised index = lower quality)
    this.onChange = onChange;
    this.windowMs = 0;
    this.windowFrames = 0;
    this.goodWindows = 0;
    this.lastUpgradeAt = -Infinity;
    this.elapsedMs = 0;
  }

  get dpr() {
    return this.steps[this.idx];
  }

  /** Call once per rendered (active, non-idle) frame. */
  sample(frameMs) {
    if (frameMs <= 0 || frameMs > 250) return; // tab switches, hitches
    this.elapsedMs += frameMs;
    this.windowMs += frameMs;
    this.windowFrames++;
    if (this.windowMs < 2000) return;

    const fps = (this.windowFrames * 1000) / this.windowMs;
    this.windowMs = 0;
    this.windowFrames = 0;

    if (fps < 45 && this.idx < this.steps.length - 1) {
      // A downgrade shortly after an upgrade means that level is not sustainable.
      if (this.elapsedMs - this.lastUpgradeAt < 8000) this.ceilingIdx = Math.max(this.ceilingIdx, this.idx);
      this.idx++;
      this.goodWindows = 0;
      this.onChange(this.dpr);
    } else if (fps >= 57) {
      this.goodWindows++;
      if (this.goodWindows >= 4 && this.idx > this.ceilingIdx) {
        this.idx--;
        this.goodWindows = 0;
        this.lastUpgradeAt = this.elapsedMs;
        this.onChange(this.dpr);
      }
    } else {
      this.goodWindows = 0;
    }
  }
}

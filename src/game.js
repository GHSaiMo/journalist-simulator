import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { BokehPass } from 'three/examples/jsm/postprocessing/BokehPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { SoundFX } from './audio_fx.js';
import { createFirstPersonCameraRig } from './camera_viewmodel.js';
import { AlbumManager } from './album_manager.js';
import { mergeStaticMeshes, AdaptiveResolution } from './perf_utils.js';

// Blender (X, Y, Z) -> Three.js (X, Z, -Y)
const b2t = (bx, by, bz) => new THREE.Vector3(bx, bz, -by);

// True 35mm full-frame vertical FOV (deg) from focal length (mm) (24mm sensor height)
const focalToFov = (mm) => THREE.MathUtils.radToDeg(2 * Math.atan(24 / (2 * mm)));

// Classic 9-stop SLR Aperture Ring (f/1.4 wide-open creamy bokeh -> f/16 deep focus) + Av Shutter Speeds
const F_STOPS = [1.4, 1.8, 2.0, 2.8, 4.0, 5.6, 8.0, 11, 16];
const AV_SHUTTERS = [1000, 640, 500, 250, 125, 60, 30, 15, 8];

function calcBokehUniforms(focalMm, fStop, focusM) {
  if (fStop >= 15.5) return { aperture: 0.0001, maxblur: 0.0005 };
  // Calibrated so 41-tap concentric kernel stays 100% buttery-smooth with zero tap stippling
  const focalGain = Math.pow(focalMm / 50.0, 1.25);
  const aperture = ((0.0135 / fStop) * focalGain) / Math.max(0.85, focusM * 0.42);
  const maxblur = Math.min(0.022, (0.028 / Math.pow(fStop, 0.88)) * Math.max(0.78, focalGain * 0.82));
  return { aperture, maxblur };
}

const LOOP_DURATION = 32.0;
const NPC_FLASH_TIMES = [7.35, 17.45, 18.65, 23.35];

// Static furniture & stationary crowd circle colliders in Three.js (x = bx, z = -by, radius)
const STATIC_COLLIDERS = [
  // 2 Main VIP Armchairs + 8 Perimeter Armchairs
  { id: 'VIP_Left', x: -0.86, z: -2.90, r: 0.54 },
  { id: 'VIP_Right', x: 0.86, z: -2.90, r: 0.56 },
  { id: 'Chair_L1', x: -4.70, z: -2.45, r: 0.54 },
  { id: 'Chair_L2', x: -4.82, z: -0.80, r: 0.54 },
  { id: 'Chair_L3', x: -4.82, z: 2.35, r: 0.52 },
  { id: 'Chair_S1', x: -2.85, z: 3.55, r: 0.52 },
  { id: 'Chair_R1', x: 4.70, z: -2.45, r: 0.52 },
  { id: 'Chair_R2', x: 4.82, z: -0.80, r: 0.52 },
  { id: 'Chair_R3', x: 4.82, z: 2.35, r: 0.52 },
  { id: 'Chair_S2', x: 2.85, z: 3.55, r: 0.52 },
  // 5 Rosewood Tea Tables
  { id: 'Tbl_VIP', x: 0.0, z: -2.96, r: 0.42 },
  { id: 'Tbl_L1', x: -4.78, z: -1.62, r: 0.36 },
  { id: 'Tbl_L2', x: -4.75, z: 3.18, r: 0.36 },
  { id: 'Tbl_R1', x: 4.78, z: -1.62, r: 0.36 },
  { id: 'Tbl_R2', x: 4.75, z: 3.18, r: 0.36 },
  // Vases & Palms
  { id: 'Vase_L', x: -3.25, z: -4.15, r: 0.36 },
  { id: 'Vase_R', x: 3.25, z: -4.15, r: 0.36 },
  { id: 'Palm_IL', x: -2.15, z: -3.72, r: 0.36 },
  { id: 'Palm_IR', x: 2.15, z: -3.72, r: 0.36 },
  { id: 'Palm_OL', x: -4.55, z: -3.95, r: 0.38 },
  { id: 'Palm_OR', x: 4.55, z: -3.95, r: 0.38 },
  // Stationary Press Reporters, Cameramen, Boom Op, Photographer & Protocol Staff
  { id: 'Rep_05', x: 0.28, z: 0.82, r: 0.36 },
  { id: 'Rep_06', x: -0.48, z: 0.88, r: 0.36 },
  { id: 'Rep_07', x: 0.90, z: 0.78, r: 0.36 },
  { id: 'Rep_08', x: -1.06, z: 0.82, r: 0.36 },
  { id: 'CamOp_09', x: -0.72, z: 1.66, r: 0.46 },
  { id: 'Betacam_02', x: 1.22, z: 1.48, r: 0.38 },
  { id: 'CamOp_10', x: 1.40, z: 1.86, r: 0.40 },
  { id: 'Boom_11', x: -1.62, z: 1.32, r: 0.42 },
  { id: 'Photo_12', x: 0.68, z: 1.55, r: 0.40 },
  { id: 'Guard_West', x: -5.25, z: -3.35, r: 0.40 },
  { id: 'Guard_East', x: 5.25, z: -3.35, r: 0.40 },
];

// Exact Three.js camera yaw facing inward toward hall center (0, -0.8)
const yawTowardCenter = (sx, sz) => Math.atan2(sx, sz + 0.8);

// 7 Empty Armchairs around the perimeter (+ vacated VIP_Left) that the player can sit in!
const SITTABLE_CHAIRS = [
  { id: 'Chair_R1', seatPos: new THREE.Vector3(4.60, 1.18, -2.42), exitPos: new THREE.Vector3(3.80, 1.64, -2.20), seatYaw: yawTowardCenter(4.60, -2.42), vipOnlyWhenAway: false },
  { id: 'Chair_R2', seatPos: new THREE.Vector3(4.72, 1.18, -0.80), exitPos: new THREE.Vector3(3.90, 1.64, -0.80), seatYaw: yawTowardCenter(4.72, -0.80), vipOnlyWhenAway: false },
  { id: 'Chair_R3', seatPos: new THREE.Vector3(4.72, 1.18, 2.32), exitPos: new THREE.Vector3(3.90, 1.64, 2.10), seatYaw: yawTowardCenter(4.72, 2.32), vipOnlyWhenAway: false },
  { id: 'Chair_S2', seatPos: new THREE.Vector3(2.82, 1.18, 3.48), exitPos: new THREE.Vector3(2.55, 1.64, 2.75), seatYaw: yawTowardCenter(2.82, 3.48), vipOnlyWhenAway: false },
  { id: 'Chair_L3', seatPos: new THREE.Vector3(-4.72, 1.18, 2.32), exitPos: new THREE.Vector3(-3.90, 1.64, 2.10), seatYaw: yawTowardCenter(-4.72, 2.32), vipOnlyWhenAway: false },
  { id: 'Chair_S1', seatPos: new THREE.Vector3(-2.82, 1.18, 3.48), exitPos: new THREE.Vector3(-2.55, 1.64, 2.75), seatYaw: yawTowardCenter(-2.82, 3.48), vipOnlyWhenAway: false },
  { id: 'VIP_Left', seatPos: new THREE.Vector3(-0.86, 1.18, -2.80), exitPos: new THREE.Vector3(-0.86, 1.64, -1.95), seatYaw: Math.PI * 0.96, vipOnlyWhenAway: true },
];

window.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('viewport');
  const loaderRing = document.getElementById('loader-ring');
  const ovfOverlay = document.getElementById('ovf-overlay');
  const hipReticle = document.getElementById('hip-reticle');
  const mirrorBlackout = document.getElementById('mirror-blackout');
  const flashScreenPulse = document.getElementById('flash-screen-pulse');
  const seatHintBtn = document.getElementById('seat-hint-icon');
  const touchControlsEl = document.getElementById('touch-controls');

  const ovfFocalEl = document.getElementById('ovf-focal');
  const ovfApertureEl = document.getElementById('ovf-aperture');
  const ovfShutterEl = document.getElementById('ovf-shutter');
  const ovfDistEl = document.getElementById('ovf-dist');
  const ovfFlashLed = document.getElementById('ovf-flash-led');
  const hudApertureVal = document.getElementById('hud-aperture-val');

  const sfx = new SoundFX();

  // Renderer & Scene
  // Performance: cap pixel ratio at 1.5 (Retina 2x/3x costs 1.8x-4x more fragment work for
  // barely visible gain under MSAA + AgX), then adapt downward if frame rate drops.
  // Override with ?dpr=2 (or any number) in the URL for screenshots / beefy GPUs.
  const urlDpr = parseFloat(new URLSearchParams(window.location.search).get('dpr'));
  const nativeDpr = window.devicePixelRatio || 1;
  const maxDpr = Number.isFinite(urlDpr) && urlDpr > 0 ? urlDpr : Math.min(nativeDpr, 1.5);
  const adaptiveRes = new AdaptiveResolution({
    maxDpr,
    minDpr: Number.isFinite(urlDpr) ? maxDpr : Math.min(maxDpr, 0.85),
    onChange: (next) => applyPixelRatio(next),
  });
  let dpr = adaptiveRes.dpr;
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    // 'default' lets dual-GPU laptops stay on the cool integrated GPU instead of
    // spinning up the discrete one (a major source of fan noise).
    powerPreference: 'default',
    preserveDrawingBuffer: false,
  });
  renderer.setPixelRatio(dpr);
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.toneMappingExposure = 0.84;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap; // PCFSoft was removed in r18x and silently fell back to PCF
  container.appendChild(renderer.domElement);

  // Shadow maps are refreshed manually (see refreshShadows) instead of on every
  // renderer.render() call; previously the BokehPass depth render re-rendered
  // all shadow maps a second time each frame.
  const throttledShadowLights = [];

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x100b09);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.12;

  // Player First-Person Camera (YXZ Euler order for FPS look; near=0.10 doubles WebGL depth precision!)
  const BASE_HIP_FOV = 58;
  const camera = new THREE.PerspectiveCamera(BASE_HIP_FOV, container.clientWidth / container.clientHeight, 0.10, 65);
  camera.rotation.order = 'YXZ';
  scene.add(camera);

  // Post-Processing Optical Depth-of-Field Pipeline (4x MSAA HDR RenderTarget + BokehPass + AgX OutputPass)
  const msaaTarget = new THREE.WebGLRenderTarget(
    Math.max(1, Math.floor(container.clientWidth * dpr)),
    Math.max(1, Math.floor(container.clientHeight * dpr)),
    { type: THREE.HalfFloatType, samples: 4 }
  );
  const composer = new EffectComposer(renderer, msaaTarget);
  composer.setPixelRatio(dpr);
  composer.setSize(container.clientWidth, container.clientHeight);

  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);

  const bokehPass = new BokehPass(scene, camera, {
    focus: 2.8,
    aperture: 0.004,
    maxblur: 0.014,
  });
  composer.addPass(bokehPass);

  const outputPass = new OutputPass();
  composer.addPass(outputPass);

  // Attach 3D SLR Camera Viewmodel to Player Camera
  const camRig = createFirstPersonCameraRig();
  camera.add(camRig.group);

  // Player's Hot-Shoe Speedlight 3D Flash (illuminates room during shutter capture & flash decay!)
  const playerFlashSpot = new THREE.SpotLight(0xf6faff, 0, 14, Math.PI * 0.36, 0.55, 1.35);
  playerFlashSpot.position.set(0, 0.14, -0.08);
  playerFlashSpot.target.position.set(0, 0, -4.0);
  playerFlashSpot.castShadow = true;
  playerFlashSpot.shadow.mapSize.set(1024, 1024);
  playerFlashSpot.shadow.bias = -0.0008;
  playerFlashSpot.shadow.normalBias = 0.035;
  playerFlashSpot.shadow.autoUpdate = false;
  playerFlashSpot.shadow.needsUpdate = true;
  camera.add(playerFlashSpot);
  camera.add(playerFlashSpot.target);

  const playerFlashFill = new THREE.PointLight(0xf6faff, 0, 8.5, 1.6);
  playerFlashFill.position.set(0, 0.12, -0.15);
  camera.add(playerFlashFill);

  // Hall & Broadcast Lighting
  const hemi = new THREE.HemisphereLight(0xffe9c8, 0x3b1512, 0.16);
  scene.add(hemi);

  const chandelierLight = new THREE.PointLight(0xffdca0, 12.5, 21, 1.55);
  chandelierLight.position.copy(b2t(0.0, 0.35, 3.95));
  chandelierLight.castShadow = true;
  chandelierLight.shadow.mapSize.set(1024, 1024);
  chandelierLight.shadow.bias = -0.001;
  chandelierLight.shadow.normalBias = 0.035;
  chandelierLight.shadow.autoUpdate = false;
  chandelierLight.shadow.needsUpdate = true;
  throttledShadowLights.push(chandelierLight);
  scene.add(chandelierLight);

  for (const fc of [
    b2t(-3.6, 2.8, 4.7),
    b2t(3.6, 2.8, 4.7),
    b2t(-3.6, -2.6, 4.7),
    b2t(3.6, -2.6, 4.7),
  ]) {
    const pl = new THREE.PointLight(0xffe6bd, 4.2, 15, 1.7);
    pl.position.copy(fc);
    scene.add(pl);
  }

  const screenSpot = new THREE.SpotLight(0xffe4b2, 9.5, 14, Math.PI * 0.34, 0.6, 1.35);
  screenSpot.position.copy(b2t(0.0, 1.5, 4.65));
  screenSpot.target.position.copy(b2t(0.0, 4.35, 1.75));
  scene.add(screenSpot);
  scene.add(screenSpot.target);

  const engSpot1 = new THREE.SpotLight(0xf3f8ff, 14.5, 15, Math.PI * 0.26, 0.48, 1.45);
  engSpot1.position.copy(b2t(-0.62, -1.42, 1.80));
  engSpot1.target.position.copy(b2t(-0.30, 1.50, 1.35));
  engSpot1.castShadow = true;
  engSpot1.shadow.mapSize.set(1024, 1024);
  engSpot1.shadow.bias = -0.0008;
  engSpot1.shadow.normalBias = 0.035;
  engSpot1.shadow.autoUpdate = false;
  engSpot1.shadow.needsUpdate = true;
  throttledShadowLights.push(engSpot1);
  scene.add(engSpot1);
  scene.add(engSpot1.target);

  const engSpot2 = new THREE.SpotLight(0xf4f8ff, 8.5, 15, Math.PI * 0.28, 0.55, 1.5);
  engSpot2.position.copy(b2t(1.22, -1.32, 1.75));
  engSpot2.target.position.copy(b2t(-0.10, 1.80, 1.30));
  scene.add(engSpot2);
  scene.add(engSpot2.target);

  const npcSlrFlash = new THREE.PointLight(0xf8fbff, 0.0, 14, 1.5);
  npcSlrFlash.position.copy(b2t(0.62, -1.25, 1.68));
  scene.add(npcSlrFlash);

  // Warm Outer Reception Corridor Sconce & Portal Lighting (outside South double doors at z > 5.8m)
  const corridorLight = new THREE.PointLight(0xffe1ad, 6.8, 12, 1.45);
  corridorLight.position.set(0.0, 3.45, 8.10);
  scene.add(corridorLight);

  const corridorDoorFill = new THREE.PointLight(0xffdca2, 3.6, 7.5, 1.6);
  corridorDoorFill.position.set(0.0, 2.25, 6.45);
  scene.add(corridorDoorFill);

  // =========================================================================
  // Player State, Opening Corridor Walk-In Cutscene, Camera Optics & Album
  // =========================================================================
  const STAND_EYE_Y = 1.64;
  const CROUCH_EYE_Y = 1.02;
  const INTRO_DURATION = 4.65;

  const smoothstep01 = (x) => {
    const u = Math.max(0, Math.min(1, x));
    return u * u * (3 - 2 * u);
  };
  const smootherstep01 = (x) => {
    const u = Math.max(0, Math.min(1, x));
    return u * u * u * (u * (u * 6 - 15) + 10);
  };

  let introState = 'waiting'; // 'waiting' (outside closed doors) -> 'walking_in' (forced entrance) -> 'done' (locked inside)
  let introTime = 0.0;
  let doorOpenPlayed = false;
  let doorClosePlayed = false;
  document.body.classList.add('intro-playing');

  const player = {
    pos: new THREE.Vector3(0.0, STAND_EYE_Y, 8.45), // Starts OUTSIDE in the hushed outer corridor facing closed doors!
    yaw: 0.0,
    pitch: 0.01,
    eyeY: STAND_EYE_Y,
    targetEyeY: STAND_EYE_Y,
    crouched: false,
    seatedChair: null, // entry from SITTABLE_CHAIRS when seated
    walkBobPhase: 0,
    stepAccum: 0,
    swayX: 0,
    swayY: 0,
  };

  let isAiming = false;      // Right-click held or mobile OVF toggled
  let adsBlend = 0.0;        // 0 = chest hip-carry, 1 = eye against OVF
  let focalMm = 50.0;        // 24mm .. 135mm optical zoom
  let targetFocalMm = 50.0;
  let fStopIdx = 2;          // Default index 2 -> f/2.0 (natural shallow DoF out of the box!)
  let fStop = F_STOPS[fStopIdx];
  let focusDistM = 2.8;
  let smoothFocusDistM = 2.8;
  let flashEnabled = true;
  let shutterRecoil = 0.0;
  let playerFlashDecay = 0.0;
  let lastShutterMs = 0;

  // Album Manager
  let onAlbumClosedHook = null;
  const album = new AlbumManager({
    onOpenChange: (opened) => {
      if (opened && document.pointerLockElement) {
        wasPointerLocked = false;
        document.exitPointerLock?.();
      }
      if (opened) {
        isAiming = false;
        syncAimUI();
        document.body.classList.remove('fps-active');
      } else if (onAlbumClosedHook) {
        onAlbumClosedHook();
      }
    },
  });

  // =========================================================================
  // Load Animated Scene & Bind NPC Reactive Nodes
  // =========================================================================
  let mixer = null;
  let speakerRootNode = null;
  let speakerTorsoNode = null;
  let slrFlashNode = null;
  let entryDoorL = null;
  let entryDoorR = null;
  const focusableMeshes = [];
  const npcNecks = []; // { name, neckNode, rootNode, glanceTimer, glanceStrength }
  const guardRigs = {}; // 'West' | 'East' -> { root, neck, shR, elR, shL, elL, homePos, curPos, activeAmt }

  function setEntryDoorsAngle(rad) {
    if (entryDoorL) entryDoorL.rotation.y = rad;
    if (entryDoorR) entryDoorR.rotation.y = -rad;
  }

  const loader = new GLTFLoader();
  try {
    const gltf = await loader.loadAsync('./assets/press_hall.glb?v=4');
    const root = gltf.scene;
    const maxAniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());

    const neckMap = new Map();
    const rootMap = new Map();

    root.traverse((node) => {
      if (node.name === 'Char_01_MainSpeaker_Root') speakerRootNode = node;
      if (node.name === 'Char_01_MainSpeaker_Torso') speakerTorsoNode = node;
      if (node.name === 'Press_SLR_Flash') slrFlashNode = node;
      if (node.name === 'EntryDoor_Hinge_L') entryDoorL = node;
      if (node.name === 'EntryDoor_Hinge_R') entryDoorR = node;

      if (node.name.endsWith('_Neck')) {
        const prefix = node.name.slice(0, -5);
        neckMap.set(prefix, node);
      }
      if (node.name.endsWith('_Root') && node.name.startsWith('Char_')) {
        const prefix = node.name.slice(0, -5);
        rootMap.set(prefix, node);
      }

      if (node.isMesh) {
        const isLace = node.name.includes('Lace') || (node.material && node.material.name === 'Mat_Lace_Antimacassar');
        const isOuterShell =
          node.name.startsWith('Wall_') ||
          node.name.startsWith('Ceiling_') ||
          node.name.startsWith('Arch_Floor');
        // Thin lace overlays must NOT cast shadow-map acne onto 5mm-adjacent tabletops/armrests!
        node.castShadow = !isOuterShell && !isLace;
        node.receiveShadow = true;
        focusableMeshes.push(node);

        const mats = Array.isArray(node.material) ? node.material : [node.material];
        for (const mat of mats) {
          if (!mat) continue;
          for (const tKey of ['map', 'normalMap', 'roughnessMap', 'metalnessMap']) {
            if (mat[tKey]) {
              mat[tKey].anisotropy = maxAniso;
            }
          }
          if (isLace || mat.transparent) {
            // Alpha-cutout + depth offset eliminates Z-fighting & alpha-sort flickering on tea tables!
            mat.alphaTest = 0.35;
            mat.transparent = false;
            mat.depthWrite = true;
            mat.polygonOffset = true;
            mat.polygonOffsetFactor = -2;
            mat.polygonOffsetUnits = -2;
            mat.needsUpdate = true;
          }
        }
      }
    });

    for (const [prefix, neckNode] of neckMap.entries()) {
      const rNode = rootMap.get(prefix);
      if (rNode) {
        npcNecks.push({
          prefix,
          neckNode,
          rootNode: rNode,
          savedQuat: neckNode.quaternion.clone(),
          hadGlance: false,
          glanceTimer: 0,
          glanceDur: 0.9,
        });
      }
    }

    // Bind West & East Protocol Guards for physical perimeter pushback!
    for (const [tag, prefix] of [
      ['West', 'Char_13_Protocol_West'],
      ['East', 'Char_14_Protocol_East'],
    ]) {
      const rObj = root.getObjectByName(`${prefix}_Root`);
      if (rObj) {
        const neck = root.getObjectByName(`${prefix}_Neck`);
        const shR = root.getObjectByName(`${prefix}_Shoulder_R`);
        const elR = root.getObjectByName(`${prefix}_Elbow_R`);
        const shL = root.getObjectByName(`${prefix}_Shoulder_L`);
        const elL = root.getObjectByName(`${prefix}_Elbow_L`);
        guardRigs[tag] = {
          root: rObj,
          neck,
          shR,
          elR,
          shL,
          elL,
          savedRootQuat: rObj.quaternion.clone(),
          savedNeckQuat: neck ? neck.quaternion.clone() : new THREE.Quaternion(),
          baseShR: shR ? shR.quaternion.clone() : new THREE.Quaternion(),
          baseElR: elR ? elR.quaternion.clone() : new THREE.Quaternion(),
          baseShL: shL ? shL.quaternion.clone() : new THREE.Quaternion(),
          baseElL: elL ? elL.quaternion.clone() : new THREE.Quaternion(),
          wasModified: false,
          homePos: rObj.position.clone(),
          curPos: rObj.position.clone(),
          alertAmt: 0,
          stepPhase: 0,
        };
      }
    }

    // Collapse ~1400 meshes into a few hundred draw calls (static geometry baked per material)
    const mergeStats = mergeStaticMeshes(root, gltf.animations || []);
    focusableMeshes.length = 0;
    focusableMeshes.push(...mergeStats.raycastTargets);
    console.info(`[perf] meshes ${mergeStats.before} -> ${mergeStats.after} draw calls per pass`);

    scene.add(root);

    if (gltf.animations && gltf.animations.length > 0) {
      mixer = new THREE.AnimationMixer(root);
      for (const clip of gltf.animations) {
        const action = mixer.clipAction(clip);
        action.setLoop(THREE.LoopRepeat, Infinity);
        action.play();
      }
      mixer.setTime(2.0);
    }

    if (loaderRing) {
      loaderRing.classList.add('done');
      setTimeout(() => loaderRing.remove(), 380);
    }
  } catch (err) {
    console.error(err);
  }

  // =========================================================================
  // Collision, Sittable Armchairs & Posture Transitions
  // =========================================================================
  const spWorldVec = new THREE.Vector3();

  function isVipChairVacated() {
    if (!mixer) return false;
    const loopT = mixer.time % LOOP_DURATION;
    return loopT > 5.2 && loopT < 26.4;
  }

  function findNearbyAvailableChair() {
    if (player.seatedChair) return null;
    const lookX = -Math.sin(player.yaw);
    const lookZ = -Math.cos(player.yaw);
    let best = null;
    let bestScore = 2.05; // Generous proximity + gaze-assisted chair selection!
    for (const ch of SITTABLE_CHAIRS) {
      if (ch.vipOnlyWhenAway && !isVipChairVacated()) continue;
      const dx = ch.seatPos.x - player.pos.x;
      const dz = ch.seatPos.z - player.pos.z;
      const d = Math.hypot(dx, dz);
      if (d > 2.45) continue;
      const dot = d > 0.05 ? (dx * lookX + dz * lookZ) / d : 1.0;
      // Looking toward a chair extends effective reach up to ~2.4m; standing right beside works within ~1.95m
      const score = d - Math.max(0, dot) * 0.48;
      if (score < bestScore) {
        bestScore = score;
        best = ch;
      }
    }
    return best;
  }

  let satAtMs = 0;
  let freshMoveAfterSit = false;

  function togglePostureOrSit() {
    if (album.isOpen) return;
    sfx.playClothRustle();

    if (player.seatedChair) {
      // Stand up out of armchair!
      const exit = player.seatedChair.exitPos;
      player.seatedChair = null;
      freshMoveAfterSit = false;
      player.pos.x = exit.x;
      player.pos.z = exit.z;
      player.crouched = false;
      player.targetEyeY = STAND_EYE_Y;
      syncPostureUI();
      showDesktopToast('已起身');
      return;
    }

    const nearbyChair = findNearbyAvailableChair();
    if (nearbyChair) {
      player.seatedChair = nearbyChair;
      satAtMs = performance.now();
      freshMoveAfterSit = false;
      // Clear held WASD keys so walking into a chair while pressing C NEVER pops right back up!
      keys.clear();
      player.crouched = false;
      player.targetEyeY = nearbyChair.seatPos.y;
      // Gently turn toward the room center when sitting down
      player.yaw = nearbyChair.seatYaw;
      player.pitch = -0.02;
      syncPostureUI();
      showDesktopToast('已落座 · 按 C 或移动起身');
      return;
    }

    // Standard Stand <-> Photographer Crouch toggle anywhere in the hall!
    player.crouched = !player.crouched;
    player.targetEyeY = player.crouched ? CROUCH_EYE_Y : STAND_EYE_Y;
    syncPostureUI();
    showDesktopToast(player.crouched ? '蹲姿低机位 · 按 C 站起' : '站姿');
  }

  function syncPostureUI() {
    const crouchBtn = document.getElementById('btn-touch-crouch');
    crouchBtn?.classList.toggle('active', player.crouched || Boolean(player.seatedChair));
  }

  function resolveCollisions(nx, nz) {
    const PLAYER_R = 0.33;
    // Hall perimeter bounds
    let x = Math.max(-6.25, Math.min(6.25, nx));
    let z = Math.max(-3.78, Math.min(5.25, nz));

    // 7-panel standing screen barrier along z ~ -4.35, x in [-2.65, 2.65]
    if (z < -3.82 && Math.abs(x) < 2.75) {
      z = -3.82;
    }

    // Static furniture & NPC circle colliders
    for (const c of STATIC_COLLIDERS) {
      if (player.seatedChair && player.seatedChair.id === c.id) continue;
      const dx = x - c.x;
      const dz = z - c.z;
      const minD = PLAYER_R + c.r;
      const distSq = dx * dx + dz * dz;
      if (distSq < minD * minD && distSq > 1e-6) {
        const dist = Math.sqrt(distSq);
        const push = (minD - dist) / dist;
        x += dx * push;
        z += dz * push;
      }
    }

    // Dynamic Moving Central Speaker collider
    if (speakerRootNode) {
      speakerRootNode.getWorldPosition(spWorldVec);
      const dx = x - spWorldVec.x;
      const dz = z - spWorldVec.z;
      const minD = PLAYER_R + 0.48;
      const distSq = dx * dx + dz * dz;
      if (distSq < minD * minD && distSq > 1e-6) {
        const dist = Math.sqrt(distSq);
        const push = (minD - dist) / dist;
        x += dx * push;
        z += dz * push;
      }
    }

    return { x, z };
  }

  // =========================================================================
  // NPC Physical Body-Language Reactions (Zero Text!)
  //   1. Protocol Guard Intercept & Double-Palm Pushback when crossing VIP line
  //   2. Nearby Character Head-Glance when Camera Flash Fires Close Up
  // =========================================================================
  const tmpNpcPos = new THREE.Vector3();
  const tmpGuardTarget = new THREE.Vector3();

  function triggerNearbyFlashGlances() {
    const camDir = new THREE.Vector3();
    camera.getWorldDirection(camDir);

    for (const item of npcNecks) {
      item.rootNode.getWorldPosition(tmpNpcPos);
      const toNpc = tmpNpcPos.clone().sub(player.pos);
      toNpc.y = 0;
      const dist = toNpc.length();
      if (dist < 4.6 && dist > 0.2) {
        toNpc.normalize();
        const inCone = toNpc.dot(new THREE.Vector3(camDir.x, 0, camDir.z).normalize());
        if (inCone > 0.25) {
          item.glanceTimer = item.glanceDur;
        }
      }
    }
  }

  const AXIS_X = new THREE.Vector3(1, 0, 0);
  const AXIS_Y = new THREE.Vector3(0, 1, 0);
  const tmpGlanceQuat = new THREE.Quaternion();
  const tmpYawQuat = new THREE.Quaternion();
  const tmpShQuat = new THREE.Quaternion();
  const tmpElQuat = new THREE.Quaternion();

  function updateNpcReactions(dt) {
    // 1. Evict player politely from Central Speaker's VIP_Left chair when he walks back (t > 26.2s)!
    if (player.seatedChair && player.seatedChair.id === 'VIP_Left' && !isVipChairVacated()) {
      togglePostureOrSit();
    }

    // Check if player is intruding inside VIP horseshoe zone or crowding Central Speaker
    let spDist = 99;
    if (speakerRootNode) {
      speakerRootNode.getWorldPosition(spWorldVec);
      spDist = Math.hypot(player.pos.x - spWorldVec.x, player.pos.z - spWorldVec.z);
    }
    const inVipHorseshoe =
      !player.seatedChair &&
      ((player.pos.z < -1.52 && Math.abs(player.pos.x) < 2.15) || spDist < 1.08);

    const activeSide = player.pos.x <= 0 ? 'West' : 'East';
    for (const [side, g] of Object.entries(guardRigs)) {
      if (!g) continue;
      const shouldIntercept = inVipHorseshoe && side === activeSide;
      g.alertAmt = THREE.MathUtils.lerp(g.alertAmt, shouldIntercept ? 1.0 : 0.0, Math.min(1, dt * 5.5));

      if (shouldIntercept) {
        // Guard steps to a spot 0.95m between player and VIP center, facing player!
        const dirFromVip = new THREE.Vector3(player.pos.x, 0, player.pos.z + 2.4).normalize();
        tmpGuardTarget.set(
          player.pos.x - dirFromVip.x * 0.92,
          g.homePos.y,
          player.pos.z - dirFromVip.z * 0.92
        );
        g.curPos.lerp(tmpGuardTarget, Math.min(1, dt * 3.8));
        g.stepPhase += dt * 9.0;

        // Gentle physical pushback nudging player back toward polite press line!
        if (Math.hypot(g.curPos.x - player.pos.x, g.curPos.z - player.pos.z) < 1.28) {
          const pushStep = dt * 1.45;
          const pushed = resolveCollisions(player.pos.x + dirFromVip.x * pushStep, player.pos.z + dirFromVip.z * pushStep);
          player.pos.x = pushed.x;
          player.pos.z = pushed.z;
        }
      } else {
        g.curPos.lerp(g.homePos, Math.min(1, dt * 2.4));
      }

      if (g.alertAmt > 0.002) {
        const a = g.alertAmt;
        g.savedRootQuat.copy(g.root.quaternion);
        if (g.neck) g.savedNeckQuat.copy(g.neck.quaternion);
        if (g.shR) g.baseShR.copy(g.shR.quaternion);
        if (g.elR) g.baseElR.copy(g.elR.quaternion);
        if (g.shL) g.baseShL.copy(g.shL.quaternion);
        if (g.elL) g.baseElL.copy(g.elL.quaternion);
        g.wasModified = true;

        g.root.position.copy(g.curPos);
        const dx = player.pos.x - g.curPos.x;
        const dz = player.pos.z - g.curPos.z;
        tmpYawQuat.setFromAxisAngle(AXIS_Y, Math.atan2(dx, dz));
        g.root.quaternion.slerpQuaternions(g.savedRootQuat, tmpYawQuat, a);

        // Polite chest-level double-palm "please step back" gesture + bounded horizontal head-shake
        tmpShQuat.setFromAxisAngle(AXIS_X, -0.72 * a);
        tmpElQuat.setFromAxisAngle(AXIS_X, -0.42 * a);
        if (g.shR) g.shR.quaternion.copy(g.baseShR).multiply(tmpShQuat);
        if (g.elR) g.elR.quaternion.copy(g.baseElR).multiply(tmpElQuat);
        if (g.shL) g.shL.quaternion.copy(g.baseShL).multiply(tmpShQuat);
        if (g.elL) g.elL.quaternion.copy(g.baseElL).multiply(tmpElQuat);
        if (g.neck) {
          const shake = Math.sin(performance.now() * 0.009) * 0.16 * a;
          tmpGlanceQuat.setFromAxisAngle(AXIS_Y, shake);
          g.neck.quaternion.copy(g.savedNeckQuat).multiply(tmpGlanceQuat);
        }
      }
    }

    // 2. Bounded Pure-Quaternion Flash-Startle Horizontal Glance (restored pre-mixer every frame -> zero drift!)
    for (const item of npcNecks) {
      if (item.glanceTimer <= 0) continue;
      item.glanceTimer = Math.max(0, item.glanceTimer - dt);
      if (item.glanceTimer <= 0) continue;
      const u = item.glanceTimer / item.glanceDur;
      const env = Math.sin(u * Math.PI);
      item.savedQuat.copy(item.neckNode.quaternion);
      item.hadGlance = true;
      tmpGlanceQuat.setFromAxisAngle(AXIS_Y, 0.20 * env);
      item.neckNode.quaternion.multiply(tmpGlanceQuat);
    }
  }

  // =========================================================================
  // Photograph Rendering & Capture (Full AgX + sRGB Direct Framebuffer 3:2 Crop)
  // =========================================================================
  const photoSceneCam = new THREE.PerspectiveCamera(40, 1.5, 0.10, 65);
  photoSceneCam.rotation.order = 'YXZ';
  const offscreenCanvas = document.createElement('canvas');
  offscreenCanvas.width = 1500;
  offscreenCanvas.height = 1000;
  const offCtx = offscreenCanvas.getContext('2d');

  function triggerShutter() {
    if (album.isOpen) return;
    const now = performance.now();
    if (now - lastShutterMs < 280) return; // Realistic SLR wind/flash recycle cadence
    lastShutterMs = now;

    const usingOVF = adsBlend > 0.65;
    const shotFocal = usingOVF ? focalMm : 35;

    sfx.playShutter(flashEnabled);
    shutterRecoil = 1.0;

    // Match viewport aspect during render, then center-crop cleanly to 3:2 SLR frame!
    const srcCanvas = renderer.domElement;
    photoSceneCam.aspect = srcCanvas.width / Math.max(1, srcCanvas.height);

    if (usingOVF) {
      photoSceneCam.position.copy(camera.position);
      photoSceneCam.rotation.set(player.pitch, player.yaw, 0, 'YXZ');
      photoSceneCam.fov = focalToFov(shotFocal);
    } else {
      // Waist/Chest Hip-Fire Candid Shot ("腰平盲拍")
      photoSceneCam.position.copy(camera.position);
      photoSceneCam.position.y -= 0.22;
      const candidRoll = (Math.random() - 0.5) * 0.045;
      photoSceneCam.rotation.set(player.pitch + 0.02, player.yaw, candidRoll, 'YXZ');
      photoSceneCam.fov = focalToFov(35);
    }
    photoSceneCam.updateProjectionMatrix();
    photoSceneCam.updateMatrixWorld(true);

    // Measure exact center split-prism focus distance for this shot
    let shotFocusDist = focusDistM;
    if (focusableMeshes.length > 0) {
      afRaycaster.setFromCamera(centerNdc, photoSceneCam);
      const hits = afRaycaster.intersectObjects(focusableMeshes, false);
      if (hits.length > 0) {
        shotFocusDist = Math.max(0.5, Math.min(25, hits[0].distance));
        focusDistM = shotFocusDist;
        smoothFocusDistM = shotFocusDist;
      }
    }

    // Balanced realistic 6000K hot-shoe speedlight fill (never blowing out highlights!)
    if (flashEnabled) {
      playerFlashSpot.intensity = 8.5;
      playerFlashFill.intensity = 3.2;
      playerFlashDecay = 1.0;
      camRig.flashDiffuserMat.emissiveIntensity = 3.5;
      triggerNearbyFlashGlances();
    }

    // Photo needs fully up-to-date shadows (incl. the speedlight's own shadow)
    playerFlashSpot.shadow.needsUpdate = true;
    for (const l of throttledShadowLights) l.shadow.needsUpdate = true;

    // Hide first-person viewmodel & render through optical BokehPass + AgX + sRGB composer!
    const prevVis = camRig.group.visible;
    camRig.group.visible = false;
    renderPass.camera = photoSceneCam;
    bokehPass.camera = photoSceneCam;
    bokehPass.enabled = fStop < 15.5;
    if (bokehPass.enabled) {
      const bk = calcBokehUniforms(shotFocal, fStop, shotFocusDist);
      bokehPass.uniforms.focus.value = shotFocusDist;
      bokehPass.uniforms.aperture.value = bk.aperture;
      bokehPass.uniforms.maxblur.value = bk.maxblur;
    }
    composer.render(0.016);
    renderPass.camera = camera;
    bokehPass.camera = camera;
    camRig.group.visible = prevVis;

    // Center-crop to 3:2 full-frame SLR aspect ratio at 1500x1000
    const sw = srcCanvas.width;
    const sh = srcCanvas.height;
    const targetAspect = 1.5;
    let cw = sw;
    let ch = sh;
    let cx = 0;
    let cy = 0;
    if (sw / sh > targetAspect) {
      cw = Math.round(sh * targetAspect);
      cx = Math.round((sw - cw) * 0.5);
    } else {
      ch = Math.round(sw / targetAspect);
      cy = Math.round((sh - ch) * 0.5);
    }
    offCtx.drawImage(srcCanvas, cx, cy, cw, ch, 0, 0, 1500, 1000);

    // Subtle analog 35mm optical corner vignette
    const grad = offCtx.createRadialGradient(750, 500, 440, 750, 500, 920);
    grad.addColorStop(0, 'rgba(0,0,0,0)');
    grad.addColorStop(1, 'rgba(0,0,0,0.24)');
    offCtx.fillStyle = grad;
    offCtx.fillRect(0, 0, 1500, 1000);

    const dataUrl = offscreenCanvas.toDataURL('image/jpeg', 0.93);
    album.addPhoto({ dataUrl, focalMm: shotFocal, fStop, distM: shotFocusDist });

    // Restore current player viewport frame immediately so zero flicker
    if (usingOVF) {
      bokehPass.enabled = fStop < 15.5;
      if (bokehPass.enabled) {
        const bkLive = calcBokehUniforms(focalMm, fStop, smoothFocusDistM);
        bokehPass.uniforms.focus.value = smoothFocusDistM;
        bokehPass.uniforms.aperture.value = bkLive.aperture;
        bokehPass.uniforms.maxblur.value = bkLive.maxblur;
      }
      composer.render(0);
    } else {
      renderer.render(scene, camera);
    }

    // Visual SLR Mirror Blackout (OVF) or Speedlight Room Pulse (Hip)
    if (usingOVF && mirrorBlackout) {
      mirrorBlackout.style.opacity = '0.96';
      setTimeout(() => { mirrorBlackout.style.opacity = '0'; }, 58);
    } else if (flashEnabled && flashScreenPulse) {
      flashScreenPulse.style.opacity = '0.28';
      requestAnimationFrame(() => { flashScreenPulse.style.opacity = '0'; });
    }
  }

  // =========================================================================
  // Input Handling: Desktop (Pure FPS Mouse Look + Retro Field Manual)
  //                 & Mobile (Translucent Joystick + Touch Look + Action Pad)
  // =========================================================================
  const keys = new Set();
  const isMobileDevice =
    window.matchMedia('(pointer: coarse) and (hover: none)').matches ||
    /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
  document.body.classList.add(isMobileDevice ? 'mobile-mode' : 'desktop-mode');

  const desktopGuideEl = document.getElementById('desktop-guide');
  const mobileEntryGateEl = document.getElementById('mobile-entry-gate');
  const desktopToastEl = document.getElementById('desktop-toast');
  let desktopFpsActive = false;
  let toastTimer = null;

  function showDesktopToast(text) {
    if (isMobileDevice || !desktopToastEl || introState !== 'done') return;
    desktopToastEl.textContent = text;
    desktopToastEl.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => desktopToastEl.classList.remove('show'), 950);
  }

  function setDesktopGuideVisible(visible) {
    if (isMobileDevice || !desktopGuideEl) return;
    desktopGuideEl.classList.toggle('hidden', !visible);
    desktopFpsActive = !visible && !album.isOpen;
    document.body.classList.toggle('fps-active', desktopFpsActive);
  }

  function startIntroWalkIn() {
    if (introState !== 'waiting') return;
    introState = 'walking_in';
    introTime = 0.0;
    doorOpenPlayed = false;
    doorClosePlayed = false;
    mobileEntryGateEl?.classList.add('hidden');
    if (mixer) mixer.setTime(0.2);
    sfx.playFootstep(true, true);
  }

  // Show nostalgic Field Manual on Desktop opening, or Tap Gate on Mobile!
  if (!isMobileDevice) {
    setDesktopGuideVisible(true);
    onAlbumClosedHook = () => enterDesktopHall();
  } else {
    mobileEntryGateEl?.classList.remove('hidden');
    mobileEntryGateEl?.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      e.stopPropagation();
      startIntroWalkIn();
    });
  }

  let touchUiVisible = isMobileDevice;

  function syncTouchVisibility() {
    touchControlsEl?.classList.toggle('hidden', !touchUiVisible);
    document.getElementById('btn-toggle-touch')?.classList.toggle('active-gold', touchUiVisible);
  }
  syncTouchVisibility();

  function syncAimUI() {
    document.getElementById('btn-touch-aim')?.classList.toggle('active', isAiming);
  }

  function setFocalLength(nextMm) {
    const clamped = Math.max(24, Math.min(135, nextMm));
    if (Math.floor(clamped / 8) !== Math.floor(targetFocalMm / 8)) {
      sfx.playZoomTick();
    }
    targetFocalMm = clamped;
    syncZoomSliderThumb();
  }

  function syncZoomSliderThumb() {
    const thumb = document.getElementById('touch-zoom-thumb');
    if (!thumb) return;
    // Top = 135mm (y=12px), Bottom = 24mm (y=108px)
    const u = (targetFocalMm - 24) / (135 - 24);
    const topPx = 108 - u * 96;
    thumb.style.top = `${topPx.toFixed(1)}px`;
  }
  syncZoomSliderThumb();

  const formatFStop = (val) => (val < 10 ? val.toFixed(1) : String(Math.round(val)));

  function syncApertureSliderThumb() {
    const thumb = document.getElementById('touch-aperture-thumb');
    if (!thumb) return;
    // Top = f/1.4 (idx 0 -> y=12px, max bokeh), Bottom = f/16 (idx 8 -> y=108px, deep focus)
    const u = fStopIdx / Math.max(1, F_STOPS.length - 1);
    const topPx = 12 + u * 96;
    thumb.style.top = `${topPx.toFixed(1)}px`;
  }

  function setApertureIndex(nextIdx, silent = false) {
    const clamped = Math.max(0, Math.min(F_STOPS.length - 1, Math.round(nextIdx)));
    if (clamped !== fStopIdx && !silent) {
      sfx.playApertureClick();
    }
    fStopIdx = clamped;
    fStop = F_STOPS[fStopIdx];
    const fStr = formatFStop(fStop);
    if (hudApertureVal) hudApertureVal.textContent = fStr;
    if (ovfApertureEl) ovfApertureEl.textContent = `F${fStr}`;
    if (ovfShutterEl) ovfShutterEl.textContent = String(AV_SHUTTERS[fStopIdx]);
    syncApertureSliderThumb();
  }
  setApertureIndex(fStopIdx, true);

  // Top-right Aperture Ring Button (Click to cycle, or Scroll over button to step stops!)
  const btnAperture = document.getElementById('btn-cycle-aperture');
  btnAperture?.addEventListener('click', (e) => {
    e.stopPropagation();
    const step = e.shiftKey ? -1 : 1;
    setApertureIndex((fStopIdx + step + F_STOPS.length) % F_STOPS.length);
  });
  btnAperture?.addEventListener('wheel', (e) => {
    e.preventDefault();
    e.stopPropagation();
    setApertureIndex(fStopIdx + (e.deltaY > 0 ? 1 : -1));
  }, { passive: false });

  // Top-right Icon Buttons
  document.getElementById('btn-toggle-touch')?.addEventListener('click', (e) => {
    e.stopPropagation();
    touchUiVisible = !touchUiVisible;
    syncTouchVisibility();
  });

  document.getElementById('btn-toggle-flash')?.addEventListener('click', (e) => {
    e.stopPropagation();
    flashEnabled = !flashEnabled;
    document.getElementById('btn-toggle-flash')?.classList.toggle('active-gold', flashEnabled);
    if (ovfFlashLed) ovfFlashLed.style.opacity = flashEnabled ? '1' : '0.18';
  });

  document.getElementById('btn-toggle-sound')?.addEventListener('click', (e) => {
    e.stopPropagation();
    const muted = sfx.toggleMute();
    document.getElementById('btn-toggle-sound')?.classList.toggle('active-gold', !muted);
    document.getElementById('icon-sound-on')?.classList.toggle('hidden', muted);
    document.getElementById('icon-sound-off')?.classList.toggle('hidden', !muted);
  });

  seatHintBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePostureOrSit();
  });

  // Desktop Opening Guide Click -> Fade Out Guide, Lock Pointer & Trigger Forced Walk-In!
  function enterDesktopHall() {
    if (isMobileDevice || album.isOpen) return;
    setDesktopGuideVisible(false);
    hoverMouseInit = false;
    if (introState === 'waiting') {
      startIntroWalkIn();
    }
    try {
      const req = renderer.domElement.requestPointerLock?.();
      if (req && typeof req.catch === 'function') req.catch(() => {});
    } catch (_) {}
  }

  desktopGuideEl?.addEventListener('mousedown', (e) => {
    e.preventDefault();
    e.stopPropagation();
    enterDesktopHall();
  });

  let wasPointerLocked = false;
  document.addEventListener('pointerlockchange', () => {
    const locked = document.pointerLockElement === renderer.domElement;
    if (locked) {
      wasPointerLocked = true;
      setDesktopGuideVisible(false);
    } else if (wasPointerLocked && !isMobileDevice && !album.isOpen) {
      // Pressing Esc exits PointerLock -> surface the Field Manual cleanly
      isAiming = false;
      syncAimUI();
      setDesktopGuideVisible(true);
    }
  });

  // Desktop Mouse Events
  renderer.domElement.addEventListener('contextmenu', (e) => e.preventDefault());

  let hoverMouseInit = false;
  let lastHoverX = 0;
  let lastHoverY = 0;

  renderer.domElement.addEventListener('mousedown', (e) => {
    if (album.isOpen) return;

    if (introState !== 'done') {
      if (!isMobileDevice && introState === 'waiting') {
        enterDesktopHall();
      }
      return;
    }

    if (e.button === 2) {
      // Right-Click Held -> Bring Eye to Viewfinder!
      e.preventDefault();
      if (!desktopFpsActive && !isMobileDevice) {
        enterDesktopHall();
      }
      if (!isAiming) sfx.playClothRustle();
      isAiming = true;
      syncAimUI();
      return;
    }

    if (e.button === 0 && !isMobileDevice) {
      if (!desktopFpsActive) {
        enterDesktopHall();
        return;
      }
      if (document.pointerLockElement !== renderer.domElement) {
        try {
          const req = renderer.domElement.requestPointerLock?.();
          if (req && typeof req.catch === 'function') req.catch(() => {});
        } catch (_) {}
      }
      triggerShutter();
    }
  });

  window.addEventListener('mouseup', (e) => {
    if (e.button === 2 && !touchAimToggled) {
      if (isAiming) sfx.playClothRustle();
      isAiming = false;
      syncAimUI();
    }
  });

  window.addEventListener('mousemove', (e) => {
    if (album.isOpen || isMobileDevice || !desktopFpsActive || introState !== 'done') return;
    const zoomScale = camera.fov / BASE_HIP_FOV;
    const sens = 0.0021 * zoomScale;

    if (document.pointerLockElement === renderer.domElement) {
      player.yaw -= e.movementX * sens;
      player.pitch = THREE.MathUtils.clamp(player.pitch - e.movementY * sens, -1.38, 1.38);
      player.swayX = THREE.MathUtils.clamp(player.swayX - e.movementX * 0.00035, -0.025, 0.025);
      player.swayY = THREE.MathUtils.clamp(player.swayY + e.movementY * 0.00035, -0.025, 0.025);
    } else {
      // Fallback smooth mouse-steer if browser restricts PointerLock!
      if (!hoverMouseInit) {
        hoverMouseInit = true;
        lastHoverX = e.clientX;
        lastHoverY = e.clientY;
        return;
      }
      const dx = typeof e.movementX === 'number' && e.movementX !== 0 ? e.movementX : (e.clientX - lastHoverX);
      const dy = typeof e.movementY === 'number' && e.movementY !== 0 ? e.movementY : (e.clientY - lastHoverY);
      lastHoverX = e.clientX;
      lastHoverY = e.clientY;
      player.yaw -= dx * sens * 1.15;
      player.pitch = THREE.MathUtils.clamp(player.pitch - dy * sens * 1.15, -1.38, 1.38);
    }
  });

  renderer.domElement.addEventListener('wheel', (e) => {
    if (album.isOpen) return;
    e.preventDefault();
    // Shift+Wheel or Alt+Wheel turns the Aperture Ring (f/1.4 <-> f/16); plain Wheel zooms focal length!
    if (e.shiftKey || e.altKey) {
      setApertureIndex(fStopIdx + (e.deltaY > 0 ? 1 : -1));
      if (adsBlend < 0.7) showDesktopToast(`f/${formatFStop(fStop)}`);
    } else {
      setFocalLength(targetFocalMm - e.deltaY * 0.065);
    }
  }, { passive: false });

  // Keyboard Controls (supports both physical e.code and fallback e.key for IME / international layouts)
  window.addEventListener('keydown', (e) => {
    const k = (e.key || '').toLowerCase();

    if (introState === 'waiting') {
      if (['Enter', 'Space', 'KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp'].includes(e.code) || ['w', 'a', 's', 'd'].includes(k)) {
        e.preventDefault();
        if (!isMobileDevice) enterDesktopHall();
        else startIntroWalkIn();
      }
      return;
    }
    if (introState === 'walking_in') {
      return;
    }

    if (e.code === 'Tab' || e.code === 'KeyG' || k === 'g') {
      if (e.repeat) return;
      e.preventDefault();
      const willClose = album.isOpen;
      album.toggle();
      if (willClose && !isMobileDevice) {
        enterDesktopHall();
      } else if (!willClose) {
        document.body.classList.remove('fps-active');
      }
      return;
    }
    if (e.code === 'Escape' && album.isOpen) {
      album.close();
      if (!isMobileDevice) setDesktopGuideVisible(true);
      return;
    }
    if (album.isOpen) return;

    if (e.code === 'KeyH' || k === 'h') {
      if (e.repeat) return;
      const guideOpen = desktopGuideEl && !desktopGuideEl.classList.contains('hidden');
      if (guideOpen) {
        enterDesktopHall();
      } else {
        if (document.pointerLockElement) document.exitPointerLock?.();
        setDesktopGuideVisible(true);
      }
      return;
    }
    if (e.code === 'Escape' && !isMobileDevice && !document.pointerLockElement) {
      if (e.repeat) return;
      const guideOpen = desktopGuideEl && !desktopGuideEl.classList.contains('hidden');
      setDesktopGuideVisible(!guideOpen);
      return;
    }
    if (!isMobileDevice && !desktopFpsActive && (['KeyW', 'KeyA', 'KeyS', 'KeyD', 'KeyC', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code) || ['w', 'a', 's', 'd', 'c'].includes(k))) {
      setDesktopGuideVisible(false);
    }

    if (e.code === 'KeyQ' || e.code === 'BracketLeft' || k === 'q' || k === '[') {
      setApertureIndex(fStopIdx - 1);
      if (adsBlend < 0.7) showDesktopToast(`f/${formatFStop(fStop)}`);
      return;
    }
    if (e.code === 'KeyE' || e.code === 'BracketRight' || k === 'e' || k === ']') {
      setApertureIndex(fStopIdx + 1);
      if (adsBlend < 0.7) showDesktopToast(`f/${formatFStop(fStop)}`);
      return;
    }
    if (e.code === 'KeyC' || k === 'c') {
      if (e.repeat) return;
      togglePostureOrSit();
      return;
    }
    if (e.code === 'Space' && player.seatedChair) {
      if (e.repeat) return;
      e.preventDefault();
      togglePostureOrSit();
      return;
    }
    if (e.code === 'KeyF' || k === 'f') {
      if (e.repeat) return;
      flashEnabled = !flashEnabled;
      document.getElementById('btn-toggle-flash')?.classList.toggle('active-gold', flashEnabled);
      if (ovfFlashLed) ovfFlashLed.style.opacity = flashEnabled ? '1' : '0.18';
      showDesktopToast(flashEnabled ? '⚡ ON' : '⚡ OFF');
      return;
    }
    if (e.code === 'KeyM' || k === 'm') {
      if (e.repeat) return;
      const muted = sfx.toggleMute();
      document.getElementById('btn-toggle-sound')?.classList.toggle('active-gold', !muted);
      document.getElementById('icon-sound-on')?.classList.toggle('hidden', muted);
      document.getElementById('icon-sound-off')?.classList.toggle('hidden', !muted);
      showDesktopToast(muted ? 'MUTE' : 'SOUND ON');
      return;
    }

    const moveCode =
      e.code ||
      (k === 'w' ? 'KeyW' : k === 's' ? 'KeyS' : k === 'a' ? 'KeyA' : k === 'd' ? 'KeyD' : '');
    if (moveCode) {
      if (!e.repeat && player.seatedChair && performance.now() - satAtMs > 550 && ['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(moveCode)) {
        freshMoveAfterSit = true;
      }
      keys.add(moveCode);
    }
  });
  window.addEventListener('keyup', (e) => {
    keys.delete(e.code);
    const k = (e.key || '').toLowerCase();
    if (k === 'w') keys.delete('KeyW');
    if (k === 's') keys.delete('KeyS');
    if (k === 'a') keys.delete('KeyA');
    if (k === 'd') keys.delete('KeyD');
  });
  window.addEventListener('blur', () => {
    keys.clear();
    if (!touchAimToggled) {
      isAiming = false;
      syncAimUI();
    }
  });

  // =========================================================================
  // Multi-Touch Mobile Controls (Left Virtual Joystick + Right Look + Buttons)
  // =========================================================================
  let joyTouchId = null;
  let joyVec = { x: 0, y: 0 }; // x: right [-1..1], y: forward [-1..1]
  const joyZone = document.getElementById('touch-joystick-zone');
  const joyKnob = document.getElementById('touch-joystick-knob');

  function updateJoystickFromTouch(touch) {
    const rect = joyZone.getBoundingClientRect();
    const cx = rect.left + rect.width * 0.5;
    const cy = rect.top + rect.height * 0.5;
    const maxR = rect.width * 0.38;
    let dx = touch.clientX - cx;
    let dy = touch.clientY - cy;
    const d = Math.hypot(dx, dy);
    if (d > maxR) {
      dx = (dx / d) * maxR;
      dy = (dy / d) * maxR;
    }
    joyKnob.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px)`;
    joyVec.x = dx / maxR;
    joyVec.y = -dy / maxR; // Up on screen = +1 forward
  }

  joyZone?.addEventListener('touchstart', (e) => {
    e.stopPropagation();
    const t = e.changedTouches[0];
    joyTouchId = t.identifier;
    updateJoystickFromTouch(t);
  }, { passive: false });

  joyZone?.addEventListener('touchmove', (e) => {
    e.stopPropagation();
    e.preventDefault();
    for (const t of e.changedTouches) {
      if (t.identifier === joyTouchId) updateJoystickFromTouch(t);
    }
  }, { passive: false });

  const resetJoy = (e) => {
    for (const t of e.changedTouches) {
      if (t.identifier === joyTouchId) {
        joyTouchId = null;
        joyVec.x = 0;
        joyVec.y = 0;
        if (joyKnob) joyKnob.style.transform = 'translate(0px, 0px)';
      }
    }
  };
  joyZone?.addEventListener('touchend', resetJoy);
  joyZone?.addEventListener('touchcancel', resetJoy);

  // Right-Half Screen Touch-Look
  let lookTouchId = null;
  let lastTouchX = 0;
  let lastTouchY = 0;

  renderer.domElement.addEventListener('touchstart', (e) => {
    if (album.isOpen) return;
    for (const t of e.changedTouches) {
      if (lookTouchId === null) {
        lookTouchId = t.identifier;
        lastTouchX = t.clientX;
        lastTouchY = t.clientY;
      }
    }
  }, { passive: true });

  renderer.domElement.addEventListener('touchmove', (e) => {
    if (album.isOpen) return;
    e.preventDefault();
    const zoomScale = camera.fov / BASE_HIP_FOV;
    const sens = 0.0038 * zoomScale;
    for (const t of e.changedTouches) {
      if (t.identifier === lookTouchId) {
        const dx = t.clientX - lastTouchX;
        const dy = t.clientY - lastTouchY;
        lastTouchX = t.clientX;
        lastTouchY = t.clientY;
        player.yaw -= dx * sens;
        player.pitch = THREE.MathUtils.clamp(player.pitch - dy * sens, -1.38, 1.38);
      }
    }
  }, { passive: false });

  const endLookTouch = (e) => {
    for (const t of e.changedTouches) {
      if (t.identifier === lookTouchId) lookTouchId = null;
    }
  };
  renderer.domElement.addEventListener('touchend', endLookTouch);
  renderer.domElement.addEventListener('touchcancel', endLookTouch);

  // Mobile Action Buttons
  let touchAimToggled = false;
  document.getElementById('btn-touch-aim')?.addEventListener('click', (e) => {
    e.stopPropagation();
    sfx.playClothRustle();
    isAiming = !isAiming;
    touchAimToggled = isAiming;
    syncAimUI();
  });

  document.getElementById('btn-touch-shutter')?.addEventListener('click', (e) => {
    e.stopPropagation();
    triggerShutter();
  });

  document.getElementById('btn-touch-crouch')?.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePostureOrSit();
  });

  // Mobile Vertical Optical Zoom Slider
  const zoomTrack = document.getElementById('touch-zoom-track');
  let draggingZoom = false;
  const updateZoomFromClientY = (clientY) => {
    const rect = zoomTrack.getBoundingClientRect();
    const pad = 16;
    const u = 1.0 - THREE.MathUtils.clamp((clientY - (rect.top + pad)) / (rect.height - pad * 2), 0, 1);
    setFocalLength(24 + u * (135 - 24));
  };
  zoomTrack?.addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    draggingZoom = true;
    zoomTrack.setPointerCapture(e.pointerId);
    updateZoomFromClientY(e.clientY);
  });
  zoomTrack?.addEventListener('pointermove', (e) => {
    if (!draggingZoom) return;
    e.stopPropagation();
    updateZoomFromClientY(e.clientY);
  });
  zoomTrack?.addEventListener('pointerup', () => { draggingZoom = false; });

  // Mobile Vertical Aperture Ring Slider (Top = f/1.4 Max Bokeh, Bottom = f/16 Deep Focus)
  const apertureTrack = document.getElementById('touch-aperture-track');
  let draggingAperture = false;
  const updateApertureFromClientY = (clientY) => {
    const rect = apertureTrack.getBoundingClientRect();
    const pad = 16;
    const u = THREE.MathUtils.clamp((clientY - (rect.top + pad)) / (rect.height - pad * 2), 0, 1);
    setApertureIndex(Math.round(u * (F_STOPS.length - 1)));
  };
  apertureTrack?.addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    draggingAperture = true;
    apertureTrack.setPointerCapture(e.pointerId);
    updateApertureFromClientY(e.clientY);
  });
  apertureTrack?.addEventListener('pointermove', (e) => {
    if (!draggingAperture) return;
    e.stopPropagation();
    updateApertureFromClientY(e.clientY);
  });
  apertureTrack?.addEventListener('pointerup', () => { draggingAperture = false; });

  // =========================================================================
  // Resize & Main 60fps Game Loop
  // =========================================================================
  const onResize = () => {
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (w === 0 || h === 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    composer.setSize(w, h);
  };

  function applyPixelRatio(next) {
    dpr = next;
    renderer.setPixelRatio(dpr);
    composer.setPixelRatio(dpr);
    onResize();
  }
  window.addEventListener('resize', onResize);
  new ResizeObserver(onResize).observe(container);

  const afRaycaster = new THREE.Raycaster();
  const centerNdc = new THREE.Vector2(0, 0);
  const trackVec = new THREE.Vector3();
  const flashVec = new THREE.Vector3();

  let lastTime = performance.now();
  let afFrameCounter = 0;

  // Frame pacing: cap at 60fps (120/144Hz ProMotion/gaming displays otherwise double the GPU
  // load) and drop to ~24fps while the scene sits behind the Field Manual / album / entry gate.
  const ACTIVE_FRAME_MS = 1000 / 60;
  const IDLE_FRAME_MS = 1000 / 24;
  const SHADOW_INTERVAL_S = 1 / 30; // NPCs move slowly; 30Hz shadow refresh is visually identical
  let frameClock = 0;
  let shadowAccum = 0;

  function isSceneIdle() {
    if (album.isOpen) return true;
    if (introState === 'waiting') return true;
    if (!isMobileDevice && introState === 'done' && !desktopFpsActive) return true;
    return false;
  }

  function refreshShadows(dt) {
    shadowAccum += dt;
    if (shadowAccum >= SHADOW_INTERVAL_S) {
      shadowAccum %= SHADOW_INTERVAL_S;
      for (const l of throttledShadowLights) l.shadow.needsUpdate = true;
    }
    // Speedlight shadow only matters while the flash is actually lit
    if (playerFlashDecay > 0) playerFlashSpot.shadow.needsUpdate = true;
  }

  function animate(now) {
    requestAnimationFrame(animate);
    const idle = isSceneIdle();
    const frameMs = idle ? IDLE_FRAME_MS : ACTIVE_FRAME_MS;
    const sinceFrame = now - frameClock;
    if (sinceFrame < frameMs - 1.5) return;
    frameClock = sinceFrame > frameMs * 2 ? now : now - (sinceFrame % frameMs);

    const rawMs = now - lastTime;
    const dt = Math.min(rawMs / 1000, 0.08);
    lastTime = now;
    if (!idle && introState !== 'waiting') adaptiveRes.sample(rawMs);

    // 0. Restore any procedural quaternion offsets from last frame BEFORE mixer.update(dt)
    for (const item of npcNecks) {
      if (item.hadGlance) {
        item.neckNode.quaternion.copy(item.savedQuat);
        item.hadGlance = false;
      }
    }
    for (const g of Object.values(guardRigs)) {
      if (g && g.wasModified) {
        g.root.position.copy(g.homePos);
        g.root.quaternion.copy(g.savedRootQuat);
        if (g.neck) g.neck.quaternion.copy(g.savedNeckQuat);
        if (g.shR) g.shR.quaternion.copy(g.baseShR);
        if (g.elR) g.elR.quaternion.copy(g.baseElR);
        if (g.shL) g.shL.quaternion.copy(g.baseShL);
        if (g.elL) g.elL.quaternion.copy(g.baseElL);
        g.wasModified = false;
      }
    }

    // 1. Update 32s Scene Animation Loop & Dynamic Broadcast Lights
    if (mixer) {
      mixer.update(dt);

      if (speakerTorsoNode) {
        speakerTorsoNode.getWorldPosition(trackVec);
        trackVec.y += 0.32;
        engSpot1.target.position.lerp(trackVec, 0.18);
        engSpot2.target.position.lerp(trackVec, 0.14);
      }

      const loopT = mixer.time % LOOP_DURATION;
      let npcFlashI = 0.0;
      for (const ft of NPC_FLASH_TIMES) {
        const diff = loopT - ft;
        if (diff >= 0.0 && diff < 0.14) {
          npcFlashI = Math.max(npcFlashI, 26.0 * Math.exp(-diff * 28.0));
        }
      }
      npcSlrFlash.intensity = npcFlashI;
      if (npcFlashI > 0.1 && slrFlashNode) {
        slrFlashNode.getWorldPosition(flashVec);
        npcSlrFlash.position.copy(flashVec);
      }
    }

    // 2. Forced Opening Corridor Walk-In Cutscene OR Free Player Movement
    let walkSpeedFactor = 0;

    if (introState === 'waiting') {
      setEntryDoorsAngle(0.0);
      player.pos.set(0.0, STAND_EYE_Y, 8.45);
      player.yaw = 0.0;
      player.pitch = 0.01;
    } else if (introState === 'walking_in') {
      introTime += dt;
      const t = introTime;

      // A) Grand Rosewood Double Doors Swing Open (0.28s..1.58s) -> Hold Open -> Swing Shut Behind Player (3.45s..4.55s)
      if (t >= 0.28 && !doorOpenPlayed) {
        doorOpenPlayed = true;
        sfx.playDoorOpen();
      }
      let doorAngle = 0.0;
      if (t < 1.58) {
        doorAngle = 1.40 * smoothstep01((t - 0.28) / (1.58 - 0.28));
      } else if (t < 3.45) {
        doorAngle = 1.40;
      } else if (t < 4.55) {
        doorAngle = 1.40 * (1.0 - smoothstep01((t - 3.45) / (4.55 - 3.45)));
      } else {
        doorAngle = 0.0;
      }
      setEntryDoorsAngle(doorAngle);

      if (t >= 4.46 && !doorClosePlayed) {
        doorClosePlayed = true;
        sfx.playDoorClose();
      }

      // B) Player Walks Forward from Outer Corridor (z=8.45m) -> Across Brass Threshold (z=5.80m) -> Into Hall (z=2.65m)
      const uWalk = smootherstep01((t - 0.06) / 3.82);
      const nextZ = 8.45 + (2.65 - 8.45) * uWalk;
      const nextX = -0.06 * smoothstep01((t - 2.15) / 1.70);
      const stepDist = Math.hypot(nextX - player.pos.x, nextZ - player.pos.z);
      player.pos.x = nextX;
      player.pos.z = nextZ;

      if (t > 0.06 && t < 3.88) {
        walkSpeedFactor = Math.sin(Math.min(1, (t - 0.06) / 3.82) * Math.PI) * 0.85;
        player.walkBobPhase += stepDist * 4.2;
        player.stepAccum += stepDist;
        if (player.stepAccum > 0.72) {
          player.stepAccum = 0;
          const onBrassOrStone = Math.abs(player.pos.z - 5.80) < 0.42;
          sfx.playFootstep(!onBrassOrStone, false);
        }
      }

      // Subtle natural upward gaze as the crystal chandelier & 7-panel screen come into view, then settle
      const aweEnv = Math.sin(smoothstep01((t - 0.95) / 2.65) * Math.PI);
      player.pitch = 0.01 * (1 - uWalk) + (-0.02) * uWalk + 0.055 * aweEnv;
      player.yaw = 0.03 * smoothstep01((t - 2.2) / 1.6);

      if (t >= INTRO_DURATION) {
        setEntryDoorsAngle(0.0);
        introState = 'done';
        hoverMouseInit = false;
        document.body.classList.remove('intro-playing');
      }
    } else {
      let moveFwd = joyVec.y;
      let moveRight = joyVec.x;
      if (!album.isOpen) {
        if (keys.has('KeyW') || keys.has('ArrowUp')) moveFwd += 1;
        if (keys.has('KeyS') || keys.has('ArrowDown')) moveFwd -= 1;
        if (keys.has('KeyD') || keys.has('ArrowRight')) moveRight += 1;
        if (keys.has('KeyA') || keys.has('ArrowLeft')) moveRight -= 1;
      }

      // Pressing a fresh movement key (or mobile joystick after 0.6s) while seated smoothly stands up!
      if (
        player.seatedChair &&
        (freshMoveAfterSit || (Math.hypot(joyVec.x, joyVec.y) > 0.45 && performance.now() - satAtMs > 600))
      ) {
        togglePostureOrSit();
      }

      if (!player.seatedChair && Math.hypot(moveFwd, moveRight) > 0.04) {
        const mag = Math.min(1, Math.hypot(moveFwd, moveRight));
        const nxInput = moveRight / Math.max(1, Math.hypot(moveFwd, moveRight));
        const nyInput = moveFwd / Math.max(1, Math.hypot(moveFwd, moveRight));

        const sprinting = keys.has('ShiftLeft') || keys.has('ShiftRight');
        let baseSpeed = player.crouched ? 1.45 : (sprinting ? 3.65 : 2.55);
        if (isAiming) baseSpeed *= 0.62; // Steady deliberate walk when eye is at viewfinder

        // Camera forward on XZ is (-sin(yaw), -cos(yaw)); right is (cos(yaw), -sin(yaw))
        const sinY = Math.sin(player.yaw);
        const cosY = Math.cos(player.yaw);
        const vx = (-sinY * nyInput + cosY * nxInput) * baseSpeed;
        const vz = (-cosY * nyInput - sinY * nxInput) * baseSpeed;

        const resolved = resolveCollisions(player.pos.x + vx * dt, player.pos.z + vz * dt);
        const movedDist = Math.hypot(resolved.x - player.pos.x, resolved.z - player.pos.z);
        player.pos.x = resolved.x;
        player.pos.z = resolved.z;

        walkSpeedFactor = mag;
        player.walkBobPhase += movedDist * 3.9;
        player.stepAccum += movedDist;
        if (player.stepAccum > (player.crouched ? 0.62 : 0.76)) {
          player.stepAccum = 0;
          const onCarpet = Math.abs(player.pos.x) < 5.3 && Math.abs(player.pos.z + 0.15) < 4.3;
          sfx.playFootstep(onCarpet, player.crouched || isAiming);
        }
      } else if (player.seatedChair) {
        player.pos.x = THREE.MathUtils.lerp(player.pos.x, player.seatedChair.seatPos.x, Math.min(1, dt * 8));
        player.pos.z = THREE.MathUtils.lerp(player.pos.z, player.seatedChair.seatPos.z, Math.min(1, dt * 8));
      }
    }

    // Smooth Standing <-> Crouching <-> Armchair Sitting eye-height transition
    player.eyeY = THREE.MathUtils.lerp(player.eyeY, player.targetEyeY, Math.min(1, dt * 9.5));

    // Show/hide nearby empty armchair Sit Prompt Icon
    const availChair = introState === 'done' ? findNearbyAvailableChair() : null;
    if (seatHintBtn) {
      seatHintBtn.classList.toggle('hidden', !availChair || isAiming || album.isOpen);
    }

    // 3. Apply Additive NPC Reactions (Protocol Guard Intercept + Flash Startle)
    updateNpcReactions(dt);

    // 4. Update Eye-to-Viewfinder ADS Blend, Optical Zoom & Center Auto-Focus
    adsBlend = THREE.MathUtils.lerp(adsBlend, isAiming ? 1.0 : 0.0, Math.min(1, dt * 15.0));
    focalMm = THREE.MathUtils.lerp(focalMm, targetFocalMm, Math.min(1, dt * 14.0));
    shutterRecoil = Math.max(0, shutterRecoil - dt * 6.5);

    const targetFov = THREE.MathUtils.lerp(BASE_HIP_FOV, focalToFov(focalMm), adsBlend);
    if (Math.abs(camera.fov - targetFov) > 0.01) {
      camera.fov = targetFov;
      camera.updateProjectionMatrix();
    }

    // Subtle organic breathing + footstep head-bob
    const breathT = now * 0.0018;
    const bobAmp = (1.0 - adsBlend * 0.78) * walkSpeedFactor;
    const headBobY = Math.sin(player.walkBobPhase * 2.0) * 0.022 * bobAmp + Math.sin(breathT) * 0.004 * (1 - adsBlend * 0.6);
    const headBobX = Math.cos(player.walkBobPhase) * 0.014 * bobAmp;

    camera.position.set(player.pos.x + headBobX, player.eyeY + headBobY, player.pos.z);
    camera.rotation.set(player.pitch, player.yaw, 0, 'YXZ');

    // Update 3D First-Person SLR Camera Viewmodel (Chest Hip-Carry <-> Eye Lift)
    player.swayX = THREE.MathUtils.lerp(player.swayX, 0, Math.min(1, dt * 8));
    player.swayY = THREE.MathUtils.lerp(player.swayY, 0, Math.min(1, dt * 8));

    const hipX = 0.165 + player.swayX + Math.cos(player.walkBobPhase) * 0.010 * walkSpeedFactor;
    const hipY = -0.205 + player.swayY + Math.abs(Math.sin(player.walkBobPhase)) * -0.012 * walkSpeedFactor + Math.sin(breathT) * 0.003;
    const hipZ = -0.365 + shutterRecoil * 0.022;

    // Lift smoothly right up to the eye along (0, -0.054, -0.09)
    camRig.group.position.set(
      THREE.MathUtils.lerp(hipX, 0.0, adsBlend),
      THREE.MathUtils.lerp(hipY, -0.052, adsBlend) + shutterRecoil * 0.010,
      THREE.MathUtils.lerp(hipZ, -0.095, adsBlend)
    );
    camRig.group.rotation.set(
      THREE.MathUtils.lerp(0.06, 0.0, adsBlend) + shutterRecoil * 0.085,
      THREE.MathUtils.lerp(0.11, 0.0, adsBlend),
      THREE.MathUtils.lerp(-0.03, 0.0, adsBlend)
    );

    // Telescope the front white zoom barrel as focal length changes 24mm -> 135mm
    const zoomU = (focalMm - 24) / (135 - 24);
    camRig.zoomBarrel.position.z = -zoomU * 0.052;
    camRig.shutterBtn.position.y = 0.056 - shutterRecoil * 0.004;

    // Crossfade 3D Viewmodel into Full-Screen Optical Viewfinder Mask
    const inOVF = adsBlend > 0.78;
    camRig.group.visible = !inOVF;
    ovfOverlay?.classList.toggle('active', inOVF);
    if (hipReticle) hipReticle.style.opacity = inOVF ? '0' : '1';

    // Center Auto-Focus Distance Raycast & Green OVF LED Readout
    if (inOVF && (++afFrameCounter % 3 === 0) && focusableMeshes.length > 0) {
      afRaycaster.setFromCamera(centerNdc, camera);
      const hits = afRaycaster.intersectObjects(focusableMeshes, false);
      if (hits.length > 0) {
        focusDistM = Math.max(0.5, Math.min(25, hits[0].distance));
      }
      if (ovfFocalEl) ovfFocalEl.textContent = String(Math.round(focalMm));
      if (ovfApertureEl) ovfApertureEl.textContent = `F${formatFStop(fStop)}`;
      if (ovfShutterEl) ovfShutterEl.textContent = String(AV_SHUTTERS[fStopIdx]);
      if (ovfDistEl) ovfDistEl.textContent = focusDistM.toFixed(1);
    }
    smoothFocusDistM = THREE.MathUtils.lerp(smoothFocusDistM, focusDistM, Math.min(1, dt * 14.0));

    // Player Speedlight Flash Decay
    if (playerFlashDecay > 0) {
      playerFlashDecay = Math.max(0, playerFlashDecay - dt * 8.5);
      const curve = playerFlashDecay * playerFlashDecay;
      playerFlashSpot.intensity = 8.5 * curve;
      playerFlashFill.intensity = 3.2 * curve;
      camRig.flashDiffuserMat.emissiveIntensity = 0.15 + 3.5 * curve;
    }

    refreshShadows(dt);

    // Optical Depth-of-Field Bokeh when looking through SLR Viewfinder; crisp naked eye in Hip-Carry!
    if (inOVF) {
      bokehPass.enabled = fStop < 15.5;
      if (bokehPass.enabled) {
        const bk = calcBokehUniforms(focalMm, fStop, smoothFocusDistM);
        bokehPass.uniforms.focus.value = smoothFocusDistM;
        bokehPass.uniforms.aperture.value = bk.aperture;
        bokehPass.uniforms.maxblur.value = bk.maxblur;
      }
      composer.render(dt);
    } else {
      renderer.render(scene, camera);
    }
  }

  // Dev/QA testing hooks
  window.__pressSim = {
    getState: () => ({
      introState,
      doorAngleDeg: entryDoorL ? Number(THREE.MathUtils.radToDeg(entryDoorL.rotation.y).toFixed(1)) : 0,
      pos: player.pos.toArray().map((v) => Number(v.toFixed(2))),
      eyeY: Number(player.eyeY.toFixed(2)),
      isAiming,
      focalMm: Math.round(focalMm),
      fStop,
      focusDistM: Number(focusDistM.toFixed(2)),
      crouched: player.crouched,
      seated: player.seatedChair?.id || null,
      photosCount: album.photos.length,
    }),
    skipIntro: () => {
      setEntryDoorsAngle(0.0);
      introState = 'done';
      player.pos.set(-0.06, STAND_EYE_Y, 2.65);
      player.yaw = 0.03;
      player.pitch = -0.02;
      document.body.classList.remove('intro-playing');
      setDesktopGuideVisible(false);
    },
    setAim: (val) => { isAiming = val; syncAimUI(); },
    setFocal: (mm) => setFocalLength(mm),
    setFStop: (val) => {
      const idx = F_STOPS.findIndex((x) => Math.abs(x - val) < 0.05);
      if (idx >= 0) setApertureIndex(idx);
    },
    snap: () => triggerShutter(),
    moveTo: (x, z, yaw = player.yaw, pitch = player.pitch) => {
      player.pos.set(x, player.eyeY, z);
      player.yaw = yaw;
      player.pitch = pitch;
    },
    aimAtSpeaker: () => {
      if (!speakerTorsoNode) return;
      const wp = new THREE.Vector3();
      speakerTorsoNode.getWorldPosition(wp);
      wp.y += 0.25;
      const dx = wp.x - player.pos.x;
      const dz = wp.z - player.pos.z;
      const dy = wp.y - player.eyeY;
      player.yaw = Math.atan2(-dx, -dz);
      player.pitch = Math.atan2(dy, Math.hypot(dx, dz));
    },
  };

  requestAnimationFrame(animate);
});

import * as THREE from 'three';

/**
 * First-Person 3D SLR Camera Viewmodel (held at chest/hip when walking,
 * lifted smoothly up to the eye when pressing right-click / viewfinder button).
 */
export function createFirstPersonCameraRig() {
  const rig = new THREE.Group();

  const matBody = new THREE.MeshStandardMaterial({
    color: 0x18191c,
    roughness: 0.48,
    metalness: 0.35,
  });
  const matGrip = new THREE.MeshStandardMaterial({
    color: 0x101113,
    roughness: 0.82,
    metalness: 0.10,
  });
  const matTeleWhite = new THREE.MeshStandardMaterial({
    color: 0xdad6cb,
    roughness: 0.32,
    metalness: 0.22,
  });
  const matRedRing = new THREE.MeshStandardMaterial({
    color: 0xb81d24,
    roughness: 0.30,
    metalness: 0.45,
  });
  const matChrome = new THREE.MeshStandardMaterial({
    color: 0xb8bec6,
    roughness: 0.24,
    metalness: 0.88,
  });
  const matGlass = new THREE.MeshStandardMaterial({
    color: 0x102544,
    roughness: 0.06,
    metalness: 0.35,
  });
  const matFlashDiffuser = new THREE.MeshStandardMaterial({
    color: 0xf4f7fb,
    roughness: 0.22,
    emissive: 0xdbe9ff,
    emissiveIntensity: 0.15,
  });
  const matSkin = new THREE.MeshStandardMaterial({
    color: 0xb88467,
    roughness: 0.55,
  });
  const matSleeve = new THREE.MeshStandardMaterial({
    color: 0x26282e,
    roughness: 0.75,
  });

  // Main Magnesium SLR Body
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.152, 0.108, 0.074), matBody);
  rig.add(body);

  // Right-hand ergonomic rubberized grip + shutter button
  const grip = new THREE.Mesh(new THREE.BoxGeometry(0.044, 0.110, 0.088), matGrip);
  grip.position.set(0.064, -0.002, -0.012);
  rig.add(grip);

  const shutterBtn = new THREE.Mesh(new THREE.CylinderGeometry(0.009, 0.009, 0.010, 16), matChrome);
  shutterBtn.position.set(0.065, 0.056, -0.032);
  rig.add(shutterBtn);

  // Top Pentaprism housing + mode dials
  const prism = new THREE.Mesh(new THREE.BoxGeometry(0.068, 0.036, 0.072), matBody);
  prism.position.set(0.0, 0.066, 0.002);
  rig.add(prism);

  const dialL = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.017, 0.016, 20), matGrip);
  dialL.position.set(-0.052, 0.060, 0.004);
  rig.add(dialL);

  // Optical Viewfinder Eyepiece (facing +Z toward player's eye!)
  const eyepiece = new THREE.Mesh(new THREE.BoxGeometry(0.034, 0.026, 0.018), matGrip);
  eyepiece.position.set(0.0, 0.054, 0.043);
  rig.add(eyepiece);

  const eyeGlass = new THREE.Mesh(new THREE.PlaneGeometry(0.024, 0.017), matGlass);
  eyeGlass.position.set(0.0, 0.054, 0.053);
  rig.add(eyeGlass);

  // Back monochrome top/rear status LCD (pure subtle glow, zero letters)
  const rearScreen = new THREE.Mesh(
    new THREE.PlaneGeometry(0.068, 0.052),
    new THREE.MeshStandardMaterial({ color: 0x0d1216, roughness: 0.18, metalness: 0.2 })
  );
  rearScreen.position.set(-0.016, -0.006, 0.038);
  rig.add(rearScreen);

  // Hot-shoe Speedlight Flash Unit on top
  const flashFoot = new THREE.Mesh(new THREE.BoxGeometry(0.046, 0.056, 0.046), matBody);
  flashFoot.position.set(0.0, 0.110, 0.0);
  rig.add(flashFoot);

  const flashHead = new THREE.Mesh(new THREE.BoxGeometry(0.066, 0.044, 0.074), matBody);
  flashHead.position.set(0.0, 0.154, -0.010);
  rig.add(flashHead);

  const flashLens = new THREE.Mesh(new THREE.PlaneGeometry(0.056, 0.032), matFlashDiffuser);
  flashLens.position.set(0.0, 0.154, -0.048);
  flashLens.rotation.y = Math.PI;
  rig.add(flashLens);

  // Off-White L-Series 24-135mm Telephoto Zoom Barrel (extends forward along -Z on zoom!)
  const lensMount = new THREE.Mesh(new THREE.CylinderGeometry(0.039, 0.041, 0.022, 28), matChrome);
  lensMount.rotation.x = Math.PI * 0.5;
  lensMount.position.set(0.0, 0.0, -0.046);
  rig.add(lensMount);

  const lensOuter = new THREE.Mesh(new THREE.CylinderGeometry(0.040, 0.040, 0.125, 28), matTeleWhite);
  lensOuter.rotation.x = Math.PI * 0.5;
  lensOuter.position.set(0.0, 0.0, -0.116);
  rig.add(lensOuter);

  const zoomRing = new THREE.Mesh(new THREE.CylinderGeometry(0.0415, 0.0415, 0.042, 28), matGrip);
  zoomRing.rotation.x = Math.PI * 0.5;
  zoomRing.position.set(0.0, 0.0, -0.105);
  rig.add(zoomRing);

  // Telescoping front barrel group
  const zoomBarrel = new THREE.Group();
  rig.add(zoomBarrel);

  const innerBarrel = new THREE.Mesh(new THREE.CylinderGeometry(0.038, 0.038, 0.085, 28), matTeleWhite);
  innerBarrel.rotation.x = Math.PI * 0.5;
  innerBarrel.position.set(0.0, 0.0, -0.195);
  zoomBarrel.add(innerBarrel);

  const redRing = new THREE.Mesh(new THREE.CylinderGeometry(0.0392, 0.0392, 0.006, 28), matRedRing);
  redRing.rotation.x = Math.PI * 0.5;
  redRing.position.set(0.0, 0.0, -0.228);
  zoomBarrel.add(redRing);

  const hood = new THREE.Mesh(new THREE.CylinderGeometry(0.046, 0.040, 0.042, 28, 1, true), matGrip);
  hood.rotation.x = Math.PI * 0.5;
  hood.position.set(0.0, 0.0, -0.252);
  hood.material.side = THREE.DoubleSide;
  zoomBarrel.add(hood);

  // Subtle Stylized First-Person Photographer Hands cradling lens & grip
  const leftPalm = new THREE.Mesh(new THREE.SphereGeometry(0.038, 14, 12), matSkin);
  leftPalm.scale.set(1.1, 0.65, 1.35);
  leftPalm.position.set(-0.015, -0.048, -0.118);
  rig.add(leftPalm);

  const leftSleeve = new THREE.Mesh(new THREE.CylinderGeometry(0.038, 0.046, 0.18, 14), matSleeve);
  leftSleeve.rotation.set(0.65, 0.0, -0.38);
  leftSleeve.position.set(-0.072, -0.115, -0.045);
  rig.add(leftSleeve);

  const rightHand = new THREE.Mesh(new THREE.SphereGeometry(0.036, 14, 12), matSkin);
  rightHand.scale.set(0.85, 1.05, 1.2);
  rightHand.position.set(0.080, -0.005, -0.005);
  rig.add(rightHand);

  const rightSleeve = new THREE.Mesh(new THREE.CylinderGeometry(0.038, 0.046, 0.18, 14), matSleeve);
  rightSleeve.rotation.set(0.75, 0.0, 0.30);
  rightSleeve.position.set(0.115, -0.095, 0.068);
  rig.add(rightSleeve);

  // Neck strap loops on sides
  for (const sx of [-0.080, 0.080]) {
    const lug = new THREE.Mesh(new THREE.TorusGeometry(0.008, 0.0022, 8, 16), matChrome);
    lug.position.set(sx, 0.036, 0.0);
    rig.add(lug);
  }

  // Prevent viewmodel clipping into near plane
  rig.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = false;
      child.receiveShadow = true;
      child.renderOrder = 5;
    }
  });

  return {
    group: rig,
    zoomBarrel,
    shutterBtn,
    flashDiffuserMat: matFlashDiffuser,
  };
}

import re
from pathlib import Path

hud_file = Path(r"c:\Users\pramo\Desktop\jarvis\ui\web\jarvis_hud.html")
html = hud_file.read_text(encoding="utf-8")

start_marker = "window.HUD_CONFIG = {"
end_marker = "loaderTag.style.opacity = '0';"

idx_start = html.find(start_marker)
idx_end = html.find(end_marker)

if idx_start == -1 or idx_end == -1:
    print(f"ERROR: markers not found: start={idx_start}, end={idx_end}")
    exit(1)

new_js = """window.HUD_CONFIG = {
      // 1. HARMONIOUS PARTICLE PROPORTIONS (Matching Reference Image)
      dotSize: 0.0054,           // Rich, luminous background 3D point cloud
      eyeDotSize: 0.0094,        // Glowing iris ring dots
      eyelidDotSize: 0.0095,     // Crisp eyelid filament dots
      contourDotSize: 0.0084,    // Flowing facial streamlines & eyebrows
      highlightNodeSize: 0.026,  // Glowing cyber accent nodes (pupils, mouth corners, ears)

      // 2. BACKGROUND DENSITY (Solid, vibrant 3D holographic presence)
      densityCrown: 1500,        // Forehead dome & crown
      densityNeck: 1200,         // Neck & throat
      densityShoulders: 750,     // Shoulders & upper chest
      densityFace: 1850,         // Dense, luminous facial surface

      // 3. HOLOGRAM LIGHTING COLORS
      baseColor: '#00d9ff',     // Vibrant electric cyan
      topLightColor: '#d6f8ff', // Luminous cyan-white crown highlight
      rimLightColor: '#40f0ff', // Outer silhouette rim glow

      // 4. INTERIOR FILTER
      removeInsideCylinder: true,

      // 5. EYE POSITIONS (Exact anatomical alignment with 3D scan orbital cavities)
      rightEyeX: 0.140,
      rightEyeY: 0.442,
      leftEyeX: -0.140,
      leftEyeY: 0.442,

      // 6. MOUTH POSITION & PARTICLES
      mouthX: 0.0,
      mouthY: 0.160,
      mouthZ: 0.606,
      mouthDotSize: 0.0084,
      mouthMotionScale: 1.2,
    };

    const container = document.getElementById('canvas-container');
    const loaderTag = document.getElementById('loader-tag');
    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(38, (container.clientWidth || 300) / (container.clientHeight || 300), 0.1, 100);
    camera.position.set(0, 0.33, 1.84);
    camera.lookAt(0, 0.33, 0);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(container.clientWidth || 300, container.clientHeight || 300);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x0a1a29, 1.0);
    container.appendChild(renderer.domElement);

    const composerPixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    const bloomRenderTarget = new THREE.WebGLRenderTarget(
      (container.clientWidth || 300) * composerPixelRatio,
      (container.clientHeight || 300) * composerPixelRatio,
      { format: THREE.RGBAFormat, stencilBuffer: false }
    );
    const composer = new THREE.EffectComposer(renderer, bloomRenderTarget);
    composer.setPixelRatio(composerPixelRatio);
    composer.addPass(new THREE.RenderPass(scene, camera));

    const bloomPass = new THREE.UnrealBloomPass(
      new THREE.Vector2(container.clientWidth || 300, container.clientHeight || 300),
      0.60,  // strength
      0.26,  // radius
      0.32   // threshold (luminous glow on eyes, mouth nodes, and cyber streamlines)
    );
    composer.addPass(bloomPass);
    window.__bloomPass = bloomPass;
    window.__composer = composer;

    const faceRoot = new THREE.Group();
    scene.add(faceRoot);

    const createGlowTexture = () => {
      const c = document.createElement('canvas');
      c.width = 64;
      c.height = 64;
      const ctx = c.getContext('2d');
      const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 30);
      g.addColorStop(0, 'rgba(255, 255, 255, 1.0)');
      g.addColorStop(0.25, 'rgba(255, 255, 255, 0.95)');
      g.addColorStop(0.60, 'rgba(100, 240, 255, 0.45)');
      g.addColorStop(1, 'rgba(0, 217, 255, 0.0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(32, 32, 30, 0, Math.PI * 2);
      ctx.fill();
      return new THREE.CanvasTexture(c);
    };

    const dotTexture = createGlowTexture();

    const headMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0.0 },
        uAmp: { value: 0.0 },
        uSize: { value: window.HUD_CONFIG.dotSize },
        uOpacity: { value: 0.88 },
        uColor: { value: new THREE.Color(window.HUD_CONFIG.baseColor) },
        uTopColor: { value: new THREE.Color(window.HUD_CONFIG.topLightColor) },
        uRimColor: { value: new THREE.Color(window.HUD_CONFIG.rimLightColor) },
        uMap: { value: dotTexture }
      },
      vertexShader: `
        uniform float uTime;
        uniform float uSize;
        uniform float uAmp;
        uniform vec3 uColor;
        uniform vec3 uTopColor;
        uniform vec3 uRimColor;

        varying vec3 vNormal;
        varying vec3 vViewPosition;
        varying float vLighting;
        varying vec3 vColor;
        varying float vFacing;

        void main() {
          vNormal = normalize(normalMatrix * normal);
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          vViewPosition = -mvPosition.xyz;

          vec3 viewDir = normalize(vViewPosition);
          float NdotV = dot(viewDir, vNormal);

          // Softly fade points facing away from the camera
          float facing = smoothstep(-0.25, 0.25, NdotV);
          vFacing = facing;

          // 1. Overhead Key / Crown Light (Forehead & skull dome)
          vec3 topLightDir = normalize((viewMatrix * vec4(0.0, 1.0, 0.45, 0.0)).xyz);
          float topDiff = max(0.0, dot(vNormal, topLightDir));
          float crownFactor = smoothstep(0.40, 0.95, position.y);
          float topLight = (topDiff * 0.90 + crownFactor * 0.85);

          // 2. Upward Neck & Throat Light
          vec3 neckLightDir = normalize((viewMatrix * vec4(0.0, -0.75, 0.5, 0.0)).xyz);
          float neckDiff = max(0.0, dot(vNormal, neckLightDir));
          float neckFactor = smoothstep(0.18, -0.22, position.y) * smoothstep(-0.68, -0.28, position.y);
          float neckLight = (neckDiff * 0.75 + neckFactor * 0.85);

          // 3. Shoulder Radiance
          vec3 shoulderLightDir = normalize((viewMatrix * vec4(0.0, -1.0, 0.35, 0.0)).xyz);
          float shoulderDiff = max(0.0, dot(vNormal, shoulderLightDir));
          float shoulderFactor = smoothstep(-0.42, -0.95, position.y);
          float shoulderLight = (shoulderDiff * 0.65 + shoulderFactor * 0.85);

          // 4. Fresnel Holographic Rim Light
          float fresnel = pow(1.0 - clamp(abs(NdotV), 0.0, 1.0), 2.2) * facing;

          // 5. Front Dimensional Key/Fill Light (Illuminates cheeks, nose, and facial contours)
          vec3 frontLightDir = normalize((viewMatrix * vec4(0.0, 0.25, 0.96, 0.0)).xyz);
          float frontDiff = max(0.0, dot(vNormal, frontLightDir)) * 0.75;

          // 6. Holographic Scanline Wave
          float scanline = sin(position.y * 36.0 - uTime * 2.0) * 0.08;

          // 7. Base Ambient Illumination
          float ambient = 0.52;

          // Composite lighting factor
          float totalLight = ambient
                           + (topLight * 0.85)
                           + (neckLight * 0.70)
                           + (shoulderLight * 0.70)
                           + (fresnel * 1.10)
                           + frontDiff
                           + scanline;

          totalLight *= (1.0 + uAmp * 0.35);
          totalLight = clamp(totalLight, 0.30, 2.0);

          vLighting = totalLight;

          // Highlight color blending for lit areas
          float highlight = clamp((topLight * 0.50 + fresnel * 0.60 + frontDiff * 0.50 - 0.20), 0.0, 1.0);
          vColor = mix(uColor, uTopColor, highlight);

          // Distance attenuation and particle size scaling
          float pSize = uSize * (350.0 / -mvPosition.z) * (0.85 + 0.35 * min(totalLight, 2.0) + uAmp * 0.2);
          gl_PointSize = clamp(pSize, 1.5, 32.0);
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform sampler2D uMap;
        uniform float uOpacity;

        varying vec3 vNormal;
        varying vec3 vViewPosition;
        varying float vLighting;
        varying vec3 vColor;
        varying float vFacing;

        void main() {
          vec4 texColor = texture2D(uMap, gl_PointCoord);
          if (texColor.a < 0.02) discard;

          vec3 finalRgb = vColor * texColor.rgb * vLighting;
          float alpha = texColor.a * uOpacity * (0.25 + 0.75 * vFacing);
          if (alpha < 0.015) discard;
          gl_FragColor = vec4(finalRgb, alpha);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    window.headMat = headMat;

    // =========================================================================
    // 🌟 CYBERNETIC HOLOGRAPHIC MATERIALS & CRISP NODE TEXTURES
    // =========================================================================
    const createCrispDotTexture = () => {
      const c = document.createElement('canvas');
      c.width = 64;
      c.height = 64;
      const ctx = c.getContext('2d');
      const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 30);
      g.addColorStop(0, 'rgba(255, 255, 255, 1.0)');
      g.addColorStop(0.35, 'rgba(240, 255, 255, 0.95)');
      g.addColorStop(0.70, 'rgba(68, 244, 255, 0.55)');
      g.addColorStop(0.95, 'rgba(0, 217, 255, 0.12)');
      g.addColorStop(1, 'rgba(0, 217, 255, 0.0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(32, 32, 30, 0, Math.PI * 2);
      ctx.fill();
      return new THREE.CanvasTexture(c);
    };
    const crispDotTexture = createCrispDotTexture();

    const createNodeTexture = () => {
      const c = document.createElement('canvas');
      c.width = 64;
      c.height = 64;
      const ctx = c.getContext('2d');
      const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 31);
      g.addColorStop(0, 'rgba(255, 255, 255, 1.0)');
      g.addColorStop(0.40, 'rgba(240, 255, 255, 0.98)');
      g.addColorStop(0.75, 'rgba(68, 244, 255, 0.55)');
      g.addColorStop(1, 'rgba(0, 217, 255, 0.0)');
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(32, 32, 31, 0, Math.PI * 2);
      ctx.fill();
      return new THREE.CanvasTexture(c);
    };
    const nodeTexture = createNodeTexture();

    const eyelidMat = new THREE.PointsMaterial({
      color: 0xa8ffff,
      size: (window.HUD_CONFIG && window.HUD_CONFIG.eyelidDotSize) || 0.0095,
      map: crispDotTexture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 1.0
    });

    const irisMat = new THREE.PointsMaterial({
      color: 0x70ffff,
      size: (window.HUD_CONFIG && window.HUD_CONFIG.eyeDotSize) || 0.0094,
      map: crispDotTexture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 1.0
    });

    const contourMat = new THREE.PointsMaterial({
      color: 0x48f4ff,
      size: (window.HUD_CONFIG && window.HUD_CONFIG.contourDotSize) || 0.0084,
      map: crispDotTexture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 0.95
    });

    const highlightNodeMat = new THREE.PointsMaterial({
      color: 0xffffff,
      size: (window.HUD_CONFIG && window.HUD_CONFIG.highlightNodeSize) || 0.026,
      map: nodeTexture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 1.0
    });

    const mouthMat = new THREE.PointsMaterial({
      color: 0x58f8ff,
      size: (window.HUD_CONFIG && window.HUD_CONFIG.mouthDotSize) || 0.0084,
      map: crispDotTexture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 1.0
    });

    const eyeGimbalList = [];

    // =========================================================================
    // 🏔️ FAST 3D FACIAL SURFACE HEIGHTFIELD (Query exact Z depth on human skull)
    // =========================================================================
    const H_GRID_RES = 64;
    const H_X_MIN = -0.38, H_X_MAX = 0.38;
    const H_Y_MIN = -0.15, H_Y_MAX = 0.88;
    const surfaceHeightGrid = new Float32Array(H_GRID_RES * H_GRID_RES).fill(-999.0);

    function buildSurfaceHeightfield(positions, count) {
      for (let i = 0; i < count; i++) {
        const x = positions[i * 3];
        const y = positions[i * 3 + 1];
        const z = positions[i * 3 + 2];
        if (z < 0.05) continue;

        const gx = Math.floor(((x - H_X_MIN) / (H_X_MAX - H_X_MIN)) * (H_GRID_RES - 1));
        const gy = Math.floor(((y - H_Y_MIN) / (H_Y_MAX - H_Y_MIN)) * (H_GRID_RES - 1));
        if (gx >= 0 && gx < H_GRID_RES && gy >= 0 && gy < H_GRID_RES) {
          const idx = gy * H_GRID_RES + gx;
          if (z > surfaceHeightGrid[idx]) {
            surfaceHeightGrid[idx] = z;
          }
        }
      }

      for (let gy = 1; gy < H_GRID_RES - 1; gy++) {
        for (let gx = 1; gx < H_GRID_RES - 1; gx++) {
          const idx = gy * H_GRID_RES + gx;
          if (surfaceHeightGrid[idx] < -900) {
            let sum = 0, n = 0;
            const neighbors = [idx - 1, idx + 1, idx - H_GRID_RES, idx + H_GRID_RES];
            for (let k = 0; k < 4; k++) {
              const val = surfaceHeightGrid[neighbors[k]];
              if (val > -900) { sum += val; n++; }
            }
            if (n > 0) surfaceHeightGrid[idx] = sum / n;
          }
        }
      }
    }

    function getFaceSurfaceZ(x, y) {
      const gx = Math.floor(((x - H_X_MIN) / (H_X_MAX - H_X_MIN)) * (H_GRID_RES - 1));
      const gy = Math.floor(((y - H_Y_MIN) / (H_Y_MAX - H_Y_MIN)) * (H_GRID_RES - 1));
      if (gx >= 0 && gx < H_GRID_RES && gy >= 0 && gy < H_GRID_RES) {
        const val = surfaceHeightGrid[gy * H_GRID_RES + gx];
        if (val > -900) return val;
      }
      const rX = Math.abs(x) / 0.32;
      const rY = (y - 0.35) / 0.45;
      const rad2 = rX * rX + rY * rY;
      return Math.max(0.15, Math.sqrt(Math.max(0.01, 1.0 - Math.min(0.95, rad2))) * 0.54);
    }

    // =========================================================================
    // 👁️ 1. PRECISION ALMOND CYBER EYES (Matching Reference Image)
    // - Striking, expansive almond eye contour seated at X = ±0.140
    // - Inner tear duct tapers smoothly to X = 0.082 (natural intercanthal spacing)
    // - Parallel double eyelid crease fold line
    // - Radiant concentric dual-ring iris (Outer R=0.024, Inner R=0.012)
    // - Brilliant white-cyan pinpoint pupil core node
    // - Soft sclera micro-particles so eyeball has dimensional volume
    // =========================================================================
    function buildCyberEye(x, y, z, isRight) {
      const eyeGroup = new THREE.Group();
      eyeGroup.position.set(x, y, z);

      const sign = isRight ? 1.0 : -1.0;
      const halfW = 0.058;

      // ---- A. Eyelids, Crease & Sclera Contours ----
      const countUpper = 58;
      const countCrease = 48;
      const countLower = 52;
      const countTear = 16;
      const countSclera = 36;
      const totalLidPts = countUpper + countCrease + countLower + countTear + countSclera;
      const lidPos = new Float32Array(totalLidPts * 3);
      let ptr = 0;

      // Upper Eyelid Arch (Striking, elegant almond arch)
      for (let i = 0; i < countUpper; i++) {
        const t = (i / (countUpper - 1)) * 2.0 - 1.0;
        const px = sign * t * halfW;
        const arch = 1.0 - t * t;
        const asym = 1.0 - 0.08 * t;
        const py = 0.002 * t + 0.024 * arch * asym;
        const pz = 0.014 * arch - 0.008 * t * t;
        lidPos[ptr++] = px;
        lidPos[ptr++] = py;
        lidPos[ptr++] = pz;
      }

      // Upper Palpebral Crease (Double eyelid fold line)
      for (let i = 0; i < countCrease; i++) {
        const t = -0.85 + (i / (countCrease - 1)) * 1.95;
        const px = sign * t * halfW * 1.08;
        const arch = Math.max(0.0, 1.0 - t * t);
        const py = 0.003 * t + 0.036 * arch;
        const pz = 0.016 * arch - 0.010 * t * t;
        lidPos[ptr++] = px;
        lidPos[ptr++] = py;
        lidPos[ptr++] = pz;
      }

      // Lower Eyelid Arch (Gentle downward almond curve)
      for (let i = 0; i < countLower; i++) {
        const t = (i / (countLower - 1)) * 2.0 - 1.0;
        const px = sign * t * halfW;
        const arch = 1.0 - t * t;
        const py = 0.001 * t - 0.018 * arch * (1.0 + 0.06 * t);
        const pz = 0.010 * arch - 0.008 * t * t;
        lidPos[ptr++] = px;
        lidPos[ptr++] = py;
        lidPos[ptr++] = pz;
      }

      // Medial Tear Duct (Pointing inward toward nose bridge)
      for (let i = 0; i < countTear; i++) {
        const t = i / (countTear - 1);
        const px = -sign * (halfW + 0.001 + 0.008 * t);
        const py = -0.003 - 0.004 * t;
        const pz = -0.002 + 0.002 * (1.0 - t);
        lidPos[ptr++] = px;
        lidPos[ptr++] = py;
        lidPos[ptr++] = pz;
      }

      // Subtle sclera micro-particles inside eyeball aperture
      for (let i = 0; i < countSclera; i++) {
        const u = (i / (countSclera - 1)) * 2.0 - 1.0;
        const arch = Math.sqrt(Math.max(0.0, 1.0 - u * u));
        const side = (i % 2 === 0) ? 1.0 : -1.0;
        const px = sign * u * halfW * 0.85;
        const py = side * arch * 0.011 * (0.35 + 0.55 * Math.random());
        const pz = 0.005 * arch;
        lidPos[ptr++] = px;
        lidPos[ptr++] = py;
        lidPos[ptr++] = pz;
      }

      const lidGeom = new THREE.BufferGeometry();
      lidGeom.setAttribute('position', new THREE.BufferAttribute(lidPos, 3));
      eyeGroup.add(new THREE.Points(lidGeom, eyelidMat));

      // ---- B. Concentric Dual-Ring Iris & Pupil (Gimbal for Interactive Gaze Tracking) ----
      const irisGimbal = new THREE.Group();
      irisGimbal.position.set(0, 0, 0.006);

      const ring1Count = 68; // Outer iris ring (R=0.024)
      const ring2Count = 44; // Inner iris ring (R=0.012)
      const spokeCount = 20; // Radial tick micro-particles
      const totalIrisPts = ring1Count + ring2Count + spokeCount;
      const irisPos = new Float32Array(totalIrisPts * 3);
      let iPtr = 0;

      const r1 = 0.024;
      const r2 = 0.012;

      // Outer Iris Ring
      for (let i = 0; i < ring1Count; i++) {
        const ang = (i / ring1Count) * Math.PI * 2.0;
        irisPos[iPtr++] = Math.cos(ang) * r1;
        irisPos[iPtr++] = Math.sin(ang) * r1;
        irisPos[iPtr++] = 0.008;
      }

      // Inner Iris Ring
      for (let i = 0; i < ring2Count; i++) {
        const ang = (i / ring2Count) * Math.PI * 2.0;
        irisPos[iPtr++] = Math.cos(ang) * r2;
        irisPos[iPtr++] = Math.sin(ang) * r2;
        irisPos[iPtr++] = 0.010;
      }

      // Radial ticks between outer and inner rings
      for (let i = 0; i < spokeCount; i++) {
        const ang = (i / spokeCount) * Math.PI * 2.0;
        const radT = (r1 + r2) * 0.50;
        irisPos[iPtr++] = Math.cos(ang) * radT;
        irisPos[iPtr++] = Math.sin(ang) * radT;
        irisPos[iPtr++] = 0.009;
      }

      const irisGeom = new THREE.BufferGeometry();
      irisGeom.setAttribute('position', new THREE.BufferAttribute(irisPos, 3));
      irisGimbal.add(new THREE.Points(irisGeom, irisMat));

      // Central Pinpoint Pupil Node (Bright glowing cyber core)
      const pupilGeom = new THREE.BufferGeometry();
      const pupilPos = new Float32Array([
        0.0, 0.0, 0.014,
        0.0030, 0.0, 0.0135,
        -0.0030, 0.0, 0.0135,
        0.0, 0.0030, 0.0135,
        0.0, -0.0030, 0.0135,
      ]);
      pupilGeom.setAttribute('position', new THREE.BufferAttribute(pupilPos, 3));
      irisGimbal.add(new THREE.Points(pupilGeom, highlightNodeMat));

      eyeGroup.add(irisGimbal);
      eyeGimbalList.push(irisGimbal);

      return eyeGroup;
    }

    // =========================================================================
    // 👃 2. PRECISION SCULPTED CYBER NOSE (Matching Reference Image)
    // Features:
    // - Continuous vertical nasal streamlines flowing from glabella over the tip
    // - Clean, anatomical dorsum and philtrum lines
    // - Clean nostril margins without artificial butterfly wing blobs
    // =========================================================================
    function buildCyberNose() {
      const group = new THREE.Group();

      const bridgeCount = 48;
      const lateralBridgeCount = 38;
      const columellaCount = 20;
      const philtrumCount = 24;

      const totalNosePts = bridgeCount + lateralBridgeCount * 2
        + columellaCount + philtrumCount * 2;
      const nosePos = new Float32Array(totalNosePts * 3);
      let ptr = 0;

      // 1. Centerline Streamline (Flows from Glabella Y=0.460, over tip Y=0.282, under columella Y=0.245)
      for (let i = 0; i < bridgeCount; i++) {
        const t = i / (bridgeCount - 1);
        const y = 0.460 - 0.215 * t;
        const tipBulge = Math.exp(-Math.pow((t - 0.82) / 0.15, 2.0)) * 0.015;
        const z = 0.520 + 0.150 * Math.pow(Math.min(1.0, t * 1.15), 0.85) + tipBulge;
        nosePos[ptr++] = 0.0;
        nosePos[ptr++] = y;
        nosePos[ptr++] = z;
      }

      // 2. Lateral Bridge Streamlines (Hugging nasal bone gracefully)
      [-1, 1].forEach((sign) => {
        for (let i = 0; i < lateralBridgeCount; i++) {
          const t = i / (lateralBridgeCount - 1);
          const y = 0.455 - 0.200 * t;
          const tipBulge = Math.exp(-Math.pow((t - 0.82) / 0.15, 2.0)) * 0.011;
          const z = (0.520 + 0.146 * Math.pow(Math.min(1.0, t * 1.15), 0.85) + tipBulge) - 0.006;
          nosePos[ptr++] = sign * (0.007 + 0.005 * t);
          nosePos[ptr++] = y;
          nosePos[ptr++] = z;
        }
      });

      // 3. Columella (Central Under-Nose Partition)
      for (let i = 0; i < columellaCount; i++) {
        const t = i / (columellaCount - 1);
        nosePos[ptr++] = 0.0;
        nosePos[ptr++] = 0.265 - 0.024 * t;
        nosePos[ptr++] = 0.625 - 0.032 * t;
      }

      // 4. Philtrum (Dual vertical streamlines to Cupid's bow peaks)
      [-1, 1].forEach((sign) => {
        for (let i = 0; i < philtrumCount; i++) {
          const t = i / (philtrumCount - 1);
          nosePos[ptr++] = sign * (0.008 + 0.006 * t);
          nosePos[ptr++] = 0.238 - 0.068 * t;
          nosePos[ptr++] = 0.605 - 0.008 * t;
        }
      });

      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.BufferAttribute(nosePos, 3));
      group.add(new THREE.Points(geom, contourMat));

      return group;
    }

    // =========================================================================
    // 👄 3. PRECISION CYBERNETIC MOUTH (Matching Reference Image)
    // Features:
    // - 5 Upper Lip contour rows with Cupid's bow crest
    // - 5 Lower Lip contour rows with full curved vermilion
    // - TWO SIGNATURE CYAN GLOWING HIGHLIGHT FLARES AT MOUTH CORNERS (Signature of Image!)
    // - Seamless speech reactive articulation when JARVIS speaks
    // =========================================================================
    let mouthRig = null;

    function buildCyberMouth(centerX, centerY, centerZ) {
      const group = new THREE.Group();
      group.position.set(centerX, centerY, centerZ);

      const N_COLS = 54;
      const halfWidth = 0.088;
      const N_ROWS = 5;

      const upperPos = new Float32Array(N_COLS * N_ROWS * 3);
      const lowerPos = new Float32Array(N_COLS * N_ROWS * 3);

      for (let i = 0; i < N_COLS; i++) {
        const t = (i / (N_COLS - 1)) * 2.0 - 1.0;
        const x = t * halfWidth;
        const t2 = t * t;
        const taper = Math.max(0.0, 1.0 - t2);
        const cupid = Math.exp(-Math.pow((Math.abs(t) - 0.24) / 0.16, 2.0)) * taper;
        const tubercle = Math.exp(-Math.pow(t / 0.14, 2.0)) * taper;
        const zBase = -0.042 * t2;

        // Upper Lip 5 Rows (Crest down to stomion closure line)
        for (let r = 0; r < N_ROWS; r++) {
          const rT = r / (N_ROWS - 1);
          const uIdx = (i * N_ROWS + r) * 3;
          const yTop = 0.008 * taper + 0.010 * cupid;
          const yBot = -0.0018 * taper;
          const yVal = yTop * (1.0 - rT) + yBot * rT;
          const zDepth = (0.005 + 0.008 * Math.sin(rT * Math.PI)) * taper + 0.002 * tubercle;
          upperPos[uIdx] = x * (1.0 - 0.04 * rT);
          upperPos[uIdx + 1] = yVal;
          upperPos[uIdx + 2] = zBase + zDepth;
        }

        // Lower Lip 5 Rows (Closure line down to mental crease)
        for (let r = 0; r < N_ROWS; r++) {
          const rT = r / (N_ROWS - 1);
          const lIdx = (i * N_ROWS + r) * 3;
          const yTop = -0.0022 * taper;
          const yBot = -0.0190 * taper * (1.0 - 0.12 * t2);
          const yVal = yTop * (1.0 - rT) + yBot * rT;
          const zDepth = (0.004 + 0.011 * Math.sin(rT * Math.PI)) * taper;
          lowerPos[lIdx] = x * (0.94 + 0.06 * rT);
          lowerPos[lIdx + 1] = yVal;
          lowerPos[lIdx + 2] = zBase + zDepth;
        }
      }

      const upperGeom = new THREE.BufferGeometry();
      upperGeom.setAttribute('position', new THREE.BufferAttribute(upperPos, 3));
      const lowerGeom = new THREE.BufferGeometry();
      lowerGeom.setAttribute('position', new THREE.BufferAttribute(lowerPos, 3));

      group.add(new THREE.Points(upperGeom, mouthMat));
      group.add(new THREE.Points(lowerGeom, mouthMat));

      // ---- 🌟 TWO BRIGHT CYAN GLOWING HIGHLIGHT FLARES AT MOUTH CORNERS (Signature of Reference Image!) ----
      const cornerGeom = new THREE.BufferGeometry();
      const cornerPos = new Float32Array([
        -halfWidth - 0.002, 0.000, -0.042,
        halfWidth + 0.002, 0.000, -0.042,
        -halfWidth - 0.006, 0.000, -0.043,
        halfWidth + 0.006, 0.000, -0.043,
        -halfWidth - 0.010, 0.000, -0.044,
        halfWidth + 0.010, 0.000, -0.044,
        -halfWidth, 0.003, -0.042,
        halfWidth, 0.003, -0.042,
        -halfWidth, -0.003, -0.042,
        halfWidth, -0.003, -0.042
      ]);
      cornerGeom.setAttribute('position', new THREE.BufferAttribute(cornerPos, 3));
      group.add(new THREE.Points(cornerGeom, highlightNodeMat));

      mouthRig = { upperGeom, lowerGeom, upperPos, lowerPos, N_COLS, N_ROWS, halfWidth };
      return group;
    }

    function updateCyberMouth(openAmount) {
      if (!mouthRig) return;
      const { upperPos, lowerPos, N_COLS, N_ROWS, halfWidth, upperGeom, lowerGeom } = mouthRig;
      const cfg = window.HUD_CONFIG || {};
      const scale = cfg.mouthMotionScale !== undefined ? cfg.mouthMotionScale : 1.2;
      const eff = Math.min(1.0, openAmount * scale);

      for (let i = 0; i < N_COLS; i++) {
        const t = (i / (N_COLS - 1)) * 2.0 - 1.0;
        const t2 = t * t;
        const taper = Math.max(0.0, 1.0 - t2);
        const cupid = Math.exp(-Math.pow((Math.abs(t) - 0.24) / 0.16, 2.0)) * taper;
        const tubercle = Math.exp(-Math.pow(t / 0.14, 2.0)) * taper;
        const zBase = -0.042 * t2;
        const stretch = 1.0 - eff * 0.025 * taper;
        const x = t * halfWidth * stretch;

        // Upper lip animation
        for (let r = 0; r < N_ROWS; r++) {
          const rT = r / (N_ROWS - 1);
          const uIdx = (i * N_ROWS + r) * 3;
          const yTop = 0.008 * taper + 0.010 * cupid;
          const yBot = -0.0018 * taper;
          const yVal = yTop * (1.0 - rT) + yBot * rT;
          const uLift = eff * 0.010 * taper * rT;
          upperPos[uIdx] = x * (1.0 - 0.04 * rT);
          upperPos[uIdx + 1] = yVal + uLift;
          upperPos[uIdx + 2] = zBase + (0.005 + 0.008 * Math.sin(rT * Math.PI)) * taper + 0.002 * tubercle;
        }

        // Lower lip drop animation
        for (let r = 0; r < N_ROWS; r++) {
          const rT = r / (N_ROWS - 1);
          const lIdx = (i * N_ROWS + r) * 3;
          const yTop = -0.0022 * taper;
          const yBot = -0.0190 * taper * (1.0 - 0.12 * t2);
          const yVal = yTop * (1.0 - rT) + yBot * rT;
          const lDrop = eff * 0.050 * taper * (1.0 - 0.3 * rT);
          lowerPos[lIdx] = x * (0.94 + 0.06 * rT);
          lowerPos[lIdx + 1] = yVal - lDrop;
          lowerPos[lIdx + 2] = zBase + (0.004 + 0.011 * Math.sin(rT * Math.PI)) * taper - eff * 0.015 * taper;
        }
      }

      upperGeom.attributes.position.needsUpdate = true;
      lowerGeom.attributes.position.needsUpdate = true;
    }

    // =========================================================================
    // 🤨 4. SCULPTED CYBERNETIC EYEBROWS (Matching Reference Image)
    // - Arched supraorbital contour bands (4 sculpted strands per brow)
    // - Centered naturally over the eyes at X = ±0.140
    // =========================================================================
    function buildCyberEyebrows() {
      const group = new THREE.Group();

      const count = 52;
      const strands = 4;
      const stippleCount = 14;
      const totalPts = (count * strands + stippleCount) * 2;
      const pos = new Float32Array(totalPts * 3);
      let ptr = 0;

      [-1, 1].forEach((sign) => {
        for (let s = 0; s < strands; s++) {
          const sOffset = (s - 1.5) * 0.0035;
          for (let i = 0; i < count; i++) {
            const t = i / (count - 1);
            const x = sign * (0.035 + t * 0.175);
            // Smooth natural eyebrow arch: peaks right over eye center at X ~ 0.140
            const arch = Math.sin(Math.pow(t, 0.85) * Math.PI) * 0.026;
            const y = 0.510 + arch + sOffset - t * 0.016;
            const z = getFaceSurfaceZ(x, y) + 0.004;
            pos[ptr++] = x;
            pos[ptr++] = y;
            pos[ptr++] = z;
          }
        }
        for (let k = 0; k < stippleCount; k++) {
          const t = k / (stippleCount - 1);
          const x = sign * (0.032 + 0.015 * Math.sin(t * Math.PI));
          const y = 0.500 + 0.024 * t;
          const z = getFaceSurfaceZ(x, y) + 0.004;
          pos[ptr++] = x;
          pos[ptr++] = y;
          pos[ptr++] = z;
        }
      });

      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      group.add(new THREE.Points(geom, contourMat));

      return group;
    }

    // =========================================================================
    // 🌐 5. FLOWING FACIAL STREAMLINES (THE SIGNATURE LOOK OF REFERENCE IMAGE!)
    // Features:
    // - 10 Spaced Zygomatic Streamlines sweeping upward along the cheekbones
    // - 11 Cranial Radial Streamlines fanning upward across the forehead dome
    // - 4 Clean Chin Crescent Arcs & 3 Mandibular Jawlines
    // - 2-Ring Ear Helix & Lobule Contour Structures with Accent Nodes
    // =========================================================================
    function buildFacialTopographyStreamlines() {
      const group = new THREE.Group();

      // ---- A. 10 Spaced Zygomatic Cheek Streamlines (Cheekbone Flow) ----
      const streamCount = 10;
      const ptsPerStream = 48;
      const totalStreamPts = streamCount * ptsPerStream * 2;
      const streamPos = new Float32Array(totalStreamPts * 3);
      let sPtr = 0;

      [-1, 1].forEach((sign) => {
        for (let k = 0; k < streamCount; k++) {
          const t_k = k / (streamCount - 1);
          const y_start = 0.230 + 0.160 * t_k;
          const x_start = 0.024 + 0.038 * t_k;

          for (let i = 0; i < ptsPerStream; i++) {
            const t = i / (ptsPerStream - 1);

            // Smooth horizontal-upward sweep across cheekbone toward ear/temple
            const px = sign * (x_start + (0.165 + 0.050 * t_k) * Math.pow(t, 0.85));
            const py = y_start + (0.042 - 0.020 * t_k) * Math.sin(t * Math.PI * 0.75) + 0.016 * t * t;
            const pz = getFaceSurfaceZ(px, py) + 0.0035;

            streamPos[sPtr++] = px;
            streamPos[sPtr++] = py;
            streamPos[sPtr++] = pz;
          }
        }
      });

      const streamGeom = new THREE.BufferGeometry();
      streamGeom.setAttribute('position', new THREE.BufferAttribute(streamPos, 3));
      group.add(new THREE.Points(streamGeom, contourMat));

      // ---- B. Forehead & Cranial Streamlines (11 clean lines fanning over the dome) ----
      const fhLines = 11;
      const fhPtsPerLine = 48;
      const fhPos = new Float32Array(fhLines * fhPtsPerLine * 3);
      let fPtr = 0;

      for (let k = 0; k < fhLines; k++) {
        const u = (k / (fhLines - 1)) * 2.0 - 1.0;
        const xOffset = u * 0.180;
        for (let i = 0; i < fhPtsPerLine; i++) {
          const t = i / (fhPtsPerLine - 1);
          const y = 0.525 + 0.335 * t;
          const px = xOffset * (0.65 + 0.55 * t);
          const pz = getFaceSurfaceZ(px, y) + 0.003;
          fhPos[fPtr++] = px;
          fhPos[fPtr++] = y;
          fhPos[fPtr++] = pz;
        }
      }

      const fhGeom = new THREE.BufferGeometry();
      fhGeom.setAttribute('position', new THREE.BufferAttribute(fhPos, 3));
      group.add(new THREE.Points(fhGeom, contourMat));

      // ---- C. Chin Anatomical Crescent Contours (4 clean arcs) ----
      const chinCrescents = 4;
      const chinPtsPerArc = 42;
      const jawLines = 3;
      const jawPts = 46;
      const chinJawTotal = (chinCrescents * chinPtsPerArc + jawLines * jawPts * 2);
      const chinJawPos = new Float32Array(chinJawTotal * 3);
      let jPtr = 0;

      for (let k = 0; k < chinCrescents; k++) {
        const yBase = 0.080 - k * 0.024;
        const halfChinW = 0.048 + k * 0.015;
        for (let i = 0; i < chinPtsPerArc; i++) {
          const t = (i / (chinPtsPerArc - 1)) * 2.0 - 1.0;
          const px = t * halfChinW;
          const py = yBase + 0.009 * (1.0 - t * t);
          const pz = getFaceSurfaceZ(px, py) + 0.003;
          chinJawPos[jPtr++] = px;
          chinJawPos[jPtr++] = py;
          chinJawPos[jPtr++] = pz;
        }
      }

      // 3 Mandibular Jawline Streamlines
      [-1, 1].forEach((sign) => {
        for (let j = 0; j < jawLines; j++) {
          const jOffset = (j - 1.0) * 0.009;
          for (let i = 0; i < jawPts; i++) {
            const t = i / (jawPts - 1);
            const px = sign * (0.044 + 0.190 * Math.pow(t, 0.90));
            const py = 0.016 + 0.154 * Math.pow(t, 1.25) + jOffset * (1.0 - 0.5 * t);
            const pz = getFaceSurfaceZ(px, py) + 0.003;
            chinJawPos[jPtr++] = px;
            chinJawPos[jPtr++] = py;
            chinJawPos[jPtr++] = pz;
          }
        }
      });

      const chinJawGeom = new THREE.BufferGeometry();
      chinJawGeom.setAttribute('position', new THREE.BufferAttribute(chinJawPos, 3));
      group.add(new THREE.Points(chinJawGeom, contourMat));

      // ---- D. Ear 2-Ring Helix & Tragus Structural Outlines ----
      const earRings = 2;
      const earPts = 44;
      const earPos = new Float32Array(earRings * earPts * 2 * 3);
      let ePtr = 0;

      [-1, 1].forEach((sign) => {
        for (let er = 0; er < earRings; er++) {
          const rScale = 1.0 - er * 0.14;
          for (let i = 0; i < earPts; i++) {
            const t = i / (earPts - 1);
            const ang = Math.PI * (0.15 + 1.25 * t);
            const rEarY = 0.118 * rScale;
            const rEarX = 0.044 * rScale;
            const px = sign * (0.245 + rEarX * Math.cos(ang));
            const py = 0.320 + rEarY * Math.sin(ang);
            const pz = 0.190 + 0.080 * Math.cos(ang);
            earPos[ePtr++] = px;
            earPos[ePtr++] = py;
            earPos[ePtr++] = pz;
          }
        }
      });

      const earGeom = new THREE.BufferGeometry();
      earGeom.setAttribute('position', new THREE.BufferAttribute(earPos, 3));
      group.add(new THREE.Points(earGeom, contourMat));

      // Ear accent highlight nodes
      const earNodeGeom = new THREE.BufferGeometry();
      const earNodePos = new Float32Array([
        -0.282, 0.425, 0.215,
        0.282, 0.425, 0.215,
        -0.260, 0.205, 0.210,
        0.260, 0.205, 0.210
      ]);
      earNodeGeom.setAttribute('position', new THREE.BufferAttribute(earNodePos, 3));
      group.add(new THREE.Points(earNodeGeom, highlightNodeMat));

      // ---- E. Ambient Holographic Stardust Floating Particles ----
      const dustCount = 260;
      const dustPos = new Float32Array(dustCount * 3);
      for (let i = 0; i < dustCount; i++) {
        const rad = 0.25 + 0.35 * Math.sqrt(Math.random());
        const theta = Math.random() * Math.PI * 2.0;
        dustPos[i * 3] = Math.cos(theta) * rad;
        dustPos[i * 3 + 1] = -0.40 + 1.30 * Math.random();
        dustPos[i * 3 + 2] = -0.10 + 0.70 * Math.random();
      }
      const dustGeom = new THREE.BufferGeometry();
      dustGeom.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
      const dustMat = new THREE.PointsMaterial({
        color: 0x4df5ff,
        size: 0.0042,
        map: crispDotTexture,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        opacity: 0.65
      });
      group.add(new THREE.Points(dustGeom, dustMat));

      return group;
    }

    const gltfLoader = new THREE.GLTFLoader();
    const LOCAL_MODEL_URL = './LeePerrySmith.glb';
    const REMOTE_MODEL_URL = 'https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/models/gltf/LeePerrySmith/LeePerrySmith.glb';

    function isPointFiltered(px, py, pz) {
      const cfg = window.HUD_CONFIG || {};
      const rEyeX = cfg.rightEyeX || 0.140;
      const rEyeY = cfg.rightEyeY || 0.442;
      const lEyeX = cfg.leftEyeX || -0.140;
      const lEyeY = cfg.leftEyeY || 0.442;

      // 1. Clean elliptical aperture for eye sockets: completely clears original scan mesh inside sockets
      const dxL = (px - lEyeX) / 0.076;
      const dyL = (py - lEyeY) / 0.046;
      const inLeftEye = (dxL * dxL + dyL * dyL < 1.0) && (pz > 0.08);

      const dxR = (px - rEyeX) / 0.076;
      const dyR = (py - rEyeY) / 0.046;
      const inRightEye = (dxR * dxR + dyR * dyR < 1.0) && (pz > 0.08);

      // 2. Filter original scanned mouth slit
      const mMeshX = cfg.mouthX !== undefined ? cfg.mouthX : 0.0;
      const mMeshY = cfg.mouthY !== undefined ? cfg.mouthY : 0.160;
      const dxM = (px - mMeshX) / 0.098;
      const dyM = (py - mMeshY) / 0.038;
      const inScannedMouth = (dxM * dxM + dyM * dyM < 1.0) && (pz > 0.35);

      // 3. Filter internal oral cavity and throat cylinder
      const filterCylinder = cfg.removeInsideCylinder !== false;
      const inInsideCylinder = filterCylinder && (
        (Math.abs(px) < 0.13 && py > -0.08 && py < 0.22 && pz > 0.12 && pz < 0.43) ||
        (Math.abs(px) < 0.11 && py > -0.075 && py < -0.050 && pz > 0.18 && pz < 0.40)
      );

      return inLeftEye || inRightEye || inScannedMouth || inInsideCylinder;
    }

    function initFaceGeometry(rawGeom) {
      rawGeom.center();
      if (!rawGeom.attributes.normal) {
        rawGeom.computeVertexNormals();
      }

      const origPos = rawGeom.attributes.position;
      const origNorm = rawGeom.attributes.normal;
      const indexAttr = rawGeom.index;

      const filteredPos = [];
      const filteredNorm = [];

      // Shift mesh X by +0.025 to perfectly center the facial symmetry axis on X=0
      const xFaceCenterOffset = 0.025;

      // Build heightfield for exact surface conformance
      const rawAlignedPositions = new Float32Array(origPos.count * 3);
      for (let i = 0; i < origPos.count; i++) {
        rawAlignedPositions[i * 3] = origPos.getX(i) * 0.26 + xFaceCenterOffset;
        rawAlignedPositions[i * 3 + 1] = origPos.getY(i) * 0.26;
        rawAlignedPositions[i * 3 + 2] = origPos.getZ(i) * 0.26;
      }
      buildSurfaceHeightfield(rawAlignedPositions, origPos.count);

      // 1. Base scan vertices
      for (let i = 0; i < origPos.count; i++) {
        if ((i >= 951 && i <= 1220) || (i >= 5646 && i <= 5914)) continue;

        const px = origPos.getX(i) * 0.26 + xFaceCenterOffset;
        const py = origPos.getY(i) * 0.26;
        const pz = origPos.getZ(i) * 0.26;

        if (!isPointFiltered(px, py, pz)) {
          filteredPos.push(px, py, pz);
          filteredNorm.push(origNorm.getX(i), origNorm.getY(i), origNorm.getZ(i));
        }
      }

      // 2. Uniform background particle fill across triangles
      if (indexAttr) {
        const indices = indexAttr.array;
        const triangleCount = indices.length / 3;

        for (let t = 0; t < triangleCount; t++) {
          const ia = indices[t * 3];
          const ib = indices[t * 3 + 1];
          const ic = indices[t * 3 + 2];

          if ((ia >= 951 && ia <= 1220) || (ib >= 951 && ib <= 1220) || (ic >= 951 && ic <= 1220) ||
            (ia >= 5646 && ia <= 5914) || (ib >= 5646 && ib <= 5914) || (ic >= 5646 && ic <= 5914)) {
            continue;
          }

          const pAx = origPos.getX(ia) * 0.26 + xFaceCenterOffset, pAy = origPos.getY(ia) * 0.26, pAz = origPos.getZ(ia) * 0.26;
          const pBx = origPos.getX(ib) * 0.26 + xFaceCenterOffset, pBy = origPos.getY(ib) * 0.26, pBz = origPos.getZ(ib) * 0.26;
          const pCx = origPos.getX(ic) * 0.26 + xFaceCenterOffset, pCy = origPos.getY(ic) * 0.26, pCz = origPos.getZ(ic) * 0.26;

          const midY = (pAy + pBy + pCy) / 3.0;

          const v1x = pBx - pAx, v1y = pBy - pAy, v1z = pBz - pAz;
          const v2x = pCx - pAx, v2y = pCy - pAy, v2z = pCz - pAz;
          const cx = v1y * v2z - v1z * v2y;
          const cy = v1z * v2x - v1x * v2z;
          const cz = v1x * v2y - v1y * v2x;
          const area = 0.5 * Math.sqrt(cx * cx + cy * cy + cz * cz);

          let samples = 0;
          const cfg = window.HUD_CONFIG || {};
          if (midY > 0.52) {
            samples = Math.floor(area * (cfg.densityCrown || 1500)) + 1;
          } else if (midY < -0.55) {
            samples = Math.floor(area * (cfg.densityShoulders || 750)) + 1;
          } else if (midY < 0.10 && midY >= -0.55) {
            samples = Math.floor(area * (cfg.densityNeck || 1200)) + 1;
          } else {
            samples = Math.floor(area * (cfg.densityFace || 1850)) + 1;
          }

          if (samples <= 0) continue;

          const nAx = origNorm.getX(ia), nAy = origNorm.getY(ia), nAz = origNorm.getZ(ia);
          const nBx = origNorm.getX(ib), nBy = origNorm.getY(ib), nBz = origNorm.getZ(ib);
          const nCx = origNorm.getX(ic), nCy = origNorm.getY(ic), nCz = origNorm.getZ(ic);

          for (let k = 0; k < samples; k++) {
            let r1 = Math.random();
            let r2 = Math.random();
            if (r1 + r2 > 1.0) {
              r1 = 1.0 - r1;
              r2 = 1.0 - r2;
            }
            const r3 = 1.0 - r1 - r2;

            const px = r1 * pAx + r2 * pBx + r3 * pCx;
            const py = r1 * pAy + r2 * pBy + r3 * pCy;
            const pz = r1 * pAz + r2 * pBz + r3 * pCz;

            if (isPointFiltered(px, py, pz)) continue;

            let nx = r1 * nAx + r2 * nBx + r3 * nCx;
            let ny = r1 * nAy + r2 * nBy + r3 * nCy;
            let nz = r1 * nAz + r2 * nBz + r3 * nCz;
            const invLen = 1.0 / (Math.sqrt(nx * nx + ny * ny + nz * nz) || 1.0);

            filteredPos.push(px, py, pz);
            filteredNorm.push(nx * invLen, ny * invLen, nz * invLen);
          }
        }
      }

      const headCleanGeom = new THREE.BufferGeometry();
      headCleanGeom.setAttribute('position', new THREE.Float32BufferAttribute(filteredPos, 3));
      headCleanGeom.setAttribute('normal', new THREE.Float32BufferAttribute(filteredNorm, 3));

      const faceCloud = new THREE.Points(headCleanGeom, headMat);
      faceCloud.position.set(0, 0, 0);
      faceRoot.add(faceCloud);

      // ---- Assemble High-Detail Cybernetic Systems ----
      const cfgEye = window.HUD_CONFIG || {};
      const rEyeX = cfgEye.rightEyeX || 0.140;
      const rEyeY = cfgEye.rightEyeY || 0.442;
      const lEyeX = cfgEye.leftEyeX || -0.140;
      const lEyeY = cfgEye.leftEyeY || 0.442;

      // 1. Left & Right Cybernetic Eyes (Z = 0.455, seated inside orbital cavities)
      const leftEye = buildCyberEye(lEyeX, lEyeY, 0.455, false);
      const rightEye = buildCyberEye(rEyeX, rEyeY, 0.455, true);
      faceRoot.add(leftEye);
      faceRoot.add(rightEye);

      // 2. Precision Sculpted Cybernetic Nose
      const cyberNose = buildCyberNose();
      faceRoot.add(cyberNose);

      // 3. Precision Cybernetic Mouth (With Signature Corner Nodes!)
      const mouthX = cfgEye.mouthX !== undefined ? cfgEye.mouthX : 0.0;
      const mouthY = cfgEye.mouthY !== undefined ? cfgEye.mouthY : 0.160;
      const mouthZ = cfgEye.mouthZ !== undefined ? cfgEye.mouthZ : 0.606;
      const cyberMouth = buildCyberMouth(mouthX, mouthY, mouthZ);
      faceRoot.add(cyberMouth);

      // 4. Arched Cybernetic Eyebrows (4 Sculpted Strands + Stipples)
      const cyberEyebrows = buildCyberEyebrows();
      faceRoot.add(cyberEyebrows);

      // 5. Facial Topography Streamlines (Zygomatic Sweeps, Forehead Lines, Chin & Jaw Arcs, Ears)
      const facialTopography = buildFacialTopographyStreamlines();
      faceRoot.add(facialTopography);

      """

new_html = html[:idx_start] + new_js + html[idx_end:]
hud_file.write_text(new_html, encoding="utf-8")
print("SUCCESS: jarvis_hud.html perfectly refined!")

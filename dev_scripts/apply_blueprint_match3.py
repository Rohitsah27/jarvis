from pathlib import Path

hud_path = Path(r"c:\Users\pramo\Desktop\jarvis\ui\web\jarvis_hud.html")
html = hud_path.read_text(encoding="utf-8")

# 1. Update buildCyberNose with symmetric, delicate button nose wings
old_nose_start = "function buildCyberNose() {"
old_nose_end = "return group;\n    }"
new_nose = """function buildCyberNose() {
      const group = new THREE.Group();

      const bridgeCount = 32;
      const wingPts = 18;
      const totalNosePts = bridgeCount + wingPts * 2;
      const nosePos = new Float32Array(totalNosePts * 3);
      let ptr = 0;

      // 1. Sleek, slender central dorsal bridge
      for (let i = 0; i < bridgeCount; i++) {
        const t = i / (bridgeCount - 1);
        const y = 0.435 - 0.170 * t;
        const z = 0.518 + 0.145 * Math.pow(Math.min(1.0, t * 1.14), 0.96);
        nosePos[ptr++] = 0.0;
        nosePos[ptr++] = y;
        nosePos[ptr++] = z;
      }

      // 2. Symmetric delicate nostril wing contours (Subject ID: PHM-731)
      [-1, 1].forEach((sign) => {
        for (let i = 0; i < wingPts; i++) {
          const t = i / (wingPts - 1);
          const ang = Math.PI * (0.08 + 0.92 * t);
          const px = sign * (0.010 + 0.024 * Math.sin(ang));
          const py = 0.258 + 0.014 * Math.cos(ang);
          const pz = 0.638 + 0.016 * Math.sin(ang);
          nosePos[ptr++] = px;
          nosePos[ptr++] = py;
          nosePos[ptr++] = pz;
        }
      });

      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.BufferAttribute(nosePos, 3));
      group.add(new THREE.Points(geom, contourMat));

      return group;
    }"""

idx1 = html.find(old_nose_start)
idx2 = html.find(old_nose_end, idx1) + len(old_nose_end)
if idx1 != -1 and idx2 != -1:
    html = html[:idx1] + new_nose + html[idx2:]
    print("Symmetric cyber nose applied!")

# 2. Update buildCyberMouth with fuller, organic, beautiful lips
old_mouth_start = "function buildCyberMouth(centerX, centerY, centerZ) {"
old_mouth_end = "return group;\n    }"
new_mouth = """function buildCyberMouth(centerX, centerY, centerZ) {
      const group = new THREE.Group();
      group.position.set(centerX, centerY, centerZ);

      const N_COLS = 52;
      const halfWidth = 0.078;
      const N_ROWS = 5;

      const upperPos = new Float32Array(N_COLS * N_ROWS * 3);
      const lowerPos = new Float32Array(N_COLS * N_ROWS * 3);

      for (let i = 0; i < N_COLS; i++) {
        const t = (i / (N_COLS - 1)) * 2.0 - 1.0;
        const x = t * halfWidth;
        const t2 = t * t;
        const taper = Math.max(0.0, 1.0 - t2);
        const cupid = Math.exp(-Math.pow((Math.abs(t) - 0.22) / 0.15, 2.0)) * taper;
        const tubercle = Math.exp(-Math.pow(t / 0.13, 2.0)) * taper;
        const zBase = -0.036 * t2;

        for (let r = 0; r < N_ROWS; r++) {
          const rT = r / (N_ROWS - 1);
          const uIdx = (i * N_ROWS + r) * 3;
          const yTop = 0.0085 * taper + 0.0095 * cupid;
          const yBot = -0.0010 * taper;
          const yVal = yTop * (1.0 - rT) + yBot * rT;
          const zDepth = (0.004 + 0.007 * Math.sin(rT * Math.PI)) * taper + 0.002 * tubercle;
          upperPos[uIdx] = x;
          upperPos[uIdx + 1] = yVal;
          upperPos[uIdx + 2] = zBase + zDepth;
        }

        for (let r = 0; r < N_ROWS; r++) {
          const rT = r / (N_ROWS - 1);
          const lIdx = (i * N_ROWS + r) * 3;
          const yTop = -0.0012 * taper;
          const yBot = -0.0175 * taper * (1.0 - 0.08 * t2);
          const yVal = yTop * (1.0 - rT) + yBot * rT;
          const zDepth = (0.004 + 0.010 * Math.sin(rT * Math.PI)) * taper;
          lowerPos[lIdx] = x * (0.96 + 0.04 * rT);
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

      // Delicate single cyan accent dot at each mouth corner
      const cornerGeom = new THREE.BufferGeometry();
      const cornerPos = new Float32Array([
        -halfWidth, 0.000, -0.036,
        halfWidth, 0.000, -0.036
      ]);
      cornerGeom.setAttribute('position', new THREE.BufferAttribute(cornerPos, 3));
      group.add(new THREE.Points(cornerGeom, highlightNodeMat));

      mouthRig = { upperGeom, lowerGeom, upperPos, lowerPos, N_COLS, N_ROWS, halfWidth };
      return group;
    }"""

idx1 = html.find(old_mouth_start)
idx2 = html.find(old_mouth_end, idx1) + len(old_mouth_end)
if idx1 != -1 and idx2 != -1:
    html = html[:idx1] + new_mouth + html[idx2:]
    print("Full organic cyber lips applied!")

# 3. Deterministic nostril cavity filter (eliminate asymmetric nostril holes)
old_nostril_filter = """// 5. Nostril cavity decimation: eliminate bright headlight blobs at nostrils
      const inNostril = (py > 0.19 && py < 0.30 && Math.abs(px) > 0.010 && Math.abs(px) < 0.080 && pz > 0.52 && pz < 0.68);
      if (inNostril && Math.random() > 0.08) {
        return true;
      }"""

new_nostril_filter = """// 5. Deterministic nostril cavity filter (cleans irregular scan nostril pits symmetrically)
      const inNostrilCavity = (py > 0.20 && py < 0.285 && Math.abs(px) < 0.048 && pz > 0.54 && pz < 0.63);
      if (inNostrilCavity) return true;"""

if old_nostril_filter in html:
    html = html.replace(old_nostril_filter, new_nostril_filter, 1)
    print("Deterministic nostril cavity filter replaced!")

# 4. Remove random nostril triangle check
old_tri_check = """const midX = (pAx + pBx + pCx) / 3.0;
          if (midY > 0.19 && midY < 0.30 && Math.abs(midX) > 0.010 && Math.abs(midX) < 0.080) {
            // Decimate 92% of dense nostril cavity triangles
            if (Math.random() > 0.08) continue;
          }"""

new_tri_check = """const midX = (pAx + pBx + pCx) / 3.0;
          if (midY > 0.20 && midY < 0.285 && Math.abs(midX) < 0.048) {
            // Cull nostril interior cavity triangles
            continue;
          }"""

if old_tri_check in html:
    html = html.replace(old_tri_check, new_tri_check, 1)
    print("Nostril interior triangle culling applied!")

hud_path.write_text(html, encoding="utf-8")
print("SUCCESS: jarvis_hud.html fully updated!")

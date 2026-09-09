from pathlib import Path
import re

hud_path = Path(r"c:\Users\pramo\Desktop\jarvis\ui\web\jarvis_hud.html")
html = hud_path.read_text(encoding="utf-8")

# 1. Update buildCyberEye
old_eye_start = "function buildCyberEye(x, y, z, isRight) {"
old_eye_end = "return eyeGroup;\n    }"
new_eye = """function buildCyberEye(x, y, z, isRight) {
      const eyeGroup = new THREE.Group();
      eyeGroup.position.set(x, y, z);

      const sign = isRight ? 1.0 : -1.0;
      const halfW = 0.052;

      // Clean, sleek almond cyber eyelid (Subject ID: PHM-731)
      const countUpper = 48;
      const countLower = 42;
      const countSclera = 26;
      const totalLidPts = countUpper + countLower + countSclera;
      const lidPos = new Float32Array(totalLidPts * 3);
      let ptr = 0;

      // Upper eyelid: sleek upward cyber tilt at lateral canthus (t = 1.0 is temporal/outer)
      for (let i = 0; i < countUpper; i++) {
        const t = (i / (countUpper - 1)) * 2.0 - 1.0;
        const px = sign * t * halfW;
        const arch = Math.max(0.0, 1.0 - t * t);
        const py = 0.0045 * t + 0.021 * arch;
        const pz = 0.013 * arch - 0.007 * t * t;
        lidPos[ptr++] = px;
        lidPos[ptr++] = py;
        lidPos[ptr++] = pz;
      }

      // Lower eyelid: delicate, gentle curve
      for (let i = 0; i < countLower; i++) {
        const t = (i / (countLower - 1)) * 2.0 - 1.0;
        const px = sign * t * halfW;
        const arch = Math.max(0.0, 1.0 - t * t);
        const py = 0.0025 * t - 0.015 * arch;
        const pz = 0.009 * arch - 0.007 * t * t;
        lidPos[ptr++] = px;
        lidPos[ptr++] = py;
        lidPos[ptr++] = pz;
      }

      // Subtle sclera stipples
      for (let i = 0; i < countSclera; i++) {
        const u = (i / (countSclera - 1)) * 2.0 - 1.0;
        const arch = Math.sqrt(Math.max(0.0, 1.0 - u * u));
        const px = sign * u * halfW * 0.82;
        const py = (0.0035 * u) + (i % 2 === 0 ? 0.006 : -0.005) * arch;
        const pz = 0.005 * arch;
        lidPos[ptr++] = px;
        lidPos[ptr++] = py;
        lidPos[ptr++] = pz;
      }

      const lidGeom = new THREE.BufferGeometry();
      lidGeom.setAttribute('position', new THREE.BufferAttribute(lidPos, 3));
      eyeGroup.add(new THREE.Points(lidGeom, eyelidMat));

      const irisGimbal = new THREE.Group();
      irisGimbal.position.set(0, 0, 0.006);

      const ring1Count = 56;
      const ring2Count = 36;
      const totalIrisPts = ring1Count + ring2Count;
      const irisPos = new Float32Array(totalIrisPts * 3);
      let iPtr = 0;

      const r1 = 0.020;
      const r2 = 0.010;

      for (let i = 0; i < ring1Count; i++) {
        const ang = (i / ring1Count) * Math.PI * 2.0;
        irisPos[iPtr++] = Math.cos(ang) * r1;
        irisPos[iPtr++] = Math.sin(ang) * r1;
        irisPos[iPtr++] = 0.008;
      }

      for (let i = 0; i < ring2Count; i++) {
        const ang = (i / ring2Count) * Math.PI * 2.0;
        irisPos[iPtr++] = Math.cos(ang) * r2;
        irisPos[iPtr++] = Math.sin(ang) * r2;
        irisPos[iPtr++] = 0.010;
      }

      const irisGeom = new THREE.BufferGeometry();
      irisGeom.setAttribute('position', new THREE.BufferAttribute(irisPos, 3));
      irisGimbal.add(new THREE.Points(irisGeom, irisMat));

      // Single crisp central pupil star
      const pupilGeom = new THREE.BufferGeometry();
      const pupilPos = new Float32Array([0.0, 0.0, 0.013]);
      pupilGeom.setAttribute('position', new THREE.BufferAttribute(pupilPos, 3));
      irisGimbal.add(new THREE.Points(pupilGeom, highlightNodeMat));

      eyeGroup.add(irisGimbal);
      eyeGimbalList.push(irisGimbal);

      return eyeGroup;
    }"""

idx1 = html.find(old_eye_start)
idx2 = html.find(old_eye_end, idx1) + len(old_eye_end)
if idx1 == -1 or idx2 == -1:
    print("ERROR: eye markers not found")
    exit(1)
html = html[:idx1] + new_eye + html[idx2:]

# 2. Update buildCyberNose
old_nose_start = "function buildCyberNose() {"
old_nose_end = "return group;\n    }\n\n      return group;\n    }"
if old_nose_end not in html:
    old_nose_end = "return group;\n    }"
new_nose = """function buildCyberNose() {
      const group = new THREE.Group();

      const bridgeCount = 30;
      const totalNosePts = bridgeCount;
      const nosePos = new Float32Array(totalNosePts * 3);
      let ptr = 0;

      // Delicate single dorsal bridge filament (Subject ID: PHM-731 button nose)
      for (let i = 0; i < bridgeCount; i++) {
        const t = i / (bridgeCount - 1);
        const y = 0.435 - 0.170 * t;
        const z = 0.518 + 0.145 * Math.pow(Math.min(1.0, t * 1.14), 0.96);
        nosePos[ptr++] = 0.0;
        nosePos[ptr++] = y;
        nosePos[ptr++] = z;
      }

      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.BufferAttribute(nosePos, 3));
      group.add(new THREE.Points(geom, contourMat));

      return group;
    }"""

idx1 = html.find(old_nose_start)
idx2 = html.find(old_nose_end, idx1) + len(old_nose_end)
if idx1 == -1 or idx2 == -1:
    print("ERROR: nose markers not found")
    exit(1)
html = html[:idx1] + new_nose + html[idx2:]

# 3. Update buildCyberMouth
old_mouth_start = "function buildCyberMouth(centerX, centerY, centerZ) {"
old_mouth_end = "return group;\n    }"
new_mouth = """function buildCyberMouth(centerX, centerY, centerZ) {
      const group = new THREE.Group();
      group.position.set(centerX, centerY, centerZ);

      const N_COLS = 48;
      const halfWidth = 0.080;
      const N_ROWS = 4;

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
          const yTop = 0.007 * taper + 0.009 * cupid;
          const yBot = -0.0012 * taper;
          const yVal = yTop * (1.0 - rT) + yBot * rT;
          const zDepth = (0.004 + 0.006 * Math.sin(rT * Math.PI)) * taper + 0.002 * tubercle;
          upperPos[uIdx] = x;
          upperPos[uIdx + 1] = yVal;
          upperPos[uIdx + 2] = zBase + zDepth;
        }

        for (let r = 0; r < N_ROWS; r++) {
          const rT = r / (N_ROWS - 1);
          const lIdx = (i * N_ROWS + r) * 3;
          const yTop = -0.0015 * taper;
          const yBot = -0.0155 * taper * (1.0 - 0.10 * t2);
          const yVal = yTop * (1.0 - rT) + yBot * rT;
          const zDepth = (0.003 + 0.008 * Math.sin(rT * Math.PI)) * taper;
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
if idx1 == -1 or idx2 == -1:
    print("ERROR: mouth markers not found")
    exit(1)
html = html[:idx1] + new_mouth + html[idx2:]

# 4. Update buildCyberEyebrows
old_brow_start = "function buildCyberEyebrows() {"
old_brow_end = "return group;\n    }"
new_brow = """function buildCyberEyebrows() {
      const group = new THREE.Group();

      const count = 48;
      const totalPts = count * 2;
      const pos = new Float32Array(totalPts * 3);
      let ptr = 0;

      // Single, sleek, high-arched cyber filament (Subject ID: PHM-731)
      [-1, 1].forEach((sign) => {
        for (let i = 0; i < count; i++) {
          const t = i / (count - 1);
          const x = sign * (0.036 + t * 0.145);
          const arch = Math.sin(Math.pow(t, 0.75) * Math.PI) * 0.028;
          const y = 0.525 + arch - t * 0.014;
          const z = getFaceSurfaceZ(x, y) + 0.005;
          pos[ptr++] = x;
          pos[ptr++] = y;
          pos[ptr++] = z;
        }
      });

      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      group.add(new THREE.Points(geom, contourMat));

      return group;
    }"""

idx1 = html.find(old_brow_start)
idx2 = html.find(old_brow_end, idx1) + len(old_brow_end)
if idx1 == -1 or idx2 == -1:
    print("ERROR: brow markers not found")
    exit(1)
html = html[:idx1] + new_brow + html[idx2:]

# 5. Update buildFacialTopographyStreamlines
old_stream_start = "function buildFacialTopographyStreamlines() {"
old_stream_end = "return group;\n    }"
new_stream = """function buildFacialTopographyStreamlines() {
      const group = new THREE.Group();

      // Lateral Zygomatic Streamlines (strictly on lateral cheekbone/temple, ZERO horizontal whiskers across frontal cheeks!)
      const streamCount = 5;
      const ptsPerStream = 36;
      const totalStreamPts = streamCount * ptsPerStream * 2;
      const streamPos = new Float32Array(totalStreamPts * 3);
      let sPtr = 0;

      [-1, 1].forEach((sign) => {
        for (let k = 0; k < streamCount; k++) {
          const t_k = k / (streamCount - 1);
          const x_start = 0.130 + 0.020 * t_k;
          const y_start = 0.260 + 0.130 * t_k;

          for (let i = 0; i < ptsPerStream; i++) {
            const t = i / (ptsPerStream - 1);
            const px = sign * (x_start + (0.075 + 0.030 * t_k) * Math.pow(t, 0.85));
            const py = y_start + (0.030 - 0.015 * t_k) * Math.sin(t * Math.PI * 0.75) + 0.010 * t * t;
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

      // Subtle Jawline Streamline (1 crisp arc per side)
      const jawPts = 38;
      const jawPos = new Float32Array(jawPts * 2 * 3);
      let jPtr = 0;

      [-1, 1].forEach((sign) => {
        for (let i = 0; i < jawPts; i++) {
          const t = i / (jawPts - 1);
          const px = sign * (0.038 + 0.180 * Math.pow(t, 0.90));
          const py = 0.020 + 0.150 * Math.pow(t, 1.25);
          const pz = getFaceSurfaceZ(px, py) + 0.003;
          jawPos[jPtr++] = px;
          jawPos[jPtr++] = py;
          jawPos[jPtr++] = pz;
        }
      });

      const jawGeom = new THREE.BufferGeometry();
      jawGeom.setAttribute('position', new THREE.BufferAttribute(jawPos, 3));
      group.add(new THREE.Points(jawGeom, contourMat));

      return group;
    }"""

idx1 = html.find(old_stream_start)
idx2 = html.find(old_stream_end, idx1) + len(old_stream_end)
if idx1 == -1 or idx2 == -1:
    print("ERROR: stream markers not found")
    exit(1)
html = html[:idx1] + new_stream + html[idx2:]

# 6. Update isPointFiltered to decimate ear cavity points
old_filter = "return inLeftEye || inRightEye || inScannedMouth || inInsideCylinder;"
new_filter = """// 4. Ear decimation (prevent solid glowing cyan blocks)
      const inEar = (Math.abs(px) > 0.18 && py > 0.14 && py < 0.46 && pz < 0.14);
      if (inEar && Math.random() > 0.15) {
        return true;
      }

      return inLeftEye || inRightEye || inScannedMouth || inInsideCylinder;"""
html = html.replace(old_filter, new_filter, 1)

# 7. Update triangle sampling in initFaceGeometry for ear decimation
old_sample_check = "if (midY > 0.52) {"
new_sample_check = """const midX = (pAx + pBx + pCx) / 3.0;
          if (Math.abs(midX) > 0.18 && midY > 0.14 && midY < 0.46) {
            // Decimate 85% of ear triangles
            if (Math.random() > 0.15) continue;
          }

          if (midY > 0.52) {"""
html = html.replace(old_sample_check, new_sample_check, 1)

hud_path.write_text(html, encoding="utf-8")
print("SUCCESS: jarvis_hud.html refined to match blueprint!")

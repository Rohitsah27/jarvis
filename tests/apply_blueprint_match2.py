from pathlib import Path

hud_path = Path(r"c:\Users\pramo\Desktop\jarvis\ui\web\jarvis_hud.html")
html = hud_path.read_text(encoding="utf-8")

# 1. Remove cheek streamlines completely from buildFacialTopographyStreamlines
old_stream_start = "function buildFacialTopographyStreamlines() {"
old_stream_end = "return group;\n    }"
new_stream = """function buildFacialTopographyStreamlines() {
      const group = new THREE.Group();

      // Frontal cheeks are kept 100% clean and smooth (Subject ID: PHM-731 blueprint)
      // Subtle single jawline contour defining the sharp cyber V-jaw
      const jawPts = 42;
      const jawPos = new Float32Array(jawPts * 2 * 3);
      let jPtr = 0;

      [-1, 1].forEach((sign) => {
        for (let i = 0; i < jawPts; i++) {
          const t = i / (jawPts - 1);
          const px = sign * (0.038 + 0.180 * Math.pow(t, 0.90));
          const py = 0.016 + 0.150 * Math.pow(t, 1.25);
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
if idx1 != -1 and idx2 != -1:
    html = html[:idx1] + new_stream + html[idx2:]
    print("Cheek streamlines removed!")

# 2. Add nostril cavity filter to isPointFiltered
old_filter_ret = "return inLeftEye || inRightEye || inScannedMouth || inInsideCylinder;"
new_filter_ret = """// 5. Nostril cavity decimation: eliminate bright headlight blobs at nostrils
      const inNostril = (py > 0.19 && py < 0.30 && Math.abs(px) > 0.010 && Math.abs(px) < 0.080 && pz > 0.52 && pz < 0.68);
      if (inNostril && Math.random() > 0.08) {
        return true;
      }

      return inLeftEye || inRightEye || inScannedMouth || inInsideCylinder;"""
if old_filter_ret in html:
    html = html.replace(old_filter_ret, new_filter_ret, 1)
    print("Nostril filter added to isPointFiltered!")

# 3. Add nostril triangle decimation to initFaceGeometry
old_tri_check = "const midX = (pAx + pBx + pCx) / 3.0;"
new_tri_check = """const midX = (pAx + pBx + pCx) / 3.0;
          if (midY > 0.19 && midY < 0.30 && Math.abs(midX) > 0.010 && Math.abs(midX) < 0.080) {
            // Decimate 92% of dense nostril cavity triangles
            if (Math.random() > 0.08) continue;
          }"""
if old_tri_check in html:
    html = html.replace(old_tri_check, new_tri_check, 1)
    print("Nostril triangle decimation added!")

hud_path.write_text(html, encoding="utf-8")
print("SUCCESS: jarvis_hud.html updated!")

import QtQuick

// Circular HUD portal with a dotted/wireframe anatomical face — matches the
// reference "Iron Man style" portrait: a precise frontal face line-art
// (eyebrows, eyes, nose, lips, jaw contour, ears) made of glowing dots and
// thin connecting lines, framed by a thick ring bezel with tick marks,
// sitting inside the existing app UI. This replaced an earlier real 3D
// mesh (see tools/build_face_glb.py) — a shaded volumetric bust reads as a
// smooth blob, not a crisp anatomical face, so the reference's look is a
// 2D vector line-art problem rather than a 3D lighting one. Everything
// here is plain Qt Quick Canvas (JS 2D drawing), driven by properties set
// from Python (ui/components/ai_core_3d.py) once per animation tick.
Item {
    id: root
    anchors.fill: parent

    property color accentColor: "#00d2ff"
    property real ringSpeedFactor: 1.0
    property real glowMult: 0.85
    property real pulseScale: 1.0
    property real scanPhase: 0.0
    property string aiState: "IDLE"
    property real smoothedAmp: 0.0

    Rectangle {
        anchors.fill: parent
        color: "#070b12"
    }

    Canvas {
        id: hud
        anchors.fill: parent
        property real outerRot: 0
        property real innerRot: 0
        property real orbitPhase: 0

        NumberAnimation on outerRot { from: 0; to: 360; duration: 22000 / Math.max(0.05, root.ringSpeedFactor); loops: Animation.Infinite }
        NumberAnimation on innerRot { from: 360; to: 0; duration: 16000 / Math.max(0.05, root.ringSpeedFactor); loops: Animation.Infinite }
        NumberAnimation on orbitPhase { from: 0; to: 360; duration: 15000 / Math.max(0.05, root.ringSpeedFactor); loops: Animation.Infinite }

        Timer {
            interval: 33
            running: true
            repeat: true
            onTriggered: hud.requestPaint()
        }

        function rgba(ctx, c, a) {
            return Qt.rgba(c.r, c.g, c.b, Math.max(0, Math.min(1, a)));
        }

        // Piecewise-linear face-width profile: y is normalized top-of-head
        // (-1) to chin (+1.05); returns half-width at that height. Widest
        // at the cheekbone line, tapering to points at the crown and chin
        // — the same silhouette idea as the (now-removed) 3D mesh's
        // _face_width_profile, just expressed as explicit anchor pairs
        // since this is now a flat 2D contour, not a spherical dome.
        function halfWidthAt(y) {
            var stops = [
                [-1.00, 0.00], [-0.85, 0.60], [-0.55, 0.82], [-0.05, 0.97],
                [0.30, 0.86], [0.55, 0.72], [0.78, 0.56], [0.95, 0.38], [1.08, 0.10], [1.15, 0.00]
            ];
            for (var i = 0; i < stops.length - 1; i++) {
                var a = stops[i], b = stops[i + 1];
                if (y >= a[0] && y <= b[0]) {
                    var t = (y - a[0]) / (b[0] - a[0]);
                    return a[1] + (b[1] - a[1]) * t;
                }
            }
            return 0.0;
        }

        function headOutlinePoints(stepsPerSide) {
            var pts = [];
            var i;
            for (i = 0; i <= stepsPerSide; i++) {
                var y = -1.0 + (2.15 * i) / stepsPerSide;
                pts.push({ x: halfWidthAt(y), y: y });
            }
            for (i = stepsPerSide; i >= 0; i--) {
                var y2 = -1.0 + (2.15 * i) / stepsPerSide;
                pts.push({ x: -halfWidthAt(y2), y: y2 });
            }
            return pts;
        }

        function polylinePoints(anchors, stepsPerSeg, closed) {
            var pts = [];
            var n = anchors.length;
            var count = closed ? n : n - 1;
            for (var i = 0; i < count; i++) {
                var p0 = anchors[i];
                var p1 = anchors[(i + 1) % n];
                for (var s = 0; s < stepsPerSeg; s++) {
                    var t = s / stepsPerSeg;
                    pts.push({ x: p0.x + (p1.x - p0.x) * t, y: p0.y + (p1.y - p0.y) * t });
                }
            }
            if (!closed) pts.push(anchors[n - 1]);
            return pts;
        }

        // Strokes thin connecting segments + draws a dot at every Nth
        // sampled point along a path — the "wireframe + dot matrix" look.
        function drawDotted(ctx, pts, sx, sy, cx, cy, color, lineAlpha, dotAlpha, dotEvery, dotR, closeLoop) {
            ctx.strokeStyle = rgba(ctx, color, lineAlpha);
            ctx.lineWidth = 0.9;
            ctx.beginPath();
            for (var i = 0; i < pts.length; i++) {
                var px = cx + pts[i].x * sx, py = cy + pts[i].y * sy;
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            if (closeLoop) ctx.closePath();
            ctx.stroke();

            ctx.fillStyle = rgba(ctx, color, dotAlpha);
            for (var j = 0; j < pts.length; j += dotEvery) {
                var dx = cx + pts[j].x * sx, dy = cy + pts[j].y * sy;
                ctx.beginPath();
                ctx.arc(dx, dy, dotR, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            var cx = width / 2;
            var cy = height * 0.46;
            var ringOuterR = Math.min(width, height) * 0.47;
            var ringInnerR = ringOuterR * 0.90;
            var accent = root.accentColor;
            var gm = root.glowMult;
            var pulse = root.pulseScale;

            // ---- Outer ring bezel (double ring + ticks) ----
            ctx.save();
            ctx.translate(cx, cy);
            ctx.strokeStyle = hud.rgba(ctx, accent, 0.55 * gm);
            ctx.lineWidth = 2.4;
            ctx.beginPath();
            ctx.arc(0, 0, ringOuterR, 0, Math.PI * 2);
            ctx.stroke();
            ctx.strokeStyle = hud.rgba(ctx, accent, 0.22 * gm);
            ctx.lineWidth = 1.0;
            ctx.beginPath();
            ctx.arc(0, 0, ringOuterR * 0.965, 0, Math.PI * 2);
            ctx.stroke();
            ctx.restore();

            // Rotating segmented ring just inside the bezel
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(hud.outerRot * Math.PI / 180);
            ctx.strokeStyle = hud.rgba(ctx, accent, 0.4 * gm);
            ctx.lineWidth = 1.4;
            ctx.setLineDash([ringInnerR * 0.30, ringInnerR * 0.20]);
            ctx.beginPath();
            ctx.arc(0, 0, ringInnerR, 0, Math.PI * 2);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.restore();

            // Tick marks around the bezel
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(hud.innerRot * 0.15 * Math.PI / 180);
            var tickCount = 60;
            for (var i = 0; i < tickCount; i++) {
                var a = i * (2 * Math.PI / tickCount);
                var isMajor = (i % 5 === 0);
                var tickLen = isMajor ? 9.0 : 4.0;
                ctx.strokeStyle = hud.rgba(ctx, accent, (isMajor ? 0.6 : 0.28) * gm);
                ctx.lineWidth = isMajor ? 1.3 : 0.8;
                var r0 = ringOuterR * 0.905;
                var x1 = r0 * Math.cos(a), y1 = r0 * Math.sin(a);
                var x2 = (r0 - tickLen) * Math.cos(a), y2 = (r0 - tickLen) * Math.sin(a);
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
            }
            ctx.restore();

            // Orbiting nodes on the ring
            [0, 120, 240].forEach(function (offsetDeg) {
                var oa = (hud.orbitPhase + offsetDeg) * Math.PI / 180;
                var ox = cx + ringOuterR * Math.cos(oa);
                var oy = cy + ringOuterR * Math.sin(oa);
                var grad = ctx.createRadialGradient(ox, oy, 0, ox, oy, 8.0);
                grad.addColorStop(0, hud.rgba(ctx, accent, 0.55 * gm));
                grad.addColorStop(1, hud.rgba(ctx, accent, 0));
                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.arc(ox, oy, 8.0, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = hud.rgba(ctx, accent, 0.9 * gm);
                ctx.beginPath();
                ctx.arc(ox, oy, 2.6, 0, Math.PI * 2);
                ctx.fill();
            });

            // ---- Dotted anatomical face, centered a little above ring center ----
            var faceCx = cx;
            var faceCy = cy - ringOuterR * 0.06;
            var sx = ringOuterR * 0.50 * pulse;
            var sy = ringOuterR * 0.58 * pulse;

            // Background contour bands (horizontal "digitized" texture)
            var bands = [-0.62, -0.42, -0.22, -0.02, 0.18, 0.38, 0.58, 0.78];
            for (var b = 0; b < bands.length; b++) {
                var by = bands[b];
                var hw = hud.halfWidthAt(by) * 0.94;
                var bandPts = [];
                var steps = 14;
                for (var s2 = 0; s2 <= steps; s2++) {
                    bandPts.push({ x: -hw + (2 * hw * s2) / steps, y: by });
                }
                ctx.fillStyle = hud.rgba(ctx, accent, 0.14 * gm);
                for (var k = 0; k < bandPts.length; k += 2) {
                    var bx = faceCx + bandPts[k].x * sx, byy = faceCy + bandPts[k].y * sy;
                    ctx.beginPath();
                    ctx.arc(bx, byy, 0.9, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            // Head/jaw silhouette
            var headPts = hud.headOutlinePoints(40);
            hud.drawDotted(ctx, headPts, sx, sy, faceCx, faceCy, accent, 0.5 * gm, 0.75 * gm, 3, 1.3, true);

            // Eyebrows
            [-1, 1].forEach(function (side) {
                var eb = [
                    { x: side * 0.56, y: -0.32 },
                    { x: side * 0.38, y: -0.39 },
                    { x: side * 0.20, y: -0.34 },
                ];
                var pts = hud.polylinePoints(eb, 6, false);
                hud.drawDotted(ctx, pts, sx, sy, faceCx, faceCy, accent, 0.55 * gm, 0.85 * gm, 3, 1.2, false);
            });

            // Eyes (almond outline + iris + pupil)
            [-1, 1].forEach(function (side) {
                var ex = side * 0.36;
                var eye = [
                    { x: side * 0.52, y: -0.13 },
                    { x: side * 0.36, y: -0.19 },
                    { x: side * 0.20, y: -0.13 },
                    { x: side * 0.36, y: -0.07 },
                ];
                var pts = hud.polylinePoints(eye, 6, true);
                hud.drawDotted(ctx, pts, sx, sy, faceCx, faceCy, accent, 0.6 * gm, 0.9 * gm, 3, 1.2, true);

                var irisX = faceCx + ex * sx, irisY = faceCy + (-0.13) * sy;
                ctx.strokeStyle = hud.rgba(ctx, accent, 0.7 * gm);
                ctx.lineWidth = 1.0;
                ctx.beginPath();
                ctx.arc(irisX, irisY, sx * 0.055, 0, Math.PI * 2);
                ctx.stroke();
                ctx.fillStyle = hud.rgba(ctx, accent, 0.9 * gm);
                ctx.beginPath();
                ctx.arc(irisX, irisY, sx * 0.020, 0, Math.PI * 2);
                ctx.fill();
            });

            // Nose (bridge line + base curve + nostrils)
            var bridge = hud.polylinePoints([{ x: 0, y: -0.30 }, { x: 0.015, y: -0.02 }], 10, false);
            hud.drawDotted(ctx, bridge, sx, sy, faceCx, faceCy, accent, 0.4 * gm, 0.55 * gm, 3, 1.0, false);
            var noseBase = hud.polylinePoints([
                { x: -0.15, y: 0.13 }, { x: -0.06, y: 0.18 }, { x: 0.0, y: 0.16 },
                { x: 0.06, y: 0.18 }, { x: 0.15, y: 0.13 },
            ], 5, false);
            hud.drawDotted(ctx, noseBase, sx, sy, faceCx, faceCy, accent, 0.55 * gm, 0.85 * gm, 3, 1.1, false);

            // Lips (upper + lower)
            var upperLip = hud.polylinePoints([
                { x: -0.30, y: 0.45 }, { x: -0.12, y: 0.42 }, { x: 0, y: 0.44 },
                { x: 0.12, y: 0.42 }, { x: 0.30, y: 0.45 },
            ], 6, false);
            hud.drawDotted(ctx, upperLip, sx, sy, faceCx, faceCy, accent, 0.55 * gm, 0.85 * gm, 3, 1.1, false);
            var lowerLip = hud.polylinePoints([
                { x: -0.30, y: 0.45 }, { x: 0, y: 0.55 }, { x: 0.30, y: 0.45 },
            ], 8, false);
            hud.drawDotted(ctx, lowerLip, sx, sy, faceCx, faceCy, accent, 0.5 * gm, 0.8 * gm, 3, 1.1, false);

            // Ears — small and tucked well inside the jaw silhouette so
            // they read as a subtle detail, not a shape competing with the
            // telemetry columns further out.
            [-1, 1].forEach(function (side) {
                var ear = [
                    { x: side * 0.68, y: -0.16 },
                    { x: side * 0.76, y: -0.03 },
                    { x: side * 0.69, y: 0.11 },
                    { x: side * 0.63, y: -0.02 },
                ];
                var pts = hud.polylinePoints(ear, 6, true);
                hud.drawDotted(ctx, pts, sx, sy, faceCx, faceCy, accent, 0.22 * gm, 0.4 * gm, 4, 0.8, true);
            });

            // Horizontal scanning beam sweeping the face
            var scanY = -1.0 + 2.0 * root.scanPhase;
            var scanHw = hud.halfWidthAt(scanY) * 0.98;
            var sYpx = faceCy + scanY * sy;
            var scanGrad = ctx.createLinearGradient(faceCx - scanHw * sx, sYpx, faceCx + scanHw * sx, sYpx);
            scanGrad.addColorStop(0, hud.rgba(ctx, accent, 0));
            scanGrad.addColorStop(0.5, hud.rgba(ctx, accent, 0.8 * gm));
            scanGrad.addColorStop(1, hud.rgba(ctx, accent, 0));
            ctx.strokeStyle = scanGrad;
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            ctx.moveTo(faceCx - scanHw * sx, sYpx);
            ctx.lineTo(faceCx + scanHw * sx, sYpx);
            ctx.stroke();

            // ---- Telemetry columns (inside the ring) ----
            var leftItems = ["LISTENING", "THINKING", "ANALYZING", "EXECUTING"];
            var rightItems = ["INTELLIGENCE", "ASSISTANCE", "AUTOMATION", "ALWAYS ON"];
            var colX = ringOuterR * 0.62;
            var rowStart = faceCy - 46;
            var st = root.aiState;
            var amp = root.smoothedAmp;
            ctx.textAlign = "right";
            ctx.font = "600 8px 'Segoe UI'";
            for (var li = 0; li < leftItems.length; li++) {
                var ly = rowStart + li * 20;
                var item = leftItems[li];
                var leftActive = (item === "LISTENING" && st === "LISTENING") ||
                    (item === "THINKING" && st === "THINKING") ||
                    ((item === "ANALYZING" || item === "EXECUTING") && st === "PROCESSING");
                ctx.fillStyle = hud.rgba(ctx, accent, (leftActive ? 0.95 : 0.4) * gm);
                ctx.fillText(item, cx - colX, ly);
            }
            ctx.textAlign = "left";
            for (var ri = 0; ri < rightItems.length; ri++) {
                var ry = rowStart + ri * 20;
                var ritem = rightItems[ri];
                var rightActive = ((ritem === "INTELLIGENCE" || ritem === "ASSISTANCE") && (st === "SPEAKING" || amp > 0.15)) ||
                    (ritem === "ALWAYS ON" && st !== "OFFLINE");
                var rightColor = (ritem === "ALWAYS ON" && rightActive) ? Qt.rgba(0, 1, 0.616, 1) : accent;
                ctx.fillStyle = hud.rgba(ctx, rightColor, (rightActive ? 0.95 : 0.4) * gm);
                ctx.fillText(ritem, cx + colX - 78, ry);
            }

            // ---- Title / subtitle ----
            var textY = cy + ringOuterR * 0.72;
            ctx.textAlign = "center";
            ctx.font = "bold 15px 'Segoe UI'";
            ctx.fillStyle = "#ffffff";
            ctx.fillText("J A R V I S", cx, textY);
            ctx.font = "600 7px 'Segoe UI'";
            ctx.fillStyle = hud.rgba(ctx, accent, 0.85 * Math.min(1.0, gm));
            ctx.fillText("H O W   C A N   I   A S S I S T   Y O U ?", cx, textY + 18);
        }
    }
}

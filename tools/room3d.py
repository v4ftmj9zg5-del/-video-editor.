"""3D walkthrough stills + vertical video of a designed room (three.js in headless Chromium).

The room is a list of simple parts (boxes, cylinders, wall planes with painted canvas
textures) in plan centimetres: x = along the window wall, y = from the window wall
towards the door wall, z = height. Lighting: daylight through the window (soft
shadows), sky fill, warm pendant. Renders on CPU (SwiftShader), so expect minutes.

Usage: room3d.py PROFILE OUT_DIR [--video]
"""
import json
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reel_how_it_works import ease_io, ease_out, font  # noqa: E402

THREE = os.environ.get("THREE_JS", "/tmp/claude-0/-home-user--video-editor-/f43aeb84-1337-572a-984d-15b89b7ace5f/scratchpad/node/node_modules/three/build/three.module.min.js")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def B(name, x0, y0, z0, x1, y1, z1, mat, **kw):
    return dict(k="box", n=name, a=[x0, y0, z0], b=[x1, y1, z1], m=mat, **kw)


def C(name, cx, cy, z0, r, h, mat, **kw):
    return dict(k="cyl", n=name, c=[cx, cy, z0], r=r, h=h, m=mat, **kw)


def S(name, cx, cy, cz, r, mat, **kw):
    return dict(k="sph", n=name, c=[cx, cy, cz], r=r, m=mat, **kw)


# ------------------------------------------------------------------ Michal Aharoni: boys' room (simulation client)
def michal():
    W, D, H = 330, 300, 260
    win = (110, 270, 100, 210)          # x0, x1, sill, head
    door = (30, 110, 210)
    p = []
    M = {
        "wall": dict(c="#f4f1ea", r=.95), "floor": dict(c="#d9d6cf", r=.6, tex="tiles"),
        "ceil": dict(c="#f7f5f0", r=1), "white": dict(c="#f5f3ee", r=.55), "wood": dict(c="#c9a27a", r=.65, tex="wood"),
        "navy": dict(c="#2f3e56", r=.9), "olive": dict(c="#7b8452", r=.9), "mustard": dict(c="#d4a640", r=.85),
        "linen": dict(c="#e9e1d2", r=.95), "rug": dict(c="#e6dccb", r=1, tex="rug"), "glass": dict(c="#cfe3ee", r=.1, e="#dfeef5", ei=.9),
        "alu": dict(c="#c9cbcc", r=.4, me=.3), "mural": dict(c="#ffffff", r=.95, tex="mural"), "rattan": dict(c="#c49a63", r=.9, tex="rattan"),
        "lamp": dict(c="#fff3dc", r=.5, e="#ffe2b0", ei=1.2), "poster1": dict(c="#fff", r=.9, tex="rocket"),
        "poster2": dict(c="#fff", r=.9, tex="dino"), "poster3": dict(c="#fff", r=.9, tex="moon"), "dark": dict(c="#3a3632", r=.6),
        "red": dict(c="#c4553f", r=.6), "blue": dict(c="#4f7fb5", r=.6), "yellow": dict(c="#e3b53c", r=.6), "green": dict(c="#6f9a5a", r=.6),
    }
    # shell: floor, ceiling, walls (with openings), accent mural on the left wall
    p.append(B("floor", -12, -12, -2, W + 12, D + 12, 0, "floor"))
    p.append(B("ceiling", -12, -12, H, W + 12, D + 12, H + 2, "ceil", ceiling=1))
    x0, x1, sill, head = win
    p += [B("wall_n_l", -12, -12, 0, x0, 0, H, "wall"), B("wall_n_r", x1, -12, 0, W + 12, 0, H, "wall"),
          B("wall_n_b", x0, -12, 0, x1, 0, sill, "wall"), B("wall_n_t", x0, -12, head, x1, 0, H, "wall")]
    d0, d1, dh = door
    p += [B("wall_s_l", -12, D, 0, d0, D + 12, H, "wall"), B("wall_s_r", d1, D, 0, W + 12, D + 12, H, "wall"),
          B("wall_s_t", d0, D, dh, d1, D + 12, H, "wall")]
    p += [B("wall_w", -12, 0, 0, 0, D, H, "wall"), B("wall_e", W, 0, 0, W + 12, D, H, "wall")]
    p.append(dict(k="plane", n="mural", x=0.4, y0=0, y1=D, z0=0, z1=H, m="mural", face="+x"))
    # window: frame, glass, roller-shutter box, sill, linen curtains on a rod
    p += [B("win_frame", x0, -8, sill, x1, -4, head, "alu"), B("glass", x0 + 4, -7, sill + 4, x1 - 4, -6, head - 4, "glass"),
          B("win_mull", (x0 + x1) / 2 - 2, -8, sill, (x0 + x1) / 2 + 2, -3, head, "alu"),
          B("shutter_box", x0 - 6, 0, head, x1 + 6, 18, head + 25, "white"), B("sill", x0 - 4, 0, sill - 3, x1 + 4, 6, sill, "white"),
          C("rod", 0, 0, 0, 1.2, 1, "dark", rod=[x0 - 30, 22, head + 34, x1 + 30]),
          B("curtain_l", x0 - 34, 16, 2, x0 + 6, 24, head + 32, "linen", folds=1),
          B("curtain_r", x1 - 6, 16, 2, x1 + 34, 24, head + 32, "linen", folds=1)]
    # door (open against the left wall), AC on the right wall
    p.append(B("door_leaf", d0 - 4, D - 80, 0, d0, D, dh - 2, "white"))
    p.append(B("ac", W - 22, 20, 212, W, 100, 242, "white"))
    # built-in closet (existing)
    p += [B("closet", 180, 240, 0, W, D, 250, "white"),
          B("closet_g1", 254, 239.4, 4, 256, 240, 246, "dark"), B("closet_g2", 217, 239.4, 4, 218, 240, 246, "dark"),
          B("closet_g3", 292, 239.4, 4, 293, 240, 246, "dark"),
          S("knob1", 250, 238.5, 110, 1.8, "wood"), S("knob2", 260, 238.5, 110, 1.8, "wood")]
    # bunk bed along the left wall: posts, two decks, rails, ladder, bedding
    bx0, by0, bx1, by1 = 0, 12, 97, 218
    for px, py in ((bx0 + 1, by0 + 1), (bx1 - 7, by0 + 1), (bx0 + 1, by1 - 7), (bx1 - 7, by1 - 7)):
        p.append(B("post", px, py, 0, px + 6, py + 6, 172, "wood"))
    for z in (24, 120):
        p += [B("deck", bx0 + 1, by0 + 1, z, bx1 - 1, by1 - 1, z + 6, "wood"),
              B("mattress", bx0 + 4, by0 + 4, z + 6, bx1 - 4, by1 - 4, z + 18, "white")]
    p += [B("duvet_low", bx0 + 4, by0 + 46, 42, bx1 - 3, by1 - 6, 47, "navy"),
          B("pillow_low", bx0 + 10, by0 + 10, 42, bx1 - 14, by0 + 40, 52, "white"),
          B("cushion_low", bx1 - 24, by0 + 70, 42, bx1 - 6, by0 + 100, 60, "mustard"),
          B("duvet_up", bx0 + 4, by0 + 46, 138, bx1 - 3, by1 - 6, 143, "olive"),
          B("pillow_up", bx0 + 10, by0 + 10, 138, bx1 - 14, by0 + 40, 148, "white"),
          B("rail_side", bx1 - 4, by0 + 1, 150, bx1, by1 - 60, 158, "wood"),
          B("rail_side2", bx1 - 4, by0 + 1, 132, bx1, by1 - 60, 138, "wood"),
          B("rail_head", bx0 + 1, by0 + 1, 126, bx1 - 1, by0 + 5, 168, "wood"),
          B("rail_foot", bx0 + 1, by1 - 5, 126, bx1 - 1, by1 - 1, 168, "wood")]
    for z in (60, 88, 116, 144):
        p.append(B("rung", bx1, by1 - 52, z, bx1 + 3, by1 - 8, z + 4, "wood"))
    p += [B("ladder_l", bx1, by1 - 56, 0, bx1 + 4, by1 - 50, 172, "wood"), B("ladder_r", bx1, by1 - 10, 0, bx1 + 4, by1 - 4, 172, "wood")]
    # desk under the window with chair and lamp
    p += [B("desk_top", 160, 2, 70, 240, 52, 73, "wood")]
    for lx, ly in ((162, 4), (234, 4), (162, 46), (234, 46)):
        p.append(B("desk_leg", lx, ly, 0, lx + 4, ly + 4, 70, "white"))
    p += [B("chair_seat", 182, 62, 42, 218, 96, 46, "white"), B("chair_back", 182, 92, 46, 218, 96, 80, "white"),
          C("chair_leg", 186, 66, 0, 1.5, 42, "dark"), C("chair_leg", 214, 66, 0, 1.5, 42, "dark"),
          C("chair_leg", 186, 92, 0, 1.5, 42, "dark"), C("chair_leg", 214, 92, 0, 1.5, 42, "dark"),
          C("lamp_base", 228, 14, 73, 6, 2, "mustard"), C("lamp_arm", 228, 14, 75, 1, 32, "mustard"),
          C("lamp_shade", 220, 18, 100, 7, 9, "mustard", cone=1),
          B("books", 166, 8, 73, 186, 22, 82, "navy"), B("books2", 166, 8, 82, 184, 22, 86, "olive")]
    # cube storage with bins, posters above it
    sx0, sy0 = 291, 100
    p.append(B("kallax", sx0, sy0, 0, W, sy0 + 77, 77, "white"))
    for (cy, cz), m in zip(((sy0 + 4, 4), (sy0 + 41, 4), (sy0 + 4, 40), (sy0 + 41, 40)), ("olive", "navy", "mustard", "linen")):
        p.append(B("bin", sx0 - 0.5, cy, cz, sx0 + 2, cy + 32, cz + 32, m))
    for i, (m, y) in enumerate((("poster1", 104), ("poster2", 140), ("poster3", 122))):
        z0 = 120 if i < 2 else 170
        p.append(dict(k="plane", n="poster", x=W - 1.4, y0=y, y1=y + 30, z0=z0, z1=z0 + 40, m=m, face="-x", frame=1))
    # play rug with LEGO bricks, pendant light
    p += [C("rug", 212, 172, 0, 58, .8, "rug"), C("rug_rim", 212, 172, 0, 60, .5, "navy")]
    for i, (dx, dy, m) in enumerate(((-12, 4, "red"), (6, -10, "blue"), (14, 12, "yellow"), (-4, 18, "green"), (20, -2, "red"))):
        p.append(B("lego", 212 + dx, 172 + dy, .8, 212 + dx + 6, 172 + dy + 3, 3.8, m, rot=i * 25))
    p += [C("cord", 190, 150, 200, .4, 60, "dark"), S("pendant", 190, 150, 186, 20, "rattan"), S("bulb", 190, 150, 184, 5, "lamp")]
    room = dict(w=W, d=D, h=H, win=win, door=door)
    shots = {
        "door": dict(eye=[132, 238, 152], at=[175, 30, 100], fov=74),
        "bunk": dict(eye=[300, 60, 135], at=[40, 150, 95], fov=70),
        "top": dict(eye=[165, 220, 520], at=[165, 140, 0], fov=55, cutaway=1),
    }
    # vertical video path: dolly in from the door, pan to the bunk, rise to the dollhouse view
    path = [(0.0, [132, 240, 152], [175, 30, 100]), (4.0, [205, 232, 150], [200, 20, 95]),
            (7.5, [302, 205, 150], [40, 110, 100]), (10.0, [306, 175, 165], [40, 130, 80]),
            (13.0, [165, 215, 520], [165, 140, 0])]
    return dict(mats=M, parts=p, room=room, shots=shots, path=path, cut_from=10.0,
                title="חדר הבנים", sub="איתי ויונתן · הדמיה בתלת־ממד")


PROFILES = {"michal": michal}

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#000;overflow:hidden}</style></head>
<body><script type="module">
import * as THREE from 'file://__THREE__';
const S = __SCENE__;
const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
renderer.setPixelRatio(1); renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color('#f3efe8');
const P = (x, y, z) => new THREE.Vector3(x, z, y);          // plan (x, y, z-up) -> three (x, y-up, z)

function canvasTex(kind, w, h){
  const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d');
  const rnd = (s => () => (s = (s * 16807) % 2147483647) / 2147483647)(7);
  if (kind === 'tiles'){ g.fillStyle = '#dcd9d2'; g.fillRect(0,0,w,h); for (let i=0;i<4000;i++){g.fillStyle=`rgba(0,0,0,${rnd()*.03})`;g.fillRect(rnd()*w,rnd()*h,2,2);} g.strokeStyle='#c3c0b8'; g.lineWidth=3; g.strokeRect(0,0,w,h); }
  if (kind === 'wood'){ g.fillStyle='#c9a27a'; g.fillRect(0,0,w,h); for(let i=0;i<60;i++){g.strokeStyle=`rgba(120,80,45,${.05+rnd()*.08})`;g.lineWidth=1+rnd()*2;g.beginPath();const y=rnd()*h;g.moveTo(0,y);g.bezierCurveTo(w*.3,y+rnd()*8-4,w*.6,y+rnd()*8-4,w,y+rnd()*6-3);g.stroke();} }
  if (kind === 'rug'){ g.fillStyle='#e6dccb'; g.fillRect(0,0,w,h); g.strokeStyle='rgba(150,120,90,.25)'; for(let r=8;r<w/2;r+=7){g.lineWidth=2;g.beginPath();g.arc(w/2,h/2,r,0,7);g.stroke();} g.strokeStyle='#2f3e56'; g.lineWidth=10; g.beginPath(); g.arc(w/2,h/2,w/2-22,0,7); g.stroke(); }
  if (kind === 'rattan'){ g.fillStyle='#c49a63'; g.fillRect(0,0,w,h); g.strokeStyle='rgba(90,60,30,.45)'; g.lineWidth=3; for(let i=-h;i<w;i+=14){g.beginPath();g.moveTo(i,0);g.lineTo(i+h,h);g.stroke();g.beginPath();g.moveTo(i+h,0);g.lineTo(i,h);g.stroke();} }
  if (kind === 'mural'){   // peel-and-stick mountains: cream sky, mustard sun, layered sage / olive / navy ridges
    const sky = g.createLinearGradient(0,0,0,h); sky.addColorStop(0,'#f4efe4'); sky.addColorStop(1,'#efe6d6'); g.fillStyle=sky; g.fillRect(0,0,w,h);
    g.fillStyle='#d9ae4a'; g.beginPath(); g.arc(w*.68,h*.30,h*.07,0,7); g.fill();
    const ridge=(base,amp,col,seed)=>{g.fillStyle=col;g.beginPath();g.moveTo(0,h);let x=0;g.lineTo(0,base);while(x<=w){const y=base-amp*(.5+.5*Math.sin(x/w*Math.PI*seed+seed))-amp*.35*Math.sin(x/w*Math.PI*seed*2.3);g.lineTo(x,y);x+=w/60;}g.lineTo(w,h);g.closePath();g.fill();};
    ridge(h*.52,h*.16,'#b8bf9a',3.1); ridge(h*.62,h*.15,'#8e9563',4.3); ridge(h*.72,h*.12,'#5d6744',2.7); ridge(h*.84,h*.08,'#2f3e56',5.2);
    g.fillStyle='rgba(47,62,86,.9)'; for(let i=0;i<14;i++){const x=w*(.05+i*.07),y=h*(.80-((i*37)%5)*.012),s=h*.035; g.beginPath(); g.moveTo(x,y-s*2.2); g.lineTo(x-s*.7,y); g.lineTo(x+s*.7,y); g.fill();}
  }
  if (kind === 'rocket' || kind === 'dino' || kind === 'moon'){
    g.fillStyle = kind==='moon' ? '#2f3e56' : '#f4efe4'; g.fillRect(0,0,w,h);
    if (kind==='rocket'){ g.fillStyle='#d4a640'; g.beginPath(); g.ellipse(w/2,h*.45,w*.12,h*.25,0,0,7); g.fill(); g.fillStyle='#2f3e56'; g.beginPath(); g.arc(w/2,h*.38,w*.05,0,7); g.fill(); g.fillStyle='#7b8452'; g.beginPath(); g.moveTo(w*.38,h*.62); g.lineTo(w*.62,h*.62); g.lineTo(w/2,h*.78); g.fill(); }
    if (kind==='dino'){ g.fillStyle='#7b8452'; g.beginPath(); g.ellipse(w*.5,h*.6,w*.28,h*.13,0,0,7); g.fill(); g.beginPath(); g.ellipse(w*.75,h*.4,w*.07,h*.12,-.4,0,7); g.fill(); g.fillRect(w*.35,h*.68,w*.06,h*.12); g.fillRect(w*.58,h*.68,w*.06,h*.12); }
    if (kind==='moon'){ g.fillStyle='#e9d9a8'; g.beginPath(); g.arc(w*.5,h*.45,w*.22,0,7); g.fill(); g.fillStyle='#2f3e56'; g.beginPath(); g.arc(w*.58,h*.4,w*.2,0,7); g.fill(); g.fillStyle='#e9d9a8'; for(let i=0;i<12;i++){g.fillRect(rnd()*w,rnd()*h,3,3);} }
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}
const texCache = {};
function mat(name){
  const m = S.mats[name]; const o = {color: new THREE.Color(m.c), roughness: m.r ?? .8, metalness: m.me ?? 0};
  if (m.e){ o.emissive = new THREE.Color(m.e); o.emissiveIntensity = m.ei ?? 1; }
  if (m.tex){ const sz = {mural:[2048,1774], tiles:[256,256], wood:[512,512], rug:[1024,1024], rattan:[256,256]}[m.tex] || [512,682];
    texCache[m.tex] = texCache[m.tex] || canvasTex(m.tex, ...sz); o.map = texCache[m.tex]; o.color = new THREE.Color('#fff'); }
  return new THREE.MeshStandardMaterial(o);
}
const ceilingParts = [];
for (const p of S.parts){
  let mesh;
  if (p.k === 'box'){
    const [x0,y0,z0] = p.a, [x1,y1,z1] = p.b;
    const geo = new THREE.BoxGeometry(Math.abs(x1-x0), Math.abs(z1-z0), Math.abs(y1-y0));
    const m = mat(p.m);
    if (S.mats[p.m].tex === 'tiles'){ m.map = m.map.clone(); m.map.wrapS = m.map.wrapT = THREE.RepeatWrapping; m.map.repeat.set((x1-x0)/60,(y1-y0)/60); m.map.needsUpdate = true; }
    if (S.mats[p.m].tex === 'wood'){ m.map = m.map.clone(); m.map.wrapS = m.map.wrapT = THREE.RepeatWrapping; m.map.repeat.set(1,1); m.map.needsUpdate = true; }
    mesh = new THREE.Mesh(geo, m); mesh.position.copy(P((x0+x1)/2,(y0+y1)/2,(z0+z1)/2));
    if (p.rot) mesh.rotation.y = p.rot * Math.PI/180;
    if (p.folds){ const n = 6; mesh.visible = false; const wdt = (x1-x0)/n;
      for (let i=0;i<n;i++){ const f = new THREE.Mesh(new THREE.CylinderGeometry(wdt*.62,wdt*.62,z1-z0,16,1,false,0,Math.PI), m);
        f.position.copy(P(x0+wdt*(i+.5),(y0+y1)/2,(z0+z1)/2)); f.rotation.y = (i%2? 0 : Math.PI); f.castShadow = f.receiveShadow = true; scene.add(f);} }
  } else if (p.k === 'cyl'){
    if (p.rod){ const [ax, y, z, bx] = p.rod; const geo = new THREE.CylinderGeometry(1.2,1.2,bx-ax,12); mesh = new THREE.Mesh(geo, mat(p.m)); mesh.rotation.z = Math.PI/2; mesh.position.copy(P((ax+bx)/2,y,z)); }
    else { const geo = p.cone ? new THREE.CylinderGeometry(p.r*.45, p.r, p.h, 24, 1, true) : new THREE.CylinderGeometry(p.r, p.r, p.h, 48);
      mesh = new THREE.Mesh(geo, mat(p.m)); mesh.position.copy(P(p.c[0], p.c[1], p.c[2] + p.h/2)); }
  } else if (p.k === 'sph'){
    mesh = new THREE.Mesh(new THREE.SphereGeometry(p.r, 32, 24), mat(p.m)); mesh.position.copy(P(...p.c));
  } else if (p.k === 'plane'){
    const geo = new THREE.PlaneGeometry(p.y1 - p.y0, p.z1 - p.z0); mesh = new THREE.Mesh(geo, mat(p.m));
    mesh.position.copy(P(p.x, (p.y0+p.y1)/2, (p.z0+p.z1)/2)); mesh.rotation.y = p.face === '+x' ? Math.PI/2 : -Math.PI/2;
    if (p.frame){ const fr = new THREE.Mesh(new THREE.BoxGeometry(1.5, p.z1-p.z0+3, p.y1-p.y0+3), mat('wood')); fr.position.copy(P(p.x + (p.face==='+x'? -1 : 1), (p.y0+p.y1)/2, (p.z0+p.z1)/2)); scene.add(fr); }
  }
  if (!mesh) continue;
  mesh.castShadow = !['glass','floor'].includes(p.n); mesh.receiveShadow = true;
  if (p.ceiling) ceilingParts.push(mesh);
  scene.add(mesh);
}
// lights: sky fill, sun through the window, warm pendant, window bounce
scene.add(new THREE.HemisphereLight('#fff7ec', '#c9bfb0', .65));
const sun = new THREE.DirectionalLight('#ffeccc', 3.0); sun.position.copy(P(260, -260, 330)); sun.target.position.copy(P(150, 160, 0));
sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); const sc = sun.shadow.camera; sc.left = -260; sc.right = 260; sc.top = 260; sc.bottom = -260; sc.near = 10; sc.far = 1200; sun.shadow.radius = 6; sun.shadow.bias = -0.0008;
scene.add(sun, sun.target);
const bounce = new THREE.PointLight('#fff4e4', 1.0, 0, 0); bounce.position.copy(P(190, 60, 150)); scene.add(bounce);
const pend = new THREE.PointLight('#ffd9a0', .6, 0, 0); pend.position.copy(P(190, 150, 175)); scene.add(pend);
const cam = new THREE.PerspectiveCamera(70, innerWidth/innerHeight, 1, 3000);
window.shot = (eye, at, fov, cutaway) => {
  cam.fov = fov; cam.aspect = innerWidth/innerHeight; cam.updateProjectionMatrix();
  cam.position.copy(P(...eye)); cam.lookAt(P(...at));
  for (const m of ceilingParts) m.visible = !cutaway;
  renderer.render(scene, cam); return true;
};
window.ready = true;
</script></body></html>"""


def render_frames(scene, size, jobs, out_frame):
    """jobs: list of (eye, at, fov, cutaway); out_frame(i, png_bytes)."""
    from playwright.sync_api import sync_playwright
    html = HTML.replace("__THREE__", THREE).replace("__SCENE__", json.dumps(scene))
    hp = os.path.join(os.path.dirname(THREE), "_room3d.html")    # next to three.js so the module import resolves
    open(hp, "w").write(html)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                                             "--ignore-gpu-blocklist", "--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": size[0], "height": size[1]})
        pg.goto("file://" + hp)
        pg.wait_for_function("window.ready === true", timeout=120000)
        for i, (eye, at, fov, cut) in enumerate(jobs):
            pg.evaluate("([e,a,f,c]) => window.shot(e,a,f,c)", [eye, at, fov, cut])
            out_frame(i, pg.screenshot(type="png"))
        b.close()


def lerp(a, b, k):
    return [x + (y - x) * k for x, y in zip(a, b)]


def cam_at(path, t):
    for (t0, e0, a0), (t1, e1, a1) in zip(path, path[1:]):
        if t <= t1:
            k = ease_io((t - t0) / (t1 - t0))
            return lerp(e0, e1, k), lerp(a0, a1, k)
    return path[-1][1], path[-1][2]


def overlay(img, t, total, scene):
    """Hebrew title at the start, label on the dollhouse view."""
    W, H = img.size
    d = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(d)
    f1, f2 = font("FrankRuhlLibre.ttf", 92, 500), font("Heebo.ttf", 44, 300)
    a = ease_out((t - .2) / .6) * (1 - ease_io((t - 3.2) / .5))
    if t > total - 2.6:
        a = ease_out((t - (total - 2.6)) / .6)
    if a > 0:
        cx = 470
        for txt, f, y in ((scene["title"], f1, 330), (scene["sub"], f2, 430)):
            dr.text((cx, y), "‏" + txt, font=f, fill=(43, 33, 28, int(255 * a)), anchor="mm", direction="rtl", language="he")
        box = d.getbbox()
        if box:
            pill = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle((box[0] - 50, box[1] - 34, box[2] + 50, box[3] + 34), 46, fill=(250, 246, 240, int(215 * a)))
            img = Image.alpha_composite(img.convert("RGBA"), pill.filter(ImageFilter.GaussianBlur(1)))
    return Image.alpha_composite(img.convert("RGBA"), d).convert("RGB")


def main(profile, out, video=False):
    os.makedirs(out, exist_ok=True)
    scene = PROFILES[profile]()
    jobs = [(s["eye"], s["at"], s["fov"], s.get("cutaway", 0)) for s in scene["shots"].values()]
    names = list(scene["shots"])

    def save(i, png):
        p = os.path.join(out, f"{profile}_{names[i]}.png")
        open(p, "wb").write(png)
        print("wrote", p)
    render_frames(scene, (1600, 1200), jobs, save)
    if not video:
        return
    fps, total = 30, scene["path"][-1][0] + 1.0
    n = int(total * fps)
    vj = []
    for f in range(n):
        t = f / fps
        e, a = cam_at(scene["path"], t)
        vj.append((e, a, 88, 1 if t >= scene["cut_from"] else 0))
    mp4 = os.path.join(out, f"{profile}_walkthrough_silent.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                             "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "slow",
                             "-movflags", "+faststart", mp4], stdin=subprocess.PIPE)
    import io

    def put(i, png):
        img = overlay(Image.open(io.BytesIO(png)), i / fps, total, scene)
        buf = io.BytesIO()
        img.save(buf, "PNG", compress_level=1)
        proc.stdin.write(buf.getvalue())
        if i % 30 == 0:
            print("frame", i, "/", n, flush=True)
    render_frames(scene, (1080, 1920), vj, put)
    proc.stdin.close()
    proc.wait()
    print("wrote", mp4)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--video" in sys.argv)

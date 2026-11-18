// Moodboard template for Room Story Tell (5:4 landscape, Hebrew RTL).
// Slide 1: empty template, 8 labelled slots. Slide 2: filled example.
// Usage: NODE_PATH=<node_modules> node tools/moodboard/build.js OUT.pptx
const path = require("path");
const pptxgen = require("pptxgenjs");

const out = process.argv[2] || "moodboard_template.pptx";
const A = (f) => path.join(__dirname, "assets", f);

const W = 13.333, H = 10.667, M = 0.5, GAP = 0.3;
const C = { ink: "4A3226", muted: "8C7466", slot: "F3EEE7", line: "E2D6C8", sage: "5F7053", rose: "B9857B", white: "FFFFFF" };
const FONT = "Heebo";

const colW = (W - 2 * M - 2 * GAP) / 3;
const colX = [M + 2 * (colW + GAP), M + colW + GAP, M];      // right-to-left
const top = 2.15, bottom = H - 0.75;
const rowH = (bottom - top - 2 * GAP) / 3;
const rowY = [0, 1, 2].map((i) => top + i * (rowH + GAP));

// slot: [col, row, rowSpan, number, title, hint]
const SLOTS = [
  [0, 0, 2, "2", "קירות", "הטיפול בקיר המוביל: צבע, טפט, פסים או חיפוי. רק אחד"],
  [0, 2, 1, "1", "פלטת צבעים", null],
  [1, 0, 1, "4", "ריהוט מרכזי", "הרהיט הגדול: עריסה, מיטה. מה שקיים, כפי שהוא"],
  [1, 1, 1, "4", "ריהוט מרכזי", "ארון, שידה או אחסון. במידות שנכנסות לחדר"],
  [1, 2, 1, "3", "חומרים וטקסטורות", "3 דוגמיות קטנות: עץ, בד, קש, בוקלה"],
  [2, 0, 1, "5", "טקסטיל", "שטיח, וילון או מצעים"],
  [2, 1, 1, "6", "תאורה", "מנורת תקרה ומנורת לילה"],
  [2, 2, 1, "7", "הפרט האישי", "מה שהופך את החדר לשל הילד הזה"],
];

const pres = new pptxgen();
pres.defineLayout({ name: "BOARD_5x4", width: W, height: H });
pres.layout = "BOARD_5x4";
pres.title = "לוח השראה · Room Story Tell";
pres.author = "Room Story Tell";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

const he = (o) => Object.assign({ rtlMode: true, lang: "he-IL", fontFace: FONT, isTextBox: true, margin: 0 }, o);

function slotRect(col, row, span) {
  return { x: colX[col], y: rowY[row], w: colW, h: rowH * span + GAP * (span - 1) };
}

function chip(slide, r, num, title) {
  slide.addText([{ text: `${num} · `, options: { color: C.rose, bold: true } }, { text: title, options: { color: C.ink } }],
    he({ x: r.x + 0.15, y: r.y + 0.12, w: r.w - 0.3, h: 0.32, fontSize: 11, align: "right", objectName: `label ${num} ${title}` }));
}

function header(slide, title, concept, filled) {
  slide.addText(title, he({ x: M, y: 0.45, w: W - 2 * M, h: 0.7, fontSize: 30, bold: true, color: C.ink, align: "right", objectName: "title" }));
  slide.addText(concept, he({ x: M + 3.2, y: 1.2, w: W - 2 * M - 3.2, h: 0.75, fontSize: 13, color: filled ? C.ink : C.muted,
    align: "right", valign: "top", objectName: "concept" }));
  slide.addText("ROOM STORY TELL", { x: M, y: 0.62, w: 3, h: 0.3, fontSize: 9, charSpacing: 4, color: C.muted, fontFace: FONT, margin: 0, isTextBox: true });
  slide.addText("מה הכי אהבת? ויש משהו שפחות מדבר אלייך? 🤍", he({ x: M, y: H - 0.55, w: W - 2 * M, h: 0.3, fontSize: 10, color: C.muted, align: "right", objectName: "footer" }));
}

function swatches(slide, r, items) {
  // items: [hex, name, use]
  const n = items.length, d = 0.78;
  const gap = (r.w - 0.4 - n * d) / (n - 1);
  items.forEach(([hex, name, use], i) => {
    const x = r.x + r.w - 0.2 - d - i * (d + gap);
    slide.addShape(pres.shapes.OVAL, { x, y: r.y + 0.6, w: d, h: d, fill: { color: hex }, line: { color: C.line, width: 0.75 }, objectName: `swatch ${i + 1}` });
    slide.addText([{ text: name, options: { bold: true, breakLine: true } }, { text: use }],
      he({ x: x - 0.2, y: r.y + 0.6 + d + 0.08, w: d + 0.4, h: 0.6, fontSize: 9, color: C.ink, align: "center", valign: "top" }));
  });
}

// ---------------------------------------------------------------- slide 1: template
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  header(s, "לוח השראה · החדר של ___", "כתבי כאן 2–3 משפטים: מה הילד/ה אוהב/ת, מה ביקשתם, ואיך זה מתורגם לעיצוב. למשל: חדר רך ושקט שיגדל איתה, עם פינת ספרים לאח הגדול.", false);
  SLOTS.forEach(([col, row, span, num, title, hint], i) => {
    const r = slotRect(col, row, span);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { ...r, rectRadius: 0.06, fill: { color: C.slot }, line: { color: C.line, width: 0.75 }, objectName: `slot ${num} ${title} ${i}` });
    chip(s, r, num, title);
    if (hint) s.addText(hint, he({ x: r.x + 0.35, y: r.y + r.h / 2 - 0.35, w: r.w - 0.7, h: 0.7, fontSize: 11, color: C.muted, align: "center", valign: "middle" }));
    if (num === "1") swatches(s, r, [["F2EBE1", "שם הגוון", "קירות"], ["D9B8AE", "שם הגוון", "משני"], ["A9BC9A", "שם הגוון", "הדגשה"], ["C9A98B", "שם הגוון", "עץ"]]);
  });
  s.addNotes("איך משתמשים: מוחקים את הטקסט שבתוך כל מסגרת ומכניסים תמונה באותו גודל. 8–12 תמונות לכל היותר. פלטה אחת, תבנית קיר אחת, גוון עץ אחד. מוסיפים תווית קצרה לכל תמונה.");
}

// ---------------------------------------------------------------- slide 2: filled example
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  header(s, "לוח השראה · החדר של התינוקת",
    "חדר רך ושקט שיגדל איתה. טפט ארנבים בצבעי מים על קיר העריסה בלבד, שאר הקירות בשמנת חמה, עץ טבעי אחד בכל החדר, ופינת ספרים קטנה בשביל האח הגדול.", true);
  const IMG = {
    "קירות": [["mural.jpg", "טפט ארנבים · קיר העריסה בלבד"]],
    "ריהוט מרכזי0": [["crib.jpg", "העריסה הקיימת · לבנה"]],
    "ריהוט מרכזי1": [["wardrobe.jpg", "ארון לבן בפאנלים · לבחור דגם 2 דלתות"]],
    "טקסטיל": [["rug.jpg", "שטיח שמנת · מחמם את האריחים האפורים"]],
    "תאורה": [["lamp.jpg", "מנורת קיר מעץ · אור חם וצהבהב"]],
    "הפרט האישי": [["house.jpg", "בית-מדף לספרים של האח הגדול"]],
  };
  let furn = 0;
  SLOTS.forEach(([col, row, span, num, title]) => {
    const r = slotRect(col, row, span);
    const key = title === "ריהוט מרכזי" ? title + furn++ : title;
    if (title === "פלטת צבעים") {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { ...r, rectRadius: 0.06, fill: { color: "FAF7F3" }, line: { color: C.line, width: 0.75 } });
      chip(s, r, num, title);
      swatches(s, r, [["F2EBE1", "שמנת חמה", "קירות"], ["C9978E", "ורוד מעושן", "טקסטיל"], ["A9BC9A", "ירוק מרווה", "הדגשה"], ["B98A5E", "אלון טבעי", "עץ"]]);
      return;
    }
    if (title === "חומרים וטקסטורות") {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { ...r, rectRadius: 0.06, fill: { color: "FAF7F3" }, line: { color: C.line, width: 0.75 } });
      chip(s, r, num, title);
      const sq = (r.w - 0.4 - 2 * 0.2) / 3;
      [["wood.jpg", "עץ אלון"], ["silk.jpg", "פשתן מרווה"], ["fabric.jpg", "כותנה משובצת"]].forEach(([f, lab], i) => {
        const x = r.x + r.w - 0.2 - sq - i * (sq + 0.2);
        s.addImage({ path: A(f), x, y: r.y + 0.55, w: sq, h: sq, sizing: { type: "cover", w: sq, h: sq }, altText: lab });
        s.addText(lab, he({ x, y: r.y + 0.6 + sq, w: sq, h: 0.3, fontSize: 9, color: C.ink, align: "center" }));
      });
      return;
    }
    const [f, cap] = IMG[key][0];
    s.addImage({ path: A(f), ...r, sizing: { type: "cover", w: r.w, h: r.h }, altText: cap });
    s.addShape(pres.shapes.RECTANGLE, { x: r.x, y: r.y + r.h - 0.42, w: r.w, h: 0.42, fill: { color: C.white, transparency: 12 }, line: { type: "none" } });
    s.addText([{ text: `${num} · `, options: { color: C.rose, bold: true } }, { text: cap, options: { color: C.ink } }],
      he({ x: r.x + 0.12, y: r.y + r.h - 0.38, w: r.w - 0.24, h: 0.34, fontSize: 10, align: "right", valign: "middle" }));
  });
  s.addNotes("דוגמה: הלוח של נועה אחרי התיקונים. קיר מוביל אחד, ארון של 2 דלתות, תאורה, גוון עץ אחד ותוויות.");
}

pres.writeFile({ fileName: out }).then((f) => console.log("wrote", f));

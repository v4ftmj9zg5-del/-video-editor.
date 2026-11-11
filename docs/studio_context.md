# Studio context (carried over from the "Instagram reel analysis" session, Oct 12 - Nov 10 2026)

Read this before working with Tamar. Talk to her in Hebrew only (she objected
when answers came in English).

## Who she is
- Tamar, Instagram creator `roomstorytell_`, interior designer of kids' and nursery rooms.
  So far the only room she fully designed was her own kids' room; she is launching a business.
- Business: **online design service, a render plus a shopping list.**
  - Two packages: **1,000 ₪** and **1,800 ₪** (the 1,800 one tagged "מומלצת", never
    "הכי מבוקשת": no invented claims). Both include **one week of WhatsApp support** after delivery.
  - Waitlist / lead CTA: "כתבי לי ״חדר״".
- Look of the account: soft palette **cream, antique pink, sage, chocolate**; serif English
  title cards with small Hebrew subtitle; unified grid covers (tools/covers.py).
- Software she uses: **SketchUp Pro 2021 on Windows** (3D Warehouse doesn't load in-app:
  download in the browser), AutoCAD (opens our DXF, saves as DWG). She is learning both from us
  step by step; next lessons were materials, camera scenes, then D5 render.
- Connected tools in that session: Metricool MCP (brandId 7377941), Canva MCP (image quota ran out).

## What already exists in tools/ (branch covers-tool, merged here)
- `covers.py` unified Reel covers. `carousel/` launch carousel (6 slides, her handwriting font).
- `client_kit/`: questionnaire, measuring guide (3 pages, own-sketch page, window/door questions,
  room video), two-package quote, delivery template, workflow, zoom intro-call sheet,
  shopping-list workbook. All built to **fillable PDFs** for phone (build.sh, fillable.py).
- Plans: `floorplan.py` (to-scale options + 60 cm clearance checks), `cadplan.py` (A4 1:20 PDF + DXF,
  layers WALLS/OPENINGS/FURNITURE/DIMS/TEXT/HATCH/HIDDEN, cm), `sketchup_room.py` (Ruby + DAE),
  `room3d.py` (three.js stills + vertical walkthrough), ROOM_PROFILE=michal.
- Reels: `reel_how_it_works.py` (hook, 4 steps, own room, CTA), `reel_room_build.py`,
  `reel_room_drop.py` (furniture drop-in, LaMa empty-shell `room_shell.py`), `reel_audio.py`
  (original music bed, SFX, ducked VO; -14 LUFS). VO: edge-tts he-IL-HilaNeural (patch certifi to
  /root/.ccr/ca-bundle.crt), QA pronunciation with faster-whisper; fix with rephrasing/niqqud.
- `moodboard/`: PPTX template (8 slots), direction sheet + 6 wallpaper options for Michal's room.

## Hard-won technical notes
- Hebrew/bidi: wrap numbers and Latin in LRI/PDI, write "1 מתוך 2" not "1 / 2", avoid "×" (use "על"),
  write budget ranges in words; Excel cells need readingOrder=2. Verify a rendered frame/page.
- Artifacts can't ship zip/xlsx/pptx directly: base64 .txt decoded in the page. Her phone can't
  open DXF/m4a: give a download page with player + save buttons.
- faster-whisper: pass a numpy array, not a path (PyAV `metadata_errors` error).

## Practice simulations (role-play, she is the designer)
1. **Noa Levi** - nursery. Option C layout: nursing chair by the socket, crib beside it (127 cm
   between), reading nook under the window, wall shelf. Window: white aluminium, sill 95, head 210,
   shutter box drops 235-260. Shopping list 32 rows with sourced prices.
2. **Michal** - shared room for two brothers, rental (no paint/renovation; removable wallpaper,
   2-screw shelves, textiles). **Itay (7)** sleeps on top, "no baby stuff", builds big Lego;
   **Yonatan (4)** below, afraid of the dark. Palette olive / night blue / mustard / natural wood /
   cream, concept "הרפתקה בטבע". Floor grey 60x60 glossy tiles (big rug + anti-slip).
   Ceiling 260: top mattress at most ~180 cm high, rail >= 16 cm above mattress, EN 747, anchor to wall.
   Night light: ~2200K, dimmable, low, timer, button he can reach. Wallpaper: lighter version of
   her chosen mountain mural (blue kept, ~15% lighter).
   **Open item:** update the layout plan with the taller bunk bed and Itay's display shelf
   (at top-bunk height, by the ladder, not over his head, 15-20 cm deep, lip, warm LED).

## Open offers she hasn't confirmed
W/D/H fields in the questionnaire; Google Form for the landing page; her own voice instead of AI
VO; confirm Noa's socket location.

## Instagram performance snapshot (Metricool, brandId 7377941, pulled 2026-11-11)
13 reels, 31 Aug - 26 Oct 2026. Views 174-699 (median ~338), reach 123-439.
3-second hold 16-43% (skip 57-84%); avg watch 4.6-11.9 s. Saves 0-2, shares 0-2 per reel.
- Best reach: intro "נעים מאוד, אני תמר" (20 Oct, 699 views, 43% hold) and an uncaptioned
  reel 26 Oct (506 views, 43% hold).
- Longest watch: "5 nursery mistakes" (12 Oct, 11.9 s), focal-point question (10.5 s),
  curtains (10.2 s): list / practical-tip reels hold attention best.
- Weakest: lighting reel 19 Oct (84% skip, 174 views): hook didn't stop the scroll.
- Main gaps: first 3 seconds, and almost no saves/shares (needs save-worthy, specific tips).

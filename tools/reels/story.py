"""Content-aware storyboard: read the Hebrew transcript, find what is being talked
about (numbers, mistakes/tips, furniture, lighting, colours, materials, space,
before/after, calls to action) and plan one motion-graphics scene per idea, timed
to the word that triggers it. Writes the plan as JSON (for Remotion) and as a
readable Hebrew storyboard table.
"""
import re

from .broll import stems
from .cuts import sound_key, to_out

# ---------------------------------------------------------------- lexicon
FURNITURE = {"ספה": "sofa", "ספות": "sofa", "כורסה": "armchair", "כורסא": "armchair", "כורסאות": "armchair",
             "כיסא": "armchair", "כסא": "armchair", "שולחן": "table", "שולחנות": "table", "מיטה": "bed",
             "מדף": "shelf", "מדפים": "shelf", "ספרייה": "shelf", "שטיח": "rug", "שטיחים": "rug",
             "צמח": "plant", "צמחים": "plant", "עציץ": "plant", "עציצים": "plant"}
FURNITURE_HE = {"sofa": "ספה", "armchair": "כורסה", "table": "שולחן", "bed": "מיטה", "shelf": "מדפים",
                "rug": "שטיח", "plant": "צמחים"}
LIGHT = {"תאורה", "אור", "מנורה", "מנורות", "נברשת", "ספוט", "ספוטים", "חשוך", "חשוכה", "תאורת", "אורות"}
COLOUR_WORDS = {"צבע", "צבעים", "גוון", "גוונים", "פלטה", "פלטת"}
COLOURS = {"לבן": "#F4F1EA", "לבנה": "#F4F1EA", "שמנת": "#EFE6D2", "בז": "#D9C7A7", "חום": "#7B5A43",
           "אפור": "#A7A39C", "שחור": "#2B2A28", "ירוק": "#7C8B6A", "זית": "#707A4E", "כחול": "#3E5C76",
           "תכלת": "#A9C6D8", "טרקוטה": "#C06A4B", "ורוד": "#E3B5A4", "צהוב": "#E9C46A", "חרדל": "#C9A227",
           "אדום": "#A63D32", "כתום": "#D9822B", "זהב": "#C8A45D", "נחושת": "#B87333", "אבן": "#B9B3A9"}
COLOUR_NAME = {"בז": "בז׳", "זית": "ירוק זית", "לבנה": "לבן"}
DEFAULT_PALETTE = [("שמנת", "#EFE6D2"), ("בז׳", "#D9C7A7"), ("ירוק זית", "#707A4E"), ("טרקוטה", "#C06A4B"),
                   ("פחם", "#2B2A28")]
MATERIALS = {"עץ": "wood", "שיש": "marble", "פשתן": "linen", "בד": "linen", "בדים": "linen", "אבן": "stone",
             "ראטן": "rattan", "קש": "rattan", "קטיפה": "velvet"}
MATERIAL_HE = {"wood": "עץ", "marble": "שיש", "linen": "פשתן", "stone": "אבן", "rattan": "ראטן", "velvet": "קטיפה"}
SPACE = {"קטן", "קטנה", "מרווח", "מרווחת", "מקום", "שטח", "מטר", "מטרים", "גדול"}
BIG = {"ענק", "ענקית", "ענקי", "ענקיים", "גדול", "גדולה", "גדולים", "מסיבית"}
CTA = {"תעקבו", "עקבו", "תשמרו", "שמרו", "לייק", "תגובות", "שתפו", "תשתפו", "תכתבו"}
TIP = {"טיפ", "טיפים", "סוד", "סודות", "חשוב", "כלל"}
BEFORE, AFTER = {"לפני"}, {"אחרי"}
CHANGE = {"מהפך", "שינוי", "הפכתי", "שדרגתי", "שדרוג"}
CARDINAL = {"אחת": 1, "אחד": 1, "שתיים": 2, "שניים": 2, "שתי": 2, "שלוש": 3, "שלושה": 3, "ארבע": 4,
            "ארבעה": 4, "חמש": 5, "חמישה": 5, "שש": 6, "שישה": 6, "שבע": 7, "שבעה": 7, "שמונה": 8,
            "תשע": 9, "תשעה": 9, "עשר": 10, "עשרה": 10}
ORDINAL = {"ראשון": 1, "ראשונה": 1, "שני": 2, "שנייה": 2, "שניה": 2, "שלישי": 3, "שלישית": 3,
           "רביעי": 4, "רביעית": 4, "חמישי": 5, "חמישית": 5, "אחרון": 0, "אחרונה": 0}
COUNTABLE = {"טעות", "טעויות", "טיפ", "טיפים", "שלב", "שלבים", "כלל", "כללים", "דרך", "דרכים", "סוד", "סודות",
             "רעיון", "רעיונות", "דברים", "פריטים", "צבעים", "גוונים"}
STOP = {"את", "של", "על", "עם", "זה", "זו", "אני", "אתם", "הוא", "היא", "כל", "גם", "רק", "יותר", "מאוד",
        "איך", "מה", "לא", "כן", "יש", "אין", "הכי", "לכם", "לי", "שלי", "שלכם", "היום", "ככה"}

# Priority when one moment could show two things (higher wins)
PRIORITY = {"beforeAfter": 9, "number": 8, "mistake": 7, "lighting": 6, "palette": 6, "furniture": 5,
            "materials": 5, "cta": 5, "space": 3, "callout": 2, "kinetic": 1}
LAYOUT = {"number": "card", "furniture": "split"}


def clean(w):
    return re.sub(r"[^\wא-ת׳']", "", re.sub(r"[֑-ׇ]", "", w)).replace("'", "")


_SOUND_CACHE = {}


def hit(word, vocab):
    """vocab entry the word matches, with or without Hebrew prefixes; falls back to a
    sound-alike match because Whisper spells some words differently (תרקוטה / טרקוטה)."""
    cands = stems(clean(word))
    for s in cands:
        if s in vocab:
            return s
    key = id(vocab)
    if key not in _SOUND_CACHE:
        _SOUND_CACHE[key] = {}
        for v in vocab:
            if len(v) >= 3:
                _SOUND_CACHE[key].setdefault(sound_key([v]), []).append(v)
    by_sound = _SOUND_CACHE[key]
    for s in cands:
        opts = by_sound.get(sound_key([s])) if len(s) >= 3 else None
        if opts:  # several words can sound alike (טעות / טעויות): take the closest length
            return min(opts, key=lambda v: abs(len(v) - len(s)))
    return None


def detect(words, total_hint):
    """Triggers in one phrase: [(word_index, kind, params)]."""
    found = []
    ws = [w["w"] for w in words]
    n = len(ws)
    for i, w in enumerate(ws):
        c = clean(w)
        # numbers: digits or number words followed by a countable noun -> big number
        val = int(c) if c.isdigit() and 0 < int(c) < 1000 else CARDINAL.get(c)
        if val is not None and (c.isdigit() or (i + 1 < n and hit(ws[i + 1], COUNTABLE))):
            # canonical spelling of the counted noun (ASR may misspell it: תאויות -> טעויות)
            label = (hit(ws[i + 1], COUNTABLE) or clean(ws[i + 1])) if i + 1 < n else ""
            found.append((i, "number", dict(value=val, label=label)))
            continue
        # ordinals after a countable noun: "טעות ראשונה", "טיפ שני"
        if c in ORDINAL and i > 0 and hit(ws[i - 1], COUNTABLE):
            noun = clean(ws[i - 1])
            k = ORDINAL[c] or total_hint or 1
            found.append((i - 1, "mistake", dict(n=k, total=max(total_hint or 0, k), word=noun,
                                                  good=hit(ws[i - 1], {"טיפ", "טיפים", "סוד", "כלל"}) is not None)))
            continue
        if hit(w, BEFORE) and any(hit(x, AFTER) for x in ws[i + 1:]) or hit(w, CHANGE):
            found.append((i, "beforeAfter", {}))
            continue
        f = hit(w, FURNITURE)
        if f:
            art = FURNITURE[f]
            near = ws[max(0, i - 2):i + 3]
            big = any(hit(x, BIG) for x in near)
            mark = "bad" if any(hit(x, {"טעות", "טעויות"}) for x in ws) or big else None
            found.append((i, "furniture", dict(art=art, label=FURNITURE_HE[art], big=big, mark=mark)))
            continue
        if hit(w, LIGHT):
            found.append((i, "lighting", dict(label="אור חם ורך")))
            continue
        if hit(w, COLOUR_WORDS) or hit(w, COLOURS):
            names = []
            for x in ws:
                h = hit(x, COLOURS)
                if h and h not in [m[0] for m in names]:
                    names.append((h, COLOURS[h]))
            # "ירוק זית" is one colour
            if any(h == "זית" for h, _ in names):
                names = [m for m in names if m[0] != "ירוק"]
            cols = [dict(name=COLOUR_NAME.get(h, h), hex=v) for h, v in names]
            named = len(cols) >= 2
            if not named:
                cols = [dict(name=a, hex=b) for a, b in DEFAULT_PALETTE]
            found.append((i, "palette", dict(colors=cols[:5], named=named)))
            continue
        m = hit(w, MATERIALS)
        if m:
            mats = []
            for x in ws:
                h = hit(x, MATERIALS)
                if h and MATERIALS[h] not in [q["tex"] for q in mats]:
                    mats.append(dict(name=MATERIAL_HE[MATERIALS[h]], tex=MATERIALS[h]))
            found.append((i, "materials", dict(items=mats[:3])))
            continue
        if hit(w, CTA):
            found.append((i, "cta", {}))
            continue
        if hit(w, TIP) and not any(hit(x, CTA) for x in ws):
            rest = [clean(x) for x in ws[i + 1:i + 5] if clean(x)]
            found.append((i, "callout", dict(tag="טיפ", label=" ".join(rest[:3]) or c)))
            continue
        if hit(w, SPACE) and not any(k == "furniture" for _, k, _ in found):
            found.append((i, "space", dict(label="מרגיש גדול" if hit(w, {"קטן", "קטנה"}) else "מקום")))
    # one of each kind per phrase, first mention wins
    seen, out = set(), []
    for t in sorted(found, key=lambda x: x[0]):
        if t[1] not in seen:
            seen.add(t[1])
            out.append(t)
    return out


def key_word(words):
    cands = [clean(w["w"]) for w in words if clean(w["w"]) and clean(w["w"]) not in STOP]
    return max(cands, key=len) if cands else ""


def plan(phrases, timeline, preset, out_dur, broll_places=(), ba_images=None):
    """Scenes on the output timeline + one storyboard row per kept phrase."""
    style = preset["name"]
    dyn = style == "dynamic"
    min_len, max_len = (1.3, 3.6) if dyn else (1.8, 4.6)
    total_hint = None
    raw = []  # (start, end, kind, params, phrase_index, text)
    for pi, ph in enumerate(phrases):
        words = []
        for w in ph["words"]:
            s, e = to_out(timeline, w["s"]), to_out(timeline, w["e"])
            if s is not None and e is not None:
                words.append(dict(w=w["w"], s=s, e=e))
        if not words:
            continue
        p_e = words[-1]["e"]
        trig = detect(words, total_hint)
        for _, k, prm in trig:
            if k == "number":
                total_hint = prm["value"]
        if pi == 0 and not any(k in ("number", "beforeAfter") for _, k, _ in trig):
            trig = [(0, "kinetic", dict(words=[clean(w["w"]) or w["w"] for w in words], key=key_word(words)))] + trig
        trig.sort(key=lambda x: x[0])
        for j, (wi, k, prm) in enumerate(trig):
            s = max(0.0, words[wi]["s"] - 0.12)
            nxt = words[trig[j + 1][0]]["s"] - 0.12 if j + 1 < len(trig) else max(p_e + 0.35, s + min_len)
            raw.append([s, min(nxt, s + max_len), k, prm, pi, ph["text"]])
    # resolve overlaps and too-short scenes by priority
    raw.sort(key=lambda r: r[0])
    scenes = []
    for r in raw:
        if r[2] == "beforeAfter" and ba_images:
            r[3].update(ba_images)
        if scenes and r[0] < scenes[-1][1]:
            prev = scenes[-1]
            if r[0] - prev[0] >= min_len * 0.8:
                prev[1] = r[0]  # cut the previous one short
            elif PRIORITY[r[2]] > PRIORITY[prev[2]]:
                scenes[-1] = r
                continue
            else:
                continue
        scenes.append(r)
    merged = []
    for r in scenes:  # the same idea over two phrases is one scene ("too many colours ... beige, olive")
        if merged and merged[-1][2] == r[2] and r[0] - merged[-1][1] < 1.2 and r[2] not in ("mistake", "number"):
            prev = merged[-1]
            prev[1] = max(prev[1], min(r[1], prev[0] + max_len * 1.4))
            if r[2] == "palette" and r[3].get("named") and not prev[3].get("named"):
                prev[3] = r[3]
            continue
        merged.append(r)
    scenes = merged
    res = []
    for i, (s, e, k, prm, pi, text) in enumerate(scenes):
        e = min(e, out_dur - 0.05)
        if e - s < 0.9:
            continue
        if s < 0.3:
            tr = "none"
        elif dyn:
            tr = "flash" if k in ("number", "beforeAfter", "mistake", "cta") else "whip"
        else:
            tr = "leak" if k in ("beforeAfter", "lighting", "palette", "number") else "fade"
        res.append(dict(id=len(res), kind=k, s=round(s, 3), e=round(e, 3), text=text, layout=LAYOUT.get(k, "full"),
                        transition=tr, params=prm, phrase=pi))
    punches = []
    for sc in res:
        if sc["layout"] == "full" and sc["kind"] not in ("beforeAfter",):
            punches.append(dict(t=sc["s"], amount=0.07 if dyn else 0.035))
    if dyn:  # also on every jump cut that has no scene
        starts = {round(sc["s"], 1) for sc in res}
        for c in timeline[1:]:
            if round(c["out_s"], 1) not in starts:
                punches.append(dict(t=c["out_s"], amount=0.05))
    return res, sorted(punches, key=lambda p: p["t"])


# ------------------------------------------------------------- storyboard
DESC = {
    "kinetic": ("טיפוגרפיה קינטית של משפט הפתיחה", {"dynamic": "המילים נוחתות בזו אחר זו עם קפיץ, מילת מפתח עם סימון צהוב",
                                                   "elegant": "המילים עולות מטשטוש, מילת המפתח בסריף ובצבע טרקוטה"}),
    "number": ("מספר ענק: {value} {label}", {"dynamic": "ספירה 0→{value}, טבעת מצטיירת, חלקיקים; הווידאו מתכווץ לכרטיס",
                                            "elegant": "ספירה רכה 0→{value}, טבעת דקה, רשת עדינה ברקע; הווידאו בכרטיס"}),
    "mistake": ("תג \"{word} #{n}\" עם חותמת", {"dynamic": "התג נופל מלמעלה, חותמת נוחתת, נקודות התקדמות {n}/{total}",
                                              "elegant": "כרטיס מחליק פנימה, חותמת עדינה, פסי התקדמות {n}/{total}"}),
    "furniture": ("איור {label} מצטייר בקו", {"dynamic": "מסך מפוצל: איור למעלה, וידאו למטה; קו מצטייר ואז מילוי",
                                             "elegant": "מסך מפוצל: איור בקו דק על רקע שמנת, מילוי מתמלא לאט"}),
    "lighting": ("מעבר תאורה: חשוך ← אור חם", {"dynamic": "החדר מחשיך, מנורה מתנדנדת ונדלקת, הילה חמה, 6500K→2700K",
                                               "elegant": "החשכה רכה, מנורה יורדת ונדלקת, אור חם מתפשט, 6500K→2700K"}),
    "palette": ("פלטת צבעים: {names}", {"dynamic": "שבבי צבע נפרשים בזה אחר זה עם סיבוב, HEX מוקלד",
                                       "elegant": "עיגולי צבע עולים בעדינות, שמות בסריף, HEX מוקלד"}),
    "materials": ("דוגמיות חומרים: {mats}", {"dynamic": "עיגולי טקסטורה מתגלגלים פנימה", "elegant": "עיגולי טקסטורה מתגלגלים פנימה לאט"}),
    "beforeAfter": ("לפני / אחרי במסך מלא", {"dynamic": "פס הזזה חושף את ה'אחרי' ומתנדנד", "elegant": "פס הזזה איטי חושף את ה'אחרי'"}),
    "space": ("חיצי מידות מתרחבים", {"dynamic": "מסגרת החדר גדלה + תווית \"{label}\"", "elegant": "מסגרת מקווקוות נפתחת + תווית"}),
    "callout": ("חץ הסבר: \"{label}\"", {"dynamic": "נקודה פועמת, קו מצטייר, תווית צהובה מחליקה", "elegant": "נקודה פועמת, קו דק, כרטיס שמנת"}),
    "cta": ("כפתורי עקבו + שמרו", {"dynamic": "הכפתורים קופצים, אצבע לוחצת, לבבות עפים", "elegant": "הכפתורים עולים, לחיצה עדינה"}),
}
TRANS = {"flash": "הבזק לבן + פאנץ' אין", "whip": "Whip pan עם טשטוש תנועה", "leak": "דליפת אור חמה",
         "fade": "דיזולב רך", "none": "—"}


def describe(sc, style):
    p = dict(sc["params"])
    p.setdefault("label", "")
    p["names"] = ", ".join(c["name"] for c in p.get("colors", []))
    p["mats"] = ", ".join(m["name"] for m in p.get("items", []))
    vis, anim = DESC[sc["kind"]]
    return _fmt(vis, p), _fmt(anim[style], p)


def _fmt(s, p):
    try:
        return s.format(**p)
    except (KeyError, IndexError):
        return s


def storyboard(phrases, timeline, scenes, broll_places, style):
    rows = []
    for pi, ph in enumerate(phrases):
        ws = [(to_out(timeline, w["s"]), to_out(timeline, w["e"])) for w in ph["words"]]
        ws = [x for x in ws if x[0] is not None and x[1] is not None]
        if not ws:
            continue
        s, e = ws[0][0], ws[-1][1]
        mine = [sc for sc in scenes if sc["phrase"] == pi]
        vis = [describe(sc, style) for sc in mine]
        br = [f"{b[2]['path'].split('/')[-1]}" for b in broll_places if b[0] < e and b[1] > s]
        art = [f"איור {sc['params']['label']}" for sc in mine if sc["kind"] == "furniture"]
        rows.append(dict(
            time=f"{s:05.2f}–{e:05.2f}",
            sentence=ph["text"],
            visual=" + ".join(v for v, _ in vis) or ("וידאו + כתוביות, פאנץ' אין על הקאט" if style == "dynamic"
                                                     else "וידאו + כתוביות, דחיפה איטית"),
            animation=" | ".join(a for _, a in vis) or "—",
            broll=", ".join(br + art) or "—",
            transition=", ".join(TRANS[sc["transition"]] for sc in mine) or
            ("קאט קפיצה + פאנץ' אין" if style == "dynamic" else "דיזולב רך"),
            timing=", ".join(f"{sc['kind']} {sc['s']:.2f}–{sc['e']:.2f}s" for sc in mine) or f"{s:.2f}–{e:.2f}s",
        ))
    return rows


def storyboard_md(rows, style, title=""):
    head = f"# סטוריבורד — {'דינמי' if style == 'dynamic' else 'אלגנטי'}{' — ' + title if title else ''}\n\n"
    cols = ["זמן", "משפט", "אפקט ויזואלי", "אנימציה", "B-roll", "מעבר", "תזמון"]
    out = head + "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    for r in rows:
        out += "| " + " | ".join(str(r[k]).replace("|", "/") for k in
                                 ("time", "sentence", "visual", "animation", "broll", "transition", "timing")) + " |\n"
    return out

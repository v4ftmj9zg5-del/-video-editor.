"""Example: fill the shopping-list workbook for the Levi nursery (simulation client).

Prices and links are left for the designer to source (cells highlighted); existing
items carry price 0 so totals only count what is bought.
Usage: fill_noa_list.py OUT.xlsx [IMG_DIR]
IMG_DIR (optional) holds product photos named as in PHOTOS; they go on a second sheet.
"""
import os
import sys

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopping_list import build  # noqa: E402

ROWS = 32
TODO = PatternFill("solid", start_color="F3E3B8", end_color="F3E3B8")
EXIST = PatternFill("solid", start_color="E3E7DA", end_color="E3E7DA")

# category, item, store, dims, qty, existing?, alternative, notes
ITEMS = [
    ("רהיטים", "עריסה לבנה עם מעקות (קיימת)", "", "66 על 124, גובה 86", 1, True, "", "מתנה מההורים, לא נכנסת לתקציב"),
    ("רהיטים", "שידה HEMNES לבנה (קיימת)", "איקאה", "108 על 50, גובה 96", 1, True, "", "משמשת גם כשידת החתלה"),
    ("רהיטים", "כורסת הנקה אפורה (קיימת)", "", "75 על 80, גובה 95", 1, True, "", "לשדרג עם כרית ושמיכה בגווני הפלטה"),
    ("רהיטים", "גוף ארון PAX לבן", "איקאה", "100 על 58, גובה 236", 1, False, "", "לעגן לקיר! לבדוק שהדלת נפתחת בלי לפגוע בעריסה"),
    ("רהיטים", "זוג דלתות פאנל לבנות לארון", "איקאה", "שתי דלתות, כל אחת 50 על 229", 1, False, "", "סגנון פאנלים, כדי להתאים לשידה"),
    ("רהיטים", "פנים ארון: 2 מוטות, מדפים ו-2 מגירות", "איקאה", "לארון ברוחב 100", 1, False, "", "בגדי תינוק קטנים: יותר מגירות, פחות תלייה"),
    ("קירות וצבע", "פס עץ לסגירת הרווח בין הארון לתקרה", "נגר / טמבוריה", "100 על 24", 1, False, "", "לצבוע בלבן כמו הארון"),
    ("אחסון", "בית-מדף לספרים", "", "", 1, False, "שני מדפי תמונות מאיקאה, צבועים במרווה", "לפינת הספרים של האח הגדול"),
    ("אחסון", "סלסלות קלועות לשידה, לארון ולמדפים", "", "", 5, False, "", "כולל 2 קטנות למדפים"),
    ("אחסון", "2 מדפים צפים מעץ טבעי", "", "אורך 90, עומק 20 בערך", 2, False, "",
     "בין הארון לדלת, מעל הקרניז. לקבע לקיר בברגים, ולשים עליהם רק פריטים קלים"),
    ("אחסון", "משטח החתלה + 2 כיסויים", "", "50 על 70", 1, False, "", "על השידה"),
    ("קירות וצבע", "טפט ארנבים בצבעי מים", "", "קיר העריסה, מעל הקרניז (למדוד)", 1, False, "מדבקות קיר של ארנבים", "קיר אחד בלבד. להזמין עם 10% עודף"),
    ("קירות וצבע", "צבע ורוד עתיק לחצי התחתון של הקירות", "טמבור / נירלט", "כל הקירות, עד גובה 95", 1, False, "",
     "גוון ההדמיה: DEC4BA. להתאים מול מניפת צבעים בחנות ולבדוק דוגמית על הקיר"),
    ("קירות וצבע", "צבע שמנת חמה לחצי העליון", "טמבור / נירלט", "מעל הקרניז, בקירות בלי טפט", 1, False, "",
     "גוון ההדמיה: F0E9DD. להתאים מול מניפת צבעים בחנות ולבדוק דוגמית על הקיר"),
    ("קירות וצבע", "פס קרניז לבן לחלוקת הקיר", "נגר / חנות פרופילים", "היקף החדר, בגובה 95", 1, False, "", "צבוע לבן"),
    ("טקסטיל", "שטיח עגול קלוע מסיבים טבעיים", "", "קוטר 140 עד 160", 1, False, "שטיח כותנה קלוע עגול, כביס",
     "שימי לב: סיבים טבעיים לא נכבסים במכונה, ונועה ביקשה שטיח כביס (חתול ותינוקת). לשקול את החלופה"),
    ("טקסטיל", "וילון פשתן חצי שקוף בשמנת", "", "שתי יריעות, מהמוט עד הרצפה", 1, False, "", "רוחב בד כפול מרוחב המוט, בשביל גלים רכים"),
    ("טקסטיל", "מוט וילון דק בגוון כהה", "", "180 עד 200, רחב מהחלון", 1, False, "", "לתלות גבוה, מעל ארגז התריס"),
    ("טקסטיל", "כרית ושמיכה לכורסה בוורוד מעושן", "", "", 1, False, "", ""),
    ("טקסטיל", "מצעים לעריסה", "", "60 על 120", 2, False, "", "סדין צמוד בלבד, בלי כריות ושמיכות פוך"),
    ("תאורה", "מנורת תקרה ענן לבנה עם בסיס ורוד", "", "", 1, False, "", "נורה בגוון חם, עדיף עם עמעום"),
    ("תאורה", "מנורת שולחן פנס מעץ עם כדור חלבי", "", "", 1, False, "", "על השידה. אור חם ועמום להנקות בלילה. להרחיק את הכבל מהעריסה"),
    ("אקססוריז", "מראה אובלית עם מסגרת עץ", "", "", 1, False, "", "מעל השידה. לעגן היטב לקיר"),
    ("אקססוריז", "מובייל לעריסה: פילים, עננים וכוכבים", "", "", 1, False, "",
     "להוריד כשהתינוקת מתחילה להתרומם על הידיים והברכיים (בערך בגיל 5 חודשים)"),
    ("אקססוריז", "ארנבת בד", "", "", 1, False, "", "בשביל האח הגדול"),
    ("אקססוריז", "סטיילינג (לא חובה): צמח תלוי על המדף", "", "", 1, False, "צמח מלאכותי איכותי",
     "פותוס אמיתי רעיל לחתולים ולילדים אם אוכלים ממנו. עם החתול בבית, עדיף צמח מלאכותי"),
    ("אקססוריז", "סטיילינג (לא חובה): מנורת לילה בצורת בית מעץ", "", "", 1, False, "",
     "על המדף. עדיף על סוללה, בלי כבל שמשתלשל"),
    ("אקססוריז", "סטיילינג (לא חובה): ארנבת סרוגה למדף", "", "", 1, False, "", "על המדף בלבד, לא בתוך העריסה"),
    ("אקססוריז", "אקססוריז וסטיילינג (סכום כולל)", "", "", 1, False, "",
     "כולל: ארנבת לאח הגדול, צמח מלאכותי, מנורת בית, ארנבת סרוגה ופריטים קטנים"),
    ("אחר", "ערכת עיגון לשידה ולארון", "", "", 2, False, "", "חובה בחדר ילדים"),
    ("אחר", "כיסויי בטיחות לשקעים", "", "", 1, False, "", ""),
]

# prices the designer has sourced: item -> fields to fill (store, price, link, qty, alt, alt_price, note)
PRICES = {
    "גוף ארון PAX לבן": dict(store="איקאה", price=545,
                             link="https://www.ikea.com/il/he/p/pax-wardrobe-frame-white-80458207/"),
    "זוג דלתות פאנל לבנות לארון": dict(store="איקאה", price=590, link="https://www.ikea.com/il/he/cat/pax-doors-with-hinges-19112/",
                                      note="2 דלתות FORSAND עם צירים, ‏295 כל אחת. דלתות פאנל כמו בהדמיה: BERGSBO, לבדוק מחיר ומלאי"),
    "פנים ארון: 2 מוטות, מדפים ו-2 מגירות": dict(store="איקאה", price=540, link="https://www.ikea.com/il/he/cat/pax-interior-organisers-19113/",
                                                note="2 מוטות (30), 2 מדפים (75), 2 מגירות (165)"),
    "שטיח עגול קלוע מסיבים טבעיים": dict(store="איקאה", price=395,
                                        link="https://www.ikea.com/il/he/p/fullmakt-rug-flatwoven-in-outdoor-beige-melange-30573120/",
                                        alt="LOHALS, יוטה טבעית (איקאה)", alt_price=295,
                                        note="FULLMAKT מתאים גם לחוץ, ולכן קל יותר לניקוי. לבדוק באתר את הוראות הניקוי. LOHALS נראה כמו ההדמיה אבל לא נכבס"),
    "מנורת תקרה ענן לבנה עם בסיס ורוד": dict(store="AliExpress", price=370, link="https://a.aliexpress.com/_c4rFUDsT",
                                           note="לבדוק תקן ישראלי וחיבור לחשמל, וזמן משלוח"),
    "2 מדפים צפים מעץ טבעי": dict(store="SHEIN", price=109, qty=1, link="https://onelink.shein.com/60/67pskf1d59h4?shc=2_RdvtYvTml44",
                                  note="סט מדפים. לבדוק אורך, ושיש ברגים לקיר"),
    "מראה אובלית עם מסגרת עץ": dict(store="אורבניקה", price=240, link="https://www.urbanica-wh.com/onl000007-013-1111"),
    "וילון פשתן חצי שקוף בשמנת": dict(store="איקאה", price=395,
                                     link="https://www.ikea.com/il/he/p/dytag-curtains-1-pair-white-with-heading-tape-20466719/",
                                     note="DYTÄG, זוג וילונות"),
    "מוט וילון דק בגוון כהה": dict(store="איקאה", price=79, note="מוט וחיבורים"),
    "כרית ושמיכה לכורסה בוורוד מעושן": dict(store="איקאה", price=50,
                                          link="https://www.ikea.com/il/he/p/krypljung-cushion-cover-natural-90565443/",
                                          note="KRYPLJUNG, ציפית בלבד: צריך גם מילוי"),
    "מצעים לעריסה": dict(store="איקאה", price=95,
                         link="https://www.ikea.com/il/he/p/len-fitted-sheet-for-cot-white-beige-muslin-00625125/",
                         note="LEN סדין צמוד. לבדוק אם המחיר ליחידה או לזוג"),
    "מנורת שולחן פנס מעץ עם כדור חלבי": dict(store="שילב", price=150, link="https://share.google/YxTWxatwTqdPGncSe"),
    "מובייל לעריסה: פילים, עננים וכוכבים": dict(store="אינפיניטי", price=120, link="https://share.google/w0IfZcqRm1WnJDVQ6"),
    "טפט ארנבים בצבעי מים": dict(price=1000),
    "פס קרניז לבן לחלוקת הקיר": dict(price=300),
    "משטח החתלה + 2 כיסויים": dict(store="שילב", price=300,
                                  link="https://www.shilav.co.il/products/%d7%9e%d7%96%d7%a8%d7%9f-%d7%94%d7%97%d7%aa%d7%9c%d7%94-%d7%a2%d7%9d-%d7%a0%d7%97%d7%a9%d7%95%d7%a9-mix-it-%d7%a7%d7%a8%d7%9d",
                                  note="מזרן החתלה Mix it, קרם. לבדוק אם כולל כיסויים להחלפה"),
    "אקססוריז וסטיילינג (סכום כולל)": dict(price=400),
    "ארנבת בד": dict(price=0, note="כלול בסעיף האקססוריז"),
    "סטיילינג (לא חובה): צמח תלוי על המדף": dict(price=0, note="כלול בסעיף האקססוריז"),
    "סטיילינג (לא חובה): מנורת לילה בצורת בית מעץ": dict(price=0, note="כלול בסעיף האקססוריז"),
    "סטיילינג (לא חובה): ארנבת סרוגה למדף": dict(price=0, note="כלול בסעיף האקססוריז"),
    "סלסלות קלועות לשידה, לארון ולמדפים": dict(store="H&M", price=150, qty=1,
                                             link="https://www2.hm.com/hw_il/productpage.1211338001.html",
                                             note="לבדוק כמה סלסלות במחיר"),
}

# item name -> photo file in IMG_DIR (inspiration photos the designer picked)
PHOTOS = {
    "טפט ארנבים בצבעי מים": "wallpaper.png",
    "פס קרניז לבן לחלוקת הקיר": "molding.png",
    "צבע ורוד עתיק לחצי התחתון של הקירות": "paint_pink.png",
    "צבע שמנת חמה לחצי העליון": "paint_cream.png",
    "מנורת תקרה ענן לבנה עם בסיס ורוד": "ceiling_cloud.png",
    "מנורת שולחן פנס מעץ עם כדור חלבי": "table_lamp.png",
    "מראה אובלית עם מסגרת עץ": "mirror.png",
    "מובייל לעריסה: פילים, עננים וכוכבים": "mobile.png",
    "שטיח עגול קלוע מסיבים טבעיים": "rug.png",
    "2 מדפים צפים מעץ טבעי": "shelves.png",
    "סטיילינג (לא חובה): צמח תלוי על המדף": "plant.png",
    "סטיילינג (לא חובה): מנורת לילה בצורת בית מעץ": "house_lamp.png",
    "סטיילינג (לא חובה): ארנבת סרוגה למדף": "bunny.png",
}


def photo_sheet(wb, img_dir):
    s = wb.create_sheet("תמונות מוצרים")
    s.sheet_view.rightToLeft = True
    s.sheet_view.showGridLines = False
    s["A1"] = "תמונות להשראה · לחפש מוצר דומה ולהוסיף מחיר וקישור ברשימה"
    s["A1"].font = Font(name="Heebo", bold=True, size=13, color="4A3226")
    s.merge_cells("A1:C1")
    s.column_dimensions["A"].width = 34
    s.column_dimensions["B"].width = 30
    s.column_dimensions["C"].width = 30
    captions = {"paint_pink.png": "גוון ההדמיה DEC4BA", "paint_cream.png": "גוון ההדמיה F0E9DD",
                "wallpaper.png": "חיתוך מתוך ההדמיה", "molding.png": "חיתוך מתוך ההדמיה"}
    r = 3
    for name, fn in PHOTOS.items():
        path = os.path.join(img_dir, fn)
        if not os.path.exists(path):
            continue
        s.cell(r, 1, name).font = Font(name="Heebo", size=12, color="4A3226")
        s.cell(r, 1).alignment = Alignment(vertical="center", wrap_text=True, readingOrder=2)
        im = XLImage(path)
        k = 160 / max(im.width, im.height)
        im.width, im.height = int(im.width * k), int(im.height * k)
        s.add_image(im, f"B{r}")
        if fn in captions:
            s.cell(r, 3, captions[fn]).font = Font(name="Heebo", size=10, italic=True, color="8C7466")
            s.cell(r, 3).alignment = Alignment(vertical="center", readingOrder=2)
        s.row_dimensions[r].height = 128
        r += 1


def main(out, img_dir=None):
    build(out, rows=ROWS)
    wb = load_workbook(out)
    ws = wb.active
    ws["A1"] = "רשימת קניות · החדר של התינוקת · משפחת לוי"
    ws["K1"] = 10000
    ws["L1"] = "← התקציב שנועה ציינה (עד 10,000)"
    first = 6
    for i, (cat, item, store, dims, qty, existing, alt, note) in enumerate(ITEMS):
        r = first + i
        ws.cell(r, 2, cat)
        ws.cell(r, 3, item)
        ws.cell(r, 4, store or None)
        ws.cell(r, 6, dims or None)
        ws.cell(r, 7, qty)
        ws.cell(r, 10, alt or None)
        ws.cell(r, 13, note or None)
        pr = PRICES.get(item)
        if pr:
            ws.cell(r, 4, pr.get("store", store) or None)
            ws.cell(r, 8, pr["price"])
            if "qty" in pr:
                ws.cell(r, 7, pr["qty"])
            if pr.get("link"):
                c = ws.cell(r, 5, pr["link"])
                c.hyperlink = pr["link"]
                c.font = Font(name="Heebo", size=9, color="5F7053", underline="single")
            if pr.get("alt"):
                ws.cell(r, 10, pr["alt"])
                ws.cell(r, 11, pr["alt_price"])
            if pr.get("note"):
                ws.cell(r, 13, pr["note"] + (" · " + note if note else ""))
        if existing:
            ws.cell(r, 8, 0)
            for c in range(1, 14):
                ws.cell(r, c).fill = EXIST
        else:
            todo = [] if pr else [5, 8]   # link + price still to source
            if pr and not pr.get("link") and pr["price"]:
                todo = [5]
            for c in todo:
                ws.cell(r, c).fill = TODO
            if alt and not (pr and pr.get("alt_price")):
                ws.cell(r, 11).fill = TODO
    ws.column_dimensions["F"].width = 24
    for r in range(first, first + ROWS):
        ws.cell(r, 6).alignment = Alignment(wrap_text=True, vertical="center", readingOrder=2)
        ws.cell(r, 7).alignment = Alignment(horizontal="center", vertical="center")
    legend = first + ROWS + 3
    ws.cell(legend, 3, "מקרא").font = Font(name="Heebo", bold=True)
    ws.cell(legend + 1, 3, "צהוב: לבדוק מחיר וקישור באתר החנות").fill = TODO
    ws.cell(legend + 2, 3, "ירוק: פריט קיים, לא נכנס לחישוב").fill = EXIST
    if img_dir:
        photo_sheet(wb, img_dir)
    wb.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])

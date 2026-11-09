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
    ("אחר", "ערכת עיגון לשידה ולארון", "", "", 2, False, "", "חובה בחדר ילדים"),
    ("אחר", "כיסויי בטיחות לשקעים", "", "", 1, False, "", ""),
]

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
    build(out, rows=30)
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
        if existing:
            ws.cell(r, 8, 0)
            for c in range(1, 14):
                ws.cell(r, c).fill = EXIST
        else:
            for c in (5, 8):            # link + price to source
                ws.cell(r, c).fill = TODO
            if alt:
                ws.cell(r, 11).fill = TODO
    ws.column_dimensions["F"].width = 24
    for r in range(first, first + 30):
        ws.cell(r, 6).alignment = Alignment(wrap_text=True, vertical="center", readingOrder=2)
        ws.cell(r, 7).alignment = Alignment(horizontal="center", vertical="center")
    legend = first + 30 + 3
    ws.cell(legend, 3, "מקרא").font = Font(name="Heebo", bold=True)
    ws.cell(legend + 1, 3, "צהוב: לבדוק מחיר וקישור באתר החנות").fill = TODO
    ws.cell(legend + 2, 3, "ירוק: פריט קיים, לא נכנס לחישוב").fill = EXIST
    if img_dir:
        photo_sheet(wb, img_dir)
    wb.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])

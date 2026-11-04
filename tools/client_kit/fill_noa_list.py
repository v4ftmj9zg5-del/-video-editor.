"""Example: fill the shopping-list workbook for the Levi nursery (simulation client).

Prices and links are left for the designer to source (cells highlighted); existing
items carry price 0 so totals only count what is bought.
Usage: fill_noa_list.py OUT.xlsx
"""
import os
import sys

from openpyxl import load_workbook
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
    ("אחסון", "סלסלות קלועות לשידה ולארון", "", "", 3, False, "", ""),
    ("אחסון", "משטח החתלה + 2 כיסויים", "", "50 על 70", 1, False, "", "על השידה"),
    ("קירות וצבע", "טפט ארנבים בצבעי מים", "", "קיר העריסה: 280 על 260", 1, False, "מדבקות קיר של ארנבים", "קיר אחד בלבד. להזמין עם 10% עודף"),
    ("קירות וצבע", "צבע לשאר הקירות: שמנת חמה", "טמבור / נירלט", "שלושה קירות", 1, False, "", "לבדוק דוגמית על הקיר לפני הקנייה"),
    ("טקסטיל", "שטיח כביס בגוון בז׳", "", "120 על 170, או עגול בקוטר 140", 1, False, "", "חייב להיות כביס: חתול ותינוקת"),
    ("טקסטיל", "וילון פשתן בירוק מרווה", "", "שתי יריעות, גובה 235 בערך", 1, False, "", "למדוד מתחת לארגז התריס (25 ס״מ מהתקרה)"),
    ("טקסטיל", "כרית ושמיכה לכורסה בוורוד מעושן", "", "", 1, False, "", ""),
    ("טקסטיל", "מצעים לעריסה", "", "60 על 120", 2, False, "", "סדין צמוד בלבד, בלי כריות ושמיכות פוך"),
    ("תאורה", "מנורת תקרה עם אהיל בד או קש", "", "", 1, False, "", "נורה חמה"),
    ("תאורה", "מנורת קיר מעץ ליד הכורסה", "", "", 1, False, "מנורת לילה ניידת", "אור חם ועמום להנקות בלילה"),
    ("אקססוריז", "ארנבת בד", "", "", 1, False, "", "בשביל האח הגדול"),
    ("אחר", "ערכת עיגון לשידה ולארון", "", "", 2, False, "", "חובה בחדר ילדים"),
    ("אחר", "כיסויי בטיחות לשקעים", "", "", 1, False, "", ""),
]


def main(out):
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
    wb.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])

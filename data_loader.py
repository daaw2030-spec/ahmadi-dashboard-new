"""تحميل وتنظيف بيانات عقد الأحمدي.

القواعد المعتمدة:
- لا تُحذف أي معاملة بسبب تاريخ غير صحيح؛ التاريخ غير الصالح يُعامل كقيمة مفقودة
  وتُستبعد المدد المرتبطة به من المؤشرات الزمنية فقط.
- الأرقام المالية الرسمية تُؤخذ من ورقة "الرصيد المتبقي واوامر الشراء" (عمود المبلغ)
  وهي نفس معادلة الورقة =SUM(D2:D288)، ولا تُحسب من السعر × الكمية.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from hijridate import Hijri

DATA_DIR = Path(__file__).parent / "data"
CONTRACT_FILE = DATA_DIR / "contract_integrated.xlsx"
PO_FILE = DATA_DIR / "purchase_orders.xlsx"
DIRECT_FILE = DATA_DIR / "direct_cancelled.xlsx"
CONSUMABLES_FILE = DATA_DIR / "consumables.xlsx"
# المفتاح -> (المسار، وصف الملف الأصلي)
FILES = {
    "contract": (CONTRACT_FILE, "الملف المتكامل لعقد الاحمدي.xlsx"),
    "po": (PO_FILE, "بيانات اوامر الشراء قابل للتحليل.xlsx"),
    "direct": (DIRECT_FILE, "طلبات المباشر-الملغي.xlsx"),
    "consumables": (CONSUMABLES_FILE, "البند الاستهلاكي.xlsx"),
}

YEARS = (2025, 2026)
# نافذة التواريخ المقبولة: بداية العقد حتى اليوم. أي تاريخ خارجها يُعد غير صالح.
VALID_MIN = pd.Timestamp("2024-01-01")
VALID_MAX = pd.Timestamp(date.today())

MONTHS_AR = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}

# توحيد أسماء الأقسام بين الملفات المختلفة
_DEPT_RULES = [
    ("مضخات", "المدنية (مضخات)"),
    ("تكييف", "التكييف"),
    ("كهرب", "الكهربائية"),
    ("ورش", "الورشة المركزية"),
    ("الور", "الورشة المركزية"),
    ("تشجير", "صحة البيئة والتشجير"),
    ("صحة البيئة", "صحة البيئة والتشجير"),
    ("مصاعد", "المصاعد"),
    ("ركاب", "صالة الركاب"),
    ("مدني", "المدنية"),
]


def normalize_dept(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "غير محدد"
    text = str(value).strip()
    if not text:
        return "غير محدد"
    for key, name in _DEPT_RULES:
        if key in text:
            return name
    return "أخرى"


def parse_date(value) -> pd.Timestamp:
    """يحوّل قيمة تاريخ (ميلادي أو هجري نصي) إلى Timestamp، ويعيد NaT إن كانت غير صالحة."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NaT
    if isinstance(value, (datetime, date, pd.Timestamp)):
        ts = pd.Timestamp(value)
    else:
        text = str(value).strip().replace("\\", "/").replace("-", "/")
        text = re.sub(r"\s+00:00:00$", "", text)
        m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", text)
        if not m:
            return pd.NaT
        y, mo, d = map(int, m.groups())
        try:
            if 1400 <= y <= 1500:
                ts = pd.Timestamp(Hijri(y, mo, d).to_gregorian().isoformat())
            else:
                ts = pd.Timestamp(year=y, month=mo, day=d)
        except (ValueError, OverflowError):
            return pd.NaT
    if pd.isna(ts) or ts < VALID_MIN or ts > VALID_MAX:
        return pd.NaT
    return ts.normalize()


def _add_period(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    df["السنة"] = df[date_col].dt.year.astype("Int64")
    df["الشهر"] = df[date_col].dt.month.astype("Int64")
    df["اسم الشهر"] = df["الشهر"].map(MONTHS_AR)
    return df


def _clean_text(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA})


# ---------------------------------------------------------------- الرصيد الرسمي
def load_official_balance(src=None) -> dict:
    """يقرأ ورقة الرصيد المتبقي ويعيد المعاملات والأرقام الرسمية."""
    raw = pd.read_excel(src or CONTRACT_FILE, sheet_name=None, header=None, dtype=object)
    sheet = next(v for k, v in raw.items() if k.strip() == "الرصيد المتبقي واوامر الشراء")

    # سطر "المبلغ المنصرف" يحدد نهاية جدول المعاملات (يقابل SUM(D2:D288))
    def find(label: str) -> tuple[int, int]:
        for r in range(sheet.shape[0]):
            for c in range(sheet.shape[1]):
                v = sheet.iat[r, c]
                if isinstance(v, str) and label in v:
                    return r, c
        raise ValueError(f"لم يتم العثور على '{label}' في ورقة الرصيد")

    total_row, _ = find("المبلغ المنصرف")
    r_app, c_app = find("المبلغ المع")  # "المبلغ المعمتد" كما هو مكتوب في الورقة
    approved = next(float(sheet.iat[r_app, c]) for c in range(c_app + 1, sheet.shape[1])
                    if isinstance(sheet.iat[r_app, c], (int, float)) and not pd.isna(sheet.iat[r_app, c]))

    body = sheet.iloc[1:total_row, :7].copy()
    body.columns = ["م", "رقم طلب الشراء", "الجهة الطالبة", "المبلغ_الأصلي", "رقم امر الشراء",
                    "التاريخ الميلادي", "التاريخ الهجري"]
    # الصفوف الفاصلة مثل "عام 2026م" ليست معاملات (بلا رقم طلب ولا مبلغ ولا أمر شراء)
    body = body[body[["رقم طلب الشراء", "المبلغ_الأصلي", "رقم امر الشراء"]].notna().any(axis=1)].copy()

    amount = pd.to_numeric(body["المبلغ_الأصلي"], errors="coerce")
    body["المبلغ"] = amount.fillna(0.0)
    body["الحالة"] = np.where(body["المبلغ_الأصلي"].astype(str).str.contains("ملغي"), "ملغي",
                              np.where(amount.notna(), "صادر", "بدون مبلغ"))
    body["رقم طلب الشراء"] = _clean_text(body["رقم طلب الشراء"])
    body["رقم امر الشراء"] = _clean_text(body["رقم امر الشراء"])
    body["القسم"] = body["الجهة الطالبة"].map(normalize_dept)

    greg = body["التاريخ الميلادي"].map(parse_date)
    hijri = body["التاريخ الهجري"].map(parse_date)
    body["التاريخ"] = greg.fillna(hijri)
    body["مصدر التاريخ"] = np.where(greg.notna(), "ميلادي", np.where(hijri.notna(), "هجري محوّل", "غير صالح"))
    body = _add_period(body, "التاريخ")

    notes = {}
    for r in range(total_row, sheet.shape[0]):
        cells = [sheet.iat[r, c] for c in range(sheet.shape[1]) if not pd.isna(sheet.iat[r, c])]
        if cells:
            notes[r + 1] = cells

    disbursed = round(float(body["المبلغ"].sum()), 2)
    return {
        "transactions": body.drop(columns=["المبلغ_الأصلي", "م"]).reset_index(drop=True),
        "approved": approved,
        "disbursed": disbursed,
        "remaining": round(approved - disbursed, 2),
        "sheet_notes": notes,
    }


# ---------------------------------------------------------------- أوامر الشراء
PO_STAGES = [
    ("تاريخ اعداد طلب الشراء من القسم (ميلادي)", "إعداد الطلب"),
    ("تاريخ استلام الطلب في إدارة عقود الصيانة(ميلادي)", "استلام الطلب"),
    ("تاريخ خطاب جلب عروض الأسعار للمقاول  (ميلادي)", "خطاب العروض"),
    ("تاريخ استلام معاملة عروض الأسعار من المقاول (ميلادي)", "استلام العروض"),
    ("تاريخ ارسال اعداد المحضر من قسم إدارة العقود للقسم الطالب(ميلادي)", "إرسال إعداد المحضر"),
    ("تاريخ اعداد المحضر من القسم الطالب  (ميلادي)", "إعداد المحضر"),
    ("تاريخ تسليم المحضر من القسم المعد لإدارة عقود الصيانة (ميلادي)", "تسليم المحضر"),
    ("تاريخ ارسال  الأصول و الخطاب لإدارة المشتريات(ميلادي)", "الإرسال للمشتريات"),
    ("تاريخ استلام معاملة امر الشراء  (ميلادي)", "استلام معاملة الأمر"),
    ("تاريخ صدورامر الشراء (ميلادي)", "صدور أمر الشراء"),
    ("تاريخ التسليم للمستودع (ميلادي)", "التسليم للمستودع"),
]
STAGE_DATES = [name for _, name in PO_STAGES]
STAGE_DURATIONS = [f"{a} ← {b}" for a, b in zip(STAGE_DATES[:-1], STAGE_DATES[1:])]
DATE_BASES = {"تاريخ إعداد الطلب": "إعداد الطلب", "تاريخ صدور أمر الشراء": "صدور أمر الشراء"}


def load_purchase_orders(src=None) -> pd.DataFrame:
    df = pd.read_excel(src or PO_FILE, dtype=object)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df[["رقم طلب الشراء", "القسم", "وصف الطلب"]].notna().any(axis=1)].copy()

    rename = {src.strip(): name for src, name in PO_STAGES}
    df = df.rename(columns=rename)
    for col in STAGE_DATES:
        df[col] = df[col].map(parse_date)

    # إعادة احتساب المدد من التواريخ؛ السالبة أو المبنية على تاريخ غير صالح = NaN
    for (a, b), label in zip(zip(STAGE_DATES[:-1], STAGE_DATES[1:]), STAGE_DURATIONS):
        days = (df[b] - df[a]).dt.days
        df[label] = days.where(days >= 0)
    total = (df["صدور أمر الشراء"] - df["إعداد الطلب"]).dt.days
    df["مدة الطلب حتى صدور الأمر"] = total.where(total >= 0)
    deliv = (df["التسليم للمستودع"] - df["صدور أمر الشراء"]).dt.days
    df["مدة الأمر حتى التسليم"] = deliv.where(deliv >= 0)

    df["رقم طلب الشراء"] = _clean_text(df["رقم طلب الشراء"])
    df["القسم"] = df["القسم"].map(normalize_dept)
    df["تكلفة الطلب"] = pd.to_numeric(df["تكلفة الطلب"], errors="coerce")
    wh = df["رقم المستودع"].astype("string").fillna("")
    df["الحالة"] = np.select(
        [wh.str.contains("إلغاء|الغاء|ملغ"), df["التسليم للمستودع"].notna() | wh.str.contains("تم التسليم"),
         df["صدور أمر الشراء"].notna()],
        ["ملغي", "تم التسليم", "صدر أمر الشراء"], default="قيد الإجراء")
    return df.reset_index(drop=True)


def with_reference_date(df: pd.DataFrame, basis: str) -> pd.DataFrame:
    """يحدد تاريخ المرجع للسنة/الشهر؛ عند غياب تاريخ الأساس يُستخدم أقرب تاريخ صالح متاح
    بدلًا من حذف المعاملة."""
    out = df.copy()
    primary = DATE_BASES[basis]
    order = [primary] + [c for c in STAGE_DATES if c != primary]
    ref = out[primary].copy()
    for col in order[1:]:
        ref = ref.fillna(out[col])
    out["تاريخ المرجع"] = ref
    out["تاريخ بديل"] = out[primary].isna() & ref.notna()
    return _add_period(out, "تاريخ المرجع")


# ---------------------------------------------------------------- المباشر والملغي
def load_direct_requests(src=None) -> pd.DataFrame:
    df = pd.read_excel(src or DIRECT_FILE, sheet_name="طلبات المباشر", dtype=object)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df[df[["رقم الطلب", "الجهة الطالبة"]].notna().any(axis=1)].copy()
    desc_col = next(c for c in df.columns if c.startswith("طلبات الشراء التي"))
    df = df.rename(columns={desc_col: "وصف الطلب", "تاريخه": "تاريخ الطلب_الأصلي",
                            "تاريخه.1": "تاريخ الصادر_الأصلي"})
    req = df["تاريخ الطلب_الأصلي"].map(parse_date)
    rec = df["تاريخ الاستلام"].map(parse_date)
    df["تاريخ الطلب"] = req.fillna(rec)
    df["تاريخ بديل"] = req.isna() & rec.notna()
    df["الصادر للجهة"] = _clean_text(df["الصادر"]).fillna("غير محدد")
    df["معاد من المشتريات"] = df["معاد من المشتريات"].notna()
    df["رقم الطلب"] = _clean_text(df["رقم الطلب"])
    df["القسم"] = df["الجهة الطالبة"].map(normalize_dept)
    return _add_period(df, "تاريخ الطلب").reset_index(drop=True)


def load_cancelled(src=None) -> pd.DataFrame:
    df = pd.read_excel(src or DIRECT_FILE, sheet_name="الملغي", dtype=object)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df[["رقم الطلب", "الجهة الطالبة"]].notna().any(axis=1)].copy()
    reason_col = next(c for c in df.columns if c.startswith("الطلبات التي تم"))
    df = df.rename(columns={reason_col: "سبب/بيان الإلغاء"})
    df["تاريخ الإلغاء (ميلادي)"] = df["تاريخ الإلغاء"].map(parse_date)
    df["رقم الطلب"] = _clean_text(df["رقم الطلب"])
    df["القسم"] = df["الجهة الطالبة"].map(normalize_dept)
    return _add_period(df, "تاريخ الإلغاء (ميلادي)").reset_index(drop=True)


# ---------------------------------------------------------------- البنود الاستهلاكية
def load_consumables(src=None) -> pd.DataFrame:
    df = pd.read_excel(src or CONSUMABLES_FILE, usecols=range(33), dtype=object)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df["الصنف البند"].notna()].copy()
    issue_cols = [c for c in df.columns if c.startswith("المنصرف") or c.startswith("منصرف")]
    for c in ["السعر", "ثلاثة اشهر", "كمية السنة", "الكمية بالعقد", "المتبقي", *issue_cols]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["الكمية المنصرفة"] = df[issue_cols].fillna(0).sum(axis=1)
    df["نسبة الصرف %"] = np.where(df["الكمية بالعقد"] > 0,
                                  df["الكمية المنصرفة"] / df["الكمية بالعقد"] * 100, np.nan)
    # قيمة تقديرية فقط (السعر × الكمية) — ليست رقمًا ماليًا رسميًا
    df["قيمة تقديرية للمنصرف"] = df["السعر"] * df["الكمية المنصرفة"]
    df["الصنف البند"] = df["الصنف البند"].astype(str).str.strip()
    return df[["البند", "الصنف البند", "الوحدة", "السعر", "الكمية بالعقد", "كمية السنة",
               "الكمية المنصرفة", "المتبقي", "نسبة الصرف %", "قيمة تقديرية للمنصرف"]].reset_index(drop=True)

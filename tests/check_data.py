"""فحوصات سريعة للبيانات: python tests/check_data.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

import json  # noqa: E402

import data_loader as dl  # noqa: E402

# الأرقام الرسمية كما في الصورة المرجعية تُحفظ محليًا فقط (الملف مستثنى من git)
EXPECTED_FILE = Path(__file__).with_name("expected_official.json")

bal = dl.load_official_balance()
assert abs(bal["remaining"] - (bal["approved"] - bal["disbursed"])) < 0.005
if EXPECTED_FILE.exists():
    OFFICIAL = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))
    for key, expected in OFFICIAL.items():
        assert abs(bal[key] - expected) < 0.005, (key, bal[key], expected)
else:
    OFFICIAL = {"disbursed": bal["disbursed"]}
    print("expected_official.json غير موجود — تم تخطي المطابقة مع الصورة المرجعية")
tx = bal["transactions"]
print("official OK:", {k: bal[k] for k in OFFICIAL})
print("balance rows:", len(tx), "status:", tx["الحالة"].value_counts().to_dict())
print("date source:", tx["مصدر التاريخ"].value_counts().to_dict())
by_year = tx.groupby("السنة", dropna=False)["المبلغ"].sum().round(2).to_dict()
print("by year:", by_year)
assert abs(sum(by_year.values()) - OFFICIAL["disbursed"]) < 0.005
print("depts:", tx["القسم"].value_counts().to_dict())
print("odd rows:\n", tx[tx["القسم"].isin(["أخرى", "غير محدد"]) | tx["السنة"].isna()].to_string())

po = dl.load_purchase_orders()
print("\nPO rows:", len(po), "status:", po["الحالة"].value_counts().to_dict())
print("PO cost sum:", round(po["تكلفة الطلب"].sum(), 2))
print("invalid dates per stage:", {c: int(po[c].isna().sum()) for c in dl.STAGE_DATES})
print("excluded durations:", {c: int(po[c].isna().sum()) for c in dl.STAGE_DURATIONS})
print("depts:", po["القسم"].value_counts().to_dict())
for basis in dl.DATE_BASES:
    r = dl.with_reference_date(po, basis)
    print(basis, "years:", r["السنة"].value_counts(dropna=False).to_dict(), "fallback:", int(r["تاريخ بديل"].sum()))

# مقارنة ملف أوامر الشراء بالرصيد الرسمي
m = tx.merge(po[["رقم طلب الشراء", "تكلفة الطلب"]].groupby("رقم طلب الشراء").sum().reset_index(),
             on="رقم طلب الشراء", how="outer", indicator=True)
print("merge:", m["_merge"].value_counts().to_dict())

d = dl.load_direct_requests()
print("\nDIRECT rows:", len(d), "years:", d["السنة"].value_counts(dropna=False).to_dict(), "fallback:", int(d["تاريخ بديل"].sum()))
print("depts:", d["القسم"].value_counts().to_dict(), "returned:", int(d["معاد من المشتريات"].sum()))
c = dl.load_cancelled()
print("CANCELLED rows:", len(c), "years:", c["السنة"].value_counts(dropna=False).to_dict())
k = dl.load_consumables()
print("CONSUMABLES rows:", len(k), "issued qty:", k["الكمية المنصرفة"].sum())
mismatch = k[(k["الكمية بالعقد"] - k["الكمية المنصرفة"] - k["المتبقي"]).abs() > 0.01]
print("remaining mismatch rows:", len(mismatch))
print("ALL CHECKS PASSED")

# ---------------------------------------------------------------- قواعد البيانات
import pandas as pd  # noqa: E402

raw_po = pd.read_excel(dl.PO_FILE).rename(columns=lambda c: str(c).strip())
assert len(po) == raw_po.dropna(how="all").dropna(subset=["رقم طلب الشراء", "القسم", "وصف الطلب"], how="all").shape[0], \
    "يجب ألا تُحذف أي معاملة"
dur_cols = dl.STAGE_DURATIONS + ["مدة الطلب حتى صدور الأمر", "مدة الأمر حتى التسليم"]
assert int((po[dur_cols] < 0).sum().sum()) == 0, "لا مدد سالبة"
for col in dl.STAGE_DATES:
    s = po[col].dropna()
    assert s.empty or (s.min() >= dl.VALID_MIN and s.max() <= dl.VALID_MAX), col
# صف فيه تاريخ غير صالح يبقى ببقية بياناته
bad_rows = po[po["إعداد الطلب"].isna()]
assert len(bad_rows) and bad_rows["القسم"].notna().all() and bad_rows["الحالة"].notna().all()
for basis in dl.DATE_BASES:
    assert set(dl.with_reference_date(po, basis)["السنة"].dropna().astype(int)) <= {2025, 2026}
print("DATA RULES PASSED: rows kept, no negative durations, invalid dates -> missing")

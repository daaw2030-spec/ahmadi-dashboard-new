import streamlit as st

import common as c
import data_loader as dl

f = st.session_state["filters"]
bal = c.official()
tx = bal["transactions"]

st.title("الملخص المالي لعقد الأحمدي")
st.caption("المصدر الرسمي: ورقة «الرصيد المتبقي واوامر الشراء» — عمود المبلغ (نفس معادلة الورقة SUM(D2:D288)).")

# ------------------------------------------------ الأرقام الرسمية (غير متأثرة بالفلاتر)
k1, k2, k3, k4 = st.columns(4)
with k1:
    c.kpi_official("المبلغ المعتمد", c.money(bal["approved"]), "قيمة العقد المعتمدة")
with k2:
    c.kpi_official("المبلغ المنصرف", c.money(bal["disbursed"]), "إجمالي أوامر الشراء الصادرة")
with k3:
    c.kpi_official("الرصيد المتبقي", c.money(bal["remaining"]), "المعتمد − المنصرف")
with k4:
    c.kpi_official("نسبة الصرف", f"{bal['disbursed'] / bal['approved'] * 100:.1f}%",
                   f"{(tx['الحالة'] == 'صادر').sum()} أمر شراء صادر · {(tx['الحالة'] == 'ملغي').sum()} ملغي")
st.caption("هذه البطاقات الأربع ثابتة ولا تتأثر بالفلاتر لأنها الأرقام الرسمية للعقد.")

# ------------------------------------------------ المقارنة 2025 مقابل 2026
months = sorted(f["months"])
st.subheader("مقارنة 2025 و2026 لنفس الأشهر")
st.caption("الأشهر المختارة: " + "، ".join(dl.MONTHS_AR[m] for m in months)
           + ("" if set(months) <= set(c.comparable_months()) else
              " — تنبيه: بعض الأشهر المختارة ليس لها بيانات بعد في 2026، فالمقارنة ليست متكافئة."))
sel = c.apply_filters(tx, f)
y25, y26 = (sel[sel["السنة"] == y] for y in (2025, 2026))
issued25, issued26 = (d[d["الحالة"] == "صادر"] for d in (y25, y26))

a, b, d = st.columns(3)
with a:
    c.kpi_compare("المبلغ المنصرف خلال الفترة", y25["المبلغ"].sum(), y26["المبلغ"].sum())
with b:
    c.kpi_compare("عدد أوامر الشراء الصادرة", len(issued25), len(issued26), fmt=c.num)
with d:
    avg = lambda s: s["المبلغ"].mean() if len(s) else 0  # noqa: E731
    c.kpi_compare("متوسط قيمة أمر الشراء", avg(issued25), avg(issued26))

l, r = st.columns(2)
with l:
    st.markdown("**المبلغ المنصرف شهريًا**")
    c.show(c.monthly_compare(sel, "المبلغ", months, "ريال"))
with r:
    st.markdown("**المنصرف التراكمي**")
    c.show(c.cumulative_compare(sel, "المبلغ", months, "ريال"))

l, r = st.columns(2)
with l:
    st.markdown("**المنصرف حسب القسم**")
    c.show(c.category_compare(sel, "القسم", "المبلغ", "ريال"))
with r:
    st.markdown("**عدد أوامر الشراء حسب القسم**")
    c.show(c.category_compare(sel[sel["الحالة"] == "صادر"], "القسم", None, "عدد الأوامر", fmt=",.0f"))

# ------------------------------------------------ التحقق والملاحظات
with st.expander("التحقق من الأرقام وجودة البيانات"):
    by_year = tx.groupby("السنة")["المبلغ"].sum()
    st.markdown(
        f"- مجموع 2025 = **{c.money(by_year.get(2025, 0))}**، مجموع 2026 = **{c.money(by_year.get(2026, 0))}**، "
        f"والمجموع = **{c.money(by_year.sum())}** ويطابق المبلغ المنصرف الرسمي.\n"
        f"- الأوامر الملغاة ({(tx['الحالة'] == 'ملغي').sum()}) مسجلة بقيمة صفر كما في الورقة.\n"
        f"- معاملات تاريخها الميلادي غير صالح وتم أخذ تاريخها من العمود الهجري: "
        f"{(tx['مصدر التاريخ'] == 'هجري محوّل').sum()}؛ بلا تاريخ صالح: {(tx['مصدر التاريخ'] == 'غير صالح').sum()} "
        "(تبقى ضمن الإجمالي الرسمي ولا تظهر في التوزيع الشهري)."
    )
    st.markdown("**ملاحظات مدخلة يدويًا أسفل الورقة المرجعية (تُعرض كما هي):**")
    for row, cells in bal["sheet_notes"].items():
        st.text(f"سطر {row}: " + "  |  ".join(str(x) for x in cells))

with st.expander("جدول المعاملات (حسب الفلاتر)"):
    st.dataframe(sel[["رقم طلب الشراء", "رقم امر الشراء", "الجهة الطالبة", "القسم", "المبلغ", "الحالة",
                      "التاريخ", "التاريخ الهجري"]].sort_values("التاريخ"),
                 width="stretch", hide_index=True,
                 column_config={"المبلغ": st.column_config.NumberColumn(format="%,.2f"),
                                "التاريخ": st.column_config.DateColumn(format="YYYY-MM-DD")})

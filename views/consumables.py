import streamlit as st

import common as c

items = c.consumables()

st.title("البنود الاستهلاكية")
c.note("ملف البنود الاستهلاكية لا يحتوي على تواريخ للصرف، لذلك لا يمكن تقسيمه على 2025 و2026، "
       "ولا تنطبق عليه فلاتر الأشهر والأقسام. «القيمة التقديرية» = السعر × الكمية المنصرفة، "
       "وهي للاسترشاد فقط وليست رقمًا ماليًا رسميًا.")

l, r = st.columns([2, 1])
with l:
    q = st.text_input("بحث باسم الصنف", key="cons_search", placeholder="مثال: دهان، فلتر، كيبل")
with r:
    units = st.multiselect("الوحدة", sorted(items["الوحدة"].dropna().unique()), key="cons_units",
                           placeholder="كل الوحدات")
sel = items
if q:
    sel = sel[sel["الصنف البند"].str.contains(q, case=False, na=False)]
if units:
    sel = sel[sel["الوحدة"].isin(units)]

used = sel[sel["الكمية المنصرفة"] > 0]
a, b, d, e = st.columns(4)
with a:
    c.kpi_official("عدد الأصناف", c.num(len(sel)), f"منها {len(used)} صنف عليه صرف")
with b:
    c.kpi_official("أصناف لم يُصرف منها", c.num(len(sel) - len(used)), "من إجمالي الأصناف المعروضة")
with d:
    pct = used["نسبة الصرف %"].median() if len(used) else 0
    c.kpi_official("وسيط نسبة الصرف", f"{pct:.1f}%", "للأصناف التي عليها صرف")
with e:
    c.kpi_official("القيمة التقديرية للمنصرف", c.money(sel["قيمة تقديرية للمنصرف"].sum()), "تقديري: السعر × الكمية")

l, r = st.columns(2)
with l:
    st.markdown("**أعلى 15 صنفًا في نسبة الصرف من كمية العقد**")
    top = used.nlargest(15, "نسبة الصرف %").iloc[::-1]
    c.show(c.single_bar(top["الصنف البند"], top["نسبة الصرف %"], "نسبة الصرف %", fmt=".1f"))
with r:
    st.markdown("**أعلى 15 صنفًا في القيمة التقديرية للمنصرف**")
    top = used.nlargest(15, "قيمة تقديرية للمنصرف").iloc[::-1]
    c.show(c.single_bar(top["الصنف البند"], top["قيمة تقديرية للمنصرف"], "ريال (تقديري)", fmt=",.2f"))

st.markdown("**جدول الأصناف**")
st.dataframe(sel, hide_index=True, width="stretch",
             column_config={
                 "السعر": st.column_config.NumberColumn(format="%,.2f"),
                 "نسبة الصرف %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                 "قيمة تقديرية للمنصرف": st.column_config.NumberColumn(format="%,.2f"),
             })

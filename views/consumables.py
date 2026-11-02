import streamlit as st

import common as c

items = c.consumables()

st.title("البنود الاستهلاكية (المستخلص الشهري)")
c.note("البند الاستهلاكي يُتابع بالكميات فقط: كم استُهلك من كمية العقد وكم بقي. لا تُحسب منه أي قيمة مالية، "
       "وهو منفصل عن ميزانية البند التعويضي في الملخص المالي. الملف لا يحتوي تواريخ للصرف، لذلك لا يمكن "
       "تقسيمه على 2025 و2026، ولا تنطبق عليه فلاتر الأشهر والأقسام.")

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
    c.kpi_official("عدد الأصناف", c.num(len(sel)), f"منها {len(used)} صنف عليه استهلاك")
with b:
    c.kpi_official("أصناف لم يُستهلك منها", c.num(len(sel) - len(used)), "كميتها التعاقدية كاملة متبقية")
with d:
    c.kpi_official("أصناف نفدت كميتها", c.num(int((sel["نسبة الصرف %"] >= 100).sum())),
                   f"و{int(((sel['نسبة الصرف %'] >= 80) & (sel['نسبة الصرف %'] < 100)).sum())} صنفًا بين 80% و99%")
with e:
    pct = used["نسبة الصرف %"].median() if len(used) else 0
    c.kpi_official("وسيط نسبة الاستهلاك", f"{pct:.1f}%", "للأصناف التي عليها استهلاك")

l, r = st.columns(2)
with l:
    top = used.nlargest(15, "نسبة الصرف %").iloc[::-1]
    c.chart("أعلى 15 صنفًا في نسبة الاستهلاك من كمية العقد",
            "يكشف الأصناف التي اقتربت من نفاد كميتها التعاقدية وقد تحتاج متابعة.",
            c.single_bar(top["الصنف البند"], top["نسبة الصرف %"], "نسبة الاستهلاك من كمية العقد %", fmt=".1f"))
with r:
    c.chart("توزيع الأصناف حسب نسبة الاستهلاك",
            "يبين كم صنفًا لم يُستهلك منه، وكم صنفًا قارب أو بلغ نفاد كميته.",
            c.consumption_bands(sel))

st.markdown("**جدول الأصناف**")
st.dataframe(sel, hide_index=True, width="stretch",
             column_config={
                 "نسبة الصرف %": st.column_config.ProgressColumn("نسبة الاستهلاك %", format="%.1f%%",
                                                                 min_value=0, max_value=100),
             })

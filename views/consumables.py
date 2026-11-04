import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c
import data_loader as dl

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

# ------------------------------------------------ الاستهلاك مقارنة بمدة العقد والتوقع
st.subheader("الاستهلاك مقارنة بمدة العقد (5 سنوات) والتوقع بنفس الوتيرة")
po = c.purchase_orders()
as_of = po[dl.STAGE_DATES].max().max()
elapsed = (as_of - dl.CONTRACT_START).days / 30.4375  # بالأشهر
end = dl.CONTRACT_START + pd.DateOffset(months=dl.CONTRACT_MONTHS)
c.note(f"الملف لا يحتوي تواريخ، لذلك يُفترض أن العقد بدأ في {dl.CONTRACT_START:%m/%Y} (أول طلب شراء بتاريخ "
       f"15/01/2025) وينتهي في {end:%m/%Y}، وأن الكميات المنصرفة حتى {as_of:%d/%m/%Y} (آخر تاريخ في ملف "
       "أوامر الشراء). التوقع يفترض استمرار كل صنف على نفس وتيرة استهلاكه الحالية، وهو تقدير للمتابعة وليس رقمًا "
       "نهائيًا. النسبة العامة متوسط نسب الأصناف، لأن وحداتها مختلفة ولا تُجمع كمياتها.")
pct_now = sel["نسبة الصرف %"].fillna(0)
proj_end = pct_now * dl.CONTRACT_MONTHS / elapsed
deplete_month = (elapsed * 100 / pct_now).where(pct_now > 0)  # الشهر الذي تنفد فيه الكمية من بداية العقد
runs_out = sel.assign(**{"النسبة الآن %": pct_now, "المتوقع عند نهاية العقد %": proj_end,
                         "تاريخ النفاد المتوقع": [dl.CONTRACT_START + pd.DateOffset(days=int(m * 30.4375))
                                                  if pd.notna(m) else pd.NaT for m in deplete_month]})
runs_out = runs_out[(pct_now > 0) & (deplete_month < dl.CONTRACT_MONTHS)].sort_values("تاريخ النفاد المتوقع")

time_pct = elapsed / dl.CONTRACT_MONTHS * 100
avg_now = pct_now.clip(upper=100).mean() if len(sel) else 0
avg_end = proj_end.clip(upper=100).mean() if len(sel) else 0
a, b, d, e = st.columns(4)
with a:
    c.kpi_official("المنقضي من مدة العقد", f"{time_pct:.1f}%", f"نحو {elapsed:.0f} شهرًا من {dl.CONTRACT_MONTHS}")
with b:
    c.kpi_official("متوسط الاستهلاك من كمية العقد", f"{avg_now:.1f}%", "متوسط نسب كل الأصناف")
with d:
    c.kpi_official("المتوقع عند نهاية العقد", f"{avg_end:.1f}%", "بنفس الوتيرة، والصنف لا يتجاوز 100%")
with e:
    already = int((pct_now >= 100).sum())
    c.kpi_official("أصناف يُتوقع نفادها قبل نهاية العقد", c.num(len(runs_out)),
                   f"منها {already} نفدت فعلًا")

l, r = st.columns(2)
with l:
    bars = pd.Series({"المنقضي من مدة العقد": time_pct, "الاستهلاك حتى الآن": avg_now,
                      "المتوقع عند نهاية العقد": avg_end})
    fig = go.Figure(go.Bar(x=bars.index, y=bars.values, text=[f"{v:.1f}%" for v in bars.values],
                           textposition="outside", marker=dict(color=["#9AA8B8", "#2F6DB5", "#0B3D91"],
                                                               cornerradius=4)))
    fig = c._layout(fig, height=380, y_title="%")
    fig.update_yaxes(range=[0, 110])
    c.chart("وتيرة الاستهلاك مقابل الوقت",
            "إذا كان الاستهلاك أقل من المنقضي من المدة فالكميات تكفي بشكل عام، والعكس يعني ضغطًا على الكميات.", fig)
with r:
    top = runs_out[runs_out["النسبة الآن %"] < 100].head(15).iloc[::-1]
    fig = c.single_bar(top["الصنف البند"], (top["تاريخ النفاد المتوقع"] - as_of).dt.days / 30.4375,
                       "الأشهر المتبقية حتى النفاد المتوقع", fmt=".1f")
    fig.update_traces(text=[f"{v:.1f}" for v in fig.data[0].x], textposition="outside", cliponaxis=False)
    c.chart("أقرب الأصناف إلى النفاد قبل نهاية العقد",
            f"الأصناف المتبقية التي ستنفد قبل نهاية العقد إذا استمر استهلاكها بنفس الوتيرة "
            f"(الأصناف التي نفدت فعلًا: {already}، وهي في القائمة الكاملة أدناه).", fig)
with st.expander(f"كل الأصناف المتوقع نفادها قبل نهاية العقد ({len(runs_out)} صنفًا)"):
    st.dataframe(runs_out[["الصنف البند", "الوحدة", "الكمية بالعقد", "الكمية المنصرفة", "المتبقي", "النسبة الآن %",
                           "تاريخ النفاد المتوقع"]],
                 hide_index=True, width="stretch",
                 column_config={"النسبة الآن %": st.column_config.NumberColumn(format="%.1f%%"),
                                "تاريخ النفاد المتوقع": st.column_config.DateColumn(format="MM/YYYY")})

st.markdown("**جدول الأصناف**")
st.dataframe(sel, hide_index=True, width="stretch",
             column_config={
                 "نسبة الصرف %": st.column_config.ProgressColumn("نسبة الاستهلاك %", format="%.1f%%",
                                                                 min_value=0, max_value=100),
             })

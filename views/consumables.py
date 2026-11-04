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

# ------------------------------------------------ الوتيرة السنوية مقارنة بالكمية السنوية
st.subheader("وتيرة الاستهلاك السنوية مقارنة بالكمية السنوية لكل صنف")
months, last = c.contract_elapsed()
c.note(f"البند الاستهلاكي سنوي: لكل صنف «كمية السنة». الملف لا يحتوي تواريخ للصرف، لذلك تُعتبر الكميات المنصرفة "
       f"من بداية العقد ({dl.CONTRACT_START:%m/%Y}) حتى آخر شهر له بيانات ({last:%m/%Y})، أي {months} شهرًا، "
       "وتُحوّل إلى معدل استهلاك سنوي = المنصرف ÷ الأشهر × 12. التوقع يفترض استمرار نفس الوتيرة، وهو تقدير "
       "للمتابعة. ملاحظة: عمود «المتبقي» في الملف محسوب من «الكمية بالعقد» (5 أضعاف الكمية السنوية).")
pace = (sel["الكمية المنصرفة"] * 12 / months / sel["كمية السنة"] * 100).where(sel["كمية السنة"] > 0)
paced = sel.assign(**{"الاستهلاك السنوي المتوقع": sel["الكمية المنصرفة"] * 12 / months,
                      "نسبة الوتيرة من الكمية السنوية %": pace})
over = paced[pace >= 100].sort_values("نسبة الوتيرة من الكمية السنوية %", ascending=False)

a, b, d, e = st.columns(4)
with a:
    c.kpi_official("فترة الاستهلاك المحسوبة", f"{months} شهرًا", f"من {dl.CONTRACT_START:%m/%Y} إلى {last:%m/%Y}")
with b:
    c.kpi_official("وسيط الوتيرة السنوية", f"{pace.median():.1f}%" if pace.notna().any() else "—",
                   "من الكمية السنوية لكل صنف")
with d:
    c.kpi_official("أصناف تتجاوز كميتها السنوية", c.num(len(over)), "بالوتيرة الحالية تحتاج أكثر من كمية السنة")
with e:
    c.kpi_official("أصناف أقل من نصف كميتها السنوية", c.num(int((pace < 50).sum())),
                   f"منها {int((pace == 0).sum())} لم يُستهلك منها")

l, r = st.columns(2)
with l:
    labels = ["لم يُستهلك منه", "أقل من نصف الكمية", "من 50 إلى 79 بالمئة", "من 80 إلى 99 بالمئة",
              "تتجاوز الكمية السنوية"]
    bands = pd.cut(pace, [-1, 0, 49.999, 79.999, 99.999, float("inf")], labels=labels).value_counts().reindex(labels)
    fig = go.Figure(go.Bar(x=labels, y=bands.values, text=bands.values, textposition="outside",
                           marker=dict(color=["#9AA8B8", "#A9C4E6", "#5B8FD0", "#2F6DB5", "#B45309"],
                                       cornerradius=4)))
    fig = c._layout(fig, height=400, y_title="عدد الأصناف", x_title="الوتيرة السنوية من الكمية السنوية")
    fig.update_yaxes(range=[0, bands.max() * 1.15])
    c.chart("توزيع الأصناف حسب وتيرة الاستهلاك السنوية",
            "يبين كم صنفًا تكفيه كميته السنوية بالوتيرة الحالية، وكم صنفًا يحتاج أكثر منها.", fig)
with r:
    top = over.head(15).iloc[::-1]
    c.chart("أعلى الأصناف تجاوزًا لكميتها السنوية",
            "الوتيرة السنوية كنسبة من كمية السنة؛ 200% تعني أن الصنف يُستهلك بضعف كميته السنوية.",
            c.single_bar(top["الصنف البند"], top["نسبة الوتيرة من الكمية السنوية %"],
                         "الوتيرة السنوية من الكمية السنوية %", fmt=".0f"))
with st.expander(f"كل الأصناف التي تتجاوز كميتها السنوية بالوتيرة الحالية ({len(over)} صنفًا)"):
    st.dataframe(over[["الصنف البند", "الوحدة", "كمية السنة", "الكمية المنصرفة", "الاستهلاك السنوي المتوقع",
                       "نسبة الوتيرة من الكمية السنوية %"]],
                 hide_index=True, width="stretch",
                 column_config={"الاستهلاك السنوي المتوقع": st.column_config.NumberColumn(format="%.1f"),
                                "نسبة الوتيرة من الكمية السنوية %": st.column_config.NumberColumn(format="%.0f%%")})

st.markdown("**جدول الأصناف**")
st.dataframe(sel, hide_index=True, width="stretch",
             column_config={
                 "نسبة الصرف %": st.column_config.ProgressColumn("نسبة الاستهلاك %", format="%.1f%%",
                                                                 min_value=0, max_value=100),
             })

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c
import data_loader as dl

items = c.consumables()

st.title("البنود الاستهلاكية (المستخلص الشهري)")
c.note("البند الاستهلاكي يُتابع بالكميات فقط: كم استُهلك من كمية العقد (لكامل مدة العقد 5 سنوات) وكم بقي. لا تُحسب منه أي قيمة مالية، "
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

# ------------------------------------------------ التوقع حتى نهاية العقد مقارنة بكمية العقد (5 سنوات)
st.subheader("وتيرة الاستهلاك والتوقع حتى نهاية العقد (5 سنوات) مقارنة بكمية العقد")
months, last = c.contract_elapsed()
c.note(f"كمية البند الاستهلاكي لكامل مدة العقد (5 سنوات = {dl.CONTRACT_MONTHS} شهرًا)، وهي «الكمية بالعقد». "
       f"الملف لا يحتوي تواريخ للصرف، لذلك تُعتبر الكميات المنصرفة من بداية العقد ({dl.CONTRACT_START:%m/%Y}) "
       f"حتى آخر شهر له بيانات ({last:%m/%Y})، أي {months} شهرًا ({months / dl.CONTRACT_MONTHS * 100:.0f}% من مدة العقد). "
       f"المتوقع حتى نهاية العقد = المنصرف ÷ {months} × {dl.CONTRACT_MONTHS}، ويفترض استمرار نفس الوتيرة، وهو تقدير للمتابعة.")
proj_qty = sel["الكمية المنصرفة"] * dl.CONTRACT_MONTHS / months
pace = (proj_qty / sel["الكمية بالعقد"] * 100).where(sel["الكمية بالعقد"] > 0)
paced = sel.assign(**{"المتوقع حتى نهاية العقد": proj_qty, "المتوقع من كمية العقد %": pace})
over = paced[pace >= 100].sort_values("المتوقع من كمية العقد %", ascending=False)

a, b, d, e = st.columns(4)
with a:
    c.kpi_official("المنقضي من مدة العقد", f"{months / dl.CONTRACT_MONTHS * 100:.0f}%",
                   f"{months} شهرًا من {dl.CONTRACT_MONTHS} ({dl.CONTRACT_START:%m/%Y} إلى {last:%m/%Y})")
with b:
    c.kpi_official("أصناف استهلكت أكثر من المنقضي", c.num(int((sel["نسبة الصرف %"] > months / dl.CONTRACT_MONTHS * 100).sum())),
                   f"صرفت أكثر من {months / dl.CONTRACT_MONTHS * 100:.0f}% من كمية العقد")
with d:
    c.kpi_official("أصناف ستنفد قبل نهاية العقد", c.num(len(over)), "بالوتيرة الحالية تحتاج أكثر من كمية العقد")
with e:
    c.kpi_official("أصناف أقل من نصف كمية العقد", c.num(int((pace < 50).sum())),
                   f"بالتوقع حتى نهاية العقد، منها {int((pace == 0).sum())} لم يُستهلك منها")

l, r = st.columns(2)
with l:
    labels = ["لم يُستهلك منه", "أقل من نصف كمية العقد", "من 50 إلى 79 بالمئة", "من 80 إلى 99 بالمئة",
              "تنفد قبل نهاية العقد"]
    bands = pd.cut(pace, [-1, 0, 49.999, 79.999, 99.999, float("inf")], labels=labels).value_counts().reindex(labels)
    fig = go.Figure(go.Bar(x=labels, y=bands.values, text=bands.values, textposition="outside",
                           marker=dict(color=["#9AA8B8", "#A9C4E6", "#5B8FD0", "#2F6DB5", "#B45309"],
                                       cornerradius=4)))
    fig = c._layout(fig, height=400, y_title="عدد الأصناف", x_title="المتوقع حتى نهاية العقد كنسبة من كمية العقد")
    fig.update_yaxes(range=[0, bands.max() * 1.15])
    c.chart("توزيع الأصناف حسب المتوقع استهلاكه حتى نهاية العقد",
            "يبين كم صنفًا تكفيه كمية العقد بالوتيرة الحالية، وكم صنفًا ستنفد كميته قبل نهاية العقد.", fig)
with r:
    top = over.head(15).iloc[::-1]
    c.chart("أعلى الأصناف تجاوزًا لكمية العقد",
            "المتوقع حتى نهاية العقد كنسبة من كمية العقد؛ 200% تعني أن الصنف يحتاج ضعف كمية العقد.",
            c.single_bar(top["الصنف البند"], top["المتوقع من كمية العقد %"],
                         "المتوقع من كمية العقد %", fmt=".0f"))
with st.expander(f"كل الأصناف التي ستنفد كميتها قبل نهاية العقد بالوتيرة الحالية ({len(over)} صنفًا)"):
    st.dataframe(over[["الصنف البند", "الوحدة", "الكمية بالعقد", "الكمية المنصرفة", "نسبة الصرف %",
                       "المتوقع حتى نهاية العقد", "المتوقع من كمية العقد %"]],
                 hide_index=True, width="stretch",
                 column_config={"نسبة الصرف %": st.column_config.NumberColumn("المنصرف من كمية العقد %", format="%.0f%%"),
                                "المتوقع حتى نهاية العقد": st.column_config.NumberColumn(format="%.1f"),
                                "المتوقع من كمية العقد %": st.column_config.NumberColumn(format="%.0f%%")})

st.markdown("**جدول الأصناف**")
st.dataframe(sel, hide_index=True, width="stretch",
             column_config={
                 "نسبة الصرف %": st.column_config.ProgressColumn("نسبة الاستهلاك %", format="%.1f%%",
                                                                 min_value=0, max_value=100),
             })

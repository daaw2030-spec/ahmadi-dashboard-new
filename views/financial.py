import numpy as np
import pandas as pd
import plotly.graph_objects as go
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
    c.kpi_official("المبلغ المعتمد", c.money(bal["approved"]), "ميزانية البند التعويضي لمدة العقد (5 سنوات)")
with k2:
    c.kpi_official("المبلغ المنصرف", c.money(bal["disbursed"]), "إجمالي أوامر الشراء الصادرة")
with k3:
    c.kpi_official("الرصيد المتبقي", c.money(bal["remaining"]), "المعتمد − المنصرف")
with k4:
    c.kpi_official("نسبة الصرف", f"{bal['disbursed'] / bal['approved'] * 100:.1f}%",
                   f"{(tx['الحالة'] == 'صادر').sum()} أمر شراء صادر · {(tx['الحالة'] == 'ملغي').sum()} ملغي")
st.caption("هذه البطاقات الأربع ثابتة ولا تتأثر بالفلاتر لأنها الأرقام الرسمية للعقد.")

# ------------------------------------------------ وتيرة الصرف من ميزانية العقد والتوقع
st.subheader("وتيرة الصرف من ميزانية العقد (5 سنوات) والتوقع بنفس الوتيرة")
months_done, last = c.contract_elapsed()
end = dl.CONTRACT_START + pd.DateOffset(months=dl.CONTRACT_MONTHS)
monthly_avg = bal["disbursed"] / months_done
months_left = bal["remaining"] / monthly_avg if monthly_avg else float("inf")
depletion = last.to_period("M").to_timestamp() + pd.DateOffset(months=int(np.ceil(months_left)))
projected_total = monthly_avg * dl.CONTRACT_MONTHS
c.note(f"العقد من {dl.CONTRACT_START:%m/%Y} إلى {end - pd.DateOffset(days=1):%m/%Y} ({dl.CONTRACT_MONTHS} شهرًا). "
       f"المنقضي حتى آخر شهر له بيانات ({last:%m/%Y}، وبياناته حتى {last:%d/%m}): {months_done} شهرًا. "
       "التوقع يفترض استمرار متوسط الصرف الشهري منذ بداية العقد، وهو تقدير للتخطيط وليس رقمًا نهائيًا.")
k1, k2, k3, k4 = st.columns(4)
with k1:
    c.kpi_official("المنقضي من مدة العقد", f"{months_done / dl.CONTRACT_MONTHS * 100:.1f}%",
                   f"{months_done} شهرًا من {dl.CONTRACT_MONTHS}")
with k2:
    c.kpi_official("متوسط الصرف الشهري", c.money(monthly_avg, 0),
                   f"مقابل {c.money(bal['approved'] / dl.CONTRACT_MONTHS, 0)} لو وُزّعت الميزانية بالتساوي")
with k3:
    c.kpi_official("الرصيد يكفي بنفس الوتيرة", f"{months_left:.1f} شهرًا", f"ينفد تقريبًا في {depletion:%m/%Y}")
with k4:
    c.kpi_official("المتوقع صرفه حتى نهاية العقد", f"{projected_total / 1e6:.2f} مليون",
                   f"يتجاوز الميزانية بـ {(projected_total - bal['approved']) / 1e6:.2f} مليون ريال"
                   if projected_total > bal["approved"] else "ضمن الميزانية")

span = pd.period_range(dl.CONTRACT_START, end - pd.DateOffset(days=1), freq="M")
actual = (tx.dropna(subset=["التاريخ"]).groupby(tx["التاريخ"].dt.to_period("M"))["المبلغ"].sum()
          .reindex(pd.period_range(dl.CONTRACT_START, last, freq="M"), fill_value=0).cumsum())
x_act = actual.index.to_timestamp()
future = pd.period_range(last.to_period("M"), span[-1], freq="M")
proj = actual.iloc[-1] + monthly_avg * np.arange(len(future))
fig = go.Figure()
fig.add_scatter(x=span.to_timestamp(), y=bal["approved"] / dl.CONTRACT_MONTHS * np.arange(1, len(span) + 1),
                name="الصرف المتوازن مع مدة العقد", line=dict(color="#9AA8B8", dash="dot"),
                hovertemplate="%{x|%m/%Y}<br>%{y:,.0f}<extra></extra>")
fig.add_scatter(x=x_act, y=actual.values, name="المنصرف الفعلي (تراكمي)", line=dict(color=c.YEAR_COLORS[2026], width=3),
                hovertemplate="%{x|%m/%Y}<br>%{y:,.0f}<extra></extra>")
fig.add_scatter(x=future.to_timestamp(), y=proj, name="المتوقع بنفس الوتيرة", line=dict(color="#B45309", dash="dash"),
                hovertemplate="%{x|%m/%Y}<br>%{y:,.0f}<extra></extra>")
fig.add_hline(y=bal["approved"], line=dict(color="#B91C1C", width=1.5),
              annotation_text=f"الميزانية المعتمدة {c.money(bal['approved'], 0)}", annotation_position="top left")
if depletion < end:
    fig.add_vline(x=depletion, line=dict(color="#B91C1C", dash="dot", width=1))
    fig.add_annotation(x=depletion, y=bal["approved"], text=f"نفاد الرصيد {depletion:%m/%Y}", showarrow=True,
                       arrowhead=2, ax=40, ay=-40, font=dict(color="#B91C1C"))
fig = c._layout(fig, height=440, y_title="المبلغ التراكمي (ريال)")
fig.update_xaxes(tickformat="%m/%Y", dtick="M6")
c.chart("المنصرف التراكمي مقابل الميزانية حتى نهاية العقد",
        "يقارن الصرف الفعلي بالصرف المتوازن مع مدة العقد، ويبين متى ينفد الرصيد إذا استمرت نفس الوتيرة.", fig)

# ------------------------------------------------ المقارنة 2025 مقابل 2026
months = sorted(f["months"])
st.subheader("مقارنة 2025 و2026 لنفس الأشهر")
st.caption("الأشهر المختارة: " + "، ".join(dl.MONTHS_AR[m] for m in months)
           + ("" if set(months) <= set(c.comparable_months()) else
              " — تنبيه: بعض الأشهر المختارة ليس لها بيانات بعد في 2026، فالمقارنة ليست متكافئة."))
statuses = c.status_filter(["صادر", "ملغي"], key="fin_status")
sel = c.apply_filters(tx, f)
sel = sel[sel["الحالة"].isin(statuses)]
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
    c.chart("المبلغ المنصرف شهريًا", "يقارن قيمة أوامر الشراء الصادرة في كل شهر بين العامين لاكتشاف أشهر الذروة.",
            c.monthly_compare(sel, "المبلغ", months, "المبلغ (ريال)"))
with r:
    c.chart("المنصرف التراكمي", "يوضح وتيرة استهلاك العقد: أي العامين كان أسرع صرفًا حتى نفس الشهر.",
            c.cumulative_compare(sel, "المبلغ", months, "المبلغ التراكمي (ريال)"))

l, r = st.columns(2)
with l:
    c.chart("المنصرف حسب القسم", "يبين الأقسام الأعلى صرفًا وكيف تغيّر نصيب كل قسم بين العامين.",
            c.category_compare(sel, "القسم", "المبلغ", "المبلغ (ريال)"))
with r:
    c.chart("عدد أوامر الشراء حسب القسم", "يقارن حجم النشاط (عدد الأوامر) بغض النظر عن قيمتها.",
            c.category_compare(sel, "القسم", None, "عدد أوامر الشراء", fmt=",.0f"))

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
    po = c.purchase_orders()
    official_ids = tx.loc[tx["الحالة"] == "صادر", ["رقم طلب الشراء", "المبلغ"]]
    absent = official_ids[~official_ids["رقم طلب الشراء"].isin(po["رقم طلب الشراء"])]
    st.markdown(
        f"- مجموع «تكلفة الطلب» في ملف أوامر الشراء = **{c.money(po['تكلفة الطلب'].sum())}**، "
        f"والفرق عن الرقم الرسمي = **{c.money(bal['disbursed'] - po['تكلفة الطلب'].sum())}**. "
        + ("سبب الفرق: أوامر موجودة في ورقة الرصيد وغير موجودة في ملف أوامر الشراء: "
           + "، ".join(f"طلب {r} بمبلغ {c.money(v)}" for r, v in absent.itertuples(index=False))
           + ". لم يُعدّل أي رقم؛ المعتمد هو ورقة الرصيد." if len(absent) else ""))
    st.markdown("**ملاحظات مدخلة يدويًا أسفل الورقة المرجعية (تُعرض كما هي):**")
    for row, cells in bal["sheet_notes"].items():
        st.text(f"سطر {row}: " + "  |  ".join(str(x) for x in cells))

with st.expander("جدول المعاملات (حسب الفلاتر)"):
    st.dataframe(sel[["رقم طلب الشراء", "رقم امر الشراء", "الجهة الطالبة", "القسم", "المبلغ", "الحالة",
                      "التاريخ", "التاريخ الهجري"]].sort_values("التاريخ"),
                 width="stretch", hide_index=True,
                 column_config={"المبلغ": st.column_config.NumberColumn(format="%,.2f"),
                                "التاريخ": st.column_config.DateColumn(format="YYYY-MM-DD")})

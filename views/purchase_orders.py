import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c
import data_loader as dl

f = st.session_state["filters"]
po_all = c.purchase_orders()

st.title("أوامر الشراء ودورة المعاملة")
basis = st.radio("أساس التاريخ للسنة والشهر", list(dl.DATE_BASES), horizontal=True, key="po_basis",
                 help="إذا كان تاريخ الأساس مفقودًا أو غير صالح يُستخدم أقرب تاريخ صالح في المعاملة بدلًا من استبعادها.")
po = dl.with_reference_date(po_all, basis)
sel = c.apply_filters(po, f)
months = sorted(f["months"])
y25, y26 = (sel[sel["السنة"] == y] for y in dl.YEARS)

c.note("المدد الزمنية محسوبة من التواريخ مباشرة. أي مدة سالبة أو مبنية على تاريخ غير صالح "
       "(خارج الفترة 2024 حتى اليوم) تُستبعد من المؤشرات الزمنية فقط، وتبقى المعاملة في العدد والتكلفة.")

a, b, d, e = st.columns(4)
with a:
    c.kpi_compare("عدد الطلبات", len(y25), len(y26), fmt=c.num)
with b:
    c.kpi_compare("متوسط الأيام: الطلب ← صدور الأمر",
                  y25["مدة الطلب حتى صدور الأمر"].mean(), y26["مدة الطلب حتى صدور الأمر"].mean(),
                  fmt=lambda v: "—" if pd.isna(v) else f"{v:.1f} يوم")
with d:
    c.kpi_compare("متوسط الأيام: الأمر ← التسليم للمستودع",
                  y25["مدة الأمر حتى التسليم"].mean(), y26["مدة الأمر حتى التسليم"].mean(),
                  fmt=lambda v: "—" if pd.isna(v) else f"{v:.1f} يوم")
with e:
    rate = lambda s: (s["الحالة"] == "تم التسليم").mean() * 100 if len(s) else 0  # noqa: E731
    c.kpi_compare("نسبة الطلبات المسلّمة", rate(y25), rate(y26), fmt=lambda v: f"{v:.1f}%")

l, r = st.columns(2)
with l:
    st.markdown("**عدد الطلبات شهريًا**")
    c.show(c.monthly_compare(sel, None, months, "عدد الطلبات", fmt=",.0f"))
with r:
    st.markdown("**متوسط مدة كل مرحلة (يوم)**")
    stages = dl.STAGE_DURATIONS
    fig = go.Figure()
    for y in dl.YEARS:
        part = sel[sel["السنة"] == y]
        fig.add_bar(name=str(y), y=stages, x=part[stages].mean().values, orientation="h",
                    marker=dict(color=c.YEAR_COLORS[y], cornerradius=4),
                    customdata=part[stages].count().values,
                    hovertemplate=f"%{{y}} {y}<br>%{{x:.1f}} يوم (من %{{customdata}} معاملة)<extra></extra>")
    fig = c._layout(fig, height=480, x_title="متوسط الأيام")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=c.GRID)
    c.show(fig)

l, r = st.columns(2)
with l:
    st.markdown("**متوسط الأيام من الطلب حتى صدور الأمر حسب القسم**")
    c.show(c.category_compare(sel, "القسم", "مدة الطلب حتى صدور الأمر", "يوم", agg="mean", fmt=".1f"))
with r:
    st.markdown("**حالة الطلبات**")
    status = sel.groupby(["الحالة", "السنة"]).size().unstack(fill_value=0).reindex(columns=list(dl.YEARS), fill_value=0)
    fig = go.Figure()
    for y in dl.YEARS:
        fig.add_bar(name=str(y), x=status.index, y=status[y], marker=dict(color=c.YEAR_COLORS[y], cornerradius=4),
                    hovertemplate=f"%{{x}} {y}<br>%{{y}} طلب<extra></extra>")
    c.show(c._layout(fig, y_title="عدد الطلبات"))

with st.expander("جودة البيانات: المدد المستبعدة من المؤشرات الزمنية"):
    raw_dates = {name: po_all[name].notna().sum() for name in dl.STAGE_DATES}
    q = pd.DataFrame({
        "المرحلة": dl.STAGE_DURATIONS,
        "مدد صالحة": [int(sel[s].notna().sum()) for s in dl.STAGE_DURATIONS],
        "مستبعدة (سالبة/تاريخ غير صالح/مرحلة لم تكتمل)": [int(sel[s].isna().sum()) for s in dl.STAGE_DURATIONS],
    })
    st.dataframe(q, hide_index=True, width="stretch")
    st.caption(f"معاملات استُخدم لها تاريخ بديل لتحديد السنة/الشهر: {int(sel['تاريخ بديل'].sum())} — "
               f"إجمالي المعاملات في الملف: {len(po_all)} ولم تُحذف أي معاملة.")
    st.caption("ملاحظة: «تكلفة الطلب» في هذا الملف مجموعها "
               f"{c.money(po_all['تكلفة الطلب'].sum())} ريال، وهي لا تُستخدم كرقم مالي رسمي؛ "
               "الرقم الرسمي في صفحة الملخص المالي.")

with st.expander("جدول الطلبات (حسب الفلاتر)"):
    cols = ["رقم طلب الشراء", "القسم", "الموقع", "وصف الطلب", "المورد", "الحالة", "تكلفة الطلب",
            "تاريخ المرجع", "مدة الطلب حتى صدور الأمر", "مدة الأمر حتى التسليم"]
    st.dataframe(sel[cols].sort_values("تاريخ المرجع"), hide_index=True, width="stretch",
                 column_config={"تكلفة الطلب": st.column_config.NumberColumn(format="%,.2f"),
                                "تاريخ المرجع": st.column_config.DateColumn(format="YYYY-MM-DD")})

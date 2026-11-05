import numpy as np
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
statuses = c.status_filter(["تم التسليم", "صدر أمر الشراء", "قيد الإجراء", "ملغي"], key="po_status")
sel = c.apply_filters(po, f)
sel = sel[sel["الحالة"].isin(statuses)]
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

st.subheader("الالتزام بمدد التسليم المعتمدة")
c.note(f"الحد الأقصى للدورة كاملة من البلاغ حتى الاستلام في المستودع {dl.CYCLE_MAX} يومًا، ومن استلام المقاول "
       f"لأمر الشراء حتى التسليم للمستودع من 3 إلى {dl.DELIVERY_MAX} أيام. الملف لا يحتوي تاريخ البلاغ ولا تاريخ "
       "استلام المقاول للأمر، لذلك تُقاس الدورة من إعداد الطلب، والتسليم من صدور أمر الشراء. "
       "النسب من الطلبات المسلّمة التي لها مدة صالحة.")
LIMITS = [("مدة الطلب حتى التسليم", dl.CYCLE_MAX, "الدورة كاملة"),
          ("مدة الأمر حتى التسليم", dl.DELIVERY_MAX, "التسليم للمستودع")]
within = lambda s, col, lim: (s[col].dropna() <= lim).mean() * 100 if s[col].notna().any() else float("nan")  # noqa: E731
pct = lambda v: "—" if pd.isna(v) else f"{v:.1f}%"  # noqa: E731
for col_ui, (col, lim, name) in zip(st.columns(2), LIMITS):
    with col_ui:
        days = "أيام" if lim <= 10 else "يومًا"
        c.kpi_compare(f"{name} خلال {lim} {days}", within(y25, col, lim), within(y26, col, lim), fmt=pct)
c.chart("توزيع مدة التسليم للمستودع",
        f"يبين نسبة الطلبات المسلّمة في كل فئة زمنية؛ الحد المعتمد {dl.DELIVERY_MAX} أيام.",
        c.delivery_bands(sel, "مدة الأمر حتى التسليم", dl.DELIVERY_MAX))
late = sel[sel["مدة الأمر حتى التسليم"] > dl.DELIVERY_MAX]
with st.expander(f"الطلبات التي تجاوز تسليمها {dl.DELIVERY_MAX} أيام ({len(late)} طلبًا)"):
    st.dataframe(late[["رقم طلب الشراء", "القسم", "وصف الطلب", "المورد", "السنة", "مدة الأمر حتى التسليم",
                       "مدة الطلب حتى التسليم"]]
                 .sort_values("مدة الأمر حتى التسليم", ascending=False), hide_index=True, width="stretch")

l, r = st.columns(2)
with l:
    c.chart("عدد الطلبات شهريًا", "يقارن حجم الطلبات الواردة في كل شهر بين العامين.",
            c.monthly_compare(sel, None, months, "عدد الطلبات", fmt=",.0f"))
with r:
    stages = dl.STAGE_DURATIONS
    fig = go.Figure()
    for y in c.active_years():
        part = sel[sel["السنة"] == y]
        fig.add_bar(name=str(y), y=stages, x=part[stages].mean().values, orientation="h",
                    marker=dict(color=c.YEAR_COLORS[y], cornerradius=4),
                    customdata=part[stages].count().values,
                    hovertemplate=f"%{{y}} {y}<br>%{{x:.1f}} يوم (من %{{customdata}} معاملة)<extra></extra>")
    fig = c._layout(fig, height=520, x_title="متوسط عدد الأيام")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=c.GRID)
    c.chart("متوسط مدة كل مرحلة (يوم)", "يحدد المراحل التي تستهلك أطول وقت؛ المدد السالبة أو غير الصالحة مستبعدة.",
            fig)

l, r = st.columns(2)
with l:
    c.chart("متوسط الأيام من الطلب حتى صدور الأمر حسب القسم",
            "يقارن سرعة إنجاز طلبات كل قسم بين العامين.",
            c.category_compare(sel, "القسم", "مدة الطلب حتى صدور الأمر", "متوسط عدد الأيام", agg="mean", fmt=".1f"))
with r:
    years = c.active_years()
    # الإلغاء يُعرض من ملف الطلبات الملغاة (صفحة الطلبات المباشرة والملغاة) وليس من حالة هذا الملف
    status = (sel[sel["الحالة"] != "ملغي"].groupby(["الحالة", "السنة"]).size().unstack(fill_value=0)
              .reindex(columns=years, fill_value=0))
    fig = go.Figure()
    for y in years:
        fig.add_bar(name=str(y), x=status.index, y=status[y], marker=dict(color=c.YEAR_COLORS[y], cornerradius=4),
                    hovertemplate=f"%{{x}} {y}<br>%{{y}} طلب<extra></extra>")
    c.chart("حالة الطلبات", "يوضح كم طلبًا وصل إلى المستودع وكم ما زال مفتوحًا. الإلغاءات في صفحة الطلبات المباشرة والملغاة.",
            c._layout(fig, y_title="عدد الطلبات", x_title="الحالة"))

# ------------------------------------------------ الطلبات المفتوحة المتأخرة
st.subheader(f"الطلبات المفتوحة التي تجاوزت {dl.OVERDUE_DAYS} يومًا")
years = c.active_years()
period, op, as_of = dl.open_snapshot(po_all, years)
if f["depts"]:
    period, op = (d[d["القسم"].isin(f["depts"])] for d in (period, op))
late_open = op[op["عمر الطلب (يوم)"] > dl.OVERDUE_DAYS].sort_values(["السنة", "عمر الطلب (يوم)"],
                                                                     ascending=[False, False])
c.note(f"2025: كل طلبات السنة ووضعها في 31/12/2025. 2026: الطلبات من 1 يناير حتى {as_of:%d/%m/%Y} (آخر تاريخ "
       "مسجل في الملف) ووضعها في ذلك اليوم. الطلب المتأخر هو الذي لم يُسلَّم للمستودع حتى يوم القطع ومضى على "
       f"إعداده أكثر من {dl.OVERDUE_DAYS} يومًا. الملغاة مستبعدة، والفترة لا تتأثر بفلتر الأشهر.")
c.note("<b>معنى الحالات:</b> «متأخر» = مضى على إعداد الطلب أكثر من 60 يومًا ولم يصل للمستودع، في أي مرحلة كان. "
       "«صدر أمرها وتنتظر التسليم» = أصدرت المشتريات أمر الشراء، والطلب ينتظر أن يورّده المقاول للمستودع "
       f"(الحد المعتمد من استلام المقاول للأمر حتى التسليم {dl.DELIVERY_MAX} أيام). «قيد الإجراء» = لم يصدر "
       "أمر الشراء بعد، والطلب ما زال في الإجراءات الداخلية (استلام الطلب، عروض الأسعار، المحضر، الإرسال للمشتريات). "
       "«الحالة الآن» في الجدول = وضع الطلب في آخر تحديث للملف، فبعض طلبات 2025 سُلّمت لاحقًا.")
count = lambda d, y: int((d["السنة"] == y).sum())  # noqa: E731
issued = late_open[late_open["الحالة عند القطع"] == "صدر أمر الشراء"]
pending = late_open[late_open["الحالة عند القطع"] == "قيد الإجراء"]
k1, k2, k3, k4 = st.columns(4)
with k1:
    c.kpi_compare("إجمالي الطلبات المتأخرة", count(late_open, 2025), count(late_open, 2026), fmt=c.num,
                  show_change=False)
with k2:
    c.kpi_compare("منها: صدر أمر الشراء وينتظر تسليم المقاول", count(issued, 2025), count(issued, 2026), fmt=c.num,
                  show_change=False)
with k3:
    c.kpi_compare("منها: قيد الإجراء (لم يصدر أمر الشراء)", count(pending, 2025), count(pending, 2026), fmt=c.num,
                  show_change=False)
with k4:
    share = lambda y: count(late_open, y) / count(period, y) * 100 if count(period, y) else 0  # noqa: E731
    c.kpi_compare("نسبة المتأخرة من طلبات السنة", share(2025), share(2026), fmt=lambda v: f"{v:.1f}%",
                  show_change=False)

late_open = late_open.assign(**{"يحتاج متابعة": np.where(late_open["الحالة"] == "تم التسليم", "لا — سُلّم لاحقًا",
                                                           "نعم")})
summary = pd.DataFrame([{
    "الفترة": "2025 كاملة (حتى 31/12/2025)" if y < as_of.year else f"{y} حتى {as_of:%d/%m/%Y}",
    "تجاوزت 60 يومًا": count(late_open, y), "صدر أمر الشراء وينتظر تسليم المقاول": count(issued, y),
    "قيد الإجراء (لم يصدر أمر الشراء)": count(pending, y),
    "سُلّمت لاحقًا": count(late_open[late_open["الحالة"] == "تم التسليم"], y),
    "ما زالت مفتوحة الآن": count(late_open[late_open["يحتاج متابعة"] == "نعم"], y)} for y in years])
st.markdown("**ملخص الطلبات المتأخرة ووضعها الآن**")
st.caption(f"«سُلّمت لاحقًا» و«ما زالت مفتوحة الآن» حسب آخر تحديث للملف ({as_of:%d/%m/%Y}). "
           f"إجمالي ما يحتاج متابعة الآن: {int((late_open['يحتاج متابعة'] == 'نعم').sum())} طلبًا.")
st.dataframe(summary, hide_index=True, width="stretch")

stages = [s for s in dl.STAGE_DATES if s in set(late_open["آخر مرحلة"])]
fig = go.Figure()
for y in years:
    g = late_open[late_open["السنة"] == y]["آخر مرحلة"].value_counts().reindex(stages, fill_value=0)
    fig.add_bar(name=str(y), y=stages, x=g.values, orientation="h", text=g.values, textposition="outside",
                marker=dict(color=c.YEAR_COLORS[y], cornerradius=4),
                hovertemplate=f"%{{y}} {y}<br>%{{x}} طلبًا<extra></extra>")
fig = c._layout(fig, height=max(280, 90 + 56 * len(stages)), x_title="عدد الطلبات")
fig.update_yaxes(autorange="reversed", showgrid=False, title="", ticksuffix="   ")
c.chart("آخر مرحلة وصلتها الطلبات المتأخرة",
        "يبين أين تتوقف الطلبات: «صدور أمر الشراء» يعني أن الأمر صدر والطلب ينتظر التسليم للمستودع.", fig)

counts = late_open["آخر مرحلة"].value_counts()
chosen = st.pills("عرض طلبات مرحلة معينة", [f"{s} ({counts[s]})" for s in stages], selection_mode="multi",
                  key="late_stage_pick")
chosen = [p.rsplit(" (", 1)[0] for p in chosen]
only_open = st.toggle("عرض الطلبات التي تحتاج متابعة الآن فقط", value=True, key="late_only_open")
shown = late_open[late_open["آخر مرحلة"].isin(chosen)] if chosen else late_open
if only_open:
    shown = shown[shown["يحتاج متابعة"] == "نعم"]
st.caption(f"المعروض: {len(shown)} طلبًا" + (f" — المرحلة: {'، '.join(chosen)}" if chosen else " — كل المراحل")
           + ". «آخر مرحلة» عند نهاية الفترة، و«الحالة الآن» وضع الطلب في آخر تحديث للملف.")
st.dataframe(
    shown[["السنة", "رقم طلب الشراء", "القسم", "وصف الطلب", "الموقع", "المورد", "آخر مرحلة", "تاريخ آخر مرحلة",
           "عمر الطلب (يوم)", "أيام في المرحلة الحالية", "الحالة", "يحتاج متابعة"]]
    .rename(columns={"الحالة": "الحالة الآن", "وصف الطلب": "اسم الطلب"})
    .replace({"الحالة الآن": {"صدر أمر الشراء": "صدر أمر الشراء — ينتظر التسليم من المقاول"}})
    .fillna({"اسم الطلب": "غير مذكور في الملف", "الموقع": "—", "المورد": "—"}),
    hide_index=True, width="stretch",
    column_config={"السنة": st.column_config.NumberColumn(format="%d"),
                   "تاريخ آخر مرحلة": st.column_config.DateColumn(format="YYYY-MM-DD")})

with st.expander("جودة البيانات: المدد المستبعدة من المؤشرات الزمنية"):
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

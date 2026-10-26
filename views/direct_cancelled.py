import streamlit as st

import common as c

f = st.session_state["filters"]
direct_all = c.direct_requests()
canc_all = c.cancelled()
months = sorted(f["months"])

st.title("الطلبات المباشرة والملغاة")
c.note("التواريخ الهجرية في الملف حُوّلت إلى ميلادي (تقويم أم القرى). الطلبات التي ليس لها تاريخ صالح "
       "تبقى في الجداول ولا تظهر في المقارنة الشهرية.")

direct = c.apply_filters(direct_all, f)
canc = c.apply_filters(canc_all, f)
d25, d26 = (direct[direct["السنة"] == y] for y in (2025, 2026))
c25, c26 = (canc[canc["السنة"] == y] for y in (2025, 2026))

a, b, d = st.columns(3)
with a:
    c.kpi_compare("الطلبات المباشرة", len(d25), len(d26), fmt=c.num)
with b:
    c.kpi_compare("الطلبات المعادة من المشتريات", d25["معاد من المشتريات"].sum(), d26["معاد من المشتريات"].sum(),
                  fmt=c.num)
with d:
    c.kpi_compare("الطلبات الملغاة", len(c25), len(c26), fmt=c.num)

l, r = st.columns(2)
with l:
    st.markdown("**الطلبات المباشرة شهريًا**")
    c.show(c.monthly_compare(direct, None, months, "عدد الطلبات", fmt=",.0f"))
with r:
    st.markdown("**الطلبات الملغاة شهريًا**")
    c.show(c.monthly_compare(canc, None, months, "عدد الطلبات", fmt=",.0f"))

l, r = st.columns(2)
with l:
    st.markdown("**الطلبات المباشرة حسب القسم**")
    c.show(c.category_compare(direct, "القسم", None, "عدد الطلبات", fmt=",.0f"))
with r:
    st.markdown("**الطلبات الملغاة حسب القسم**")
    c.show(c.category_compare(canc, "القسم", None, "عدد الطلبات", fmt=",.0f"))

with st.expander("جدول الطلبات المباشرة"):
    st.dataframe(direct[["رقم الطلب", "تاريخ الطلب", "الجهة الطالبة", "القسم", "وصف الطلب", "الصادر للجهة",
                         "معاد من المشتريات", "الملاحظات"]].sort_values("تاريخ الطلب"),
                 hide_index=True, width="stretch",
                 column_config={"تاريخ الطلب": st.column_config.DateColumn(format="YYYY-MM-DD")})
    missing = direct_all["السنة"].isna().sum()
    if missing:
        st.caption(f"طلبات بدون تاريخ صالح في الملف (غير معروضة في المقارنة): {missing}")
with st.expander("جدول الطلبات الملغاة"):
    st.dataframe(canc[["رقم الطلب", "الجهة الطالبة", "القسم", "الموقع", "سبب/بيان الإلغاء", "تاريخ الإلغاء",
                       "تاريخ الإلغاء (ميلادي)"]].sort_values("تاريخ الإلغاء (ميلادي)"),
                 hide_index=True, width="stretch",
                 column_config={"تاريخ الإلغاء (ميلادي)": st.column_config.DateColumn(format="YYYY-MM-DD")})

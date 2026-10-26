import streamlit as st

import common as c

st.set_page_config(page_title="لوحة عقد الأحمدي 2025–2026", page_icon="📊", layout="wide")
c.inject_css()

missing = c.missing_files()
if missing:
    c.upload_screen(missing)
    st.stop()

pages = [
    st.Page("views/financial.py", title="الملخص المالي", icon=":material/payments:", default=True),
    st.Page("views/purchase_orders.py", title="أوامر الشراء ودورة المعاملة", icon=":material/schedule:"),
    st.Page("views/direct_cancelled.py", title="الطلبات المباشرة والملغاة", icon=":material/assignment:"),
    st.Page("views/consumables.py", title="البنود الاستهلاكية", icon=":material/inventory_2:"),
]
nav = st.navigation(pages)
st.session_state["filters"] = c.sidebar_filters()
nav.run()

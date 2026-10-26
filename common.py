"""عناصر مشتركة: الألوان، التنسيق، الفلاتر، والرسومات."""
from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl

# درجات الأزرق: 2025 أفتح و2026 أغمق (فرق إضاءة واضح يناسب عمى الألوان)
YEAR_COLORS = {2025: "#7FB2E5", 2026: "#0B4A99"}
NAVY = "#0A2540"
INK_MUTED = "#5B6B82"
GRID = "#E3ECF7"
FONT = "Tajawal, 'Segoe UI', Tahoma, sans-serif"


# ---------------------------------------------------------------- البيانات المخزنة مؤقتًا
# مصدر كل ملف: مجلد data إن وُجد، وإلا الملف المرفوع في الجلسة (للنشر دون رفع البيانات إلى GitHub)
def missing_files() -> list[str]:
    uploads = st.session_state.get("uploads", {})
    return [k for k, (path, _) in dl.FILES.items() if not path.exists() and k not in uploads]


def _src(key: str) -> bytes | None:
    path, _ = dl.FILES[key]
    return None if path.exists() else st.session_state["uploads"][key]


def _io(data: bytes | None):
    return io.BytesIO(data) if data is not None else None


@st.cache_data(show_spinner="جارٍ تحميل البيانات…")
def _official(data):
    return dl.load_official_balance(_io(data))


@st.cache_data
def _purchase_orders(data):
    return dl.load_purchase_orders(_io(data))


@st.cache_data
def _direct_requests(data):
    return dl.load_direct_requests(_io(data))


@st.cache_data
def _cancelled(data):
    return dl.load_cancelled(_io(data))


@st.cache_data
def _consumables(data):
    return dl.load_consumables(_io(data))


def official():
    return _official(_src("contract"))


def purchase_orders():
    return _purchase_orders(_src("po"))


def direct_requests():
    return _direct_requests(_src("direct"))


def cancelled():
    return _cancelled(_src("direct"))


def consumables():
    return _consumables(_src("consumables"))


def upload_screen(missing: list[str]):
    st.title("لوحة عقد الأحمدي 2025–2026")
    st.info("ملفات البيانات غير موجودة على الخادم (لم تُرفع إلى GitHub حفاظًا على سريتها). "
            "ارفع الملفات التالية لعرض اللوحة؛ تبقى في جلستك فقط ولا تُحفظ.")
    uploads = st.session_state.setdefault("uploads", {})
    for key in missing:
        _, label = dl.FILES[key]
        f = st.file_uploader(label, type=["xlsx"], key=f"up_{key}")
        if f is not None:
            uploads[key] = f.getvalue()
    if not missing_files():
        st.rerun()


# ---------------------------------------------------------------- التنسيق
def inject_css():
    st.markdown(
        f"""
        <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
        <style>
        html, body, [class*="css"], .stMarkdown, .stText, button, input, label, select, textarea {{
            font-family: {FONT};
        }}
        .stMainBlockContainer, section[data-testid="stSidebar"] {{ direction: rtl; text-align: right; }}
        .stMainBlockContainer {{ padding-top: 2rem; }}
        h1, h2, h3 {{ color: {NAVY}; font-weight: 800; }}
        div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {{ direction: ltr; }}
        .kpi {{
            background: #FFFFFF; border: 1px solid #D6E4F5; border-radius: 12px;
            padding: 14px 16px; height: 100%; box-shadow: 0 1px 2px rgba(10,37,64,.05);
            border-top: 4px solid #0B4A99;
        }}
        .kpi.official {{ border-top-color: {NAVY}; background: linear-gradient(180deg,#F3F8FE,#FFFFFF); }}
        .kpi .label {{ color: {INK_MUTED}; font-size: .9rem; font-weight: 500; }}
        .kpi .value {{ color: {NAVY}; font-size: 1.55rem; font-weight: 800; margin-top: 2px; direction: ltr; text-align: right; }}
        .kpi .sub {{ color: {INK_MUTED}; font-size: .8rem; margin-top: 4px; }}
        .kpi .years {{ display: flex; gap: 14px; margin-top: 6px; }}
        .kpi .years div {{ flex: 1; }}
        .kpi .yl {{ font-size: .78rem; color: {INK_MUTED}; display: flex; align-items: center; gap: 6px; }}
        .kpi .yl i {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
        .kpi .yv {{ font-size: 1.2rem; font-weight: 700; color: {NAVY}; direction: ltr; text-align: right; }}
        .kpi .delta {{ font-size: .82rem; margin-top: 6px; color: {NAVY}; font-weight: 600; }}
        .note {{ background:#EEF5FD; border-right:4px solid #0B4A99; padding:10px 14px; border-radius:8px;
                 color:{NAVY}; font-size:.9rem; margin: 6px 0 14px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def money(v: float, decimals: int = 2) -> str:
    return f"{v:,.{decimals}f}"


def num(v: float) -> str:
    return f"{v:,.0f}" if abs(v - round(v)) < 1e-9 else f"{v:,.1f}"


def change_text(a: float, b: float) -> str:
    if a in (0, None) or pd.isna(a):
        return "التغير: —"
    pct = (b - a) / abs(a) * 100
    if abs(pct) < 0.05:
        return "■ بدون تغير في 2026 مقارنة بـ 2025"
    word, arrow = ("زيادة", "▲") if pct > 0 else ("انخفاض", "▼")
    return f"{arrow} {word} {abs(pct):.1f}% في 2026 مقارنة بـ 2025"


def kpi_official(label: str, value: str, sub: str = ""):
    st.markdown(f'<div class="kpi official"><div class="label">{label}</div>'
                f'<div class="value">{value}</div><div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def kpi_compare(label: str, v2025: float, v2026: float, fmt=money, show_change: bool = True):
    years = "".join(
        f'<div><div class="yl"><i style="background:{YEAR_COLORS[y]}"></i>{y}</div>'
        f'<div class="yv">{fmt(v)}</div></div>' for y, v in ((2025, v2025), (2026, v2026)))
    delta = f'<div class="delta">{change_text(v2025, v2026)}</div>' if show_change else ""
    st.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="years">{years}</div>{delta}</div>',
                unsafe_allow_html=True)


def note(text: str):
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- الفلاتر العامة
def comparable_months() -> list[int]:
    """الأشهر التي لها بيانات رسمية في 2026 — تُقارن بنفس الأشهر من 2025."""
    tx = official()["transactions"]
    return sorted(tx.loc[tx["السنة"] == 2026, "الشهر"].dropna().astype(int).unique().tolist())


ALL_DEPTS = ["التكييف", "المدنية", "المدنية (مضخات)", "الورشة المركزية", "الكهربائية",
             "صحة البيئة والتشجير", "المصاعد", "صالة الركاب", "أخرى", "غير محدد"]


def sidebar_filters():
    with st.sidebar:
        st.markdown("### الفلاتر العامة")
        same = comparable_months()
        mode = st.radio("فترة المقارنة", ["نفس الأشهر المتاحة في 2026", "كل الأشهر", "تحديد يدوي"],
                        key="month_mode", help="المقارنة العادلة تكون بين نفس الأشهر في العامين.")
        if mode == "نفس الأشهر المتاحة في 2026":
            months = same
            st.caption(f"من {dl.MONTHS_AR[same[0]]} إلى {dl.MONTHS_AR[same[-1]]}" if same else "")
        elif mode == "كل الأشهر":
            months = list(range(1, 13))
        else:
            months = st.multiselect("الأشهر", list(range(1, 13)), default=same, key="months_manual",
                                    format_func=lambda m: dl.MONTHS_AR[m])
        depts = st.multiselect("القسم / الجهة الطالبة", ALL_DEPTS, default=[], key="depts",
                               placeholder="كل الأقسام")
        st.divider()
        st.caption("العامان المقارنان: 2025 و2026 فقط.")
    return {"months": months or list(range(1, 13)), "depts": depts}


def apply_filters(df: pd.DataFrame, f: dict, dept_col: str = "القسم") -> pd.DataFrame:
    out = df[df["السنة"].isin(dl.YEARS) & df["الشهر"].isin(f["months"])]
    if f["depts"]:
        out = out[out[dept_col].isin(f["depts"])]
    return out


# ---------------------------------------------------------------- الرسومات
def _layout(fig: go.Figure, height: int = 380, y_title: str = "", x_title: str = "") -> go.Figure:
    fig.update_layout(
        height=height, font=dict(family=FONT, color=NAVY, size=13),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10), bargap=0.28, bargroupgap=0.06,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
        hoverlabel=dict(font_family=FONT, bgcolor="white"),
    )
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=y_title, tickformat=",")
    fig.update_xaxes(showgrid=False, title=x_title, linecolor="#C9D7EA")
    return fig


def monthly_compare(df: pd.DataFrame, value: str | None, months: list[int], y_title: str,
                    agg: str = "sum", fmt: str = ",.2f") -> go.Figure:
    """أعمدة متجاورة: نفس الشهر في 2025 مقابل 2026."""
    fig = go.Figure()
    for y in dl.YEARS:
        part = df[df["السنة"] == y]
        g = part.groupby("الشهر")[value].agg(agg) if value else part.groupby("الشهر").size()
        g = g.reindex(months, fill_value=0)
        fig.add_bar(name=str(y), x=[dl.MONTHS_AR[m] for m in months], y=g.values,
                    marker=dict(color=YEAR_COLORS[y], cornerradius=4, line=dict(width=0)),
                    hovertemplate=f"%{{x}} {y}<br>%{{y:{fmt}}}<extra></extra>")
    return _layout(fig, y_title=y_title)


def cumulative_compare(df: pd.DataFrame, value: str, months: list[int], y_title: str) -> go.Figure:
    """منحنى تراكمي؛ خط 2026 يتوقف عند آخر شهر له بيانات حتى لا يظهر ثباتًا وهميًا."""
    last_2026 = max(comparable_months(), default=12)
    fig = go.Figure()
    for y in dl.YEARS:
        ms = [m for m in months if y != 2026 or m <= last_2026]
        g = df[df["السنة"] == y].groupby("الشهر")[value].sum().reindex(ms, fill_value=0).cumsum()
        fig.add_scatter(name=str(y), x=[dl.MONTHS_AR[m] for m in ms], y=g.values, mode="lines+markers",
                        line=dict(color=YEAR_COLORS[y], width=2.5), marker=dict(size=8),
                        hovertemplate=f"حتى %{{x}} {y}<br>%{{y:,.2f}}<extra></extra>")
    fig.update_layout(hovermode="x unified")
    return _layout(fig, y_title=y_title)


def category_compare(df: pd.DataFrame, cat: str, value: str | None, x_title: str,
                     agg: str = "sum", fmt: str = ",.2f", height: int | None = None) -> go.Figure:
    """أعمدة أفقية لكل فئة مع مقارنة العامين."""
    if value:
        g = df.groupby([cat, "السنة"])[value].agg(agg).unstack(fill_value=0)
    else:
        g = df.groupby([cat, "السنة"]).size().unstack(fill_value=0)
    g = g.reindex(columns=list(dl.YEARS), fill_value=0)
    g = g.loc[g.sum(axis=1).sort_values().index]
    fig = go.Figure()
    for y in dl.YEARS:
        fig.add_bar(name=str(y), y=g.index, x=g[y], orientation="h",
                    marker=dict(color=YEAR_COLORS[y], cornerradius=4),
                    hovertemplate=f"%{{y}} {y}<br>%{{x:{fmt}}}<extra></extra>")
    fig = _layout(fig, height=height or max(300, 60 + 46 * len(g)), x_title=x_title)
    fig.update_xaxes(gridcolor=GRID, showgrid=True, tickformat=",")
    fig.update_yaxes(showgrid=False, title="")
    return fig


def single_bar(labels, values, x_title: str, fmt: str = ",.0f", height: int | None = None) -> go.Figure:
    labels = list(labels)
    short = [t if len(t) <= 34 else t[:32] + "…" for t in labels]
    fig = go.Figure(go.Bar(y=short, x=list(values), orientation="h", marker=dict(color="#2F6DB5", cornerradius=4),
                           customdata=labels, hovertemplate=f"%{{customdata}}<br>%{{x:{fmt}}}<extra></extra>"))
    fig = _layout(fig, height=height or max(300, 60 + 30 * len(labels)), x_title=x_title)
    fig.update_xaxes(gridcolor=GRID, showgrid=True)
    fig.update_yaxes(showgrid=False, title="")
    fig.update_layout(showlegend=False)
    return fig


def show(fig: go.Figure):
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

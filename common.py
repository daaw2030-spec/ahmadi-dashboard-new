"""عناصر مشتركة: الألوان، التنسيق، الفلاتر، والرسومات."""
from __future__ import annotations

import io
import urllib.error
import urllib.parse
import urllib.request

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
# مصدر كل ملف بالترتيب: مجلد data المحلي ← مستودع البيانات الخاص على GitHub (عبر st.secrets)
# ← ملف مرفوع في الجلسة. بذلك يبقى مستودع الكود العام خاليًا من البيانات.
DEFAULT_DATA_REPO = {"repo": "daaw2030-spec/ahmadi-dashboard", "ref": "main", "folder": "dashboard_data"}


class RemoteDataError(Exception):
    """فشل جلب ملف من المستودع الخاص؛ لا يُخزَّن مؤقتًا حتى يُعاد المحاولة في الزيارة التالية."""


def _data_repo() -> dict | None:
    """إعدادات Streamlit Secrets. المقبول: قسم [data_repo] فيه token (والباقي اختياري)،
    أو مفتاح token / GITHUB_TOKEN في أعلى الملف."""
    try:
        section = st.secrets.get("data_repo")
        token = (section or {}).get("token") or st.secrets.get("token") or st.secrets.get("GITHUB_TOKEN")
    except Exception:  # لا يوجد ملف secrets إطلاقًا
        return None
    if not token:
        return None
    cfg = dict(DEFAULT_DATA_REPO)
    cfg.update({k: str(v).strip() for k, v in dict(section or {}).items() if v})
    cfg["token"] = str(token).strip()
    return cfg


def _github_get(url: str, token: str, raw: bool) -> bytes:
    headers = {"Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28",
               "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RemoteDataError(e.code) from None
    except urllib.error.URLError as e:
        raise RemoteDataError(f"network: {e.reason}") from None


@st.cache_data(ttl=3600, show_spinner="جارٍ جلب البيانات من المستودع الخاص…")
def _remote_bytes(filename: str, repo: str, ref: str, folder: str, token: str) -> bytes:
    path = urllib.parse.quote(f"{folder.strip('/')}/{filename}".strip("/"))
    return _github_get(f"https://api.github.com/repos/{repo}/contents/{path}?ref={urllib.parse.quote(ref)}",
                       token, raw=True)


def _remote(key: str) -> bytes | None:
    cfg = _data_repo()
    if not cfg:
        return None
    path, _ = dl.FILES[key]
    try:
        return _remote_bytes(path.name, cfg["repo"], cfg["ref"], cfg["folder"], cfg["token"])
    except RemoteDataError:
        return None


def remote_diagnosis() -> str:
    """سبب عدم قراءة البيانات من المستودع الخاص، دون كشف المفتاح."""
    cfg = _data_repo()
    if not cfg:
        return ("لم يجد التطبيق مفتاح الوصول في Streamlit Secrets. المطلوب قسم [data_repo] "
                "وفيه token (تأكد من حفظ Secrets في إعدادات هذا التطبيق نفسه).")
    where = f"{cfg['repo']} / {cfg['folder']} (فرع {cfg['ref']})"
    try:
        _github_get(f"https://api.github.com/repos/{cfg['repo']}", cfg["token"], raw=False)
    except RemoteDataError as e:
        code = e.args[0]
        if code == 401:
            return "GitHub رفض المفتاح (401): المفتاح غير صحيح أو منتهي الصلاحية."
        if code in (403, 404):
            return (f"المفتاح صالح لكنه لا يملك صلاحية قراءة المستودع {cfg['repo']} ({code}). "
                    "يلزم أن يشمل المفتاح هذا المستودع وصلاحية Contents: Read-only.")
        return f"تعذّر الاتصال بـ GitHub: {code}"
    missing = []
    for key, (path, _) in dl.FILES.items():
        try:
            _remote_bytes(path.name, cfg["repo"], cfg["ref"], cfg["folder"], cfg["token"])
        except RemoteDataError as e:
            missing.append(f"{path.name} ({e.args[0]})")
    if missing:
        return f"الوصول إلى المستودع يعمل، لكن هذه الملفات غير موجودة في {where}: " + "، ".join(missing)
    return f"تم الوصول إلى جميع الملفات في {where}."


def missing_files() -> list[str]:
    uploads = st.session_state.get("uploads", {})
    return [k for k, (path, _) in dl.FILES.items()
            if not path.exists() and k not in uploads and _remote(k) is None]


def _src(key: str) -> bytes | None:
    path, _ = dl.FILES[key]
    if path.exists():
        return None
    return _remote(key) or st.session_state["uploads"][key]


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
    st.warning("تعذّر تحميل البيانات تلقائيًا من المستودع الخاص.\n\n**السبب:** " + remote_diagnosis())
    st.info("حل مؤقت: يمكن رفع الملفات التالية لعرض اللوحة في هذه الجلسة فقط (لا تُحفظ).")
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
    sel = active_years()
    years = "".join(
        f'<div><div class="yl"><i style="background:{YEAR_COLORS[y]}"></i>{y}</div>'
        f'<div class="yv">{fmt(v)}</div></div>' for y, v in ((2025, v2025), (2026, v2026)) if y in sel)
    delta = (f'<div class="delta">{change_text(v2025, v2026)}</div>'
             if show_change and len(sel) == 2 else "")
    st.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="years">{years}</div>{delta}</div>',
                unsafe_allow_html=True)


def note(text: str):
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def chart(title: str, purpose: str, fig: go.Figure):
    """عنوان الرسم + سطر يشرح هدفه + الرسم."""
    st.markdown(f"**{title}**")
    st.caption(purpose)
    show(fig)


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
        years = st.multiselect("السنوات", list(dl.YEARS), default=list(dl.YEARS), key="years",
                               help="المقارنة مقصورة على 2025 و2026 فقط.")
        depts = st.multiselect("القسم / الجهة الطالبة", ALL_DEPTS, default=[], key="depts",
                               placeholder="كل الأقسام")
        st.divider()
    return {"months": months or list(range(1, 13)), "depts": depts, "years": years or list(dl.YEARS)}


def active_years() -> list[int]:
    return list(st.session_state.get("filters", {}).get("years", dl.YEARS))


def status_filter(options: list[str], key: str) -> list[str]:
    """فلتر الحالة الخاص بالصفحة (في الشريط الجانبي)."""
    with st.sidebar:
        chosen = st.multiselect("الحالة", options, default=[], key=key, placeholder="كل الحالات")
    return chosen or options


def apply_filters(df: pd.DataFrame, f: dict, dept_col: str = "القسم") -> pd.DataFrame:
    out = df[df["السنة"].isin(f["years"]) & df["الشهر"].isin(f["months"])]
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
    fig.update_xaxes(showgrid=False, title=x_title, linecolor="#C9D7EA", automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def monthly_compare(df: pd.DataFrame, value: str | None, months: list[int], y_title: str,
                    agg: str = "sum", fmt: str = ",.2f") -> go.Figure:
    """أعمدة متجاورة: نفس الشهر في 2025 مقابل 2026."""
    fig = go.Figure()
    for y in active_years():
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
    for y in active_years():
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
    g = g.reindex(columns=active_years(), fill_value=0)
    g = g.loc[g.sum(axis=1).sort_values().index]
    fig = go.Figure()
    for y in active_years():
        fig.add_bar(name=str(y), y=g.index, x=g[y], orientation="h",
                    marker=dict(color=YEAR_COLORS[y], cornerradius=4),
                    hovertemplate=f"%{{y}} {y}<br>%{{x:{fmt}}}<extra></extra>")
    fig = _layout(fig, height=height or max(300, 60 + 46 * len(g)), x_title=x_title)
    fig.update_xaxes(gridcolor=GRID, showgrid=True, tickformat=",")
    fig.update_yaxes(showgrid=False, title="")
    return fig


def wrap_label(text: str, width: int = 30) -> str:
    """تقسيم التسمية الطويلة على أكثر من سطر بدل قصّها."""
    lines, cur = [], ""
    for word in str(text).split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    lines.append(cur)
    return "<br>".join(lines)


def single_bar(labels, values, x_title: str, fmt: str = ",.0f", height: int | None = None) -> go.Figure:
    labels = list(labels)
    short = [wrap_label(t) for t in labels]
    fig = go.Figure(go.Bar(y=short, x=list(values), orientation="h", marker=dict(color="#2F6DB5", cornerradius=4),
                           customdata=labels, hovertemplate=f"%{{customdata}}<br>%{{x:{fmt}}}<extra></extra>"))
    max_lines = max((s.count("<br>") + 1 for s in short), default=1)
    fig = _layout(fig, height=height or max(320, 90 + len(short) * (18 * max_lines + 14)), x_title=x_title)
    fig.update_xaxes(gridcolor=GRID, showgrid=True)
    fig.update_yaxes(showgrid=False, title="")
    fig.update_layout(showlegend=False)
    return fig


def show(fig: go.Figure):
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

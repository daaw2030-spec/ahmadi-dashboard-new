"""اختبار تشغيل كل صفحات اللوحة دون أخطاء: python tests/test_app.py"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import data_loader as dl  # noqa: E402

PAGES = ["views/financial.py", "views/purchase_orders.py", "views/direct_cancelled.py", "views/consumables.py"]


def run(page=None, uploads=None, month_mode=None):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    if uploads:
        at.session_state["uploads"] = uploads
    at.run()
    if month_mode:
        at.radio(key="month_mode").set_value(month_mode).run()
    if page:
        at.switch_page(page).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


if all(p.exists() for p, _ in dl.FILES.values()):
    for page in PAGES:
        for mode in (None, "كل الأشهر"):
            at = run(page, month_mode=mode)
            print("OK", page, mode or "default", "| title:", at.title[0].value if at.title else "-")
else:
    at = run()
    print("upload screen shown:", len(at.get("file_uploader")) if hasattr(at, "get") else "?")

print("ALL APP TESTS PASSED")

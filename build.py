"""
Generates public/index.html with live event + weather data.
Runs at deploy time on Vercel, or locally to preview the output.
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from web import build_page

Path("public").mkdir(exist_ok=True)
html = build_page()
Path("public/index.html").write_text(html, encoding="utf-8")
print(f"Built public/index.html ({len(html):,} bytes)")

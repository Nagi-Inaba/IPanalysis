# -*- coding: utf-8 -*-
"""CSS/HTML スタイル定義。"""
from __future__ import annotations

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@400;500;700;900&family=IBM+Plex+Mono:wght@500&display=swap');
:root{--bg-s:#f2f8f1;--bg-e:#dbe8db;--ink:#1b2b22;--acc:#b74b32;--acc2:#275f56;--paper:rgba(255,255,255,.78)}
.stApp{background:radial-gradient(circle at 12% 4%,rgba(183,75,50,.14),transparent 40%),radial-gradient(circle at 88% 16%,rgba(39,95,86,.15),transparent 40%),linear-gradient(145deg,var(--bg-s),var(--bg-e))}
.block-container{padding-top:1.4rem!important;padding-bottom:2rem!important}
h1,h2,h3,.stMarkdown,.stMetric{font-family:'Zen Kaku Gothic New',sans-serif!important;color:var(--ink)}
code{font-family:'IBM Plex Mono',monospace!important}
.hero{background:linear-gradient(122deg,rgba(255,255,255,.75),rgba(255,255,255,.52));border:1px solid rgba(39,95,86,.24);border-radius:20px;padding:1.2rem 1.4rem;box-shadow:0 12px 28px rgba(20,45,36,.1);margin-bottom:.8rem}
.hero h1{margin:0;font-size:1.8rem;font-weight:900}.hero p{margin:.5rem 0 0;font-size:.95rem}
.step-done{color:#275f56;font-weight:700}.step-current{color:#b74b32;font-weight:700}.step-pending{color:#9ab09e}
[data-testid="stSidebar"]{background:linear-gradient(180deg,rgba(255,255,255,.8),rgba(255,255,255,.58));border-left:1px solid rgba(39,95,86,.18)}
</style>
"""

HERO_HTML = """<section class="hero"><h1>IP Analysis Studio</h1>
<p>特許Excelをアップロード → 前処理 → 集計 → グラフ の3ステップで分析できます。</p></section>"""

# データ形式バッジの設定
FORMAT_LABELS = {
    "questel": "Questel Orbit",
    "jplatpat": "J-PlatPat",
    "unknown": "不明",
}
FORMAT_ICONS = {
    "questel": "\U0001f310",
    "jplatpat": "\U0001f5fe",
    "unknown": "\u2753",
}
FORMAT_COLORS = {
    "questel": "#275f56",
    "jplatpat": "#1a4a8c",
    "unknown": "#888",
}


def format_badge_html(fmt: str) -> str:
    """データ形式を示すバッジ HTML を返す。"""
    label = f"{FORMAT_ICONS.get(fmt, '')} {FORMAT_LABELS.get(fmt, fmt)}"
    color = FORMAT_COLORS.get(fmt, "#888")
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:8px;font-size:.82rem;font-weight:700;">'
        f'{label}</span> として認識しました。'
    )

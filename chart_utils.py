from __future__ import annotations

from io import BytesIO
from typing import Optional

import altair as alt


def chart_to_png_bytes(chart: alt.Chart, scale: float = 2.0) -> Optional[bytes]:
    """
    Altair チャートを PNG バイト列に変換するユーティリティ。

    altair_saver が利用できない環境では None を返し、呼び出し側で
    ダウンロードボタンを出さないようにする。
    """
    try:
        from altair_saver import save
    except ImportError:
        # altair_saver が未インストールの環境では PNG エクスポートを無効化
        # pip install altair_saver + selenium/vl-convert-python で有効になります
        return None

    buf = BytesIO()
    try:
        save(chart, fp=buf, fmt="png", scale=scale)
    except Exception:
        return None
    return buf.getvalue()


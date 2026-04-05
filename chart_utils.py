from __future__ import annotations

from typing import Optional

import altair as alt


def chart_to_png_bytes(chart: alt.Chart, scale: float = 2.0) -> Optional[bytes]:
    """
    Altair チャートを PNG バイト列に変換するユーティリティ。

    vl-convert-python が利用できない環境では None を返し、呼び出し側で
    ダウンロードボタンを出さないようにする。
    """
    try:
        import vl_convert as vlc
    except ImportError:
        # vl-convert-python が未インストールの環境では PNG エクスポートを無効化
        return None

    try:
        vl_spec = chart.to_dict(format="vega-lite")
        png_data = vlc.vegalite_to_png(vl_spec=vl_spec, scale=scale)
    except Exception:
        return None
    return png_data

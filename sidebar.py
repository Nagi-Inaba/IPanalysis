# -*- coding: utf-8 -*-
"""サイドバー UI コンポーネント。"""
from __future__ import annotations

import streamlit as st


def render_sidebar() -> None:
    """サイドバーの使い方ガイドとデータ概要を描画する。"""
    with st.sidebar:
        st.markdown("### IP Analysis Studio")
        with st.expander("使い方ガイド", expanded=False):
            st.markdown("""
1. **Step 1** -- Excel/CSVをアップロードし列マッピングを確認
2. **Step 2** -- 基準年・レンジを設定し集計を実行
3. **Step 3** -- グラフを確認・調整・ダウンロード

**グラフ操作:**
- マウスホイール: ズーム
- ドラッグ: パン移動
- Shift+ドラッグ: 範囲選択
""")
        if st.session_state.get("cleaned_df") is not None:
            _render_data_summary(st.session_state["cleaned_df"])


def _render_data_summary(cdf) -> None:
    """クリーニング済みデータの概要をサイドバーに表示する。"""
    st.markdown("---")
    st.markdown("### データ概要")
    st.metric("ファイル", st.session_state.get("upload_name", "\u2014"))
    sc1, sc2 = st.columns(2)
    sc1.metric("行数", f"{len(cdf):,}")
    sc2.metric("列数", f"{len(cdf.columns):,}")
    if "出願年" in cdf.columns:
        years = cdf["出願年"].dropna()
        if len(years) > 0:
            sc3, sc4 = st.columns(2)
            sc3.metric("最古年", int(years.min()))
            sc4.metric("最新年", int(years.max()))
    if "筆頭出願人" in cdf.columns:
        st.metric("出願人数", f"{cdf['筆頭出願人'].nunique():,}")

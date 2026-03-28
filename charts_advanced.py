# -*- coding: utf-8 -*-
"""追加分析グラフ — 技術ライフサイクル・共起・技術集中度。"""
from __future__ import annotations

from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st

from constants import CHART_HEIGHT_BUBBLE, CHART_HEIGHT_HEATMAP


def render_advanced_charts(
    cleaned_df: pd.DataFrame, classification: str, ipc_col: str, raw_ipc_col: Optional[str] = None,
) -> None:
    """追加分析グラフを描画する。"""
    from cached_agg import (
        cached_technology_lifecycle,
        cached_ipc_cooccurrence,
        cached_applicant_concentration,
    )

    with st.expander("高度な分析（3グラフ）", expanded=False):
        _render_lifecycle(cleaned_df, classification, ipc_col, cached_technology_lifecycle)
        _render_cooccurrence(cleaned_df, classification, raw_ipc_col, cached_ipc_cooccurrence)
        _render_concentration(cleaned_df, ipc_col, cached_applicant_concentration)


def _render_lifecycle(cleaned_df, classification, ipc_col, analysis_fn) -> None:
    st.markdown(f"### 技術ライフサイクル分析 — {classification}")
    st.caption("各分類のステージ（導入期→成長期→成熟期→衰退期）を出願件数の推移から判定します。")
    lc_n = st.slider("表示分類数", 5, 40, 20, key="lc_n")
    lc_df = analysis_fn(cleaned_df, ipc_col=ipc_col, top_n=lc_n)
    if lc_df.empty:
        st.info("分析対象データがありません。")
        return
    stage_colors = {"導入期": "#90caf9", "成長期": "#66bb6a", "成熟期": "#ffa726", "衰退期": "#ef5350"}
    brush_lc = alt.selection_interval()
    c = alt.Chart(lc_df).mark_circle(opacity=0.7, size=200).encode(
        x=alt.X("ピーク年:Q", title="ピーク年", scale=alt.Scale(zero=False)),
        y=alt.Y("成長率:Q", title="直近5年CAGR(%)"),
        size=alt.Size("総出願件数:Q", title="総出願件数", scale=alt.Scale(range=[60, 1200])),
        color=alt.condition(
            brush_lc,
            alt.Color("ステージ:N", scale=alt.Scale(
                domain=list(stage_colors.keys()),
                range=list(stage_colors.values()),
            )),
            alt.value("lightgray"),
        ),
        tooltip=["分類", "ステージ", "ピーク年", "成長率", "総出願件数"],
    ).add_params(brush_lc).properties(height=CHART_HEIGHT_BUBBLE).interactive()
    st.altair_chart(c, use_container_width=True)


def _render_cooccurrence(cleaned_df, classification, ipc_col, analysis_fn) -> None:
    if ipc_col is None or ipc_col not in cleaned_df.columns:
        st.info("共起分析に必要な分類列が設定されていません。")
        return
    st.markdown(f"### {classification} 共起分析（技術融合マップ）")
    st.caption("同一出願に複数の分類コードが付与されているペアを分析します。Jaccard係数が高いほど技術融合度が高いことを示します。")
    co_n = st.slider("表示ペア数", 5, 50, 20, key="co_ipc_n")
    co_level = st.selectbox("共起分析の粒度", ["subclass", "class", "section"], index=0, key="co_ipc_level",
                            format_func=lambda x: {"section": "セクション", "class": "クラス", "subclass": "サブクラス"}[x])
    co_df = analysis_fn(cleaned_df, ipc_col=ipc_col, ipc_level=co_level, top_n=co_n)
    if co_df.empty:
        st.info("共起データがありません（1出願あたり複数分類が必要です）。")
        return
    c = alt.Chart(co_df).mark_rect().encode(
        x=alt.X("分類A:N", title="分類A"),
        y=alt.Y("分類B:N", title="分類B"),
        color=alt.Color("Jaccard係数:Q", scale=alt.Scale(scheme="viridis"), title="Jaccard"),
        tooltip=["分類A", "分類B", "共起回数", "Jaccard係数"],
    ).properties(height=CHART_HEIGHT_HEATMAP).interactive()
    st.altair_chart(c, use_container_width=True)


def _render_concentration(cleaned_df, ipc_col, analysis_fn) -> None:
    st.markdown("### 出願人技術集中度（HHI指数）")
    st.caption("HHIが高い出願人は特定技術に集中、低い出願人は技術を多角化しています。")
    hhi_min = st.slider("最低出願件数", 5, 100, 10, key="hhi_min")
    hhi_df = analysis_fn(cleaned_df, ipc_col=ipc_col, min_applications=hhi_min)
    if hhi_df.empty:
        st.info("対象出願人がありません。")
        return
    type_colors = {"集中型": "#ef5350", "中程度": "#ffa726", "多角化型": "#66bb6a"}
    brush_hhi = alt.selection_interval()
    c = alt.Chart(hhi_df).mark_circle(opacity=0.7).encode(
        x=alt.X("分類数:Q", title="分類数"),
        y=alt.Y("HHI:Q", title="HHI指数"),
        size=alt.Size("総出願件数:Q", title="総出願件数", scale=alt.Scale(range=[60, 1200])),
        color=alt.condition(
            brush_hhi,
            alt.Color("タイプ:N", scale=alt.Scale(
                domain=list(type_colors.keys()),
                range=list(type_colors.values()),
            )),
            alt.value("lightgray"),
        ),
        tooltip=["出願人", "HHI", "主力分類", "分類数", "総出願件数", "タイプ"],
    ).add_params(brush_hhi).properties(height=CHART_HEIGHT_BUBBLE).interactive()
    st.altair_chart(c, use_container_width=True)

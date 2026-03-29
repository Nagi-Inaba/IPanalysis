# -*- coding: utf-8 -*-
"""Step 3: グラフ作成 — 全チャート描画ロジック。"""
from __future__ import annotations

import json
from typing import Dict

import altair as alt
import pandas as pd
import streamlit as st

from chart_utils import chart_to_png_bytes
from charts_advanced import render_advanced_charts
from constants import (
    IPC_LEVEL_OPTIONS,
    IPC_LEVEL_COL,
    FI_LEVEL_OPTIONS,
    FI_LEVEL_COL,
    FTERM_LEVEL_OPTIONS,
    CHART_HEIGHT_BUBBLE,
    CHART_HEIGHT_LINE,
    CHART_HEIGHT_AREA,
    CHART_HEIGHT_HEATMAP,
    CHART_HEIGHT_NETWORK,
    CHART_HEIGHT_BAR_PER_ITEM,
    CHART_HEIGHT_BAR_MIN,
)
from example_analysis import (
    COL_IPC,
    _editor_rows_to_dict,
    _mapping_to_editor_rows,
    analysis_ipc_growth,
    analysis_applicant_year_trend,
    analysis_ipc_treemap,
    analysis_applicant_ipc_heatmap,
    analysis_applicant_share,
    analysis_co_applicant,
    analysis_ipc_year_heatmap,
    analysis_fterm_distribution,
    analysis_fterm_year_heatmap,
)


def render_step3(agg: Dict[str, pd.DataFrame], cleaned_df: pd.DataFrame) -> None:
    """Step 3 のグラフ描画 UI を全て描画する。"""
    st.subheader("Step 3: グラフ作成")

    # ── IPC/FI粒度セレクタ（Step3で直接変更可能） ──
    st.divider()
    _s3c1, _s3c2, _s3c3 = st.columns([1, 2, 2])
    _classification = _s3c1.radio(
        "分類軸",
        ["IPC", "FI"],
        index=0 if st.session_state.get("classification", "IPC") == "IPC" else 1,
        key="classification_s3",
        horizontal=True,
    )
    st.session_state["classification"] = _classification
    if _classification == "IPC":
        _ipc_level_label_s3 = _s3c2.selectbox(
            "分類粒度",
            list(IPC_LEVEL_OPTIONS.keys()),
            index=list(IPC_LEVEL_OPTIONS.values()).index(st.session_state.get("ipc_level", "subclass")),
            key="ipc_level_s3",
            help="セクション(H) < クラス(H01) < サブクラス(H01M) < メイングループ(H01M10) < サブグループ(H01M10/0525)",
        )
        _ipc_level = IPC_LEVEL_OPTIONS[_ipc_level_label_s3]
        st.session_state["ipc_level"] = _ipc_level
        _ipc_col = IPC_LEVEL_COL.get(_ipc_level, "筆頭IPCサブクラス")
        _ipc_level_name = _ipc_level_label_s3.split(" ")[0]
    else:
        _fi_level_label_s3 = _s3c2.selectbox(
            "FI粒度",
            list(FI_LEVEL_OPTIONS.keys()),
            index=list(FI_LEVEL_OPTIONS.values()).index(st.session_state.get("fi_level", "subclass")) if st.session_state.get("fi_level", "subclass") in FI_LEVEL_OPTIONS.values() else 2,
            key="fi_level_s3",
        )
        _fi_level = FI_LEVEL_OPTIONS[_fi_level_label_s3]
        st.session_state["fi_level"] = _fi_level
        _ipc_col = FI_LEVEL_COL.get(_fi_level, "筆頭FIサブクラス")
        _ipc_level_name = _fi_level_label_s3.split(" ")[0]

    _fterm_col_name = st.session_state.get("fterm_col_name", "")
    _fterm_level = st.session_state.get("fterm_level", "theme")

    trend_df = agg.get("出願件数推移")
    # IPC増減率はStep3で選択した粒度で毎回再計算
    _base_year = st.session_state.get("by", 2015)
    _yr_range = st.session_state.get("yr", 10)
    _col_map_s3 = st.session_state.get("column_mapping", {})
    if _classification == "IPC":
        _active_ipc_src = _col_map_s3.get("ipc") or COL_IPC
    else:
        _active_ipc_src = _col_map_s3.get("fi") if _col_map_s3.get("fi") not in (None, "（なし）") else None
    ipc_df = analysis_ipc_growth(
        cleaned_df, _base_year, _yr_range,
        ipc_col=_active_ipc_src or COL_IPC,
        ipc_level=(_ipc_level if _classification == "IPC" else _fi_level),
    ) if _active_ipc_src else pd.DataFrame()
    app_count_df = agg.get("総出願人カウント")
    app_growth_df = agg.get("出願人増減率")
    entry_exit_df = agg.get("参入撤退チャート")
    citation_df = agg.get("被引用ポジショニングマップ")
    lead_count_df = agg.get("筆頭出願人件数")

    # グラフ共通設定 / プリセット / 設定ファイル
    st.divider()
    show_labels = _render_chart_config()

    # ==================== 出願動向グループ (4) ====================
    with st.expander("出願動向（4グラフ）", expanded=True):
        total_df = app_count_df if (app_count_df is not None and not app_count_df.empty) else lead_count_df
        if total_df is not None and not total_df.empty:
            _render_applicant_bar(total_df, show_labels)
        if trend_df is not None and not trend_df.empty:
            _render_trend_line(trend_df, show_labels)
        if cleaned_df is not None:
            _render_applicant_year_trend(cleaned_df)
        if cleaned_df is not None:
            _render_applicant_share(cleaned_df)

    # ==================== 技術分類グループ (4) ====================
    with st.expander(f"技術分類分析（4グラフ）", expanded=True):
        if ipc_df is not None and not ipc_df.empty:
            _render_ipc_bubble(ipc_df, _classification, _ipc_level_name, show_labels)
        if cleaned_df is not None:
            _render_ipc_treemap(cleaned_df, _classification, _ipc_level_name, _ipc_col)
        if cleaned_df is not None:
            _render_applicant_ipc_heatmap(cleaned_df, _classification, _ipc_level_name, _ipc_col)
        if cleaned_df is not None:
            _render_ipc_year_heatmap(cleaned_df, _classification, _ipc_level_name, _ipc_col)

    # ==================== 出願人分析グループ (3) ====================
    with st.expander("出願人分析（3グラフ）", expanded=False):
        if app_growth_df is not None and not app_growth_df.empty:
            _render_applicant_growth(app_growth_df, show_labels)
        if entry_exit_df is not None and not entry_exit_df.empty:
            _render_entry_exit(entry_exit_df, show_labels)
        if cleaned_df is not None:
            _render_co_applicant(cleaned_df)

    # ==================== 引用分析グループ (2) ====================
    with st.expander("引用分析（2グラフ）", expanded=False):
        if citation_df is not None and not citation_df.empty:
            _render_citation_map_a(citation_df, show_labels)
            _render_citation_map_b(citation_df, show_labels)

    # ==================== Fターム分析グループ (2) ====================
    if cleaned_df is not None and _fterm_col_name and _fterm_col_name in cleaned_df.columns:
        with st.expander("Fターム分析（2グラフ）", expanded=False):
            _render_fterm_distribution(cleaned_df, _fterm_col_name, _fterm_level)
            _render_fterm_year_heatmap(cleaned_df, _fterm_col_name, _fterm_level)

    # ==================== 高度な分析グループ (3) ====================
    if cleaned_df is not None:
        _col_map_adv = st.session_state.get("column_mapping", {})
        _adv_ipc_col = _ipc_col
        if _classification == "IPC":
            _raw_ipc_col = _col_map_adv.get("ipc") or COL_IPC
        else:
            _raw_ipc_col = _col_map_adv.get("fi") if _col_map_adv.get("fi") not in (None, "（なし）") else None
        render_advanced_charts(cleaned_df, _classification, _adv_ipc_col, _raw_ipc_col)

    # ステップ戻し
    st.divider()
    bc1, bc2 = st.columns(2)
    if bc1.button("← Step 1 に戻る", key="back1"):
        st.session_state["step"] = 1
        st.rerun()
    if bc2.button("← Step 2 に戻る", key="back2"):
        st.session_state["step"] = 2
        st.rerun()


# ==================== Private helpers ====================


def _render_chart_config() -> bool:
    """グラフ共通設定 expander を描画し、show_labels を返す。"""
    with st.expander("グラフ共通設定", expanded=False):
        preset = st.selectbox(
            "分析プリセット",
            ["カスタム", "トップ企業分析", "引用集中度分析"],
            key="analysis_preset",
        )
        show_labels = st.checkbox("データラベルを表示する", value=True, key="show_labels")

        _CONFIG_VERSION = "1.1"
        config = {
            "_version": _CONFIG_VERSION,
            "preset": preset,
            "show_labels": show_labels,
            "bar_min": st.session_state.get("bar_min"),
            "bar_max": st.session_state.get("bar_max"),
            "bar_sort": st.session_state.get("bar_sort"),
            "ipc_bmin": st.session_state.get("ipc_bmin"),
            "ee_min": st.session_state.get("ee_min"),
            "cma_min": st.session_state.get("cma_min"),
            "cmb_min": st.session_state.get("cmb_min"),
            "column_mapping": st.session_state.get("column_mapping", {}),
            "base_year": st.session_state.get("by"),
            "start_year": st.session_state.get("sy"),
            "end_year": st.session_state.get("ey"),
            "name_mapping": _editor_rows_to_dict(st.session_state.get("name_mapping_rows", [])),
        }
        st.download_button(
            "現在の設定をJSONで保存",
            data=json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="ipanalysis_config.json",
            mime="application/json",
            key="cfg_download",
        )

        uploaded_cfg = st.file_uploader("設定ファイルを読み込み", type=["json"], key="cfg_upload")
        if uploaded_cfg is not None:
            try:
                loaded = json.loads(uploaded_cfg.read().decode("utf-8"))
                if not isinstance(loaded, dict):
                    raise ValueError("設定ファイルはJSON オブジェクト形式である必要があります")
                file_ver = loaded.get("_version", "1.0")
                if file_ver != _CONFIG_VERSION:
                    st.warning(f"設定ファイルのバージョン ({file_ver}) が現在 ({_CONFIG_VERSION}) と異なります。一部設定が反映されない場合があります。")
                for k in ("preset", "show_labels", "bar_min", "bar_max", "bar_sort", "ipc_bmin", "ee_min", "cma_min", "cmb_min"):
                    if loaded.get(k) is not None:
                        st.session_state[k] = loaded[k]
                if loaded.get("column_mapping"):
                    st.session_state["column_mapping"] = loaded["column_mapping"]
                if loaded.get("base_year") is not None:
                    st.session_state["by"] = loaded["base_year"]
                if loaded.get("start_year") is not None:
                    st.session_state["sy"] = loaded["start_year"]
                if loaded.get("end_year") is not None:
                    st.session_state["ey"] = loaded["end_year"]
                if loaded.get("name_mapping") and isinstance(loaded["name_mapping"], dict):
                    st.session_state["name_mapping_rows"] = _mapping_to_editor_rows(loaded["name_mapping"])
                st.success("設定を読み込みました。")
                st.rerun()
            except (ValueError, KeyError) as e:
                st.error(f"設定ファイルの形式が正しくありません: {e}")
            except Exception as e:
                st.error(f"設定ファイルの読み込みに失敗しました: {e}")

        if preset == "トップ企業分析":
            st.session_state.setdefault("bar_min", 50)
            st.session_state.setdefault("bar_max", 35)
        elif preset == "引用集中度分析":
            st.session_state.setdefault("cma_min", 10)

    return show_labels


def _render_applicant_bar(total_df: pd.DataFrame, show_labels: bool) -> None:
    st.markdown("### 出願件数（横棒グラフ）")
    count_col = "出願件数"
    name_col = [c for c in total_df.columns if c != count_col][0]
    fc1, fc2, fc3 = st.columns(3)
    min_count = fc1.slider("最低出願件数", 1, int(total_df[count_col].max()), 50, key="bar_min")
    max_show = fc2.slider("表示件数", 5, 100, 35, key="bar_max")
    sort_by = fc3.selectbox("ソート", ["出願件数（降順）", "出願件数（昇順）", "名前順"], key="bar_sort")
    bdf = total_df[total_df[count_col] >= min_count].copy()
    if sort_by == "出願件数（降順）":
        bdf = bdf.sort_values(count_col, ascending=False)
    elif sort_by == "出願件数（昇順）":
        bdf = bdf.sort_values(count_col, ascending=True)
    else:
        bdf = bdf.sort_values(name_col)
    bdf = bdf.head(max_show)
    bar_chart = alt.Chart(bdf).mark_bar().encode(
        x=alt.X(f"{count_col}:Q", title="出願件数"),
        y=alt.Y(f"{name_col}:N", sort=bdf[name_col].tolist(), title=""),
        tooltip=[name_col, count_col],
    )
    bar_text = bar_chart.mark_text(align="left", dx=3, fontSize=11).encode(text=f"{count_col}:Q")
    bar_layer = bar_chart + bar_text if show_labels else bar_chart
    bar_layer = bar_layer.properties(height=max(CHART_HEIGHT_BAR_MIN, max_show * CHART_HEIGHT_BAR_PER_ITEM)).interactive()
    st.altair_chart(bar_layer, use_container_width=True)
    png_bytes = chart_to_png_bytes(bar_layer)
    if png_bytes:
        st.download_button("このグラフをPNGで保存", data=png_bytes, file_name="applicant_counts_bar.png", mime="image/png", key="png_bar")


def _render_trend_line(trend_df: pd.DataFrame, show_labels: bool) -> None:
    st.markdown("### 出願件数推移（折れ線グラフ）")
    min_year = int(trend_df["出願年"].min())
    max_year = int(trend_df["出願年"].max())
    y1, y2 = st.slider("表示する出願年の範囲", min_year, max_year, (min_year, max_year), key="trend_year_range")
    trend_view = trend_df[(trend_df["出願年"] >= y1) & (trend_df["出願年"] <= y2)]
    line = alt.Chart(trend_view).mark_line(point=alt.OverlayMarkDef(size=50)).encode(
        x=alt.X("出願年:O", title="出願年"), y=alt.Y("出願件数:Q", title="出願件数"), tooltip=["出願年", "出願件数"],
    )
    text = alt.Chart(trend_view).mark_text(dy=-12, fontSize=10).encode(
        x=alt.X("出願年:O"), y=alt.Y("出願件数:Q"), text="出願件数:Q",
    )
    line_layer = (line + text) if show_labels else line
    line_layer = line_layer.properties(height=CHART_HEIGHT_LINE, padding={"left": 80, "right": 20, "top": 10, "bottom": 40}).interactive()
    st.altair_chart(line_layer, use_container_width=True)
    png_bytes = chart_to_png_bytes(line_layer)
    if png_bytes:
        st.download_button("このグラフをPNGで保存", data=png_bytes, file_name="application_trend_line.png", mime="image/png", key="png_trend")


def _render_ipc_bubble(ipc_df: pd.DataFrame, classification: str, level_name: str, show_labels: bool) -> None:
    st.markdown(f"### {classification} 増減率（バブルチャート）— 粒度: {level_name}")
    bc1, bc2 = st.columns(2)
    ipc_min = bc1.slider(f"最低出願件数（{classification}）", 1, int(ipc_df["total_count"].max()), 10, key="ipc_bmin")
    ipc_sel = bc2.multiselect(f"{classification} を選択（空＝全表示）", ipc_df["IPC"].tolist(), key="ipc_sel")
    bdf = ipc_df[ipc_df["total_count"] >= ipc_min].copy()
    if ipc_sel:
        bdf = bdf[bdf["IPC"].isin(ipc_sel)]
    bdf = bdf.rename(columns={"IPC": classification})
    bdf["長期増減率(%)"] = (bdf["pct_change_10"] * 100).round(1)
    bdf["短期増減率(%)"] = (bdf["pct_change_second_5"] * 100).round(1)
    brush = alt.selection_interval()
    pts = alt.Chart(bdf).mark_circle(opacity=0.6).encode(
        x=alt.X("長期増減率(%):Q", title="長期増減率(%)"),
        y=alt.Y("短期増減率(%):Q", title="短期増減率(%)"),
        size=alt.Size("total_count:Q", title="出願件数", scale=alt.Scale(range=[40, 1500])),
        color=alt.condition(brush, alt.value("#8bc34a"), alt.value("lightgray")),
        tooltip=[classification, "total_count", "長期増減率(%)", "短期増減率(%)"],
    ).add_params(brush)
    labels = alt.Chart(bdf).mark_text(fontSize=9, dy=-10).encode(
        x="長期増減率(%):Q", y="短期増減率(%):Q", text=f"{classification}:N",
    )
    ipc_layer = (pts + labels) if show_labels else pts
    ipc_layer = ipc_layer.properties(width=750, height=CHART_HEIGHT_BUBBLE).interactive()
    st.altair_chart(ipc_layer, use_container_width=True)
    png_bytes = chart_to_png_bytes(ipc_layer)
    if png_bytes:
        st.download_button("このグラフをPNGで保存", data=png_bytes, file_name=f"{classification.lower()}_growth_bubble.png", mime="image/png", key="png_ipc")


def _render_entry_exit(entry_exit_df: pd.DataFrame, show_labels: bool) -> None:
    st.markdown("### 参入撤退チャート（バブルチャート）")
    ee = entry_exit_df.dropna(subset=["最初の出願年", "直近出願年"]).copy()
    ec1, ec2 = st.columns(2)
    ee_min = ec1.slider("最低出願件数（参入撤退）", 1, int(ee["総出願件数"].max()), 50, key="ee_min")
    ee_sel = ec2.multiselect("出願人を選択（空＝全表示）", sorted(ee["出願人名"].tolist()), key="ee_sel")
    ee = ee[ee["総出願件数"] >= ee_min]
    if ee_sel:
        ee = ee[ee["出願人名"].isin(ee_sel)]
    brush_ee = alt.selection_interval()
    pts = alt.Chart(ee).mark_circle(opacity=0.55).encode(
        x=alt.X("最初の出願年:Q", title="最初の出願年", scale=alt.Scale(zero=False)),
        y=alt.Y("直近出願年:Q", title="直近出願年", scale=alt.Scale(zero=False)),
        size=alt.Size("総出願件数:Q", scale=alt.Scale(range=[40, 1500])),
        color=alt.condition(brush_ee, alt.value("#8bc34a"), alt.value("lightgray")),
        tooltip=["出願人名", "最初の出願年", "直近出願年", "総出願件数"],
    ).add_params(brush_ee)
    lbl = alt.Chart(ee).mark_text(fontSize=9, dy=-10).encode(
        x="最初の出願年:Q", y="直近出願年:Q", text="出願人名:N",
    )
    ee_layer = (pts + lbl) if show_labels else pts
    ee_layer = ee_layer.properties(width=750, height=CHART_HEIGHT_BUBBLE).interactive()
    st.altair_chart(ee_layer, use_container_width=True)
    png_bytes = chart_to_png_bytes(ee_layer)
    if png_bytes:
        st.download_button("このグラフをPNGで保存", data=png_bytes, file_name="entry_exit_bubble.png", mime="image/png", key="png_entry_exit")


def _render_citation_map_a(citation_df: pd.DataFrame, show_labels: bool) -> None:
    st.markdown("### 被引用ポジショニングマップ A（最大引用回数）")
    cc1, cc2 = st.columns(2)
    cm_min = cc1.slider("最低出願件数（引用A）", 1, int(citation_df["出願件数"].max()), 30, key="cma_min")
    cm_sel = cc2.multiselect("出願人（引用A）", sorted(citation_df["出願人名"].tolist()), key="cma_sel")
    cm = citation_df[citation_df["出願件数"] >= cm_min].copy()
    if cm_sel:
        cm = cm[cm["出願人名"].isin(cm_sel)]
    brush_ca = alt.selection_interval()
    pts = alt.Chart(cm).mark_circle(opacity=0.6).encode(
        x=alt.X("出願件数:Q", title="出願件数"),
        y=alt.Y("最大引用回数:Q", title="最大引用回数"),
        size=alt.Size("合計引用回数:Q", scale=alt.Scale(range=[40, 1500])),
        color=alt.condition(brush_ca, alt.value("#5b86c5"), alt.value("lightgray")),
        tooltip=["出願人名", "出願件数", "最大引用回数", "合計引用回数"],
    ).add_params(brush_ca)
    lbl = alt.Chart(cm).mark_text(fontSize=9, dy=-10).encode(
        x="出願件数:Q", y="最大引用回数:Q", text="出願人名:N",
    )
    cm_layer = (pts + lbl) if show_labels else pts
    cm_layer = cm_layer.properties(width=750, height=CHART_HEIGHT_BUBBLE).interactive()
    st.altair_chart(cm_layer, use_container_width=True)
    png_bytes = chart_to_png_bytes(cm_layer)
    if png_bytes:
        st.download_button("このグラフをPNGで保存", data=png_bytes, file_name="citation_positioning_max.png", mime="image/png", key="png_citation_a")


def _render_citation_map_b(citation_df: pd.DataFrame, show_labels: bool) -> None:
    st.markdown("### 被引用ポジショニングマップ B（引用された出願割合）")
    cb_min = st.slider("最低出願件数（引用B）", 1, int(citation_df["出願件数"].max()), 30, key="cmb_min")
    cmb = citation_df[citation_df["出願件数"] >= cb_min].copy()
    brush_cb = alt.selection_interval()
    pts = alt.Chart(cmb).mark_circle(opacity=0.6).encode(
        x=alt.X("出願件数:Q", title="出願件数"),
        y=alt.Y("引用された出願割合（%）:Q", title="引用された出願割合(%)"),
        size=alt.Size("合計引用回数:Q", scale=alt.Scale(range=[40, 1500])),
        color=alt.condition(brush_cb, alt.value("#5b86c5"), alt.value("lightgray")),
        tooltip=["出願人名", "出願件数", "引用された出願割合（%）", "合計引用回数"],
    ).add_params(brush_cb)
    lbl = alt.Chart(cmb).mark_text(fontSize=9, dy=-10).encode(
        x="出願件数:Q", y="引用された出願割合（%）:Q", text="出願人名:N",
    )
    cmb_layer = (pts + lbl) if show_labels else pts
    cmb_layer = cmb_layer.properties(width=750, height=CHART_HEIGHT_BUBBLE).interactive()
    st.altair_chart(cmb_layer, use_container_width=True)
    png_bytes = chart_to_png_bytes(cmb_layer)
    if png_bytes:
        st.download_button("このグラフをPNGで保存", data=png_bytes, file_name="citation_positioning_ratio.png", mime="image/png", key="png_citation_b")


def _render_applicant_growth(app_growth_df: pd.DataFrame, show_labels: bool) -> None:
    st.markdown("### 出願増減率（バブルチャート）")
    ag1, ag2 = st.columns(2)
    ag_min = ag1.slider("最低出願件数（出願人増減率）", 1, int(app_growth_df["total_count"].max()), 30, key="ag_min")
    ag_sel = ag2.multiselect("出願人（増減率）", sorted(app_growth_df["出願人"].tolist()), key="ag_sel")
    agd = app_growth_df[app_growth_df["total_count"] >= ag_min].copy()
    if ag_sel:
        agd = agd[agd["出願人"].isin(ag_sel)]
    agd["長期増減率(%)"] = (agd["pct_change_10"] * 100).round(1)
    agd["短期増減率(%)"] = (agd["pct_change_second_5"] * 100).round(1)
    brush_ag = alt.selection_interval()
    pts = alt.Chart(agd).mark_circle(opacity=0.55).encode(
        x=alt.X("長期増減率(%):Q", title="長期増減率(%)"),
        y=alt.Y("短期増減率(%):Q", title="短期増減率(%)"),
        size=alt.Size("total_count:Q", title="出願件数", scale=alt.Scale(range=[40, 1500])),
        color=alt.condition(brush_ag, alt.value("#8bc34a"), alt.value("lightgray")),
        tooltip=["出願人", "total_count", "長期増減率(%)", "短期増減率(%)"],
    ).add_params(brush_ag)
    lbl = alt.Chart(agd).mark_text(fontSize=9, dy=-10).encode(
        x="長期増減率(%):Q", y="短期増減率(%):Q", text="出願人:N",
    )
    ag_layer = (pts + lbl) if show_labels else pts
    ag_layer = ag_layer.properties(width=750, height=CHART_HEIGHT_BUBBLE).interactive()
    st.altair_chart(ag_layer, use_container_width=True)
    png_bytes = chart_to_png_bytes(ag_layer)
    if png_bytes:
        st.download_button("このグラフをPNGで保存", data=png_bytes, file_name="applicant_growth_bubble.png", mime="image/png", key="png_applicant_growth")


def _render_applicant_year_trend(cleaned_df: pd.DataFrame) -> None:
    st.markdown("### 出願人別 年次推移（複数系列）")
    at_n = st.slider("上位N社", 3, 30, 10, key="at_n")
    at_df = analysis_applicant_year_trend(cleaned_df, top_n=at_n)
    if not at_df.empty:
        all_apps = sorted(at_df["出願人"].unique().tolist())
        at_sel = st.multiselect("出願人を選択（空＝全表示）", all_apps, key="at_sel")
        if at_sel:
            at_df = at_df[at_df["出願人"].isin(at_sel)]
        c = alt.Chart(at_df).mark_line(point=True).encode(
            x=alt.X("出願年:O", title="出願年"), y=alt.Y("出願件数:Q", title="出願件数"),
            color=alt.Color("出願人:N"), tooltip=["出願年", "出願人", "出願件数"],
        ).properties(height=CHART_HEIGHT_LINE).interactive()
        st.altair_chart(c, use_container_width=True)


def _render_ipc_treemap(cleaned_df: pd.DataFrame, classification: str, level_name: str, ipc_col: str) -> None:
    st.markdown(f"### {classification} 分布（ツリーマップ）— 粒度: {level_name}")
    tm_df = analysis_ipc_treemap(cleaned_df, ipc_col=ipc_col)
    if not tm_df.empty:
        tm_n = st.slider(f"表示{classification}数", 5, 50, 20, key="tm_n")
        tm_data = tm_df.head(tm_n).rename(columns={"IPC": classification})
        c = alt.Chart(tm_data).mark_bar().encode(
            x=alt.X("出願件数:Q", title="出願件数"),
            y=alt.Y(f"{classification}:N", sort="-x", title=level_name),
            color=alt.Color("出願件数:Q", scale=alt.Scale(scheme="greens"), legend=None),
            tooltip=[classification, "出願件数"],
        ).properties(height=max(CHART_HEIGHT_BAR_MIN, tm_n * CHART_HEIGHT_BAR_PER_ITEM)).interactive()
        st.altair_chart(c, use_container_width=True)


def _render_applicant_ipc_heatmap(cleaned_df: pd.DataFrame, classification: str, level_name: str, ipc_col: str) -> None:
    st.markdown(f"### 出願人 × {classification} ヒートマップ — 粒度: {level_name}")
    hm1, hm2 = st.columns(2)
    hm_a = hm1.slider("上位出願人数", 5, 40, 20, key="hm_a")
    hm_i = hm2.slider(f"上位{classification}数", 5, 30, 15, key="hm_i")
    hm_df = analysis_applicant_ipc_heatmap(cleaned_df, ipc_col=ipc_col, top_applicants=hm_a, top_ipcs=hm_i)
    if not hm_df.empty:
        hm_df = hm_df.rename(columns={"IPC": classification})
        c = alt.Chart(hm_df).mark_rect().encode(
            x=alt.X(f"{classification}:N", title=classification), y=alt.Y("出願人:N", title="出願人"),
            color=alt.Color("出願件数:Q", scale=alt.Scale(scheme="blues"), title="件数"),
            tooltip=["出願人", classification, "出願件数"],
        ).properties(height=max(CHART_HEIGHT_BAR_MIN, hm_a * CHART_HEIGHT_BAR_PER_ITEM)).interactive()
        st.altair_chart(c, use_container_width=True)


def _render_applicant_share(cleaned_df: pd.DataFrame) -> None:
    st.markdown("### 出願人シェア推移（積み上げ面）")
    sh_n = st.slider("上位N社", 3, 20, 8, key="sh_n")
    sh_df = analysis_applicant_share(cleaned_df, top_n=sh_n)
    if not sh_df.empty:
        c = alt.Chart(sh_df).mark_area().encode(
            x=alt.X("出願年:O", title="出願年"), y=alt.Y("出願件数:Q", title="出願件数", stack="zero"),
            color=alt.Color("出願人:N"), tooltip=["出願年", "出願人", "出願件数"],
        ).properties(height=CHART_HEIGHT_AREA).interactive()
        st.altair_chart(c, use_container_width=True)


def _render_co_applicant(cleaned_df: pd.DataFrame) -> None:
    st.markdown("### 共同出願ネットワーク")
    co_n = st.slider("表示ペア数", 5, 50, 20, key="co_n")
    co_df = analysis_co_applicant(cleaned_df, top_n=co_n)
    if not co_df.empty:
        co_show = co_df.head(co_n)
        c = alt.Chart(co_show).mark_rect().encode(
            x=alt.X("出願人A:N", title="出願人A"), y=alt.Y("出願人B:N", title="出願人B"),
            color=alt.Color("共同出願件数:Q", scale=alt.Scale(scheme="oranges"), title="件数"),
            tooltip=["出願人A", "出願人B", "共同出願件数"],
        ).properties(height=CHART_HEIGHT_NETWORK).interactive()
        st.altair_chart(c, use_container_width=True)


def _render_ipc_year_heatmap(cleaned_df: pd.DataFrame, classification: str, level_name: str, ipc_col: str) -> None:
    st.markdown(f"### {classification} 別 年次推移（ヒートマップ）— 粒度: {level_name}")
    iy_n = st.slider(f"上位{classification}数", 5, 40, 20, key="iy_n")
    iy_df = analysis_ipc_year_heatmap(cleaned_df, ipc_col=ipc_col, top_n=iy_n)
    if not iy_df.empty:
        iy_df = iy_df.rename(columns={"IPC": classification})
        c = alt.Chart(iy_df).mark_rect().encode(
            x=alt.X("出願年:O", title="出願年"), y=alt.Y(f"{classification}:N", title=classification),
            color=alt.Color("出願件数:Q", scale=alt.Scale(scheme="viridis"), title="件数"),
            tooltip=["出願年", classification, "出願件数"],
        ).properties(height=max(CHART_HEIGHT_BAR_MIN, iy_n * CHART_HEIGHT_BAR_PER_ITEM)).interactive()
        st.altair_chart(c, use_container_width=True)


def _render_fterm_distribution(cleaned_df: pd.DataFrame, fterm_col_name: str, fterm_level: str) -> None:
    st.markdown("### Fターム分布（棒グラフ）")
    ft1, ft2 = st.columns(2)
    ft_level_label = ft1.selectbox(
        "Fターム粒度（分布グラフ）",
        list(FTERM_LEVEL_OPTIONS.keys()),
        index=list(FTERM_LEVEL_OPTIONS.values()).index(fterm_level),
        key="ft_dist_level",
    )
    ft_n = ft2.slider("表示件数", 5, 50, 20, key="ft_n")
    ft_df = analysis_fterm_distribution(cleaned_df, fterm_col_name, level=FTERM_LEVEL_OPTIONS[ft_level_label], top_n=ft_n)
    if not ft_df.empty:
        c = alt.Chart(ft_df).mark_bar().encode(
            x=alt.X("出願件数:Q", title="出願件数"),
            y=alt.Y("Fターム:N", sort="-x", title=""),
            tooltip=["Fターム", "出願件数"],
        ).properties(height=max(CHART_HEIGHT_BAR_MIN, ft_n * CHART_HEIGHT_BAR_PER_ITEM)).interactive()
        st.altair_chart(c, use_container_width=True)


def _render_fterm_year_heatmap(cleaned_df: pd.DataFrame, fterm_col_name: str, fterm_level: str) -> None:
    st.markdown("### Fターム別年次推移（ヒートマップ）")
    fth1, fth2 = st.columns(2)
    fth_level_label = fth1.selectbox(
        "Fターム粒度（ヒートマップ）",
        list(FTERM_LEVEL_OPTIONS.keys()),
        index=list(FTERM_LEVEL_OPTIONS.values()).index(fterm_level),
        key="fth_level",
    )
    fth_n = fth2.slider("上位件数", 5, 30, 15, key="fth_n")
    fth_df = analysis_fterm_year_heatmap(cleaned_df, fterm_col_name, level=FTERM_LEVEL_OPTIONS[fth_level_label], top_n=fth_n)
    if not fth_df.empty:
        c = alt.Chart(fth_df).mark_rect().encode(
            x=alt.X("出願年:O", title="出願年"), y=alt.Y("Fターム:N", title="Fターム"),
            color=alt.Color("出願件数:Q", scale=alt.Scale(scheme="purples"), title="件数"),
            tooltip=["出願年", "Fターム", "出願件数"],
        ).properties(height=max(CHART_HEIGHT_BAR_MIN, fth_n * CHART_HEIGHT_BAR_PER_ITEM)).interactive()
        st.altair_chart(c, use_container_width=True)

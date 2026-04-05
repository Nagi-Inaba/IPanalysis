# -*- coding: utf-8 -*-
"""Step 2: 集計パラメータ設定・実行・結果表示の UI ロジック。"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

from cached_agg import (
    cached_application_trend,
    cached_ipc_growth,
    cached_ipc_summary,
    cached_ipc_main_group,
    cached_applicant_count,
    cached_applicant_total,
    cached_applicant_growth,
    cached_entry_exit,
    cached_citation_map,
    cached_cited_applications,
)
from constants import (
    IPC_LEVEL_OPTIONS,
    FI_LEVEL_OPTIONS,
    FTERM_LEVEL_OPTIONS,
)
from example_analysis import (
    COL_IPC,
    dataframe_to_excel_bytes,
)


def render_step2() -> None:
    """Step 2 全体を描画する。"""
    st.divider()
    st.subheader("Step 2: 集計")

    cleaned_df = st.session_state["cleaned_df"]
    params = _render_aggregation_params(cleaned_df)
    checks = _render_aggregation_checkboxes()

    if st.button("集計を実行", type="primary", key="run_agg"):
        results = _run_aggregation(cleaned_df, checks, params)
        st.session_state["agg_results"] = results
        st.session_state["step"] = 3
        st.success(f"{len(results)} 件の集計が完了しました。")
        st.rerun()

    _render_aggregation_results()


def _render_aggregation_params(cleaned_df: pd.DataFrame) -> Dict:
    """集計パラメータ UI を描画し、設定値を返す。"""
    p1, p2, p3 = st.columns(3)
    base_year = p1.number_input("基準年", 1900, 2100, 2015, key="by")
    start_year = p2.number_input("開始年", 1980, 2030, 2010, key="sy")
    end_year = p3.number_input("終了年", 1980, 2030, 2023, key="ey")
    yr_range = st.slider("増減率レンジ（年）", 5, 20, 10, key="yr")

    cls_col, ipc_col_sel, fi_col_sel = st.columns(3)
    classification = cls_col.radio(
        "分類軸",
        ["IPC", "FI"],
        index=0 if st.session_state["classification"] == "IPC" else 1,
        key="classification_radio",
        horizontal=True,
    )
    st.session_state["classification"] = classification

    if classification == "IPC":
        ipc_level_label = ipc_col_sel.selectbox(
            "分類粒度",
            list(IPC_LEVEL_OPTIONS.keys()),
            index=list(IPC_LEVEL_OPTIONS.values()).index(st.session_state["ipc_level"]),
            key="ipc_level_select",
            help="セクション(H) < クラス(H01) < サブクラス(H01M) < メイングループ(H01M10) < サブグループ(H01M10/0525)",
        )
        st.session_state["ipc_level"] = IPC_LEVEL_OPTIONS[ipc_level_label]
    else:
        fi_level_label = fi_col_sel.selectbox(
            "FI粒度",
            list(FI_LEVEL_OPTIONS.keys()),
            index=(
                list(FI_LEVEL_OPTIONS.values()).index(st.session_state["fi_level"])
                if st.session_state["fi_level"] in FI_LEVEL_OPTIONS.values()
                else 2
            ),
            key="fi_level_select",
            help="セクション(H) < クラス(H01) < サブクラス(H01M) < メイングループ(H01M10) < サブグループ(H01M10/0525) < フルFI",
        )
        st.session_state["fi_level"] = FI_LEVEL_OPTIONS[fi_level_label]

    # Fターム粒度
    fterm_col_name = st.session_state.get("fterm_col_name", "")
    if (
        fterm_col_name
        and st.session_state.get("cleaned_df") is not None
        and fterm_col_name in st.session_state["cleaned_df"].columns
    ):
        fterm_level_label = st.selectbox(
            "Fターム粒度",
            list(FTERM_LEVEL_OPTIONS.keys()),
            index=list(FTERM_LEVEL_OPTIONS.values()).index(st.session_state["fterm_level"]),
            key="fterm_level_select",
            help="テーマコード(5H029) / テーマ+観点(5H029AJ) / フルFターム(5H029AJ12)",
        )
        st.session_state["fterm_level"] = FTERM_LEVEL_OPTIONS[fterm_level_label]

    return {
        "base_year": base_year,
        "start_year": start_year,
        "end_year": end_year,
        "yr_range": yr_range,
    }


def _render_aggregation_checkboxes() -> Dict[str, bool]:
    """集計項目チェックボックス UI を描画する。"""
    st.markdown("**実行する集計を選択:**")
    sel_c1, sel_c2 = st.columns(2)
    if sel_c1.button("全選択", key="sel_all"):
        for k in ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10"]:
            st.session_state[k] = True
        st.rerun()
    if sel_c2.button("全解除", key="sel_none"):
        for k in ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10"]:
            st.session_state[k] = False
        st.rerun()

    c1, c2 = st.columns(2)
    return {
        "出願件数推移": c1.checkbox("出願件数推移", True, key="t1"),
        "特許分類増減率": c1.checkbox("特許分類増減率", True, key="t2"),
        "特許分類集計": c1.checkbox("特許分類集計", False, key="t3"),
        "筆頭分類メイングループ": c1.checkbox("筆頭分類メイングループ", False, key="t4"),
        "筆頭出願人件数": c2.checkbox("筆頭出願人件数", True, key="t5"),
        "総出願人カウント": c2.checkbox("総出願人カウント", True, key="t6"),
        "出願人増減率": c2.checkbox("出願人増減率", True, key="t7"),
        "参入撤退チャート": c2.checkbox("参入撤退チャート", True, key="t8"),
        "被引用ポジショニングマップ": c1.checkbox("被引用ポジショニングマップ", True, key="t9"),
        "被引用出願一覧": c2.checkbox("被引用出願一覧", False, key="t10"),
    }


def _run_aggregation(
    cleaned_df: pd.DataFrame,
    checks: Dict[str, bool],
    params: Dict,
) -> Dict[str, pd.DataFrame]:
    """選択された集計を実行し結果辞書を返す。"""
    results: Dict[str, pd.DataFrame] = {}
    classification = st.session_state.get("classification", "IPC")
    ipc_level = st.session_state["ipc_level"]
    fi_level = st.session_state.get("fi_level", "subclass")
    active_level = ipc_level if classification == "IPC" else fi_level

    col_map = st.session_state.get("column_mapping", {})
    fi_col_name = (
        col_map.get("fi", "公報FI")
        if col_map.get("fi") not in (None, "（なし）")
        else "公報FI"
    )
    active_ipc_col = COL_IPC if classification == "IPC" else fi_col_name

    with st.spinner("集計中..."):
        if checks["出願件数推移"]:
            results["出願件数推移"] = cached_application_trend(cleaned_df)
        if checks["特許分類増減率"]:
            results["特許分類増減率"] = cached_ipc_growth(
                cleaned_df,
                params["base_year"],
                params["yr_range"],
                active_level,
                active_ipc_col,
            )
        if checks["特許分類集計"]:
            results["特許分類集計"] = cached_ipc_summary(cleaned_df)
        if checks["筆頭分類メイングループ"]:
            results["筆頭分類メイングループ"] = cached_ipc_main_group(cleaned_df)
        if checks["筆頭出願人件数"]:
            results["筆頭出願人件数"] = cached_applicant_count(
                cleaned_df, params["start_year"], params["end_year"]
            )
        if checks["総出願人カウント"]:
            results["総出願人カウント"] = cached_applicant_total(
                cleaned_df, params["start_year"], params["end_year"]
            )
        if checks["出願人増減率"]:
            results["出願人増減率"] = cached_applicant_growth(
                cleaned_df, params["base_year"], params["yr_range"]
            )
        if checks["参入撤退チャート"]:
            results["参入撤退チャート"] = cached_entry_exit(cleaned_df)
        if checks["被引用ポジショニングマップ"]:
            results["被引用ポジショニングマップ"] = cached_citation_map(cleaned_df)
        if checks["被引用出願一覧"]:
            results["被引用出願一覧"] = cached_cited_applications(cleaned_df)

    return results


def _render_aggregation_results() -> None:
    """集計結果のメトリクスとプレビューを表示する。"""
    agg = st.session_state.get("agg_results", {})
    if not agg:
        return

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("集計項目数", len(agg))
    if "筆頭出願人件数" in agg and agg["筆頭出願人件数"] is not None:
        mc2.metric("出願人数", len(agg["筆頭出願人件数"]))
    if "特許分類増減率" in agg and agg["特許分類増減率"] is not None:
        mc3.metric("分類数", len(agg["特許分類増減率"]))

    for name, df_r in agg.items():
        if df_r is not None and not df_r.empty:
            with st.expander(f"結果: {name}"):
                st.dataframe(df_r, use_container_width=True, hide_index=True)

    stem = Path(st.session_state.get("upload_name", "data")).stem or "data"
    try:
        st.download_button(
            "集計結果をExcelでダウンロード",
            dataframe_to_excel_bytes(agg),
            file_name=f"{stem}_集計結果.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_agg",
        )
    except Exception as e:
        st.warning(f"Excelダウンロードの準備に失敗しました: {e}")

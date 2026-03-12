# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import altair as alt
import pandas as pd
import streamlit as st

from chart_utils import chart_to_png_bytes
from example_analysis import (
    DEFAULT_NAME_MAPPING,
    DEFAULT_NAME_MAPPING_ROWS,
    _editor_rows_to_dict,
    _mapping_to_editor_rows,
    clean_patent_dataframe,
    excel_to_dataframe,
    analysis_application_trend,
    analysis_ipc_growth,
    analysis_ipc_summary,
    analysis_ipc_main_group,
    analysis_applicant_count,
    analysis_applicant_total,
    analysis_applicant_growth,
    analysis_entry_exit,
    analysis_citation_map,
    analysis_cited_applications,
    analysis_applicant_year_trend,
    analysis_ipc_year_heatmap,
    analysis_applicant_ipc_heatmap,
    analysis_applicant_share,
    analysis_co_applicant,
    analysis_ipc_treemap,
    dataframe_to_excel_bytes,
)

st.set_page_config(page_title="IP Analysis Studio", page_icon="📊", layout="wide")

st.markdown("""
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
""", unsafe_allow_html=True)

st.markdown("""<section class="hero"><h1>IP Analysis Studio</h1>
<p>特許Excelをアップロード → 前処理 → 集計 → グラフ の3ステップで分析できます。</p></section>""", unsafe_allow_html=True)

# ==================== Session State ====================
for k, v in [
    ("step", 1),
    ("cleaned_df", None),
    ("upload_name", ""),
    ("agg_results", {}),
    ("name_mapping_rows", [dict(x) for x in DEFAULT_NAME_MAPPING_ROWS]),
    ("raw_df", None),
    ("column_mapping", {}),
    ("upload_bytes", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v


def _advance(step: int):
    st.session_state["step"] = step


# ==================== Cached aggregations ====================

@st.cache_data
def cached_application_trend(df: pd.DataFrame) -> pd.DataFrame:
    return analysis_application_trend(df)


@st.cache_data
def cached_ipc_growth(df: pd.DataFrame, base_year: int, yr_range: int) -> pd.DataFrame:
    return analysis_ipc_growth(df, base_year, yr_range)


@st.cache_data
def cached_ipc_summary(df: pd.DataFrame) -> pd.DataFrame:
    return analysis_ipc_summary(df)


@st.cache_data
def cached_ipc_main_group(df: pd.DataFrame) -> pd.DataFrame:
    return analysis_ipc_main_group(df)


@st.cache_data
def cached_applicant_count(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return analysis_applicant_count(df, start_year, end_year)


@st.cache_data
def cached_applicant_total(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return analysis_applicant_total(df, start_year, end_year)


@st.cache_data
def cached_applicant_growth(df: pd.DataFrame, base_year: int, yr_range: int) -> pd.DataFrame:
    return analysis_applicant_growth(df, base_year, yr_range)


@st.cache_data
def cached_entry_exit(df: pd.DataFrame) -> pd.DataFrame:
    return analysis_entry_exit(df)


@st.cache_data
def cached_citation_map(df: pd.DataFrame) -> pd.DataFrame:
    return analysis_citation_map(df)


@st.cache_data
def cached_cited_applications(df: pd.DataFrame) -> pd.DataFrame:
    return analysis_cited_applications(df)


# ==================== Progress Bar ====================
step = st.session_state["step"]
cols = st.columns(3)
labels = ["Step 1: データ前処理", "Step 2: 集計", "Step 3: グラフ作成"]
for i, (c, lbl) in enumerate(zip(cols, labels), 1):
    if i < step:
        c.markdown(f"<span class='step-done'>✔ {lbl}</span>", unsafe_allow_html=True)
    elif i == step:
        c.markdown(f"<span class='step-current'>● {lbl}</span>", unsafe_allow_html=True)
    else:
        c.markdown(f"<span class='step-pending'>○ {lbl}</span>", unsafe_allow_html=True)

st.divider()

# ==================== Step 1: 前処理 ====================
if step >= 1:
    st.subheader("Step 1: データ前処理")
    sheet_data = st.text_input("データシート名", value="データ", key="sheet_data")
    uploaded = st.file_uploader("Excelファイル (.xlsx)", type=["xlsx"], key="upload_main")

    # アップロード済みファイルを DataFrame に読み込み & 列マッピング
    raw_df = None
    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        if st.session_state["upload_bytes"] != file_bytes or st.session_state["raw_df"] is None:
            try:
                raw_df = excel_to_dataframe(file_bytes, sheet_name=sheet_data)
                st.session_state["raw_df"] = raw_df
                st.session_state["upload_bytes"] = file_bytes
                st.session_state["upload_name"] = uploaded.name
                st.session_state["column_mapping"] = {}
            except ValueError as e:
                st.error(f"シート名「{sheet_data}」が見つかりません。Excelのシート名を確認してください。詳細: {e}")
                raw_df = None
            except Exception as e:
                st.error(f"Excel の読み込みに失敗しました: {e}")
                raw_df = None
        else:
            raw_df = st.session_state["raw_df"]

    if raw_df is not None:
        st.markdown("#### 列マッピング")
        cols = list(raw_df.columns)
        col_map = st.session_state.get("column_mapping", {}) or {}

        def _guess(defaults):
            for d in defaults:
                if d in cols:
                    return d
            return cols[0] if cols else ""

        def _col_select(label: str, key: str, defaults):
            current = col_map.get(key)
            if current not in cols:
                current = _guess(defaults)
                col_map[key] = current
            idx = cols.index(current) if current in cols else 0
            sel = st.selectbox(label, cols, index=idx, key=f"map_{key}")
            col_map[key] = sel
            return sel

        c1, c2, c3 = st.columns(3)
        applicant_col = _col_select("出願人列", "applicant", ["更新出願人・権利者氏名", "出願人", "出願人名"])
        date_col = _col_select("出願日列", "date", ["出願日", "公開日"])
        num_col = _col_select("出願番号列", "number", ["出願番号"])
        ipc_col = c2.selectbox(
            "IPC列",
            cols,
            index=cols.index(col_map.get("ipc", _guess(["公報IPC", "IPC"]))) if cols else 0,
            key="map_ipc",
        )
        col_map["ipc"] = ipc_col
        fi_col = c2.selectbox(
            "FI列（任意）",
            ["（なし）"] + cols,
            index=(["（なし）"] + cols).index(col_map.get("fi", "（なし）")),
            key="map_fi",
        )
        col_map["fi"] = fi_col
        cit_col = c3.selectbox(
            "被引用回数列（任意）",
            ["（なし）"] + cols,
            index=(["（なし）"] + cols).index(col_map.get("citation", "被引用回数") if col_map.get("citation") in cols else "（なし）"),
            key="map_citation",
        )
        col_map["citation"] = cit_col
        life_col = c3.selectbox(
            "生死情報列（任意）",
            ["（なし）"] + cols,
            index=(["（なし）"] + cols).index(col_map.get("life", "生死情報") if col_map.get("life") in cols else "（なし）"),
            key="map_life",
        )
        col_map["life"] = life_col

        st.session_state["column_mapping"] = col_map

    apply_name_mapping = st.checkbox("名寄せを実行する（推奨）", value=True, key="apply_name_mapping")
    if apply_name_mapping:
        st.caption("※ Excel 側で名寄せ済みであれば OFF にしてください。")

    with st.expander("企業名寄せリスト（編集可能）", expanded=False):
        import json as _json
        st.caption("行の追加・編集・削除ができます。")
        edited = st.data_editor(
            pd.DataFrame(st.session_state["name_mapping_rows"]),
            use_container_width=True, num_rows="dynamic",
            column_config={
                "元の名前": st.column_config.TextColumn("元の名前", width="medium"),
                "名寄せ後": st.column_config.TextColumn("名寄せ後", width="medium"),
            },
            key="name_editor",
        )
        st.session_state["name_mapping_rows"] = edited.to_dict("records")
        nm_col1, nm_col2 = st.columns(2)
        current_mapping = _editor_rows_to_dict(st.session_state["name_mapping_rows"])
        nm_col1.download_button(
            "名寄せをJSONで保存",
            data=_json.dumps(current_mapping, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="name_mapping.json",
            mime="application/json",
            key="nm_download",
        )
        uploaded_nm = nm_col2.file_uploader("名寄せJSONを読み込み", type=["json"], key="nm_upload")
        if uploaded_nm is not None:
            try:
                loaded_nm = _json.loads(uploaded_nm.read().decode("utf-8"))
                if not isinstance(loaded_nm, dict):
                    raise ValueError("JSONはオブジェクト形式（辞書）である必要があります")
                st.session_state["name_mapping_rows"] = _mapping_to_editor_rows(loaded_nm)
                st.success(f"名寄せマッピングを読み込みました（{len(loaded_nm)} 件）。")
                st.rerun()
            except (ValueError, KeyError) as e:
                st.error(f"名寄せJSONの形式が正しくありません: {e}")
            except Exception as e:
                st.error(f"名寄せJSONの読み込みに失敗しました: {e}")

    if st.button("前処理を実行", type="primary", key="run_clean", disabled=uploaded is None):
        if uploaded is not None:
            try:
                with st.spinner("前処理中..."):
                    raw_df = st.session_state.get("raw_df")
                    if raw_df is None:
                        raw_df = excel_to_dataframe(uploaded.getvalue(), sheet_name=sheet_data)
                        st.session_state["raw_df"] = raw_df
                    mapping_rows = st.session_state["name_mapping_rows"]
                    mapping = _editor_rows_to_dict(mapping_rows) if apply_name_mapping else {}
                    col_map = st.session_state.get("column_mapping", {})
                    cleaned = clean_patent_dataframe(
                        raw_df,
                        name_mapping=mapping,
                        applicant_col=col_map.get("applicant", "更新出願人・権利者氏名"),
                        application_date_col=col_map.get("date", "出願日"),
                        ipc_col=col_map.get("ipc", "公報IPC"),
                        fi_col=None if col_map.get("fi") in (None, "（なし）") else col_map.get("fi", "公報FI"),
                        life_death_col=None if col_map.get("life") in (None, "（なし）") else col_map.get("life", "生死情報"),
                        enable_name_mapping=apply_name_mapping,
                    )
                    st.session_state["cleaned_df"] = cleaned
                    st.session_state["step"] = 2
                    st.session_state["agg_results"] = {}
                st.success(f"前処理完了: {len(cleaned)} 行 × {len(cleaned.columns)} 列")
                st.rerun()
            except (KeyError, ValueError) as e:
                st.error(f"前処理に失敗しました（列名が正しいか確認してください）: {e}")
            except Exception as e:
                st.error(f"前処理中に予期しないエラーが発生しました: {e}")

    if st.session_state["cleaned_df"] is not None:
        st.caption(f"整理済み: {st.session_state['upload_name']} — {len(st.session_state['cleaned_df'])} 行")
        with st.expander("プレビュー（先頭100行）"):
            st.dataframe(st.session_state["cleaned_df"].head(100), use_container_width=True, hide_index=True)

# ==================== Step 2: 集計 ====================
if step >= 2 and st.session_state["cleaned_df"] is not None:
    st.divider()
    st.subheader("Step 2: 集計")
    if True:
        cleaned_df = st.session_state["cleaned_df"]
        p1, p2, p3 = st.columns(3)
        base_year = p1.number_input("基準年", 1900, 2100, 2015, key="by")
        start_year = p2.number_input("開始年", 1980, 2030, 2010, key="sy")
        end_year = p3.number_input("終了年", 1980, 2030, 2023, key="ey")
        yr_range = st.slider("増減率レンジ（年）", 5, 20, 10, key="yr")

        st.markdown("**実行する集計を選択:**")
        c1, c2 = st.columns(2)
        checks = {
            "出願件数推移": c1.checkbox("出願件数推移", True, key="t1"),
            "公報IPC増減率": c1.checkbox("公報IPC増減率", True, key="t2"),
            "公報IPC集計": c1.checkbox("公報IPC集計", False, key="t3"),
            "筆頭IPCメイングループ": c1.checkbox("筆頭IPCメイングループ", False, key="t4"),
            "筆頭出願人件数": c2.checkbox("筆頭出願人件数", True, key="t5"),
            "総出願人カウント": c2.checkbox("総出願人カウント", True, key="t6"),
            "出願人増減率": c2.checkbox("出願人増減率", True, key="t7"),
            "参入撤退チャート": c2.checkbox("参入撤退チャート", True, key="t8"),
            "被引用ポジショニングマップ": c1.checkbox("被引用ポジショニングマップ", True, key="t9"),
            "被引用出願一覧": c2.checkbox("被引用出願一覧", False, key="t10"),
        }

        if st.button("集計を実行", type="primary", key="run_agg"):
            results = {}
            with st.spinner("集計中..."):
                if checks["出願件数推移"]:
                    results["出願件数推移"] = cached_application_trend(cleaned_df)
                if checks["公報IPC増減率"]:
                    results["公報IPC増減率"] = cached_ipc_growth(cleaned_df, base_year, yr_range)
                if checks["公報IPC集計"]:
                    results["公報IPC集計"] = cached_ipc_summary(cleaned_df)
                if checks["筆頭IPCメイングループ"]:
                    results["筆頭IPCメイングループ"] = cached_ipc_main_group(cleaned_df)
                if checks["筆頭出願人件数"]:
                    results["筆頭出願人件数"] = cached_applicant_count(cleaned_df, start_year, end_year)
                if checks["総出願人カウント"]:
                    results["総出願人カウント"] = cached_applicant_total(cleaned_df, start_year, end_year)
                if checks["出願人増減率"]:
                    results["出願人増減率"] = cached_applicant_growth(cleaned_df, base_year, yr_range)
                if checks["参入撤退チャート"]:
                    results["参入撤退チャート"] = cached_entry_exit(cleaned_df)
                if checks["被引用ポジショニングマップ"]:
                    results["被引用ポジショニングマップ"] = cached_citation_map(cleaned_df)
                if checks["被引用出願一覧"]:
                    results["被引用出願一覧"] = cached_cited_applications(cleaned_df)
            st.session_state["agg_results"] = results
            st.session_state["step"] = 3
            st.success(f"{len(results)} 件の集計が完了しました。")
            st.rerun()

        agg = st.session_state.get("agg_results", {})
        if agg:
            for name, df_r in agg.items():
                if df_r is not None and not df_r.empty:
                    with st.expander(f"結果: {name}"):
                        st.dataframe(df_r, use_container_width=True, hide_index=True)
            stem = Path(st.session_state.get("upload_name", "data")).stem or "data"
            try:
                st.download_button("集計結果をExcelでダウンロード", dataframe_to_excel_bytes(agg),
                                   file_name=f"{stem}_集計結果.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_agg")
            except Exception as e:
                st.warning(f"Excelダウンロードの準備に失敗しました: {e}")

# ==================== Step 3: グラフ作成 ====================
if step >= 3 and st.session_state.get("agg_results"):
    st.subheader("Step 3: グラフ作成")
    agg = st.session_state["agg_results"]
    cleaned_df = st.session_state["cleaned_df"]

    trend_df = agg.get("出願件数推移")
    ipc_df = agg.get("公報IPC増減率")
    app_count_df = agg.get("総出願人カウント")
    app_growth_df = agg.get("出願人増減率")
    entry_exit_df = agg.get("参入撤退チャート")
    citation_df = agg.get("被引用ポジショニングマップ")
    lead_count_df = agg.get("筆頭出願人件数")

    # グラフ共通設定 / プリセット / 設定ファイル
    st.divider()
    with st.expander("グラフ共通設定", expanded=False):
        preset = st.selectbox(
            "分析プリセット",
            ["カスタム", "トップ企業分析", "引用集中度分析"],
            key="analysis_preset",
        )
        show_labels = st.checkbox("データラベルを表示する", value=True, key="show_labels")

        import json

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
                # グラフ設定
                for k in ("preset", "show_labels", "bar_min", "bar_max", "bar_sort", "ipc_bmin", "ee_min", "cma_min", "cmb_min"):
                    if loaded.get(k) is not None:
                        st.session_state[k] = loaded[k]
                # 列マッピング
                if loaded.get("column_mapping"):
                    st.session_state["column_mapping"] = loaded["column_mapping"]
                # 年パラメータ
                if loaded.get("base_year") is not None:
                    st.session_state["by"] = loaded["base_year"]
                if loaded.get("start_year") is not None:
                    st.session_state["sy"] = loaded["start_year"]
                if loaded.get("end_year") is not None:
                    st.session_state["ey"] = loaded["end_year"]
                # 名寄せマッピング
                if loaded.get("name_mapping") and isinstance(loaded["name_mapping"], dict):
                    st.session_state["name_mapping_rows"] = _mapping_to_editor_rows(loaded["name_mapping"])
                st.success("設定を読み込みました。")
                st.rerun()
            except (ValueError, KeyError) as e:
                st.error(f"設定ファイルの形式が正しくありません: {e}")
            except Exception as e:
                st.error(f"設定ファイルの読み込みに失敗しました: {e}")

        # プリセット適用（簡易版）
        if preset == "トップ企業分析":
            st.session_state.setdefault("bar_min", 50)
            st.session_state.setdefault("bar_max", 35)
        elif preset == "引用集中度分析":
            st.session_state.setdefault("cma_min", 10)

    # --------- 1. 出願件数 横棒グラフ ---------
    total_df = app_count_df if (app_count_df is not None and not app_count_df.empty) else lead_count_df
    if total_df is not None and not total_df.empty:
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
        bar_layer = bar_layer.properties(height=max(300, max_show * 22)).interactive()
        st.altair_chart(bar_layer, use_container_width=True)
        png_bytes = chart_to_png_bytes(bar_layer)
        if png_bytes:
            st.download_button(
                "このグラフをPNGで保存",
                data=png_bytes,
                file_name="applicant_counts_bar.png",
                mime="image/png",
                key="png_bar",
            )

    # --------- 2. 出願件数推移 折れ線グラフ ---------
    if trend_df is not None and not trend_df.empty:
        st.markdown("### 出願件数推移（折れ線グラフ）")

        min_year = int(trend_df["出願年"].min())
        max_year = int(trend_df["出願年"].max())
        y1, y2 = st.slider(
            "表示する出願年の範囲",
            min_year,
            max_year,
            (min_year, max_year),
            key="trend_year_range",
        )
        trend_view = trend_df[(trend_df["出願年"] >= y1) & (trend_df["出願年"] <= y2)]

        line = alt.Chart(trend_view).mark_line(point=alt.OverlayMarkDef(size=50)).encode(
            x=alt.X("出願年:O", title="出願年"),
            y=alt.Y("出願件数:Q", title="出願件数"),
            tooltip=["出願年", "出願件数"],
        )
        text = alt.Chart(trend_view).mark_text(dy=-12, fontSize=10).encode(
            x=alt.X("出願年:O"), y=alt.Y("出願件数:Q"), text="出願件数:Q",
        )
        line_layer = (line + text) if show_labels else line
        line_layer = line_layer.properties(
            height=380,
            padding={"left": 80, "right": 20, "top": 10, "bottom": 40},
        ).interactive()
        st.altair_chart(line_layer, use_container_width=True)
        png_bytes = chart_to_png_bytes(line_layer)
        if png_bytes:
            st.download_button(
                "このグラフをPNGで保存",
                data=png_bytes,
                file_name="application_trend_line.png",
                mime="image/png",
                key="png_trend",
            )

    # --------- 3. IPC増減率 バブルチャート ---------
    if ipc_df is not None and not ipc_df.empty:
        st.markdown("### IPC増減率（バブルチャート）")
        bc1, bc2 = st.columns(2)
        ipc_min = bc1.slider("最低出願件数（IPC）", 1, int(ipc_df["total_count"].max()), 10, key="ipc_bmin")
        ipc_sel = bc2.multiselect("IPC を選択（空＝全表示）", ipc_df["IPC"].tolist(), key="ipc_sel")
        bdf = ipc_df[ipc_df["total_count"] >= ipc_min].copy()
        if ipc_sel:
            bdf = bdf[bdf["IPC"].isin(ipc_sel)]
        bdf["長期増減率(%)"] = (bdf["pct_change_10"] * 100).round(1)
        bdf["短期増減率(%)"] = (bdf["pct_change_second_5"] * 100).round(1)
        pts = alt.Chart(bdf).mark_circle(opacity=0.6).encode(
            x=alt.X("長期増減率(%):Q", title="長期増減率(%)"),
            y=alt.Y("短期増減率(%):Q", title="短期増減率(%)"),
            size=alt.Size("total_count:Q", title="出願件数", scale=alt.Scale(range=[40, 1500])),
            color=alt.value("#8bc34a"),
            tooltip=["IPC", "total_count", "長期増減率(%)", "短期増減率(%)"],
        )
        labels = alt.Chart(bdf).mark_text(fontSize=9, dy=-10).encode(
            x="長期増減率(%):Q", y="短期増減率(%):Q", text="IPC:N",
        )
        ipc_layer = (pts + labels) if show_labels else pts
        ipc_layer = ipc_layer.properties(width=750, height=500).interactive()
        st.altair_chart(ipc_layer, use_container_width=True)
        png_bytes = chart_to_png_bytes(ipc_layer)
        if png_bytes:
            st.download_button(
                "このグラフをPNGで保存",
                data=png_bytes,
                file_name="ipc_growth_bubble.png",
                mime="image/png",
                key="png_ipc",
            )

    # --------- 4. 参入撤退 バブルチャート ---------
    if entry_exit_df is not None and not entry_exit_df.empty:
        st.markdown("### 参入撤退チャート（バブルチャート）")
        ee = entry_exit_df.dropna(subset=["最初の出願年", "直近出願年"]).copy()
        ec1, ec2 = st.columns(2)
        ee_min = ec1.slider("最低出願件数（参入撤退）", 1, int(ee["総出願件数"].max()), 50, key="ee_min")
        ee_sel = ec2.multiselect("出願人を選択（空＝全表示）", sorted(ee["出願人名"].tolist()), key="ee_sel")
        ee = ee[ee["総出願件数"] >= ee_min]
        if ee_sel:
            ee = ee[ee["出願人名"].isin(ee_sel)]
        pts = alt.Chart(ee).mark_circle(opacity=0.55).encode(
            x=alt.X("最初の出願年:Q", title="最初の出願年", scale=alt.Scale(zero=False)),
            y=alt.Y("直近出願年:Q", title="直近出願年", scale=alt.Scale(zero=False)),
            size=alt.Size("総出願件数:Q", scale=alt.Scale(range=[40, 1500])),
            color=alt.value("#8bc34a"),
            tooltip=["出願人名", "最初の出願年", "直近出願年", "総出願件数"],
        )
        lbl = alt.Chart(ee).mark_text(fontSize=9, dy=-10).encode(
            x="最初の出願年:Q", y="直近出願年:Q", text="出願人名:N",
        )
        ee_layer = (pts + lbl) if show_labels else pts
        ee_layer = ee_layer.properties(width=750, height=500).interactive()
        st.altair_chart(ee_layer, use_container_width=True)
        png_bytes = chart_to_png_bytes(ee_layer)
        if png_bytes:
            st.download_button(
                "このグラフをPNGで保存",
                data=png_bytes,
                file_name="entry_exit_bubble.png",
                mime="image/png",
                key="png_entry_exit",
            )

    # --------- 5. 被引用ポジショニングマップ A (Y=最大引用回数) ---------
    if citation_df is not None and not citation_df.empty:
        st.markdown("### 被引用ポジショニングマップ A（最大引用回数）")
        cc1, cc2 = st.columns(2)
        cm_min = cc1.slider("最低出願件数（引用A）", 1, int(citation_df["出願件数"].max()), 30, key="cma_min")
        cm_sel = cc2.multiselect("出願人（引用A）", sorted(citation_df["出願人名"].tolist()), key="cma_sel")
        cm = citation_df[citation_df["出願件数"] >= cm_min].copy()
        if cm_sel:
            cm = cm[cm["出願人名"].isin(cm_sel)]
        pts = alt.Chart(cm).mark_circle(opacity=0.6).encode(
            x=alt.X("出願件数:Q", title="出願件数"),
            y=alt.Y("最大引用回数:Q", title="最大引用回数"),
            size=alt.Size("合計引用回数:Q", scale=alt.Scale(range=[40, 1500])),
            color=alt.value("#5b86c5"),
            tooltip=["出願人名", "出願件数", "最大引用回数", "合計引用回数"],
        )
        lbl = alt.Chart(cm).mark_text(fontSize=9, dy=-10).encode(
            x="出願件数:Q", y="最大引用回数:Q", text="出願人名:N",
        )
        cm_layer = (pts + lbl) if show_labels else pts
        cm_layer = cm_layer.properties(width=750, height=500).interactive()
        st.altair_chart(cm_layer, use_container_width=True)
        png_bytes = chart_to_png_bytes(cm_layer)
        if png_bytes:
            st.download_button(
                "このグラフをPNGで保存",
                data=png_bytes,
                file_name="citation_positioning_max.png",
                mime="image/png",
                key="png_citation_a",
            )

    # --------- 6. 被引用ポジショニングマップ B (Y=引用割合%) ---------
    if citation_df is not None and not citation_df.empty:
        st.markdown("### 被引用ポジショニングマップ B（引用された出願割合）")
        cb_min = st.slider("最低出願件数（引用B）", 1, int(citation_df["出願件数"].max()), 30, key="cmb_min")
        cmb = citation_df[citation_df["出願件数"] >= cb_min].copy()
        pts = alt.Chart(cmb).mark_circle(opacity=0.6).encode(
            x=alt.X("出願件数:Q", title="出願件数"),
            y=alt.Y("引用された出願割合（%）:Q", title="引用された出願割合(%)"),
            size=alt.Size("合計引用回数:Q", scale=alt.Scale(range=[40, 1500])),
            color=alt.value("#5b86c5"),
            tooltip=["出願人名", "出願件数", "引用された出願割合（%）", "合計引用回数"],
        )
        lbl = alt.Chart(cmb).mark_text(fontSize=9, dy=-10).encode(
            x="出願件数:Q", y="引用された出願割合（%）:Q", text="出願人名:N",
        )
        cmb_layer = (pts + lbl) if show_labels else pts
        cmb_layer = cmb_layer.properties(width=750, height=500).interactive()
        st.altair_chart(cmb_layer, use_container_width=True)
        png_bytes = chart_to_png_bytes(cmb_layer)
        if png_bytes:
            st.download_button(
                "このグラフをPNGで保存",
                data=png_bytes,
                file_name="citation_positioning_ratio.png",
                mime="image/png",
                key="png_citation_b",
            )

    # --------- 7. 出願増減率 バブルチャート (出願人版) ---------
    if app_growth_df is not None and not app_growth_df.empty:
        st.markdown("### 出願増減率（バブルチャート）")
        ag1, ag2 = st.columns(2)
        ag_min = ag1.slider("最低出願件数（出願人増減率）", 1, int(app_growth_df["total_count"].max()), 30, key="ag_min")
        ag_sel = ag2.multiselect("出願人（増減率）", sorted(app_growth_df["出願人"].tolist()), key="ag_sel")
        agd = app_growth_df[app_growth_df["total_count"] >= ag_min].copy()
        if ag_sel:
            agd = agd[agd["出願人"].isin(ag_sel)]
        agd["長期増減率(%)"] = (agd["pct_change_10"] * 100).round(1)
        agd["短期増減率(%)"] = (agd["pct_change_second_5"] * 100).round(1)
        pts = alt.Chart(agd).mark_circle(opacity=0.55).encode(
            x=alt.X("長期増減率(%):Q", title="長期増減率(%)"),
            y=alt.Y("短期増減率(%):Q", title="短期増減率(%)"),
            size=alt.Size("total_count:Q", title="出願件数", scale=alt.Scale(range=[40, 1500])),
            color=alt.value("#8bc34a"),
            tooltip=["出願人", "total_count", "長期増減率(%)", "短期増減率(%)"],
        )
        lbl = alt.Chart(agd).mark_text(fontSize=9, dy=-10).encode(
            x="長期増減率(%):Q", y="短期増減率(%):Q", text="出願人:N",
        )
        ag_layer = (pts + lbl) if show_labels else pts
        ag_layer = ag_layer.properties(width=750, height=500).interactive()
        st.altair_chart(ag_layer, use_container_width=True)
        png_bytes = chart_to_png_bytes(ag_layer)
        if png_bytes:
            st.download_button(
                "このグラフをPNGで保存",
                data=png_bytes,
                file_name="applicant_growth_bubble.png",
                mime="image/png",
                key="png_applicant_growth",
            )

    # ==================== 追加グラフ ====================
    st.divider()
    st.subheader("追加グラフ")

    # --------- 8. 出願人別 年次推移 折れ線（複数系列） ---------
    if cleaned_df is not None:
        st.markdown("### 出願人別 年次推移（複数系列）")
        at_n = st.slider("上位N社", 3, 30, 10, key="at_n")
        at_df = analysis_applicant_year_trend(cleaned_df, top_n=at_n)
        if not at_df.empty:
            all_apps = sorted(at_df["出願人"].unique().tolist())
            at_sel = st.multiselect("出願人を選択（空＝全表示）", all_apps, key="at_sel")
            if at_sel:
                at_df = at_df[at_df["出願人"].isin(at_sel)]
            c = alt.Chart(at_df).mark_line(point=True).encode(
                x=alt.X("出願年:O", title="出願年"),
                y=alt.Y("出願件数:Q", title="出願件数"),
                color=alt.Color("出願人:N"),
                tooltip=["出願年", "出願人", "出願件数"],
            ).properties(height=400).interactive()
            st.altair_chart(c, use_container_width=True)

    # --------- 9. IPC分布 ツリーマップ ---------
    if cleaned_df is not None:
        st.markdown("### IPC分布（ツリーマップ）")
        tm_df = analysis_ipc_treemap(cleaned_df)
        if not tm_df.empty:
            tm_n = st.slider("表示IPC数", 5, 50, 20, key="tm_n")
            tm_data = tm_df.head(tm_n)
            c = alt.Chart(tm_data).mark_bar().encode(
                x=alt.X("出願件数:Q", title="出願件数"),
                y=alt.Y("IPC:N", sort="-x", title="IPCサブクラス"),
                color=alt.Color("出願件数:Q", scale=alt.Scale(scheme="greens"), legend=None),
                tooltip=["IPC", "出願件数"],
            ).properties(height=max(300, tm_n * 22)).interactive()
            st.altair_chart(c, use_container_width=True)

    # --------- 10. 出願人 x IPC ヒートマップ ---------
    if cleaned_df is not None:
        st.markdown("### 出願人 × IPC ヒートマップ")
        hm1, hm2 = st.columns(2)
        hm_a = hm1.slider("上位出願人数", 5, 40, 20, key="hm_a")
        hm_i = hm2.slider("上位IPC数", 5, 30, 15, key="hm_i")
        hm_df = analysis_applicant_ipc_heatmap(cleaned_df, top_applicants=hm_a, top_ipcs=hm_i)
        if not hm_df.empty:
            c = alt.Chart(hm_df).mark_rect().encode(
                x=alt.X("IPC:N", title="IPC"),
                y=alt.Y("出願人:N", title="出願人"),
                color=alt.Color("出願件数:Q", scale=alt.Scale(scheme="blues"), title="件数"),
                tooltip=["出願人", "IPC", "出願件数"],
            ).properties(height=max(300, hm_a * 22)).interactive()
            st.altair_chart(c, use_container_width=True)

    # --------- 11. 出願人シェア 積み上げ面グラフ ---------
    if cleaned_df is not None:
        st.markdown("### 出願人シェア推移（積み上げ面）")
        sh_n = st.slider("上位N社", 3, 20, 8, key="sh_n")
        sh_df = analysis_applicant_share(cleaned_df, top_n=sh_n)
        if not sh_df.empty:
            c = alt.Chart(sh_df).mark_area().encode(
                x=alt.X("出願年:O", title="出願年"),
                y=alt.Y("出願件数:Q", title="出願件数", stack="zero"),
                color=alt.Color("出願人:N"),
                tooltip=["出願年", "出願人", "出願件数"],
            ).properties(height=400).interactive()
            st.altair_chart(c, use_container_width=True)

    # --------- 12. 共同出願ネットワーク（ヒートマップ） ---------
    if cleaned_df is not None:
        st.markdown("### 共同出願ネットワーク")
        co_n = st.slider("表示ペア数", 5, 50, 20, key="co_n")
        co_df = analysis_co_applicant(cleaned_df, top_n=co_n)
        if not co_df.empty:
            co_show = co_df.head(co_n)
            c = alt.Chart(co_show).mark_rect().encode(
                x=alt.X("出願人A:N", title="出願人A"),
                y=alt.Y("出願人B:N", title="出願人B"),
                color=alt.Color("共同出願件数:Q", scale=alt.Scale(scheme="oranges"), title="件数"),
                tooltip=["出願人A", "出願人B", "共同出願件数"],
            ).properties(height=400).interactive()
            st.altair_chart(c, use_container_width=True)

    # --------- 13. IPC別 年次推移 ヒートマップ ---------
    if cleaned_df is not None:
        st.markdown("### IPC別 年次推移（ヒートマップ）")
        iy_n = st.slider("上位IPC数", 5, 40, 20, key="iy_n")
        iy_df = analysis_ipc_year_heatmap(cleaned_df, top_n=iy_n)
        if not iy_df.empty:
            c = alt.Chart(iy_df).mark_rect().encode(
                x=alt.X("出願年:O", title="出願年"),
                y=alt.Y("IPC:N", title="IPC"),
                color=alt.Color("出願件数:Q", scale=alt.Scale(scheme="viridis"), title="件数"),
                tooltip=["出願年", "IPC", "出願件数"],
            ).properties(height=max(300, iy_n * 22)).interactive()
            st.altair_chart(c, use_container_width=True)

    # ステップ戻し
    st.divider()
    bc1, bc2 = st.columns(2)
    if bc1.button("← Step 1 に戻る", key="back1"):
        st.session_state["step"] = 1
        st.rerun()
    if bc2.button("← Step 2 に戻る", key="back2"):
        st.session_state["step"] = 2
        st.rerun()

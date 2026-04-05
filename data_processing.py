# -*- coding: utf-8 -*-
"""Step 1: データ前処理（ファイル読込・列マッピング・名寄せ・クリーニング）の UI ロジック。"""
from __future__ import annotations

import json as _json
from pathlib import Path
from typing import List, Optional

import pandas as pd
import streamlit as st

from example_analysis import (
    QUESTEL_COL_DEFAULTS,
    _editor_rows_to_dict,
    _mapping_to_editor_rows,
    clean_patent_dataframe,
    excel_to_dataframe,
    load_csv_to_dataframe,
    detect_data_format,
)
from styles import format_badge_html

# ==================== Step 1: 前処理 ====================


def render_step1() -> None:
    """Step 1 全体を描画する。"""
    st.subheader("Step 1: データ前処理")
    sheet_data = st.text_input("データシート名", value="データ", key="sheet_data")

    raw_df = _render_file_upload(sheet_data)

    if raw_df is not None:
        _render_format_badge()
        _render_column_mapping(raw_df)

    _render_name_mapping_editor()
    _render_preprocess_button(sheet_data)
    _render_cleaned_preview()


def _render_file_upload(sheet_data: str) -> Optional[pd.DataFrame]:
    """サンプルデータ or アップロードファイルを読み込み、raw_df を返す。"""
    sample_path = Path(__file__).parent / "excel_sample" / "非水電解質電池.xlsx"
    sample_col, upload_col = st.columns([1, 2])

    if sample_col.button(
        "\U0001f4c2 サンプルデータで試す",
        help="非水電解質電池の特許データ（約2,000件）をサンプルとして読み込みます",
    ):
        try:
            sample_bytes = sample_path.read_bytes()
            sample_df = excel_to_dataframe(sample_bytes, sheet_name="データ")
            st.session_state["raw_df"] = sample_df
            st.session_state["upload_bytes"] = sample_bytes
            st.session_state["upload_name"] = "非水電解質電池.xlsx（サンプル）"
            st.session_state["column_mapping"] = {}
            st.session_state["step"] = 1
            st.success("サンプルデータを読み込みました。このまま「前処理を実行」を押してください。")
            st.rerun()
        except Exception as e:
            st.error(f"サンプルの読み込みに失敗しました: {e}")

    uploaded = upload_col.file_uploader(
        "または、ファイルをアップロード (.xlsx / .csv)",
        type=["xlsx", "csv"],
        key="upload_main",
    )

    raw_df = None
    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        if st.session_state["upload_bytes"] != file_bytes or st.session_state["raw_df"] is None:
            try:
                if uploaded.name.lower().endswith(".csv"):
                    raw_df = load_csv_to_dataframe(file_bytes)
                else:
                    raw_df = excel_to_dataframe(file_bytes, sheet_name=sheet_data)
                fmt = detect_data_format(raw_df)
                st.session_state["raw_df"] = raw_df
                st.session_state["upload_bytes"] = file_bytes
                st.session_state["upload_name"] = uploaded.name
                st.session_state["data_format"] = fmt
                if fmt == "questel":
                    _apply_questel_mapping(raw_df)
                else:
                    st.session_state["column_mapping"] = {}
            except (ValueError, Exception) as e:
                st.error(f"ファイルの読み込みに失敗しました: {e}")
                raw_df = None
        else:
            raw_df = st.session_state["raw_df"]
    elif st.session_state.get("raw_df") is not None:
        raw_df = st.session_state["raw_df"]

    return raw_df


def _apply_questel_mapping(raw_df: pd.DataFrame) -> None:
    """Questel 形式の列マッピングを自動設定する。"""
    cols_in_df = list(raw_df.columns)
    auto_map = {}
    for key, col_name in QUESTEL_COL_DEFAULTS.items():
        auto_map[key] = col_name if col_name in cols_in_df else "（なし）"
    st.session_state["column_mapping"] = auto_map


def _render_format_badge() -> None:
    """認識されたデータ形式のバッジを表示する。"""
    fmt = st.session_state.get("data_format", "unknown")
    st.markdown(format_badge_html(fmt), unsafe_allow_html=True)


def _render_column_mapping(raw_df: pd.DataFrame) -> None:
    """列マッピング UI を描画する。"""
    st.markdown("#### 列マッピング")
    cols = list(raw_df.columns)
    col_map = st.session_state.get("column_mapping", {}) or {}

    def _guess(defaults: List[str]) -> str:
        for d in defaults:
            if d in cols:
                return d
        return cols[0] if cols else ""

    def _col_select(label: str, key: str, defaults: List[str], help_text: str = None) -> str:
        current = col_map.get(key)
        if current not in cols:
            current = _guess(defaults)
            col_map[key] = current
        idx = cols.index(current) if current in cols else 0
        sel = st.selectbox(label, cols, index=idx, key=f"map_{key}", help=help_text)
        col_map[key] = sel
        return sel

    st.markdown("##### 必須列")
    c1, c2, c3 = st.columns(3)
    _col_select("出願人列", "applicant", [
        "更新出願人・権利者氏名", "出願人", "出願人名",
        "Current standardized assignees - inventors removed", "Current assignees",
    ], help_text="出願人・権利者名が格納されている列")
    _col_select("出願日列", "date", [
        "出願日", "公開日", "Earliest application date",
    ], help_text="出願日（YYYY-MM-DD形式）の列")
    _col_select("出願番号列", "number", [
        "出願番号", "Publication numbers", "Standardized publication numbers",
    ], help_text="出願番号または公報番号の列")

    st.markdown("##### 分類列")
    ipc_col = c2.selectbox(
        "特許分類列",
        cols,
        index=cols.index(col_map.get("ipc", _guess([
            "公報IPC", "IPC", "IPC - International classification",
        ]))) if cols else 0,
        key="map_ipc",
        help="IPC分類コードが格納されている列（複数コードはカンマ区切り可）",
    )
    col_map["ipc"] = ipc_col

    _fi_default = col_map.get("fi", "（なし）")
    if _fi_default not in (["（なし）"] + cols):
        _fi_default = "（なし）"
    fi_col = c2.selectbox(
        "FI列（任意）",
        ["（なし）"] + cols,
        index=(["（なし）"] + cols).index(_fi_default),
        key="map_fi",
    )
    col_map["fi"] = fi_col

    fterm_col_options = ["（なし）"] + cols
    _fterm_default = col_map.get("fterm", "（なし）")
    if _fterm_default not in fterm_col_options:
        _fterm_default = "（なし）"
    fterm_col_val = c3.selectbox(
        "Fターム列（任意）",
        fterm_col_options,
        index=fterm_col_options.index(_fterm_default),
        key="map_fterm",
    )
    col_map["fterm"] = fterm_col_val

    cit_col = c3.selectbox(
        "被引用回数列（任意）",
        ["（なし）"] + cols,
        index=(["（なし）"] + cols).index(
            col_map.get("citation", "被引用回数")
            if col_map.get("citation") in cols
            else "（なし）"
        ),
        key="map_citation",
    )
    col_map["citation"] = cit_col

    life_col = c3.selectbox(
        "生死情報列（任意）",
        ["（なし）"] + cols,
        index=(["（なし）"] + cols).index(
            col_map.get("life", "生死情報")
            if col_map.get("life") in cols
            else "（なし）"
        ),
        key="map_life",
    )
    col_map["life"] = life_col

    st.session_state["column_mapping"] = col_map


def _render_name_mapping_editor() -> None:
    """企業名寄せリストの編集 UI を描画する。"""
    apply_name_mapping = st.checkbox(
        "名寄せを実行する（推奨）", value=True, key="apply_name_mapping"
    )
    if apply_name_mapping:
        st.caption("※ Excel 側で名寄せ済みであれば OFF にしてください。")

    with st.expander("企業名寄せリスト（編集可能）", expanded=False):
        st.caption("行の追加・編集・削除ができます。")
        edited = st.data_editor(
            pd.DataFrame(st.session_state["name_mapping_rows"]),
            use_container_width=True,
            num_rows="dynamic",
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


def _render_preprocess_button(sheet_data: str) -> None:
    """前処理実行ボタンとその処理ロジック。"""
    has_data = (
        st.session_state.get("upload_main") is not None
        or st.session_state.get("raw_df") is not None
    )
    if st.button("前処理を実行", type="primary", key="run_clean", disabled=not has_data):
        if has_data:
            try:
                with st.spinner("前処理中..."):
                    raw_df = st.session_state.get("raw_df")
                    if raw_df is None:
                        uploaded = st.session_state.get("upload_main")
                        if uploaded is not None:
                            raw_df = excel_to_dataframe(uploaded.getvalue(), sheet_name=sheet_data)
                            st.session_state["raw_df"] = raw_df
                    apply_name_mapping = st.session_state.get("apply_name_mapping", True)
                    mapping_rows = st.session_state["name_mapping_rows"]
                    mapping = _editor_rows_to_dict(mapping_rows) if apply_name_mapping else {}
                    col_map = st.session_state.get("column_mapping", {})
                    fterm_col_clean = (
                        None
                        if col_map.get("fterm") in (None, "（なし）")
                        else col_map.get("fterm")
                    )
                    cleaned = clean_patent_dataframe(
                        raw_df,
                        name_mapping=mapping,
                        applicant_col=col_map.get("applicant", "更新出願人・権利者氏名"),
                        application_date_col=col_map.get("date", "出願日"),
                        ipc_col=col_map.get("ipc", "公報IPC"),
                        fi_col=(
                            None
                            if col_map.get("fi") in (None, "（なし）")
                            else col_map.get("fi", "公報FI")
                        ),
                        life_death_col=(
                            None
                            if col_map.get("life") in (None, "（なし）")
                            else col_map.get("life", "生死情報")
                        ),
                        enable_name_mapping=apply_name_mapping,
                        fterm_col=fterm_col_clean,
                    )
                    st.session_state["fterm_col_name"] = fterm_col_clean or ""
                    st.session_state["cleaned_df"] = cleaned
                    st.session_state["step"] = 2
                    st.session_state["agg_results"] = {}
                st.success(f"前処理完了: {len(cleaned)} 行 × {len(cleaned.columns)} 列")
                st.rerun()
            except (KeyError, ValueError) as e:
                st.error(f"前処理に失敗しました（列名が正しいか確認してください）: {e}")
            except Exception as e:
                st.error(f"前処理中に予期しないエラーが発生しました: {e}")


def _render_cleaned_preview() -> None:
    """クリーニング済みデータのプレビューを表示する。"""
    if st.session_state["cleaned_df"] is not None:
        st.caption(
            f"整理済み: {st.session_state['upload_name']} "
            f"-- {len(st.session_state['cleaned_df'])} 行"
        )
        with st.expander("プレビュー（先頭100行）"):
            st.dataframe(
                st.session_state["cleaned_df"].head(100),
                use_container_width=True,
                hide_index=True,
            )



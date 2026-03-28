# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

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
from charts import render_step3
from constants import (
    IPC_LEVEL_OPTIONS,
    IPC_LEVEL_COL,
    FI_LEVEL_OPTIONS,
    FI_LEVEL_COL,
    FTERM_LEVEL_OPTIONS,
)
from example_analysis import (
    COL_IPC,
    DEFAULT_NAME_MAPPING,
    DEFAULT_NAME_MAPPING_ROWS,
    QUESTEL_COL_DEFAULTS,
    _editor_rows_to_dict,
    _mapping_to_editor_rows,
    clean_patent_dataframe,
    excel_to_dataframe,
    load_csv_to_dataframe,
    detect_data_format,
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

# ==================== Sidebar ====================
with st.sidebar:
    st.markdown("### IP Analysis Studio")
    with st.expander("使い方ガイド", expanded=False):
        st.markdown("""
1. **Step 1** — Excel/CSVをアップロードし列マッピングを確認
2. **Step 2** — 基準年・レンジを設定し集計を実行
3. **Step 3** — グラフを確認・調整・ダウンロード

**グラフ操作:**
- マウスホイール: ズーム
- ドラッグ: パン移動
- Shift+ドラッグ: 範囲選択
""")
    if st.session_state.get("cleaned_df") is not None:
        _cdf = st.session_state["cleaned_df"]
        st.markdown("---")
        st.markdown("### データ概要")
        st.metric("ファイル", st.session_state.get("upload_name", "—"))
        _sc1, _sc2 = st.columns(2)
        _sc1.metric("行数", f"{len(_cdf):,}")
        _sc2.metric("列数", f"{len(_cdf.columns):,}")
        if "出願年" in _cdf.columns:
            _years = _cdf["出願年"].dropna()
            if len(_years) > 0:
                _sc3, _sc4 = st.columns(2)
                _sc3.metric("最古年", int(_years.min()))
                _sc4.metric("最新年", int(_years.max()))
        if "筆頭出願人" in _cdf.columns:
            st.metric("出願人数", f"{_cdf['筆頭出願人'].nunique():,}")

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
    ("ipc_level", "subclass"),
    ("classification", "IPC"),
    ("fi_level", "subclass"),
    ("fterm_level", "theme"),
    ("fterm_col_name", ""),
    ("data_format", "unknown"),
]:
    if k not in st.session_state:
        st.session_state[k] = v


def _advance(step: int):
    st.session_state["step"] = step


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

    # サンプルデータ読み込み
    SAMPLE_PATH = Path(__file__).parent / "excel_sample" / "非水電解質電池.xlsx"
    sample_col, upload_col = st.columns([1, 2])
    if sample_col.button("📂 サンプルデータで試す", help="非水電解質電池の特許データ（約2,000件）をサンプルとして読み込みます"):
        sample_bytes = SAMPLE_PATH.read_bytes()
        try:
            from example_analysis import excel_to_dataframe as _etdf
            sample_df = _etdf(sample_bytes, sheet_name="データ")
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

    # アップロード済みファイルを DataFrame に読み込み & 列マッピング
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
                # Questel形式のとき列マッピングを自動設定
                if fmt == "questel":
                    cols_in_df = list(raw_df.columns)
                    auto_map = {}
                    for key, col_name in QUESTEL_COL_DEFAULTS.items():
                        auto_map[key] = col_name if col_name in cols_in_df else "（なし）"
                    st.session_state["column_mapping"] = auto_map
                else:
                    st.session_state["column_mapping"] = {}
            except ValueError as e:
                st.error(f"ファイルの読み込みに失敗しました: {e}")
                raw_df = None
            except Exception as e:
                st.error(f"ファイルの読み込みに失敗しました: {e}")
                raw_df = None
        else:
            raw_df = st.session_state["raw_df"]

    # データ形式バッジ
    if raw_df is not None:
        fmt = st.session_state.get("data_format", "unknown")
        _fmt_labels = {"questel": "🌐 Questel Orbit", "jplatpat": "🗾 J-PlatPat", "unknown": "❓ 不明"}
        _fmt_colors = {"questel": "#275f56", "jplatpat": "#1a4a8c", "unknown": "#888"}
        st.markdown(
            f'<span style="background:{_fmt_colors[fmt]};color:#fff;padding:2px 10px;border-radius:8px;font-size:.82rem;font-weight:700;">'
            f'{_fmt_labels[fmt]}</span> として認識しました。',
            unsafe_allow_html=True,
        )

    if raw_df is not None:
        st.markdown("#### 列マッピング")
        cols = list(raw_df.columns)
        col_map = st.session_state.get("column_mapping", {}) or {}

        def _guess(defaults):
            for d in defaults:
                if d in cols:
                    return d
            return cols[0] if cols else ""

        def _col_select(label: str, key: str, defaults, help_text: str = None):
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
        applicant_col = _col_select("出願人列", "applicant", [
            "更新出願人・権利者氏名", "出願人", "出願人名",
            "Current standardized assignees - inventors removed", "Current assignees",
        ], help_text="出願人・権利者名が格納されている列")
        date_col = _col_select("出願日列", "date", [
            "出願日", "公開日", "Earliest application date",
        ], help_text="出願日（YYYY-MM-DD形式）の列")
        num_col = _col_select("出願番号列", "number", [
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

    has_data = uploaded is not None or st.session_state.get("raw_df") is not None
    if st.button("前処理を実行", type="primary", key="run_clean", disabled=not has_data):
        if has_data:
            try:
                with st.spinner("前処理中..."):
                    raw_df = st.session_state.get("raw_df")
                    if raw_df is None and uploaded is not None:
                        raw_df = excel_to_dataframe(uploaded.getvalue(), sheet_name=sheet_data)
                        st.session_state["raw_df"] = raw_df
                    mapping_rows = st.session_state["name_mapping_rows"]
                    mapping = _editor_rows_to_dict(mapping_rows) if apply_name_mapping else {}
                    col_map = st.session_state.get("column_mapping", {})
                    fterm_col_clean = None if col_map.get("fterm") in (None, "（なし）") else col_map.get("fterm")
                    cleaned = clean_patent_dataframe(
                        raw_df,
                        name_mapping=mapping,
                        applicant_col=col_map.get("applicant", "更新出願人・権利者氏名"),
                        application_date_col=col_map.get("date", "出願日"),
                        ipc_col=col_map.get("ipc", "公報IPC"),
                        fi_col=None if col_map.get("fi") in (None, "（なし）") else col_map.get("fi", "公報FI"),
                        life_death_col=None if col_map.get("life") in (None, "（なし）") else col_map.get("life", "生死情報"),
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
                "IPC粒度",
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
                index=list(FI_LEVEL_OPTIONS.values()).index(st.session_state["fi_level"]) if st.session_state["fi_level"] in FI_LEVEL_OPTIONS.values() else 2,
                key="fi_level_select",
                help="セクション(H) < クラス(H01) < サブクラス(H01M) < メイングループ(H01M10) < サブグループ(H01M10/0525) < フルFI",
            )
            st.session_state["fi_level"] = FI_LEVEL_OPTIONS[fi_level_label]

        # Fターム粒度（Fterm列がある場合のみ表示）
        _fterm_col_name = st.session_state.get("fterm_col_name", "")
        if _fterm_col_name and st.session_state.get("cleaned_df") is not None and _fterm_col_name in st.session_state["cleaned_df"].columns:
            fterm_level_label = st.selectbox(
                "Fターム粒度",
                list(FTERM_LEVEL_OPTIONS.keys()),
                index=list(FTERM_LEVEL_OPTIONS.values()).index(st.session_state["fterm_level"]),
                key="fterm_level_select",
                help="テーマコード(5H029) / テーマ+観点(5H029AJ) / フルFターム(5H029AJ12)",
            )
            st.session_state["fterm_level"] = FTERM_LEVEL_OPTIONS[fterm_level_label]

        st.markdown("**実行する集計を選択:**")
        _sel_c1, _sel_c2 = st.columns(2)
        if _sel_c1.button("全選択", key="sel_all"):
            for k in ["t1","t2","t3","t4","t5","t6","t7","t8","t9","t10"]:
                st.session_state[k] = True
            st.rerun()
        if _sel_c2.button("全解除", key="sel_none"):
            for k in ["t1","t2","t3","t4","t5","t6","t7","t8","t9","t10"]:
                st.session_state[k] = False
            st.rerun()
        c1, c2 = st.columns(2)
        checks = {
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

        if st.button("集計を実行", type="primary", key="run_agg"):
            results = {}
            _classification = st.session_state.get("classification", "IPC")
            _ipc_level = st.session_state["ipc_level"]
            _fi_level = st.session_state.get("fi_level", "subclass")
            _active_level = _ipc_level if _classification == "IPC" else _fi_level
            col_map = st.session_state.get("column_mapping", {})
            _fi_col_name = col_map.get("fi", "公報FI") if col_map.get("fi") not in (None, "（なし）") else "公報FI"
            _active_ipc_col = COL_IPC if _classification == "IPC" else _fi_col_name
            with st.spinner("集計中..."):
                if checks["出願件数推移"]:
                    results["出願件数推移"] = cached_application_trend(cleaned_df)
                if checks["特許分類増減率"]:
                    results["特許分類増減率"] = cached_ipc_growth(cleaned_df, base_year, yr_range, _active_level, _active_ipc_col)
                if checks["特許分類集計"]:
                    results["特許分類集計"] = cached_ipc_summary(cleaned_df)
                if checks["筆頭分類メイングループ"]:
                    results["筆頭分類メイングループ"] = cached_ipc_main_group(cleaned_df)
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
            _mc1, _mc2, _mc3 = st.columns(3)
            _mc1.metric("集計項目数", len(agg))
            if "筆頭出願人件数" in agg and agg["筆頭出願人件数"] is not None:
                _mc2.metric("出願人数", len(agg["筆頭出願人件数"]))
            if "特許分類増減率" in agg and agg["特許分類増減率"] is not None:
                _mc3.metric("分類数", len(agg["特許分類増減率"]))
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
    agg = st.session_state["agg_results"]
    cleaned_df = st.session_state["cleaned_df"]
    render_step3(agg, cleaned_df)

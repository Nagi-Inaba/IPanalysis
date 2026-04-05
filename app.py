# -*- coding: utf-8 -*-
"""IP Analysis Studio -- Streamlit Web アプリ メインエントリポイント。"""
from __future__ import annotations

import streamlit as st

from charts import render_step3
from aggregation import render_step2
from data_processing import render_step1
from example_analysis import DEFAULT_NAME_MAPPING_ROWS
from sidebar import render_sidebar
from styles import APP_CSS, HERO_HTML

# ==================== Page Config ====================
st.set_page_config(page_title="IP Analysis Studio", page_icon="\U0001f4ca", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)
st.markdown(HERO_HTML, unsafe_allow_html=True)

# ==================== Sidebar ====================
render_sidebar()

# ==================== Session State ====================
_DEFAULTS = [
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
]
for k, v in _DEFAULTS:
    if k not in st.session_state:
        st.session_state[k] = v


# ==================== Progress Bar ====================
step = st.session_state["step"]
cols = st.columns(3)
labels = ["Step 1: データ前処理", "Step 2: 集計", "Step 3: グラフ作成"]
for i, (c, lbl) in enumerate(zip(cols, labels), 1):
    if i < step:
        c.markdown(f"<span class='step-done'>\u2714 {lbl}</span>", unsafe_allow_html=True)
    elif i == step:
        c.markdown(f"<span class='step-current'>\u25cf {lbl}</span>", unsafe_allow_html=True)
    else:
        c.markdown(f"<span class='step-pending'>\u25cb {lbl}</span>", unsafe_allow_html=True)

st.divider()

# ==================== Step 1: 前処理 ====================
if step >= 1:
    render_step1()

# ==================== Step 2: 集計 ====================
if step >= 2 and st.session_state["cleaned_df"] is not None:
    render_step2()

# ==================== Step 3: グラフ作成 ====================
if step >= 3 and st.session_state.get("agg_results"):
    agg = st.session_state["agg_results"]
    cleaned_df = st.session_state["cleaned_df"]
    render_step3(agg, cleaned_df)

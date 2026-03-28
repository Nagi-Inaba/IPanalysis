# -*- coding: utf-8 -*-
"""Streamlit キャッシュ付き集計ラッパー関数。"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from example_analysis import (
    COL_IPC,
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
)


@st.cache_data
def cached_application_trend(df: pd.DataFrame) -> pd.DataFrame:
    return analysis_application_trend(df)


@st.cache_data
def cached_ipc_growth(df: pd.DataFrame, base_year: int, yr_range: int, ipc_level: str = "subclass", ipc_col_name: str = COL_IPC) -> pd.DataFrame:
    return analysis_ipc_growth(df, base_year, yr_range, ipc_col=ipc_col_name, ipc_level=ipc_level)


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


# ===================== 高度な分析（analysis_advanced） =====================

from analysis_advanced import (
    analysis_applicant_concentration,
    analysis_ipc_cooccurrence,
    analysis_technology_lifecycle,
)


@st.cache_data
def cached_technology_lifecycle(
    df: pd.DataFrame, ipc_col: str, top_n: int = 20
) -> pd.DataFrame:
    return analysis_technology_lifecycle(df, ipc_col=ipc_col, top_n=top_n)


@st.cache_data
def cached_ipc_cooccurrence(
    df: pd.DataFrame, ipc_col: str, ipc_level: str = "subclass", top_n: int = 30
) -> pd.DataFrame:
    return analysis_ipc_cooccurrence(
        df, ipc_col=ipc_col, ipc_level=ipc_level, top_n=top_n
    )


@st.cache_data
def cached_applicant_concentration(
    df: pd.DataFrame, ipc_col: str, min_applications: int = 10
) -> pd.DataFrame:
    return analysis_applicant_concentration(
        df, ipc_col=ipc_col, min_applications=min_applications
    )

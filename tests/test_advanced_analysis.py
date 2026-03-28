# -*- coding: utf-8 -*-
"""analysis_advanced.py のユニットテスト。"""
import pandas as pd
import pytest

from analysis_advanced import (
    analysis_technology_lifecycle,
    analysis_ipc_cooccurrence,
    analysis_applicant_concentration,
)


# --------- fixtures ---------

@pytest.fixture
def lifecycle_df():
    """技術ライフサイクル分析用データ: 複数IPCと複数年"""
    rows = []
    # H01M: 2010-2022でピーク2018、直近減少 → 成熟期 or 衰退期
    for y in range(2010, 2023):
        count = max(1, 10 - abs(y - 2018))
        rows.extend([{"筆頭IPCサブクラス": "H01M", "出願年": y}] * count)
    # B60L: 2018-2022で急増 → 成長期
    for y in range(2018, 2023):
        count = y - 2017
        rows.extend([{"筆頭IPCサブクラス": "B60L", "出願年": y}] * count)
    # G06F: 1件のみ → 導入期
    rows.append({"筆頭IPCサブクラス": "G06F", "出願年": 2020})
    return pd.DataFrame(rows)


@pytest.fixture
def cooccurrence_df():
    """共起分析用データ: 1出願に複数IPCコード"""
    return pd.DataFrame({
        "公報IPC": [
            "H01M50/10,B60L11/18",
            "H01M50/10,F02D41/00",
            "B60L11/18,H01M50/10",
            "G06F17/00",
            "H01M50/10",
        ],
        "出願年": [2020, 2020, 2021, 2021, 2022],
    })


@pytest.fixture
def concentration_df():
    """技術集中度分析用データ"""
    rows = []
    # 集中型: A社はH01Mに15件のみ
    rows.extend([{"筆頭出願人": "A社", "筆頭IPCサブクラス": "H01M"}] * 15)
    # 多角化型: B社は3分類に均等
    for ipc in ["H01M", "B60L", "G06F"]:
        rows.extend([{"筆頭出願人": "B社", "筆頭IPCサブクラス": ipc}] * 5)
    # 少数: C社は2件のみ（min_applications=10でフィルタ）
    rows.extend([{"筆頭出願人": "C社", "筆頭IPCサブクラス": "H01M"}] * 2)
    return pd.DataFrame(rows)


# --------- technology_lifecycle ---------

def test_lifecycle_stages(lifecycle_df):
    """4ステージのいずれかが正しく判定されること"""
    result = analysis_technology_lifecycle(lifecycle_df, ipc_col="筆頭IPCサブクラス")
    assert not result.empty
    valid_stages = {"導入期", "成長期", "成熟期", "衰退期"}
    assert set(result["ステージ"]).issubset(valid_stages)


def test_lifecycle_columns(lifecycle_df):
    """返り値のカラムが正しいこと"""
    result = analysis_technology_lifecycle(lifecycle_df, ipc_col="筆頭IPCサブクラス")
    expected_cols = {"分類", "ステージ", "ピーク年", "成長率", "総出願件数"}
    assert set(result.columns) == expected_cols


def test_lifecycle_empty():
    """空データで空DataFrameを返すこと"""
    df = pd.DataFrame({"other": [1, 2]})
    result = analysis_technology_lifecycle(df, ipc_col="筆頭IPCサブクラス")
    assert result.empty


def test_lifecycle_top_n(lifecycle_df):
    """top_nで件数が制限されること"""
    result = analysis_technology_lifecycle(lifecycle_df, ipc_col="筆頭IPCサブクラス", top_n=2)
    assert len(result) <= 2


# --------- ipc_cooccurrence ---------

def test_cooccurrence_basic(cooccurrence_df):
    """共起ペアが正しくカウントされること"""
    result = analysis_ipc_cooccurrence(cooccurrence_df, ipc_col="公報IPC", ipc_level="subclass")
    assert not result.empty
    assert "共起回数" in result.columns
    assert "Jaccard係数" in result.columns


def test_cooccurrence_columns(cooccurrence_df):
    """返り値のカラムが正しいこと"""
    result = analysis_ipc_cooccurrence(cooccurrence_df, ipc_col="公報IPC")
    expected_cols = {"分類A", "分類B", "共起回数", "Jaccard係数"}
    assert set(result.columns) == expected_cols


def test_cooccurrence_no_multi_ipc():
    """単一IPCのみのデータでは空DataFrameを返すこと"""
    df = pd.DataFrame({
        "公報IPC": ["H01M50/10", "B60L11/18", "G06F17/00"],
        "出願年": [2020, 2021, 2022],
    })
    result = analysis_ipc_cooccurrence(df, ipc_col="公報IPC")
    assert result.empty


def test_cooccurrence_jaccard_range(cooccurrence_df):
    """Jaccard係数が0-1の範囲であること"""
    result = analysis_ipc_cooccurrence(cooccurrence_df, ipc_col="公報IPC")
    if not result.empty:
        assert (result["Jaccard係数"] >= 0).all()
        assert (result["Jaccard係数"] <= 1).all()


# --------- applicant_concentration ---------

def test_concentration_hhi(concentration_df):
    """HHI値が正しく算出されること"""
    result = analysis_applicant_concentration(
        concentration_df, ipc_col="筆頭IPCサブクラス", min_applications=5,
    )
    assert not result.empty
    # A社: H01Mに100%集中 → HHI = 10000
    a_row = result[result["出願人"] == "A社"]
    assert len(a_row) == 1
    assert a_row["HHI"].values[0] == 10000


def test_concentration_type_classification(concentration_df):
    """タイプ分類が正しいこと"""
    result = analysis_applicant_concentration(
        concentration_df, ipc_col="筆頭IPCサブクラス", min_applications=5,
    )
    a_row = result[result["出願人"] == "A社"]
    assert a_row["タイプ"].values[0] == "集中型"
    # B社: 3分類に均等(各33.3%) → HHI ≈ 3333 → "集中型"
    b_row = result[result["出願人"] == "B社"]
    assert b_row["HHI"].values[0] < a_row["HHI"].values[0]  # A社(10000)よりは低い


def test_concentration_min_filter(concentration_df):
    """min_applicationsフィルタが機能すること"""
    result = analysis_applicant_concentration(
        concentration_df, ipc_col="筆頭IPCサブクラス", min_applications=10,
    )
    # C社は2件なのでフィルタされる
    assert "C社" not in result["出願人"].values


def test_concentration_columns(concentration_df):
    """返り値のカラムが正しいこと"""
    result = analysis_applicant_concentration(
        concentration_df, ipc_col="筆頭IPCサブクラス", min_applications=5,
    )
    expected_cols = {"出願人", "HHI", "主力分類", "分類数", "総出願件数", "タイプ"}
    assert set(result.columns) == expected_cols

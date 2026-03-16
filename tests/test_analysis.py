# -*- coding: utf-8 -*-
import pandas as pd
import pytest

from example_analysis import (
    analysis_application_trend,
    analysis_ipc_growth,
    analysis_applicant_count,
    analysis_applicant_growth,
    analysis_entry_exit,
    analysis_citation_map,
)


# --------- application_trend ---------

def test_application_trend_counts(trend_df):
    """年ごとの出願件数が正しく集計されること"""
    result = analysis_application_trend(trend_df)
    assert not result.empty
    row_2010 = result[result["出願年"] == 2010]
    assert row_2010["出願件数"].values[0] == 2
    row_2012 = result[result["出願年"] == 2012]
    assert row_2012["出願件数"].values[0] == 3


def test_application_trend_ignores_null(trend_df):
    """NaN の年は集計されないこと"""
    result = analysis_application_trend(trend_df)
    assert len(result) == 3  # 2010, 2011, 2012 の3年分のみ


def test_application_trend_missing_column():
    """year_col が存在しない場合は空 DataFrame を返すこと"""
    df = pd.DataFrame({"other": [1, 2]})
    result = analysis_application_trend(df)
    assert result.empty


def test_application_trend_sorted(trend_df):
    """結果が年の昇順であること"""
    result = analysis_application_trend(trend_df)
    years = result["出願年"].tolist()
    assert years == sorted(years)


# --------- ipc_growth ---------

def test_ipc_growth_before_after(ipc_growth_df):
    """before/after カウントが正しいこと"""
    result = analysis_ipc_growth(ipc_growth_df, target_year=2015, year_range=10, ipc_level="subgroup")
    assert not result.empty
    h01m = result[result["IPC"] == "H01M50/10"]
    assert len(h01m) == 1
    assert h01m["before_count"].values[0] == 2  # 2005, 2006
    assert h01m["after_count"].values[0] == 1   # 2016


def test_ipc_growth_zero_division():
    """出願件数ゼロ時にゼロ除算が起きないこと（pct_change = 0.0）"""
    df = pd.DataFrame({"公報IPC": ["H01M"], "出願年": [2020]})
    result = analysis_ipc_growth(df, target_year=2015, year_range=5)
    # after only → before=0, total>0, pct_change_10 != error
    assert not result.empty
    assert result["pct_change_10"].isna().sum() == 0


def test_ipc_growth_missing_columns():
    """必要列がない場合は空 DataFrame"""
    df = pd.DataFrame({"dummy": [1, 2]})
    result = analysis_ipc_growth(df, target_year=2015)
    assert result.empty


def test_ipc_growth_multi_ipc_per_row():
    """1行に複数IPCがある場合、それぞれカウントされること"""
    df = pd.DataFrame({
        "公報IPC": ["H01M,F02D"],
        "出願年": [2005],
    })
    result = analysis_ipc_growth(df, target_year=2015, year_range=10)
    assert len(result) == 2


# --------- applicant_count ---------

def test_applicant_count_range():
    """年範囲フィルタが正しく機能すること"""
    df = pd.DataFrame({
        "筆頭出願人": ["A", "A", "B", "C"],
        "出願年": [2010, 2015, 2010, 2020],
    })
    result = analysis_applicant_count(df, start_year=2010, end_year=2015)
    assert result[result["筆頭出願人"] == "A"]["出願件数"].values[0] == 2
    assert "C" not in result["筆頭出願人"].values


# --------- applicant_growth ---------

def test_applicant_growth_counts():
    """出願人増減率の集計が正しいこと"""
    df = pd.DataFrame({
        "更新出願人・権利者氏名": ["A", "A", "A", "B", "B"],
        "出願年": [2005, 2006, 2016, 2005, 2017],
    })
    result = analysis_applicant_growth(df, target_year=2015, year_range=10)
    assert not result.empty
    a = result[result["出願人"] == "A"]
    assert a["before_count"].values[0] == 2
    assert a["after_count"].values[0] == 1


def test_applicant_growth_no_zero_division():
    """total=0 のケースでゼロ除算しないこと"""
    # before=5, after=0 → total=5, pct_change_10 = (0-5)/5 = -1.0, no division by zero
    df = pd.DataFrame({
        "更新出願人・権利者氏名": ["A", "A", "A", "A", "A"],
        "出願年": [2005, 2006, 2007, 2008, 2009],  # すべて before 期間
    })
    result = analysis_applicant_growth(df, target_year=2015, year_range=10)
    assert not result.empty
    a = result[result["出願人"] == "A"]
    assert a["after_count"].values[0] == 0
    assert a["pct_change_10"].values[0] == pytest.approx(-1.0)


# --------- entry_exit ---------

def test_entry_exit_basic():
    """参入撤退チャートの first/last/count が正しいこと"""
    df = pd.DataFrame({
        "更新出願人・権利者氏名": ["A", "A", "B"],
        "出願年": [2010, 2018, 2015],
    })
    result = analysis_entry_exit(df)
    a = result[result["出願人名"] == "A"]
    assert a["最初の出願年"].values[0] == 2010
    assert a["直近出願年"].values[0] == 2018
    assert a["総出願件数"].values[0] == 2


def test_entry_exit_multiple_per_row():
    """1行に複数出願人がある場合、それぞれカウントされること"""
    df = pd.DataFrame({
        "更新出願人・権利者氏名": ["A,B"],
        "出願年": [2015],
    })
    result = analysis_entry_exit(df)
    assert len(result) == 2


# --------- citation_map ---------

def test_citation_map_basic():
    """被引用分析の基本集計が正しいこと"""
    df = pd.DataFrame({
        "筆頭出願人": ["A", "A", "B"],
        "被引用回数": ["引用:3", "引用:5", "引用:1"],
    })
    result = analysis_citation_map(df)
    a = result[result["出願人名"] == "A"]
    assert a["最大引用回数"].values[0] == 5
    assert a["合計引用回数"].values[0] == 8
    assert a["出願件数"].values[0] == 2


def test_citation_map_zero_citations():
    """引用ゼロの場合もクラッシュしないこと"""
    df = pd.DataFrame({
        "筆頭出願人": ["A"],
        "被引用回数": [None],
    })
    result = analysis_citation_map(df)
    assert not result.empty
    assert result.loc[0, "最大引用回数"] == 0

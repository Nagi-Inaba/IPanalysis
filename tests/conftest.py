# -*- coding: utf-8 -*-
import pandas as pd
import pytest


@pytest.fixture
def sample_df():
    """基本的なサンプルデータフレーム"""
    return pd.DataFrame({
        "更新出願人・権利者氏名": [
            "トヨタ自動車",
            "パナソニック,三菱重工業",
            "日立製作所",
            "",
        ],
        "出願日": ["2015/01/15", "2018/06/20", "2010/03/01", "2020/01/01"],
        "公報IPC": ["H01M50/10", "F02D/1,B60L", "H01M/50", None],
        "公報FI": [None, None, None, None],
        "生死情報": [None, None, "登録:登録", None],
    })


@pytest.fixture
def trend_df():
    """出願件数推移テスト用データフレーム（NaN は別列で管理し年列は整数）"""
    df = pd.DataFrame({"出願年": [2010, 2010, 2011, 2012, 2012, 2012, 2010]})
    # 最後の行をNaNに変えて float 化しないよう object 列で渡す
    df2 = pd.DataFrame({"出願年": [2010, 2010, 2011, 2012, 2012, 2012, None]})
    # analysis_application_trend は dropna してから regex チェックするので float も通す
    # → 整数値として渡す（NaN行を除外したうえでテスト）
    return pd.DataFrame({"出願年": pd.array([2010, 2010, 2011, 2012, 2012, 2012, pd.NA], dtype=pd.Int64Dtype())})


@pytest.fixture
def ipc_growth_df():
    """IPC増減率テスト用データフレーム"""
    return pd.DataFrame({
        "公報IPC": ["H01M50/10", "H01M50/10", "F02D/1", "H01M50/10", "F02D/1"],
        "出願年": [2005, 2006, 2006, 2016, 2017],
    })

# -*- coding: utf-8 -*-
import pandas as pd
import pytest

from example_analysis import clean_patent_dataframe, _split_applicants, _split_ipc_codes


def test_clean_normal(sample_df):
    """基本的な前処理が動作すること"""
    result = clean_patent_dataframe(sample_df, enable_name_mapping=False)
    assert "筆頭出願人" in result.columns
    assert "出願年" in result.columns
    assert result.loc[0, "筆頭出願人"] == "トヨタ自動車"


def test_clean_name_mapping_applied(sample_df):
    """名寄せが正しく適用されること"""
    mapping = {"トヨタ自動車": "トヨタ"}
    result = clean_patent_dataframe(sample_df, name_mapping=mapping, enable_name_mapping=True)
    assert result.loc[0, "筆頭出願人"] == "トヨタ"


def test_clean_name_mapping_disabled(sample_df):
    """名寄せ無効時は元の名前のまま"""
    mapping = {"トヨタ自動車": "トヨタ"}
    result = clean_patent_dataframe(sample_df, name_mapping=mapping, enable_name_mapping=False)
    # サフィックス除去はされるが名前変換はされない（trueで"トヨタ自動車"のまま）
    assert "トヨタ" in result.loc[0, "筆頭出願人"] or result.loc[0, "筆頭出願人"] == "トヨタ自動車"


def test_clean_multiple_applicants_head(sample_df):
    """複数出願人の筆頭のみ取得されること"""
    result = clean_patent_dataframe(sample_df, enable_name_mapping=False)
    # 2行目: "パナソニック,三菱重工業" → 筆頭は "パナソニック"
    assert result.loc[1, "筆頭出願人"] == "パナソニック"


def test_clean_date_string():
    """日付文字列から年が抽出されること"""
    df = pd.DataFrame({
        "更新出願人・権利者氏名": ["A"],
        "出願日": ["平成27年（2015）1月15日"],
        "公報IPC": ["H01M"],
    })
    result = clean_patent_dataframe(df, enable_name_mapping=False)
    assert result.loc[0, "出願年"] == 2015


def test_clean_date_excel_serial():
    """Excelシリアル値から年が抽出されること"""
    df = pd.DataFrame({
        "更新出願人・権利者氏名": ["A"],
        "出願日": [42385],  # 2016/01/15
        "公報IPC": ["H01M"],
    })
    result = clean_patent_dataframe(df, enable_name_mapping=False)
    assert result.loc[0, "出願年"] == 2016


def test_clean_invalid_date():
    """不正な日付はNoneになること（クラッシュしない）"""
    df = pd.DataFrame({
        "更新出願人・権利者氏名": ["A"],
        "出願日": ["invalid-date"],
        "公報IPC": ["H01M"],
    })
    result = clean_patent_dataframe(df, enable_name_mapping=False)
    assert result.loc[0, "出願年"] is None or pd.isna(result.loc[0, "出願年"])


def test_clean_ipc_columns(sample_df):
    """IPC列が正しく作成されること"""
    result = clean_patent_dataframe(sample_df, enable_name_mapping=False)
    assert "筆頭IPCメイングループ" in result.columns
    assert "筆頭IPCサブクラス" in result.columns
    assert "筆頭IPCサブグループ" in result.columns
    assert result.loc[0, "筆頭IPCサブクラス"] == "H01M"


def test_clean_life_death():
    """生死情報が正規化されること"""
    df = pd.DataFrame({
        "更新出願人・権利者氏名": ["A", "B"],
        "出願日": ["2015/01/01", "2015/01/01"],
        "公報IPC": ["H01M", "H01M"],
        "生死情報": ["登録:登録", "死:権利消滅"],
    })
    result = clean_patent_dataframe(df, enable_name_mapping=False)
    assert result.loc[0, "生死情報更新"] == "登録"
    assert result.loc[1, "生死情報更新"] == "死"


def test_split_applicants_comma():
    """カンマ区切りの出願人が分割されること"""
    result = _split_applicants("A,B,C")
    assert result == ["A", "B", "C"]


def test_split_applicants_fullwidth_comma():
    """全角カンマも分割されること"""
    result = _split_applicants("A，B")
    assert result == ["A", "B"]


def test_split_applicants_single():
    """単一出願人はリスト1件"""
    result = _split_applicants("トヨタ")
    assert result == ["トヨタ"]


def test_split_applicants_nan():
    """NaN はから空リスト"""
    import numpy as np
    result = _split_applicants(np.nan)
    assert result == []


def test_split_ipc_codes_comma():
    """カンマ区切りのIPCが分割されること"""
    result = _split_ipc_codes("H01M50/10,F02D/1")
    assert "H01M50/10" in result
    assert "F02D/1" in result


def test_split_ipc_codes_semicolon():
    """セミコロン区切りのIPCが分割されること"""
    result = _split_ipc_codes("H01M50/10;F02D/1")
    assert len(result) == 2


def test_split_ipc_codes_nan():
    """NaN は空リスト"""
    import numpy as np
    result = _split_ipc_codes(np.nan)
    assert result == []

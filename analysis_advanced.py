# -*- coding: utf-8 -*-
"""高度な特許分析関数（技術ライフサイクル・IPC共起・出願人集中度）。"""
from __future__ import annotations

from itertools import combinations
from typing import Optional

import pandas as pd

from example_analysis import (
    COL_LEAD_APPLICANT,
    COL_YEAR,
    _split_ipc_codes,
    _truncate_ipc,
)


# ===================== 技術ライフサイクル分析 =====================


def analysis_technology_lifecycle(
    df: pd.DataFrame,
    ipc_col: str = "筆頭IPCサブクラス",
    year_col: str = COL_YEAR,
    top_n: int = 20,
) -> pd.DataFrame:
    """技術ライフサイクル分析。

    各IPC分類の出願件数の経年変化から技術ライフサイクルステージを判定する。

    Returns DataFrame with columns:
      - 分類: 分類コード
      - ステージ: "導入期" / "成長期" / "成熟期" / "衰退期"
      - ピーク年: 出願件数が最大の年
      - 成長率: 直近5年のCAGR(%)
      - 総出願件数: 累計
    """
    if ipc_col not in df.columns or year_col not in df.columns:
        return pd.DataFrame(
            columns=["分類", "ステージ", "ピーク年", "成長率", "総出願件数"]
        )

    sub = df[[ipc_col, year_col]].dropna()
    sub = sub[sub[year_col].astype(str).str.match(r"^(19|20)\d{2}$", na=False)].copy()
    sub[year_col] = sub[year_col].astype(int)
    sub = sub[sub[ipc_col].astype(str).str.strip() != ""]

    if sub.empty:
        return pd.DataFrame(
            columns=["分類", "ステージ", "ピーク年", "成長率", "総出願件数"]
        )

    max_year = int(sub[year_col].max())

    # 分類ごとの年別出願件数
    grouped = sub.groupby([ipc_col, year_col]).size().reset_index(name="件数")

    # 総出願件数で下位20%の閾値を算出
    total_by_ipc = grouped.groupby(ipc_col)["件数"].sum()
    threshold_20pct = total_by_ipc.quantile(0.2)

    rows: list[dict] = []
    for ipc_code, grp in grouped.groupby(ipc_col):
        year_counts = grp.set_index(year_col)["件数"]
        total_count = int(year_counts.sum())
        peak_year = int(year_counts.idxmax())

        # 直近5年のCAGR算出
        cagr = _calc_cagr(year_counts, max_year, n_years=5)

        # ステージ判定
        stage = _classify_lifecycle_stage(
            peak_year=peak_year,
            max_year=max_year,
            cagr=cagr,
            total_count=total_count,
            threshold_20pct=threshold_20pct,
        )

        rows.append({
            "分類": ipc_code,
            "ステージ": stage,
            "ピーク年": peak_year,
            "成長率": round(cagr, 2),
            "総出願件数": total_count,
        })

    result = pd.DataFrame(rows)
    return (
        result.sort_values("総出願件数", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def _calc_cagr(
    year_counts: pd.Series, max_year: int, n_years: int = 5
) -> float:
    """直近n_years年のCAGR（年平均成長率）を算出する。

    開始年の出願件数が0の場合は単純増減率で代替する。
    データ不足時は0.0を返す。
    """
    start_year = max_year - n_years
    end_year = max_year

    start_count = int(year_counts.get(start_year, 0))
    end_count = int(year_counts.get(end_year, 0))

    if start_count > 0 and end_count > 0:
        return ((end_count / start_count) ** (1.0 / n_years) - 1.0) * 100.0
    if start_count == 0 and end_count > 0:
        # 開始年ゼロ → 大きな成長として扱う
        return 100.0
    if start_count > 0 and end_count == 0:
        return -100.0
    return 0.0


def _classify_lifecycle_stage(
    peak_year: int,
    max_year: int,
    cagr: float,
    total_count: int,
    threshold_20pct: float,
) -> str:
    """技術ライフサイクルステージを判定する。

    判定ルール:
      - 総出願件数が全体の下位20% → "導入期"
      - ピーク年が直近3年以内 かつ CAGR > 10% → "成長期"
      - ピーク年が直近3年以内 かつ CAGR <= 10% → "成熟期"
      - ピーク年が3年以上前 かつ CAGR >= 0% → "成熟期"
      - ピーク年が3年以上前 かつ CAGR < 0% → "衰退期"
    """
    if total_count <= threshold_20pct:
        return "導入期"

    years_since_peak = max_year - peak_year
    is_recent_peak = years_since_peak <= 3

    if is_recent_peak:
        return "成長期" if cagr > 10.0 else "成熟期"
    return "成熟期" if cagr >= 0.0 else "衰退期"


# ===================== IPC共起分析 =====================


def analysis_ipc_cooccurrence(
    df: pd.DataFrame,
    ipc_col: str = "公報IPC",
    ipc_level: str = "subclass",
    top_n: int = 30,
) -> pd.DataFrame:
    """IPC共起分析（技術融合マップ）。

    1つの出願に複数IPC/FIコードが付与されている場合の共起関係を分析する。

    Returns DataFrame with columns:
      - 分類A, 分類B: 共起ペア
      - 共起回数: 同一出願に両方含まれる回数
      - Jaccard係数: 共起の強さ
    """
    if ipc_col not in df.columns:
        return pd.DataFrame(
            columns=["分類A", "分類B", "共起回数", "Jaccard係数"]
        )

    ipc_series = df[ipc_col].dropna()
    if ipc_series.empty:
        return pd.DataFrame(
            columns=["分類A", "分類B", "共起回数", "Jaccard係数"]
        )

    # 各出願のIPCリストを取得し、指定粒度に切り詰め
    doc_ipc_sets: list[frozenset[str]] = []
    ipc_doc_count: dict[str, int] = {}

    for raw_value in ipc_series:
        codes = _split_ipc_codes(raw_value)
        truncated = set()
        for code in codes:
            t = _truncate_ipc(code, ipc_level)
            if t and isinstance(t, str) and t.strip():
                truncated.add(t.strip())

        if len(truncated) < 2:
            # 共起には2分類以上必要
            # ただしipc_doc_countには単独でもカウント
            for ipc in truncated:
                ipc_doc_count[ipc] = ipc_doc_count.get(ipc, 0) + 1
            continue

        frozen = frozenset(truncated)
        doc_ipc_sets.append(frozen)
        for ipc in truncated:
            ipc_doc_count[ipc] = ipc_doc_count.get(ipc, 0) + 1

    if not doc_ipc_sets:
        return pd.DataFrame(
            columns=["分類A", "分類B", "共起回数", "Jaccard係数"]
        )

    # 共起ペアのカウント
    pair_count: dict[tuple[str, str], int] = {}
    for ipc_set in doc_ipc_sets:
        sorted_codes = sorted(ipc_set)
        for a, b in combinations(sorted_codes, 2):
            key = (a, b)
            pair_count[key] = pair_count.get(key, 0) + 1

    if not pair_count:
        return pd.DataFrame(
            columns=["分類A", "分類B", "共起回数", "Jaccard係数"]
        )

    # Jaccard係数算出
    rows: list[dict] = []
    for (a, b), co_count in pair_count.items():
        count_a = ipc_doc_count.get(a, 0)
        count_b = ipc_doc_count.get(b, 0)
        union = count_a + count_b - co_count
        jaccard = co_count / union if union > 0 else 0.0
        rows.append({
            "分類A": a,
            "分類B": b,
            "共起回数": co_count,
            "Jaccard係数": round(jaccard, 4),
        })

    result = pd.DataFrame(rows)
    return (
        result.sort_values("共起回数", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


# ===================== 出願人技術集中度分析 =====================


def analysis_applicant_concentration(
    df: pd.DataFrame,
    applicant_col: Optional[str] = None,
    ipc_col: str = "筆頭IPCサブクラス",
    min_applications: int = 10,
) -> pd.DataFrame:
    """出願人技術集中度（HHI指数）分析。

    出願人ごとにIPC分類別の出願シェアからHHI（ハーフィンダール指数）を算出し、
    技術集中度を判定する。

    Returns DataFrame with columns:
      - 出願人: 出願人名
      - HHI: 技術集中度 (0-10000)
      - 主力分類: 最多出願のIPC
      - 分類数: 出願しているIPC分類の数
      - 総出願件数: 累計
      - タイプ: "集中型"(HHI>=2500) / "中程度"(1500-2500) / "多角化型"(<1500)
    """
    if applicant_col is None:
        applicant_col = COL_LEAD_APPLICANT

    if applicant_col not in df.columns or ipc_col not in df.columns:
        return pd.DataFrame(
            columns=["出願人", "HHI", "主力分類", "分類数", "総出願件数", "タイプ"]
        )

    sub = df[[applicant_col, ipc_col]].dropna()
    sub = sub[
        (sub[applicant_col].astype(str).str.strip() != "")
        & (sub[ipc_col].astype(str).str.strip() != "")
    ].copy()

    if sub.empty:
        return pd.DataFrame(
            columns=["出願人", "HHI", "主力分類", "分類数", "総出願件数", "タイプ"]
        )

    # 出願人 x IPC のクロス集計
    cross = sub.groupby([applicant_col, ipc_col]).size().reset_index(name="件数")
    applicant_totals = cross.groupby(applicant_col)["件数"].sum()

    # min_applications以上の出願人のみ
    qualified = applicant_totals[applicant_totals >= min_applications].index
    cross = cross[cross[applicant_col].isin(qualified)]

    if cross.empty:
        return pd.DataFrame(
            columns=["出願人", "HHI", "主力分類", "分類数", "総出願件数", "タイプ"]
        )

    rows: list[dict] = []
    for applicant, grp in cross.groupby(applicant_col):
        total = int(grp["件数"].sum())
        counts = grp.set_index(ipc_col)["件数"]

        # シェア%を算出してHHIを計算
        shares = (counts / total) * 100.0
        hhi = float((shares ** 2).sum())

        # 主力分類（最多出願のIPC）
        main_ipc = str(counts.idxmax())
        n_categories = len(counts)

        # タイプ判定
        concentration_type = _classify_concentration(hhi)

        rows.append({
            "出願人": applicant,
            "HHI": round(hhi, 1),
            "主力分類": main_ipc,
            "分類数": n_categories,
            "総出願件数": total,
            "タイプ": concentration_type,
        })

    result = pd.DataFrame(rows)
    return (
        result.sort_values("総出願件数", ascending=False)
        .reset_index(drop=True)
    )


def _classify_concentration(hhi: float) -> str:
    """HHI値から集中度タイプを判定する。

    - HHI >= 2500 → "集中型"
    - 1500 <= HHI < 2500 → "中程度"
    - HHI < 1500 → "多角化型"
    """
    if hhi >= 2500:
        return "集中型"
    if hhi >= 1500:
        return "中程度"
    return "多角化型"

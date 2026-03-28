# -*- coding: utf-8 -*-
"""IPC / FI / Fターム粒度の定数定義。"""
from __future__ import annotations

# IPC粒度
IPC_LEVEL_OPTIONS = {
    "セクション (例: H)": "section",
    "クラス (例: H01)": "class",
    "サブクラス (例: H01M)": "subclass",
    "メイングループ (例: H01M10)": "main_group",
    "サブグループ (例: H01M10/0525)": "subgroup",
}
IPC_LEVEL_COL = {
    "section":    "筆頭IPCセクション",
    "class":      "筆頭IPCクラス",
    "subclass":   "筆頭IPCサブクラス",
    "main_group": "筆頭IPCメイングループ",
    "subgroup":   "筆頭IPCサブグループ",
}

# FI粒度（IPC同様の5段階 + フルFI）
FI_LEVEL_OPTIONS = {
    "セクション (例: H)": "section",
    "クラス (例: H01)": "class",
    "サブクラス (例: H01M)": "subclass",
    "メイングループ (例: H01M10)": "main_group",
    "サブグループ (例: H01M10/0525)": "subgroup",
    "フルFI (展開記号含む)": "full",
}
FI_LEVEL_COL = {
    "section":    "筆頭FIセクション",
    "class":      "筆頭FIクラス",
    "subclass":   "筆頭FIサブクラス",
    "main_group": "筆頭FIメイングループ",
    "subgroup":   "筆頭FIサブグループ",
    "full":       "筆頭FIサブグループ",
}

# Fターム粒度
FTERM_LEVEL_OPTIONS = {
    "テーマコード (例: 5H029)": "theme",
    "テーマ＋観点 (例: 5H029AJ)": "viewpoint",
    "フルFターム (例: 5H029AJ12)": "full",
}

# グラフ高さ定数
CHART_HEIGHT_BUBBLE = 600      # バブルチャート (現在 500)
CHART_HEIGHT_LINE = 480        # 折れ線グラフ (現在 380)
CHART_HEIGHT_AREA = 480        # 積み上げ面グラフ (現在 400)
CHART_HEIGHT_HEATMAP = 480     # ヒートマップ (現在 400)
CHART_HEIGHT_NETWORK = 500     # ネットワーク (現在 400)
CHART_HEIGHT_BAR_PER_ITEM = 26 # 横棒グラフの1項目あたり (現在 22)
CHART_HEIGHT_BAR_MIN = 350     # 横棒グラフの最低高さ (現在 300)

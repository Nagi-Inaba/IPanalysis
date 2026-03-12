# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# ===================== 列名定数 =====================

COL_APPLICANT = "更新出願人・権利者氏名"
COL_DATE = "出願日"
COL_IPC = "公報IPC"
COL_YEAR = "出願年"
COL_LEAD_APPLICANT = "筆頭出願人"

# ===================== サフィックス / 名寄せ =====================

SUFFIX_CHARS = [
    "株式会社", "合同会社", "カブシキガイシャ", "カブシキガイシヤ", "有限会社",
    "有限公司", "(株)", "コーポレーション", "特定非営利活動法人", "（株）",
    "公立大学法人", "財団法人", "財團法人", "コムパニー", "インコーポレイテッド",
    "インコーポレーテッド", "エルエルシー", "独立行政法人", "ホールディングス",
    "ホールディング", "一般社団法人", "一般財団法人", "合資会社", "合名会社",
    "リミテッド", "エルティーディ", "アーゲー", "ホウルディング", "社会福祉法人",
    "国立大学法人", "国立研究開発法人", "国立研究開発機構", "公益財団法人",
    "カンパニイ", "インコ－ポレイテッド", "ゲーエムベーハー", "コーポレーシヨン",
    "社団法人", "コーポレイション", "有限責任公司", "学校法人", "公益社団法人",
    "オーガナイゼーション", "コーポレイシヨン", "コ－ポレ－シヨン", "カンパニー",
    "システムズ", "インク", "インスティテュート", " ", "　", "・", ".", "．",
    "、", "，", "▼", "▲",
]

_BUILTIN_NAME_MAPPING: Dict[str, str] = {
    "－": "ー", "—": "ー",
    "三菱重工エンジニアリング": "三菱重工業", "三菱パワー": "三菱重工業", "三菱日立パワーシステムズ": "三菱重工業", "三菱造船": "三菱重工業", "三菱重工パワーインダストリー": "三菱重工業",
    "三菱重工エンジンアンドターボチャージャ": "三菱重工業", "三菱重工マリンマシナリ": "三菱重工業", "三菱エフビーアールシステムズ": "三菱重工業", "三菱原子燃料": "三菱重工業", "三菱重工サーマル": "三菱重工業",
    "三菱重工航空エンジン": "三菱重工業", "三菱ロジスネクスト": "三菱重工業", "三菱重工交通建設エンジニアリング": "三菱重工業", "三菱重工パワー環境ソリューション": "三菱重工業", "三菱重工機械システム": "三菱重工業",
    "三菱重工サーマルシステムズ": "三菱重工業", "ＭＨＩＮＳエンジニアリング": "三菱重工業", "ＭＨＩ原子力研究開発": "三菱重工業", "ＭＨＩソリューションテクノロジーズ": "三菱重工業", "ＭＨＩパワーコントロールシステムズ": "三菱重工業", "ＭＨＩパワーエンジニアリング": "三菱重工業",
    "三菱日立パワー": "三菱重工業", "テクノ電子": "三菱重工業", "三菱ＦＢＲシステムズ": "三菱重工業", "ＭＨＩエアロスペースシステムズ": "三菱重工業", "中菱エンジニアリング": "三菱重工業", "ＭＨＩ下関エンジニアリング": "三菱重工業",
    "ＭＨＩＬＮＧ": "三菱重工業", "エムエイチアイさがみハイテック": "三菱重工業", "ニチユマシナリー": "三菱重工業", "ＭＨＩハセック": "三菱重工業", "ＭＨＩマリテック": "三菱重工業", "ＭＨＩエンジニアリング": "三菱重工業", "三菱重工環境化学エンジニアリング": "三菱重工業",
    "三菱重工冷熱": "三菱重工業", "三菱重工コンプレッサ": "三菱重工業", "三菱マヒンドラ農機": "三菱重工業", "三菱農機": "三菱重工業", "バブコツク日立": "三菱重工業",
    "三菱ケミカルエンジニアリング": "三菱ケミカル", "三菱ケミカルアグリドリーム": "三菱ケミカル", "三菱レイヨン": "三菱ケミカル", "三菱化学": "三菱ケミカル", "三菱化成": "三菱ケミカル", "三菱化成ビニル": "三菱ケミカル",
    "三菱鉱業セメント": "三菱マテリアル", "三菱電線工業": "三菱マテリアル", "三菱マテリアル電子化成": "三菱マテリアル", "三菱樹脂": "三菱ケミカル", "三菱ケミカルポリエステルフィルム": "三菱ケミカル",
    "三菱電機エンジニアリング": "三菱電機", "三菱油化": "三菱ケミカル", "三菱ケミカルビニル": "三菱ケミカル", "三菱ケミカルポリテツク": "三菱ケミカル", "三菱ケミカルポリテック": "三菱ケミカル",
    "パナソニックエコ": "パナソニック", "松下電器": "パナソニック", "パナソニック産業": "パナソニック", "パナソニック電工": "パナソニック", "三洋電機": "パナソニック", "パナソニックＥＶエナジー": "プライムアースＥＶエナジー",
    "松下電工": "パナソニック", "松下電器産業": "パナソニック", "松下電子": "パナソニック", "パナソニックＩＰマネジメント": "パナソニック", "パナソニックエナジー": "パナソニック",
    "新日本製鐵": "日本製鉄", "新日本製鉄": "日本製鉄", "新日鉄住金": "日本製鉄", "住友金属工業": "日本製鉄", "日新製鋼": "日本製鉄", "日本製鉄マテリアルズ": "日本製鉄", "新日鐵住金": "日本製鉄", "日鉄ケミカル＆マテリアル": "日本製鉄", "日鉄日本製鉄": "日本製鉄", "日鉄ステンレス": "日本製鉄",
    "東芝エネルギーシステムズ": "東芝", "東芝エネルギー": "東芝", "東芝テクニカルサービスインターナショナル": "東芝", "東芝セラミックス": "東芝", "東芝アイテック": "東芝", "東芝プラントシステム": "東芝",
    "東芝クライアントソリューション": "東芝", "東芝システムテクノロジー": "東芝", "東芝テック": "東芝", "東芝プラント建設": "東芝", "東芝電池": "東芝", "東芝情報システム": "東芝", "東芝デジタルソリューションズ": "東芝", "東芝インフラ": "東芝", "東芝ライテック": "東芝",
    "ＪＦＥスチール": "JFE", "ＪＦＥエンジニアリング": "JFE", "ＪＦＥ建材": "JFE", "ＪＦＥケミカル": "JFE", "ＪＦＥテクノリサーチ": "JFE",
    "ＩＨＩプラント": "ＩＨＩ", "ＩＨＩアグリテック": "ＩＨＩ", "ＩＨＩエアロスペース": "ＩＨＩ", "石川島芝浦機械": "ＩＨＩ",
    "旭化成イーマテリアルズ": "旭化成", "旭化成ホームズ": "旭化成", "旭化成メディカル": "旭化成", "旭化成せんい": "旭化成", "旭化成エレクトロニクス": "旭化成", "旭化成ケミカルズ": "旭化成", "セルガード": "旭化成",
    "三井Ｅ＆Ｓプラントエンジニアリング": "三井Ｅ＆Ｓ",
    "ゼネラルエレクトリックテクノロジーゲゼルシャフトミットベシュレンクテルハフツング": "ゼネラルエレクトリック",
    "エクソンモービルリサーチアンドエンジニアリング": "エクソンモービル", "エクソンモービルアップストリームリサーチ": "エクソンモービル",
    "日揮グローバル": "日揮", "日揮触媒化成": "日揮",
    "豊田中央研究所": "トヨタ", "トヨタ自動車": "トヨタ", "豊田自動織機": "トヨタ", "トヨタモーターエンジニアリングアンドマニュファクチャリングノースアメリカインコーポレイティド": "トヨタ",
    "ヤンマー農機": "ヤンマー", "ヤンマーパワーテクノロジー": "ヤンマー", "ヤンマーエンジニアリング": "ヤンマー", "ヤンマーアグリ": "ヤンマー", "ヤンマーグリーンシステム": "ヤンマー", "ヤンマーディーゼル": "ヤンマー", "ヤンマーデイーゼル": "ヤンマー", "ヤンマーノウキ": "ヤンマー",
    "神崎高級工機製作所": "ヤンマー", "セイレイ工業": "ヤンマー",
    "ニコンビジネスサービス": "ニコン",
    "ユ—シン": "ユーシン", "ユ－シン": "ユーシン",
    "リコ－": "リコー",
    "ロ－ベルトボツシユゲゼルシヤフトミツトベシユレンクテルハフツング": "ボッシュ", "ボッシュオートモーティブシステム": "ボッシュ", "ローベルトボツシユゲゼルシヤフトミツトベシユレンクテルハフツング": "ボッシュ", "ローベルトボッシュゲゼルシャフトミットベシュレンクテルハフツング": "ボッシュ",
    "ＮＥＣエンベデッドプロダクツ": "ＮＥＣ", "ＮＥＣシステムテクノロジー": "ＮＥＣ", "ＮＥＣスペーステクノロジー": "ＮＥＣ", "ＮＥＣソリューションイノベータ": "ＮＥＣ", "ＮＥＣプラットフォームズ": "ＮＥＣ", "ＮＥＣモバイルコミュニケーションズ": "ＮＥＣ", "日本電気": "ＮＥＣ",
    "キヤノンマーケティングジャパン": "キヤノン", "キヤノンオプトロン": "キヤノン",
    "クボタケミックス": "クボタ", "クボタ機械サービス": "クボタ", "クボタ鉄工": "クボタ", "久保田鉄工": "クボタ",
    "シヤ－プ": "シャープ",
    "住友化学工業": "住友化学",
    "トプコンポジショニング": "トプコン",
    "ビーエーエスエフアグロトレードマークス": "BASF", "ビーエーエスエフアグロベーブイ": "BASF", "ビーエーエスエフソシエタスヨーロピア": "BASF", "ベーアーエスエフアグロトレードマークス": "BASF", "ベーアーエスエフエスエー": "BASF", "ベーアーエスエフフューエルセル": "BASF", "ビーエーエスエフ": "BASF",
    "ヒタチエナジーリミテッド": "日立",
    "マルコンデンシ": "マルコン電子",
    "日立エンジニアリング": "日立", "日立ケーイー": "日立", "日立ソリューションズ": "日立", "日立ソリューションズ東日本": "日立", "日立チャネルソリューションズ": "日立", "日立ハイテクフィールディング": "日立", "日立パワーソリューションズ": "日立", "日立プラントテクノロジー": "日立", "日立産機システム": "日立", "日立照明": "日立", "日立情報通信エンジニアリング": "日立", "日立製作所": "日立", "日立冷熱": "日立", "日立東日本": "日立",
    "日立オートモティブ": "日立Ａｓｔｅｍｏ", "日信工業": "日立Ａｓｔｅｍｏ",
    "日立金属": "プロテリアル", "日立電線": "プロテリアル",
    "ソニーセミコンダクタソリューションズ": "ソニー", "ソニーグループ": "ソニー",
    "富士重工業": "ＳＵＢＡＲＵ",
    "立石電機": "オムロン",
    "マルコン電子": "日本ケミコン",
    "佐竹製作所": "サタケ",
    "UBE": "宇部興産", "ＵＢＥ": "宇部興産",
    "日本電池": "ユアサ", "ジーエスユアサ": "ユアサ", "ジーエスユアサインダストリー": "ユアサ", "ＧＳユアサインダストリー": "ユアサ", "ユアサ開発": "ユアサ", "ＧＳユアサ": "ユアサ", "ユアサインダストリー": "ユアサ", "ユアサコーポレーション": "ユアサ", "ユアサコーポレーシヨン": "ユアサ",
    "エルジーエナジーソリューション": "LG", "エルジーケム": "LG", "エルジーケムエルティーディ": "LG", "エルジーケミカル": "LG", "エルジーケーブル": "LG",
    "日本曹達": "トクヤマ", "徳山曹達": "トクヤマ",
    "東洋曹達工業": "東ソー", "東ソーエフテック": "東ソー", "東ソーファインケム": "東ソー",
    "ＴＯＰＰＡＮ": "凸版印刷",
    "エンビジョンＡＥＳＣジャパン": "AESC", "ＡＥＳＣジャパン": "AESC", "エンビジョンＡＥＳＣエナジーデバイス": "AESC", "ＮＥＣエナジーデバイス": "AESC",
    "三星電子": "サムスン", "三星エスディアイ": "サムスン", "三星電機": "サムスン", "サムスンエレクトロニクス": "サムスン", "サムスン日本研究所": "サムスン", "サムスンエスディアイ": "サムスン",
    "レゾナックパッケージング": "レゾナック", "日立化成": "レゾナック", "昭和電工パッケージング": "レゾナック", "昭和電工マテリアルズ": "レゾナック", "昭和電工": "レゾナック", "日立粉末冶金": "レゾナック", "日立化成工業": "レゾナック", "新神戸電機": "レゾナック",
    "ルノーエスアエス": "ルノー",
    "日立マクセル": "マクセル", "日立マクセルエナジー": "マクセル", "日立ハイテク": "マクセル", "日立ハイテクファイン": "マクセル", "日立ハイテクサイエンス": "マクセル", "日立ハイテクノロジーズ": "マクセル", "マクセルエナジー": "マクセル",
    "日立ビークルエナジー": "ビークルエナジージャパン",
    "ＦＤＫ鳥取": "ＦＤＫ", "ＦＤＫトワイセル": "ＦＤＫ",
    "寧徳時代新能源科技股分": "ＣＡＴＬ", "寧徳新能源科技": "ＣＡＴＬ", "香港時代新能源科技": "ＣＡＴＬ",
    "日新電機": "住友電気工業", "富山住友電工": "住友電気工業", "住友電工ファインポリマー": "住友電気工業", "住友精化": "住友化学", "住友住友ベークライト": "住友化学",
    "東レバッテリーセパレータフィルム": "東レ", "東レフィルム加工": "東レ", "トーレアドバンストマテリアルズコリア": "東レ", "東レ韓国": "東レ", "東レ東燃機能膜合同会社": "東レ", "東レ東燃機能膜": "東レ", "東レファインケミカル": "東レ", "東レコーテックス": "東レ",
    "比亜迪股分": "ＢＹＤ", "ビーワイディー": "ＢＹＤ",
    "サイオンパワーコーポレイション": "シオンパワー", "サイオンパワー": "シオンパワー",
    "リチウムエナジーアンドパワーゲゼルシャフトミットベシュレンクテルハフッングウントコンパニーコマンディトゲゼルシャフト": "リチウムエナジーアンドパワー", "リチウムエナジージャパン": "リチウムエナジーアンドパワー", "リチウムエナジーアンドパワーウントコーカーゲー": "リチウムエナジーアンドパワー",
    "旭硝子": "ＡＧＣ", "ＡＧＣセイミケミカル": "ＡＧＣ",
    "東洋製罐グループ": "東洋製罐",
    "ポスコケミカル": "ポスコ", "ポスコインコーポレーティッド": "ポスコ",
    "ＴｅｒａＷａｔｔＴｅｃｈｎｏｌｏｇｙ": "テラワットテクノロジー",
    "華為技術": "ファーウェイ",
    "テーデーカーエレクトロニクスアーゲー": "ＴＤＫ",
    "東洋紡フイルムソリューション": "東洋紡", "東洋紡績": "東洋紡",
    "クアンタムスケイプバテリー": "クアンタム", "クアンタムスケープバッテリー": "クアンタム",
    "イーアイデュポンドウヌムールアンド": "デュポン", "デュポンセイフティーアンドコンストラクション": "デュポン", "デュポンセーフティーアンドコンストラクション": "デュポン",
    "ソルベイスペシャルティポリマーズイタリーエスピーエー": "ソルベイ", "ソルベイスペシャルティポリマーズユーエスエー": "ソルベイ", "ソルベイアセトウ": "ソルベイ", "ソルヴェイ（ソシエテアノニム）": "ソルベイ", "ソルヴェイ": "ソルベイ",
    "ＪＸ金属サーキュラーソリューションズ": "ＥＮＥＯＳ", "ＪＸＴＧエネルギー": "ＥＮＥＯＳ", "ＪＸ日鉱日石エネルギー": "ＥＮＥＯＳ", "ＥＮＥＯＳマテリアル": "ＥＮＥＯＳ", "東燃ゼネラル石油": "ＥＮＥＯＳ", "ＪＸエネルギー": "ＥＮＥＯＳ", "東燃化学": "ＥＮＥＯＳ", "ＪＸ金属": "ＥＮＥＯＳ", "新日本石油": "ＥＮＥＯＳ", "ＪＸ日鉱日石金属": "ＥＮＥＯＳ",
    "帝人化成": "帝人", "帝人フロンティア": "帝人", "帝人フィルム": "帝人", "帝人ファイバー": "帝人", "帝人テクノプロダクツ": "帝人", "帝人コードレ": "帝人", "帝人知的財産センター": "帝人",
    "富士ゼロックス": "富士フイルム", "富士フイルムビジネスイノベーション": "富士フイルム", "富士フイルム和光純薬": "富士フイルム",
    "ＪＮＣ石油化学": "ＪＮＣ",
    "スリーエム": "３Ｍ", "スリーエムイノベイティブプロパティズ": "３Ｍ", "３Ｍイノベイティブプロパティズ": "３Ｍ",
    "シェンズェンカプチェムテクノロジー": "新宙邦科技", "深せん新宙邦科技股ふん": "新宙邦科技",
    "ハイドローケベック": "ハイドロケベック", "イドローケベック": "ハイドロケベック", "ハイドローケベツク": "ハイドロケベック",
    "アーケマ": "アルケマ", "アルケマフランス": "アルケマ",
    "エイ１２３ライアビリティ": "万向集団", "エー１２３": "万向集団", "エー１２３ライアビリティ": "万向集団",
    "ソシエテデプロデユイネツスルソシエテアノニム": "ネスレ", "ソシエテデプロデュイネスレエスアー": "ネスレ", "ソシエテデプロデユイネツスレソシエテアノニム": "ネスレ",
    "ユニリーバーアイピーベーフェー": "ユニリーバ", "ユニリーバーナームローゼベンノートシヤープ": "ユニリーバ", "ユニリーバーナームローゼベンノートシャープ": "ユニリーバ",
    "ザプロクターエンドギャンブル": "Ｐ＆Ｇ", "ザプロクターエンドギヤンブルカンパニー": "Ｐ＆Ｇ",
    "ジェイエスアール": "ＪＳＲ",
    "バイエルクロップサイエンス": "バイエル", "バイエルインテレクチュアルプロパティゲゼルシャフトミットベシュレンクテルハフツング": "バイエル", "バイエルクロップサイエンスエルピー": "バイエル", "バイエルクロップサイエンスアクチェンゲゼルシャフト": "バイエル", "バイエルビジネスサービシズゲゼルシャフトミットベシュレンクテルハフツング": "バイエル",
    "バイエルアクチエンゲゼルシャフト": "バイエル",
    "騰訊科技（深セン）": "テンセント", "テンセントテクノロジー（シェンジェン）": "テンセント", "シェンジェンテンセントコンピューター": "テンセント", "テンセントアメリカ": "テンセント", "深セン市騰訊計算机系統": "テンセント",
    "インターナショナルビジネスマシーンズ": "IBM",
    "グーグル": "Google",
    "日本電信電話": "NTT", "エヌティーティーリサーチ": "NTT",
    "ベイジンバイドゥネットコムサイエンステクノロジー": "バイドゥ",
    "マイクロソフトテクノロジーライセンシング": "Microsoft",
    "アイキューエムフィンランドオイ": "IQM quantum", "アイキューエムフィンランドオーワイ": "IQM quantum",
    "アリババグループ": "アリババ", "アリババイノベーションプライベート": "アリババ", "アリババ（チャイナ）": "アリババ",
    "イオンキュークアンタムカナダ": "IonQ", "イオンキュー": "IonQ",
    "ワンキュービーインフォメーションテクノロジーズ": "1QBit", "１キュービーインフォメーションテクノロジーズ": "1QBit",
    "ディーーウェイブ": "D-Wave",
    "イェールユニバーシティー": "イェール大学",
    "ユニバーシティオブメリーランドカレッジパーク": "メリーランド大学",
    "プレジデントアンドフェローズオブハーバードカレッジ": "ハーバード大学",
    "オックスフォードユニバーシティイノベーションリミティド": "オックスフォード大学", "オックスフォードユニヴァーシティイノヴェーション": "オックスフォード大学", "オックスフォードユニバーシティイノベーション": "オックスフォード大学",
    "科学技術振興機構": "JST",
}


def _load_name_mapping_json() -> Dict[str, str]:
    """name_mapping.json を読み込む。失敗時はビルトイン辞書を返す。"""
    json_path = Path(__file__).parent / "name_mapping.json"
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _BUILTIN_NAME_MAPPING


DEFAULT_NAME_MAPPING: Dict[str, str] = _load_name_mapping_json()


def _mapping_to_editor_rows(d: Dict[str, str]) -> List[Dict[str, str]]:
    return [{"元の名前": k, "名寄せ後": v} for k, v in d.items() if k != v]


def _editor_rows_to_dict(rows: List[Dict[str, str]]) -> Dict[str, str]:
    d: Dict[str, str] = {}
    for r in rows:
        orig = (r.get("元の名前") or "").strip()
        new = (r.get("名寄せ後") or "").strip()
        if orig and new:
            d[orig] = new
    return d


DEFAULT_NAME_MAPPING_ROWS = _mapping_to_editor_rows(DEFAULT_NAME_MAPPING)


def _apply_suffix_removal(s: str) -> str:
    if not isinstance(s, str) or not s:
        return s
    out = s
    for suffix in SUFFIX_CHARS:
        out = out.replace(suffix, "")
    return out.strip()


def _apply_name_mapping(s: str, mapping: Dict[str, str]) -> str:
    if not isinstance(s, str) or not s:
        return s
    out = s
    for old_name, new_name in mapping.items():
        if old_name in out:
            out = out.replace(old_name, new_name)
    return out


def clean_patent_dataframe(
    df: pd.DataFrame,
    name_mapping: Optional[Dict[str, str]] = None,
    applicant_col: str = COL_APPLICANT,
    application_date_col: str = COL_DATE,
    ipc_col: str = COL_IPC,
    fi_col: str = "公報FI",
    life_death_col: str = "生死情報",
    enable_name_mapping: bool = True,
) -> pd.DataFrame:
    out = df.copy()
    mapping = name_mapping if name_mapping is not None else DEFAULT_NAME_MAPPING

    if applicant_col in out.columns:
        col = out[applicant_col].astype(str).fillna("")
        if enable_name_mapping and mapping:
            col = col.apply(_apply_suffix_removal)
            col = col.apply(lambda x: _apply_name_mapping(x, mapping))
        out[applicant_col] = col

        def head_applicant(v):
            if pd.isna(v) or v == "":
                return ""
            s = str(v).replace("，", ",")
            parts = [p.strip() for p in s.split(",") if p.strip()]
            return parts[0] if parts else str(v)
        out[COL_LEAD_APPLICANT] = out[applicant_col].apply(head_applicant)

    if application_date_col in out.columns:
        def to_year(v):
            if pd.isna(v):
                return None
            if isinstance(v, (datetime, pd.Timestamp)):
                return v.year
            if isinstance(v, (int, float)):
                try:
                    base = datetime(1899, 12, 30)
                    d = base + timedelta(days=int(v))
                    return d.year
                except (ValueError, OverflowError):
                    return None
            m = re.search(r"(19|20)\d{2}", str(v))
            return int(m.group(0)) if m else None
        out[COL_YEAR] = out[application_date_col].apply(to_year)

    if ipc_col in out.columns:
        def ipc_main(v):
            if pd.isna(v) or not isinstance(v, str):
                return ""
            return v.split("/")[0].strip() if "/" in v else v.strip()
        def ipc_sub_class(v):
            if pd.isna(v) or not isinstance(v, str):
                return ""
            return v[:4].strip()
        def ipc_sub_group(v):
            if pd.isna(v) or not isinstance(v, str):
                return ""
            if "," in v:
                return v.split(",")[0].strip()
            if "＠" in v:
                return v.split("＠")[0].strip()
            return v.strip()
        out["筆頭IPCメイングループ"] = out[ipc_col].apply(ipc_main)
        out["筆頭IPCサブクラス"] = out[ipc_col].apply(ipc_sub_class)
        out["筆頭IPCサブグループ"] = out[ipc_col].apply(ipc_sub_group)

    if fi_col in out.columns:
        def fi_main(v):
            if pd.isna(v) or not isinstance(v, str):
                return ""
            return v.split("/")[0].strip() if "/" in v else v.strip()
        def fi_sub_class(v):
            if pd.isna(v) or not isinstance(v, str):
                return ""
            return v[:4].strip()
        def fi_sub_group(v):
            if pd.isna(v) or not isinstance(v, str):
                return ""
            if "," in v:
                return v.split(",")[0].strip()
            if "＠" in v:
                return v.split("＠")[0].strip()
            return v.strip()
        out["筆頭FIメイングループ"] = out[fi_col].apply(fi_main)
        out["筆頭FIサブクラス"] = out[fi_col].apply(fi_sub_class)
        out["筆頭FIサブグループ"] = out[fi_col].apply(fi_sub_group)

    if life_death_col in out.columns:
        def life_death_updated(v):
            if pd.isna(v) or not isinstance(v, str) or not v:
                return ""
            parts = v.split(":", 1)
            if len(parts) == 2 and parts[0] == parts[1]:
                return parts[0]
            if v.startswith("公開:"):
                return parts[1].strip() if len(parts) == 2 else v
            if v.startswith("死:"):
                return "死"
            if v.startswith("登録:"):
                return "登録"
            return v
        out["生死情報更新"] = out[life_death_col].apply(life_death_updated)

    return out


# ===================== 集計関数 =====================

def analysis_application_trend(df: pd.DataFrame, year_col: str = COL_YEAR) -> pd.DataFrame:
    if year_col not in df.columns:
        return pd.DataFrame(columns=[year_col, "出願件数"])
    years = df[year_col].dropna()
    years = years[years.astype(str).str.match(r"^(19|20)\d{2}$", na=False)].astype(int)
    cnt = years.value_counts().sort_index()
    return pd.DataFrame({"出願年": cnt.index, "出願件数": cnt.values})


def _split_applicants(s: Any) -> List[str]:
    if pd.isna(s):
        return []
    return [x.strip() for x in str(s).replace("，", ",").split(",") if x.strip()]


def _split_ipc_codes(v: Any) -> List[str]:
    if pd.isna(v):
        return []
    tokens = re.split(r"[,\u3001\uFF0C;\uFF1B\n\r\t]+", str(v))
    return [t.strip() for t in tokens if t and t.strip()]


def analysis_ipc_growth(
    df: pd.DataFrame, target_year: int, year_range: int = 10,
    ipc_col: str = COL_IPC, year_col: str = COL_YEAR,
) -> pd.DataFrame:
    if ipc_col not in df.columns or year_col not in df.columns:
        return pd.DataFrame()
    sub = df[[ipc_col, year_col]].copy()
    sub[year_col] = pd.to_numeric(sub[year_col], errors="coerce")
    sub = sub.dropna(subset=[year_col])
    sub[year_col] = sub[year_col].astype(int)
    sub[ipc_col] = sub[ipc_col].apply(_split_ipc_codes)
    pdf = sub.explode(ipc_col)
    pdf = pdf[pdf[ipc_col].notna() & (pdf[ipc_col] != "")].rename(
        columns={ipc_col: "IPC", year_col: "year"}
    )
    if pdf.empty:
        return pd.DataFrame()
    b_mask = (pdf["year"] >= target_year - year_range) & (pdf["year"] < target_year)
    a1_mask = (pdf["year"] >= target_year) & (pdf["year"] < target_year + 5)
    a2_mask = (pdf["year"] >= target_year + 5) & (pdf["year"] <= target_year + year_range)
    bc = pdf.loc[b_mask].groupby("IPC").size()
    a1c = pdf.loc[a1_mask].groupby("IPC").size()
    a2c = pdf.loc[a2_mask].groupby("IPC").size()
    all_ipc = set(bc.index) | set(a1c.index) | set(a2c.index)
    result = []
    for ipc in all_ipc:
        b = int(bc.get(ipc, 0)); a1 = int(a1c.get(ipc, 0)); a2 = int(a2c.get(ipc, 0))
        at = a1 + a2; total = b + at
        result.append({
            "IPC": ipc, "before_count": b, "after_count": at,
            "after_first_5_count": a1, "after_second_5_count": a2,
            "pct_change_10": (at - b) / total if total else 0.0,
            "pct_change_second_5": (a2 - a1) / at if at else 0.0,
            "total_count": total,
        })
    return pd.DataFrame(result).sort_values("total_count", ascending=False).reset_index(drop=True)


def analysis_ipc_summary(df: pd.DataFrame, applicant_col: str = COL_LEAD_APPLICANT, ipc_col: str = COL_IPC) -> pd.DataFrame:
    if applicant_col not in df.columns or ipc_col not in df.columns:
        return pd.DataFrame()
    sub = df[[applicant_col, ipc_col]].copy()
    sub[applicant_col] = sub[applicant_col].apply(_split_applicants)
    sub[ipc_col] = sub[ipc_col].apply(_split_ipc_codes)
    pdf = sub.explode(applicant_col).explode(ipc_col).rename(
        columns={applicant_col: "applicant", ipc_col: "ipc"}
    )
    pdf = pdf[pdf["applicant"].notna() & (pdf["applicant"] != "") &
              pdf["ipc"].notna() & (pdf["ipc"] != "")]
    if pdf.empty:
        return pd.DataFrame()
    ac = pdf.groupby("applicant").size()
    ipc_order = pdf.groupby("ipc").size().sort_values(ascending=False).index.tolist()
    out = []
    for app in ac.sort_values(ascending=False).index:
        row = {"出願人名": app, "出願件数": int(ac[app])}
        sub_df = pdf[pdf["applicant"] == app]
        for ipc in ipc_order:
            row[ipc] = int((sub_df["ipc"] == ipc).sum())
        out.append(row)
    return pd.DataFrame(out, columns=["出願人名", "出願件数"] + ipc_order)


def analysis_ipc_main_group(df: pd.DataFrame, applicant_col: str = COL_LEAD_APPLICANT, ipc_main_col: str = "筆頭IPCメイングループ") -> pd.DataFrame:
    if applicant_col not in df.columns or ipc_main_col not in df.columns:
        return pd.DataFrame()
    sub = df[[applicant_col, ipc_main_col]].copy()
    sub[applicant_col] = sub[applicant_col].apply(_split_applicants)
    pdf = sub.explode(applicant_col).rename(columns={applicant_col: "applicant", ipc_main_col: "ipc"})
    pdf["ipc"] = pdf["ipc"].astype(str).str.strip()
    pdf = pdf[pdf["applicant"].notna() & (pdf["applicant"] != "") & (pdf["ipc"] != "") & (pdf["ipc"] != "nan")]
    if pdf.empty:
        return pd.DataFrame()
    ac = pdf.groupby("applicant").size()
    ipc_order = pdf.groupby("ipc").size().sort_values(ascending=False).index.tolist()
    out = []
    for app in ac.sort_values(ascending=False).index:
        row = {"出願人名": app, "出願件数": int(ac[app])}
        sub_df = pdf[pdf["applicant"] == app]
        for ipc in ipc_order:
            row[ipc] = int((sub_df["ipc"] == ipc).sum())
        out.append(row)
    return pd.DataFrame(out, columns=["出願人名", "出願件数"] + ipc_order)


def analysis_applicant_count(df: pd.DataFrame, start_year: int, end_year: int, applicant_col: str = COL_LEAD_APPLICANT, year_col: str = COL_YEAR) -> pd.DataFrame:
    if applicant_col not in df.columns or year_col not in df.columns:
        return pd.DataFrame()
    sub = df[(df[year_col] >= start_year) & (df[year_col] <= end_year)]
    cnt = sub[applicant_col].dropna().replace("", pd.NA).dropna().value_counts()
    return pd.DataFrame({"筆頭出願人": cnt.index.tolist(), "出願件数": cnt.values.tolist()})


def analysis_applicant_total(df: pd.DataFrame, start_year: int, end_year: int, applicant_col: str = COL_APPLICANT, year_col: str = COL_YEAR) -> pd.DataFrame:
    if applicant_col not in df.columns or year_col not in df.columns:
        return pd.DataFrame()
    sub = df[(df[year_col] >= start_year) & (df[year_col] <= end_year)]
    all_apps = []
    for v in sub[applicant_col].dropna():
        parts = set(x.strip() for x in str(v).replace("，", ",").split(",") if x.strip())
        all_apps.extend(parts)
    cnt = pd.Series(all_apps).value_counts()
    return pd.DataFrame({"出願人名": cnt.index.tolist(), "出願件数": cnt.values.tolist()})


def analysis_applicant_growth(df: pd.DataFrame, target_year: int, year_range: int = 10, applicant_col: str = COL_APPLICANT, year_col: str = COL_YEAR) -> pd.DataFrame:
    if applicant_col not in df.columns or year_col not in df.columns:
        return pd.DataFrame()
    sub = df[[applicant_col, year_col]].copy()
    sub[year_col] = pd.to_numeric(sub[year_col], errors="coerce")
    sub = sub.dropna(subset=[year_col])
    sub[year_col] = sub[year_col].astype(int)
    sub[applicant_col] = sub[applicant_col].apply(lambda x: list(set(_split_applicants(x))))
    pdf = sub.explode(applicant_col)
    pdf = pdf[pdf[applicant_col].notna() & (pdf[applicant_col] != "")]
    if pdf.empty:
        return pd.DataFrame()
    yr = pdf[year_col]
    before = pdf[((yr >= target_year - year_range) & (yr < target_year))].groupby(applicant_col).size()
    after1 = pdf[((yr >= target_year) & (yr < target_year + 5))].groupby(applicant_col).size()
    after2 = pdf[((yr >= target_year + 5) & (yr <= target_year + year_range))].groupby(applicant_col).size()
    all_apps = set(before.index) | set(after1.index) | set(after2.index)
    rows = []
    for app in all_apps:
        b = int(before.get(app, 0)); a1 = int(after1.get(app, 0)); a2 = int(after2.get(app, 0))
        at = a1 + a2; total = b + at
        rows.append({
            "出願人": app, "before_count": b, "after_count": at,
            "after_first_5": a1, "after_second_5": a2,
            "pct_change_10": (at - b) / total if total else 0.0,
            "pct_change_second_5": (a2 - a1) / at if at else 0.0,
            "total_count": total,
        })
    return pd.DataFrame(rows).sort_values("total_count", ascending=False).reset_index(drop=True)


def analysis_entry_exit(df: pd.DataFrame, applicant_col: str = COL_APPLICANT, year_col: str = COL_YEAR) -> pd.DataFrame:
    if applicant_col not in df.columns or year_col not in df.columns:
        return pd.DataFrame()
    sub = df[[applicant_col, year_col]].copy()
    sub[year_col] = pd.to_numeric(sub[year_col], errors="coerce")
    sub = sub.dropna(subset=[year_col])
    sub[year_col] = sub[year_col].astype(int)
    sub[applicant_col] = sub[applicant_col].apply(lambda x: list(set(_split_applicants(x))))
    pdf = sub.explode(applicant_col)
    pdf = pdf[pdf[applicant_col].notna() & (pdf[applicant_col] != "")]
    if pdf.empty:
        return pd.DataFrame()
    grp = pdf.groupby(applicant_col)[year_col]
    result = pd.DataFrame({
        "出願人名": grp.min().index,
        "最初の出願年": grp.min().values,
        "直近出願年": grp.max().values,
        "総出願件数": grp.size().values,
    })
    return result.reset_index(drop=True)


def _parse_citation_count(v: Any) -> int:
    if pd.isna(v):
        return 0
    m = re.search(r"引用[：:]?\s*(\d+)", str(v))
    return int(m.group(1)) if m else 0


def analysis_citation_map(df: pd.DataFrame, applicant_col: str = COL_LEAD_APPLICANT, citation_col: str = "被引用回数") -> pd.DataFrame:
    if applicant_col not in df.columns or citation_col not in df.columns:
        return pd.DataFrame()
    sub = df[[applicant_col, citation_col]].copy()
    sub["_c"] = sub[citation_col].apply(_parse_citation_count)
    sub[applicant_col] = sub[applicant_col].apply(_split_applicants)
    pdf = sub.explode(applicant_col)
    pdf = pdf[pdf[applicant_col].notna() & (pdf[applicant_col] != "")]
    if pdf.empty:
        return pd.DataFrame()
    grp = pdf.groupby(applicant_col)["_c"]
    rows = []
    for app, vals in grp:
        lst = vals.tolist()
        total_apps = len(lst)
        cited = sum(1 for v in lst if v > 0)
        rows.append({
            "出願人名": app,
            "平均引用回数": round(sum(lst) / total_apps, 2) if total_apps else 0,
            "最大引用回数": max(lst) if lst else 0,
            "合計引用回数": sum(lst),
            "出願件数": total_apps,
            "引用された出願割合（%）": round((cited / total_apps * 100), 1) if total_apps else 0,
        })
    return pd.DataFrame(rows).sort_values("最大引用回数", ascending=False).reset_index(drop=True)


def analysis_cited_applications(df: pd.DataFrame, applicant_col: str = COL_LEAD_APPLICANT, app_num_col: str = "出願番号", year_col: str = COL_YEAR, citation_col: str = "被引用回数", life_death_col: str = "生死情報更新") -> pd.DataFrame:
    need = [applicant_col, app_num_col, year_col, citation_col]
    if not all(c in df.columns for c in need):
        return pd.DataFrame()
    rows = []
    for _, r in df.iterrows():
        app = r.get(applicant_col); num = r.get(app_num_col); yr = r.get(year_col)
        if pd.isna(app) or pd.isna(num) or pd.isna(yr):
            continue
        c = _parse_citation_count(r.get(citation_col))
        life = r.get(life_death_col) if life_death_col in df.columns else ""
        combined = f"{app} - {num}"
        if life and not pd.isna(life):
            combined += f" - {life}"
        rows.append({"筆頭出願人 - 出願番号 - 生死情報更新": combined, "出願番号": num, "出願年": yr, "被引用回数": c})
    out = pd.DataFrame(rows)
    return out.sort_values("被引用回数", ascending=False).reset_index(drop=True) if not out.empty else out


# ===================== 追加集計（グラフ用） =====================

def analysis_applicant_year_trend(df: pd.DataFrame, applicant_col: str = COL_LEAD_APPLICANT, year_col: str = COL_YEAR, top_n: int = 10) -> pd.DataFrame:
    """出願人別 年次推移（上位N社）"""
    if applicant_col not in df.columns or year_col not in df.columns:
        return pd.DataFrame()
    sub = df[[applicant_col, year_col]].dropna()
    sub = sub[sub[year_col].astype(str).str.match(r"^(19|20)\d{2}$", na=False)].copy()
    sub[year_col] = sub[year_col].astype(int)
    top = sub[applicant_col].value_counts().head(top_n).index.tolist()
    sub = sub[sub[applicant_col].isin(top)]
    pivot = sub.groupby([year_col, applicant_col]).size().reset_index(name="出願件数")
    return pivot.rename(columns={year_col: "出願年", applicant_col: "出願人"})


def analysis_ipc_year_heatmap(df: pd.DataFrame, ipc_col: str = "筆頭IPCサブクラス", year_col: str = COL_YEAR, top_n: int = 20) -> pd.DataFrame:
    """IPC別 年次推移 ヒートマップ用"""
    if ipc_col not in df.columns or year_col not in df.columns:
        return pd.DataFrame()
    sub = df[[ipc_col, year_col]].dropna()
    sub = sub[sub[year_col].astype(str).str.match(r"^(19|20)\d{2}$", na=False)].copy()
    sub[year_col] = sub[year_col].astype(int)
    top_ipcs = sub[ipc_col].value_counts().head(top_n).index.tolist()
    sub = sub[sub[ipc_col].isin(top_ipcs)]
    pivot = sub.groupby([year_col, ipc_col]).size().reset_index(name="出願件数")
    return pivot.rename(columns={year_col: "出願年", ipc_col: "IPC"})


def analysis_applicant_ipc_heatmap(df: pd.DataFrame, applicant_col: str = COL_LEAD_APPLICANT, ipc_col: str = "筆頭IPCサブクラス", top_applicants: int = 20, top_ipcs: int = 15) -> pd.DataFrame:
    """出願人 x IPC ヒートマップ用"""
    if applicant_col not in df.columns or ipc_col not in df.columns:
        return pd.DataFrame()
    sub = df[[applicant_col, ipc_col]].dropna()
    top_a = sub[applicant_col].value_counts().head(top_applicants).index.tolist()
    top_i = sub[ipc_col].value_counts().head(top_ipcs).index.tolist()
    sub = sub[(sub[applicant_col].isin(top_a)) & (sub[ipc_col].isin(top_i))]
    pivot = sub.groupby([applicant_col, ipc_col]).size().reset_index(name="出願件数")
    return pivot.rename(columns={applicant_col: "出願人", ipc_col: "IPC"})


def analysis_applicant_share(df: pd.DataFrame, applicant_col: str = COL_LEAD_APPLICANT, year_col: str = COL_YEAR, top_n: int = 8) -> pd.DataFrame:
    """出願人シェア 積み上げ面グラフ用"""
    if applicant_col not in df.columns or year_col not in df.columns:
        return pd.DataFrame()
    sub = df[[applicant_col, year_col]].dropna()
    sub = sub[sub[year_col].astype(str).str.match(r"^(19|20)\d{2}$", na=False)].copy()
    sub[year_col] = sub[year_col].astype(int)
    top = sub[applicant_col].value_counts().head(top_n).index.tolist()
    sub["出願人"] = sub[applicant_col].apply(lambda x: x if x in top else "その他")
    pivot = sub.groupby([year_col, "出願人"]).size().reset_index(name="出願件数")
    return pivot.rename(columns={year_col: "出願年"})


def analysis_co_applicant(df: pd.DataFrame, applicant_col: str = COL_APPLICANT, top_n: int = 20) -> pd.DataFrame:
    """共同出願ネットワーク（隣接行列用）"""
    if applicant_col not in df.columns:
        return pd.DataFrame()

    def _get_pairs(v):
        apps = list(set(_split_applicants(v)))
        if len(apps) >= 2:
            return list(combinations(sorted(apps), 2))
        return []

    all_pairs = df[applicant_col].apply(_get_pairs).explode().dropna()
    pairs: Counter = Counter(all_pairs)
    if not pairs:
        return pd.DataFrame()
    rows = [{"出願人A": a, "出願人B": b, "共同出願件数": c} for (a, b), c in pairs.items()]
    out = pd.DataFrame(rows).sort_values("共同出願件数", ascending=False)
    return out.head(top_n * 5).reset_index(drop=True)


def analysis_ipc_treemap(df: pd.DataFrame, ipc_col: str = "筆頭IPCサブクラス") -> pd.DataFrame:
    """IPCサブクラス別 ツリーマップ用"""
    if ipc_col not in df.columns:
        return pd.DataFrame()
    cnt = df[ipc_col].dropna().value_counts()
    return pd.DataFrame({"IPC": cnt.index.tolist(), "出願件数": cnt.values.tolist()})


# ===================== I/O =====================

def excel_to_dataframe(file_bytes: bytes, sheet_name: str = "データ") -> pd.DataFrame:
    return pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_name)


def dataframe_to_excel_bytes(sheets: Dict[str, pd.DataFrame], order: Optional[List[str]] = None) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, frame in (sheets.items() if order is None else [(k, sheets[k]) for k in order if k in sheets]):
            frame.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

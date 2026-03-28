# -*- coding: utf-8 -*-
"""IP Analysis Studio — Playwright E2E テスト。

Streamlit アプリの基本フロー（Step 1→2→3）を検証する。
"""
from __future__ import annotations

import time as _time

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


# ---------- helpers ----------

def _wait_stable(page: Page, ms: int = 3000) -> None:
    """Streamlit のリレンダリングが落ち着くまで待つ。"""
    page.wait_for_timeout(ms)
    page.wait_for_load_state("networkidle")


# ---------- tests ----------

class TestAppLaunch:
    """アプリの初期表示を検証する。"""

    def test_title_and_step1(self, page: Page, app_url: str):
        """タイトル・Step 1 ヘッダー・サイドバーが表示されること。"""
        page.goto(app_url)
        expect(page.get_by_text("IP Analysis Studio").first).to_be_visible(timeout=20_000)
        expect(page.get_by_text("Step 1: データ前処理").first).to_be_visible(timeout=10_000)
        expect(page.get_by_text("使い方ガイド")).to_be_visible(timeout=10_000)

    def test_preprocess_disabled_without_data(self, page: Page, app_url: str):
        """ファイル未選択時に前処理ボタンが無効であること。"""
        page.goto(app_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        btn = page.get_by_role("button", name="前処理を実行")
        if btn.count() > 0:
            expect(btn.first).to_be_disabled()


class TestFullFlow:
    """サンプルデータを使った Step 1→2→3 の一貫フローを検証する。"""

    def test_sample_data_full_flow(self, page: Page, app_url: str):
        """サンプルデータ読み込み→前処理→集計→Step 3 表示の全フロー。"""
        # --- Step 1: サンプルデータ読み込み ---
        page.goto(app_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        sample_btn = page.get_by_role("button", name="サンプルデータで試す")
        sample_btn.first.wait_for(state="visible", timeout=20_000)
        sample_btn.first.click()
        _wait_stable(page, 8000)

        # 前処理ボタンが有効化 = サンプルデータ読み込み成功
        preprocess_btn = page.get_by_role("button", name="前処理を実行")
        preprocess_btn.first.wait_for(state="visible", timeout=20_000)
        deadline = _time.monotonic() + 30
        while _time.monotonic() < deadline:
            if preprocess_btn.first.is_enabled():
                break
            page.wait_for_timeout(500)
        expect(preprocess_btn.first).to_be_enabled(timeout=5000)

        # --- Step 1→2: 前処理を実行 ---
        preprocess_btn.first.click()
        _wait_stable(page, 8000)
        expect(page.get_by_text("Step 2: 集計").first).to_be_visible(timeout=20_000)

        # --- Step 2→3: 集計を実行 ---
        agg_btn = page.get_by_role("button", name="集計を実行")
        agg_btn.first.wait_for(state="visible", timeout=20_000)
        deadline = _time.monotonic() + 30
        while _time.monotonic() < deadline:
            if agg_btn.first.is_enabled():
                break
            page.wait_for_timeout(500)
        agg_btn.first.click()
        _wait_stable(page, 10000)

        # Step 3 に遷移したことを確認
        expect(page.get_by_text("Step 3: グラフ作成").first).to_be_visible(timeout=30_000)

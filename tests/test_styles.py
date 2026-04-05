# -*- coding: utf-8 -*-
"""styles.py のユニットテスト。"""
import pytest

from styles import APP_CSS, HERO_HTML, FORMAT_LABELS, FORMAT_COLORS, format_badge_html


def test_app_css_contains_style_tag():
    """APP_CSS が <style> タグを含むこと。"""
    assert "<style>" in APP_CSS
    assert "</style>" in APP_CSS


def test_hero_html_contains_title():
    """HERO_HTML にアプリタイトルが含まれること。"""
    assert "IP Analysis Studio" in HERO_HTML


def test_format_labels_completeness():
    """全データ形式のラベルが定義されていること。"""
    for fmt in ("questel", "jplatpat", "unknown"):
        assert fmt in FORMAT_LABELS
        assert fmt in FORMAT_COLORS


@pytest.mark.parametrize("fmt", ["questel", "jplatpat", "unknown"])
def test_format_badge_html_output(fmt):
    """format_badge_html が各形式で有効な HTML を返すこと。"""
    html = format_badge_html(fmt)
    assert "<span" in html
    assert FORMAT_LABELS[fmt] in html
    assert FORMAT_COLORS[fmt] in html

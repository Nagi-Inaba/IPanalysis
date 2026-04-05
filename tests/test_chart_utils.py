# -*- coding: utf-8 -*-
"""chart_utils.py のユニットテスト。"""
import pytest

altair = pytest.importorskip("altair", reason="altair が必要")


def test_chart_to_png_bytes_import():
    """chart_to_png_bytes がインポートできること。"""
    from chart_utils import chart_to_png_bytes
    assert callable(chart_to_png_bytes)


def test_chart_to_png_bytes_no_vl_convert(monkeypatch):
    """vl-convert-python が未インストールの場合 None を返すこと。"""
    import chart_utils

    original_import = __import__

    def mock_import(name, *args, **kwargs):
        if name == "vl_convert":
            raise ImportError("mocked")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    class MockChart:
        def to_dict(self, format=None):
            return {}

    result = chart_utils.chart_to_png_bytes(MockChart())
    assert result is None

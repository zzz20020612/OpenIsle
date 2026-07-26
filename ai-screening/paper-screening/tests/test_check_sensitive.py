"""Tests for check_sensitive.py — dim-06 敏感内容检测。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_sensitive import (
    _check_territory_context,
    _detect_map_images,
    _find_with_context,
    check_sensitive,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_paper(text: str = "", images: list | None = None) -> dict:
    return {
        "metadata": {"title": "Test"},
        "segments": [{"type": "body", "text": text}] if text else [],
        "images": images or [],
        "tables": [],
    }


# ---------------------------------------------------------------------------
# Context checking
# ---------------------------------------------------------------------------

class TestTerritoryContext:
    def test_taiwan_ok(self):
        assert _check_territory_context("台湾", "研究在中国台湾进行") is True

    def test_taiwan_bad(self):
        assert _check_territory_context("台湾", "台湾是独立的国家") is False

    def test_hongkong_ok(self):
        assert _check_territory_context("香港", "中国香港大学") is True

    def test_hongkong_bad(self):
        assert _check_territory_context("香港", "香港的政策") is False

    def test_macau_ok(self):
        assert _check_territory_context("澳门", "中国澳门科技大学") is True

    def test_other_terms(self):
        # 西藏、新疆等暂不做上下文判断，返回 True
        assert _check_territory_context("西藏", "西藏研究") is True


# ---------------------------------------------------------------------------
# Finding with context
# ---------------------------------------------------------------------------

class TestFindWithContext:
    def test_find(self):
        contexts = _find_with_context("foo 台湾 bar", "台湾")
        assert len(contexts) == 1
        assert "台湾" in contexts[0]

    def test_find_multiple(self):
        contexts = _find_with_context("台湾 and 台湾 again", "台湾")
        assert len(contexts) == 2

    def test_find_none(self):
        assert _find_with_context("no match here", "台湾") == []


# ---------------------------------------------------------------------------
# Map detection
# ---------------------------------------------------------------------------

class TestMapDetection:
    def test_detect_caption(self):
        images = [{"caption": "中国地图"}]
        result = _detect_map_images(images, "")
        assert len(result) == 1

    def test_detect_text(self):
        result = _detect_map_images([], "本文讨论了九段线问题")
        assert len(result) > 0

    def test_no_map(self):
        result = _detect_map_images([], "quantum physics is interesting")
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Full check
# ---------------------------------------------------------------------------

class TestCheckSensitive:
    def test_clean_paper(self):
        paper = _make_paper("This is a clean paper about chemistry.")
        result = check_sensitive(paper)
        assert result["dimension_id"] == "06"
        assert result["status"] == "passed"

    def test_violation_detected(self):
        paper = _make_paper("台湾独立运动")
        result = check_sensitive(paper)
        assert result["status"] == "failed"
        assert result["severity"] == "critical"

    def test_territory_issue(self):
        paper = _make_paper("本文研究了台湾的经济发展")
        result = check_sensitive(paper)
        assert result["status"] == "warning"

    def test_territory_ok(self):
        paper = _make_paper("本文研究了中国台湾的经济发展")
        result = check_sensitive(paper)
        assert result["status"] == "passed"

    def test_result_format(self):
        paper = _make_paper("test")
        result = check_sensitive(paper)
        assert "dimension_id" in result
        assert "status" in result
        assert "findings" in result

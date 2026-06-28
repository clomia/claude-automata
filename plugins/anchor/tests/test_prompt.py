"""Tests for the prompt module — deterministic advisor-input assembly."""

from src.prompt import build_analysis_input, format_region_history, wrap_section


class TestWrapSection:
    def test_wraps_in_xml(self):
        assert wrap_section("role", "X") == "<role>\n\nX\n\n</role>"


class TestFormatRegionHistory:
    def test_empty(self):
        assert format_region_history([]) == "No prior regions."

    def test_single(self):
        assert format_region_history(["A"]) == "<region-1>\n\nA\n\n</region-1>"

    def test_multiple_are_numbered(self):
        out = format_region_history(["A", "B"])
        assert "<region-1>\n\nA\n\n</region-1>" in out
        assert "<region-2>\n\nB\n\n</region-2>" in out


class TestBuildAnalysisInput:
    def test_wraps_mission_and_region_history(self):
        out = build_analysis_input("do X", ["region one"])
        assert "<original-mission>" in out
        assert "do X" in out
        assert "<parallax-region-history>" in out
        assert "<region-1>" in out
        assert "region one" in out

    def test_empty_region_history(self):
        out = build_analysis_input("do X", [])
        assert "<original-mission>" in out
        assert "No prior regions." in out

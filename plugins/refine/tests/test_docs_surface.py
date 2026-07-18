"""refine 사본은 tx 원본의 byte-identical 복사다 — 단일 작성자 계약의 기계화."""

from pathlib import Path


def test_docs_surface_byte_identical():
    refine_copy = Path(__file__).parents[1] / "skills" / "docs" / "docs-surface.md"
    tx_original = Path(__file__).parents[2] / "tx" / "references" / "docs-surface.md"
    assert refine_copy.read_bytes() == tx_original.read_bytes()

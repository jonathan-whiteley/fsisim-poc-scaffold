import os
from pathlib import Path
from data_gen.gen_manuals import generate_manuals, ManualSpec, MANUAL_SPECS


def test_manual_specs_cover_required_categories():
    titles = {m.title for m in MANUAL_SPECS}
    assert any("Glossary" in t or "Acronym" in t for t in titles)
    assert any("Hydraulic" in t for t in titles)
    assert any("Motion" in t for t in titles)
    assert any("Visual" in t for t in titles)


def test_each_manual_has_outline():
    for m in MANUAL_SPECS:
        assert len(m.outline) >= 3, f"{m.title} needs >=3 sections"


def test_generate_writes_pdfs_to_outdir(tmp_path, monkeypatch):
    """Smoke test the rendering path without calling the LLM."""
    from data_gen import gen_manuals
    monkeypatch.setattr(gen_manuals, "_author_section",
                        lambda section, manual_title: f"Stub content for {section} of {manual_title}.")
    out = generate_manuals(out_dir=tmp_path)
    assert len(out) == len(MANUAL_SPECS)
    for path in out:
        assert path.exists()
        assert path.suffix == ".pdf"
        assert path.stat().st_size > 1000

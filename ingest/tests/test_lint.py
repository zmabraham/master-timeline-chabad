import pytest
from pathlib import Path

from timeline_ingest.lint import lint_emit, LintError


def _write(path: Path, payload):
    import json
    path.write_text(json.dumps(payload))


def test_lint_passes_for_valid(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "significance": 25,
        "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "categories": ["general"], "sources": [{"name": "x"}], "related": [],
    }]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    lint_emit(public)


def test_lint_fails_for_duplicate_ids(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [
        {"id": "x", "significance": 25, "date": {"y": 1812, "precision": "year"},
         "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
         "categories": ["general"], "sources": [{"name": "x"}], "related": []},
        {"id": "x", "significance": 25, "date": {"y": 1813, "precision": "year"},
         "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
         "categories": ["general"], "sources": [{"name": "x"}], "related": []},
    ]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    with pytest.raises(LintError, match="duplicate"):
        lint_emit(public)


def test_lint_fails_for_orphan_related(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "significance": 25, "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "categories": ["general"], "sources": [{"name": "x"}], "related": ["nope"],
    }]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    with pytest.raises(LintError, match="orphan"):
        lint_emit(public)


def test_lint_fails_for_missing_story_file(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "significance": 25, "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "categories": ["general"], "sources": [{"name": "x"}], "related": [],
    }]
    _write(public / "events.json", payload)
    with pytest.raises(LintError, match="story file"):
        lint_emit(public)


def test_lint_fails_for_remote_photo_url(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "significance": 85, "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "categories": ["rebbe"], "sources": [{"name": "x"}], "related": [],
        "photo": {"url": "https://example.org/p.jpg", "credit": "c"},
    }]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    with pytest.raises(LintError, match="still remote"):
        lint_emit(public)


def test_lint_fails_for_missing_photo_file(tmp_path):
    public = tmp_path / "public"
    (public / "stories").mkdir(parents=True)
    payload = [{
        "id": "x", "significance": 85, "date": {"y": 1812, "precision": "year"},
        "title_en": "t", "summary_en": "s", "story_path": "stories/x.md",
        "categories": ["rebbe"], "sources": [{"name": "x"}], "related": [],
        "photo": {"url": "photos/x.webp", "credit": "c"},
    }]
    _write(public / "events.json", payload)
    (public / "stories" / "x.md").write_text("# t\n")
    with pytest.raises(LintError, match="photo file missing"):
        lint_emit(public)

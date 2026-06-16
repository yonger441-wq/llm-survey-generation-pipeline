"""Shared helpers for citation growth planning and metrics."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

CITATION_PATTERN = re.compile(r"\[@([^\]]+)\]")


def section_sort_key(section_id: str) -> tuple:
    """Sort section identifiers like 2.10 after 2.9."""
    parts = []
    for token in str(section_id).split("."):
        try:
            parts.append((0, int(token)))
        except ValueError:
            parts.append((1, token))
    return tuple(parts)


def classify_section(section_info: dict, cfg: dict | None = None) -> str:
    """Classify a section as meta or technical."""
    retrieval_cfg = (cfg or {}).get("retrieval", {})
    meta_chapters = set(retrieval_cfg.get("meta_chapters", [1, 15]))
    return "meta" if int(section_info.get("chapter", 0)) in meta_chapters else "technical"


def load_section_info(section_dir: Path) -> dict:
    return json.loads((section_dir / "section_info.json").read_text(encoding="utf-8"))


def find_section_dirs(
    sections_dir: Path,
    chapter: int | None = None,
    section: str | None = None,
) -> list[Path]:
    """Find section directories in stable chapter/section order."""
    items = []
    for info_path in sections_dir.rglob("section_info.json"):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        if chapter is not None and info["chapter"] != chapter:
            continue
        if section is not None and info["section"] != section:
            continue
        items.append((int(info["chapter"]), section_sort_key(info["section"]), info_path.parent))
    items.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in items]


def extract_cited_bibkeys(text: str) -> set[str]:
    """Extract unique citation keys from markdown citation spans."""
    bibkeys: set[str] = set()
    for match in CITATION_PATTERN.finditer(text):
        for part in match.group(1).split(";"):
            bibkey = part.strip().lstrip("@")
            if bibkey:
                bibkeys.add(bibkey)
    return bibkeys


def count_citation_mentions(text: str) -> int:
    """Count all citation mentions, including repeated mentions of a key."""
    total = 0
    for match in CITATION_PATTERN.finditer(text):
        total += sum(1 for part in match.group(1).split(";") if part.strip().lstrip("@"))
    return total


def load_selected_rows(path: Path) -> list[dict]:
    """Load selected.csv rows."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_selected_bibkeys(path: Path) -> list[str]:
    return [row.get("bibkey", "").strip() for row in load_selected_rows(path) if row.get("bibkey", "").strip()]


def load_notes(path: Path) -> list[dict]:
    """Load notes.jsonl."""
    notes = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            notes.append(json.loads(line))
    return notes


def build_usage_counts_from_selected(
    sections_dir: Path,
    exclude_sections: set[str] | None = None,
) -> dict[str, int]:
    """Count how many sections each selected paper appears in."""
    usage: dict[str, set[str]] = defaultdict(set)
    for sec_dir in find_section_dirs(sections_dir):
        info = load_section_info(sec_dir)
        section_id = info["section"]
        if exclude_sections and section_id in exclude_sections:
            continue
        selected_path = sec_dir / "selected.csv"
        if not selected_path.exists():
            continue
        for bibkey in load_selected_bibkeys(selected_path):
            usage[bibkey].add(section_id)
    return {bibkey: len(section_ids) for bibkey, section_ids in usage.items()}


def build_usage_counts_from_finals(
    sections_dir: Path,
    exclude_sections: set[str] | None = None,
) -> dict[str, int]:
    """Count how many sections each cited paper appears in final.md files."""
    usage: dict[str, set[str]] = defaultdict(set)
    for sec_dir in find_section_dirs(sections_dir):
        info = load_section_info(sec_dir)
        section_id = info["section"]
        if exclude_sections and section_id in exclude_sections:
            continue
        final_path = sec_dir / "final.md"
        if not final_path.exists():
            continue
        text = final_path.read_text(encoding="utf-8")
        for bibkey in extract_cited_bibkeys(text):
            usage[bibkey].add(section_id)
    return {bibkey: len(section_ids) for bibkey, section_ids in usage.items()}


def rebuild_used_papers(sections_dir: Path, output_path: Path | None = None) -> Path:
    """Rebuild used_papers.jsonl from selected.csv files."""
    if output_path is None:
        output_path = sections_dir / "used_papers.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for sec_dir in find_section_dirs(sections_dir):
        info = load_section_info(sec_dir)
        section_id = info["section"]
        selected_path = sec_dir / "selected.csv"
        if not selected_path.exists():
            continue
        for bibkey in load_selected_bibkeys(selected_path):
            lines.append(json.dumps({"bibkey": bibkey, "section": section_id}, ensure_ascii=False))
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output_path

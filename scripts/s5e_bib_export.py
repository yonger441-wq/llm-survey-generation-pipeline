"""Stage 5e: Extract used references from the bibliography with CSV fallback.

Scan all final.md files for [@bibkey] citations, extract matching entries from
references.bib, and backfill missing entries from papers_master.csv when
possible. This keeps the compile pipeline healthy when the master BibTeX file
lags behind the paper pool.

Usage:
    python scripts/s5e_bib_export.py
"""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from pathlib import Path

from llm_utils import load_config, resolve_path


def _collect_cited_bibkeys_from_text(text: str) -> set[str]:
    bibkeys = set()
    for match in re.finditer(r"\[@([^\]]+)\]", text):
        for part in match.group(1).split(";"):
            bibkey = part.strip().lstrip("@")
            if bibkey:
                bibkeys.add(bibkey)
    return bibkeys


def collect_cited_bibkeys(sections_dir: Path, output_dir: Path | None = None) -> set[str]:
    """Collect all unique bibkeys cited across section finals and merged outputs."""
    bibkeys = set()
    for final_path in sorted(sections_dir.rglob("final.md")):
        bibkeys.update(_collect_cited_bibkeys_from_text(final_path.read_text(encoding="utf-8")))
    if output_dir and output_dir.exists():
        for extra_path in list(sorted((output_dir / "chapters").glob("ch*.md"))) + [output_dir / "full_paper.md"]:
            if extra_path.exists():
                bibkeys.update(_collect_cited_bibkeys_from_text(extra_path.read_text(encoding="utf-8")))
    return bibkeys


def parse_bib_entries(bib_path: Path) -> dict[str, str]:
    """Parse BibTeX entries keyed by bibkey."""
    if not bib_path.exists():
        return {}

    text = bib_path.read_text(encoding="utf-8")
    entries: dict[str, str] = {}
    current_entry: list[str] = []
    current_key: str | None = None
    depth = 0

    for line in text.split("\n"):
        match = re.match(r"@\w+\{\s*([^,\s]+)", line)
        if match and depth == 0:
            if current_entry and current_key:
                entries[current_key] = "\n".join(current_entry)
            current_entry = [line]
            current_key = match.group(1).strip()
            depth = 1
            continue

        if current_entry:
            current_entry.append(line)
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                if current_key:
                    entries[current_key] = "\n".join(current_entry)
                current_entry = []
                current_key = None
                depth = 0

    if current_entry and current_key:
        entries[current_key] = "\n".join(current_entry)
    return entries


def _escape_bib_value(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def _ascii_safe_text(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "--",
        "\u2014": "--",
        "\u2212": "-",
        "\u00a0": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text


def _author_field(raw_authors: str) -> str:
    authors = [part.strip() for part in raw_authors.split(";") if part.strip()]
    return " and ".join(authors) if authors else "Unknown"


def build_fallback_entry(row: dict) -> str:
    """Build a minimal BibTeX entry from papers_master.csv metadata."""
    bibkey = row.get("bibkey", "").strip()
    title = _escape_bib_value(row.get("title", "").strip() or bibkey)
    year = row.get("year", "").strip() or "1900"
    authors = _escape_bib_value(_author_field(row.get("authors", "").strip()))
    venue = _escape_bib_value(row.get("venue", "").strip())
    doi = _escape_bib_value(row.get("doi", "").strip())
    url = _escape_bib_value(row.get("url", "").strip())
    fields = [
        f"  title = {{{title}}}",
        f"  author = {{{authors}}}",
        f"  year = {{{year}}}",
    ]
    if venue:
        fields.append(f"  howpublished = {{{venue}}}")
    if doi:
        fields.append(f"  doi = {{{doi}}}")
    if url:
        fields.append(f"  url = {{{url}}}")
    return "@misc{" + bibkey + ",\n" + ",\n".join(fields) + "\n}"


def sanitize_bib_entry(entry: str) -> str:
    """Convert BibTeX text to an ASCII-safe representation for bibtex."""
    return _ascii_safe_text(entry)


def load_paper_pool_rows(paper_pool_path: Path) -> dict[str, dict]:
    """Load papers_master.csv rows by bibkey."""
    rows: dict[str, dict] = {}
    if not paper_pool_path.exists():
        return rows
    with paper_pool_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            bibkey = row.get("bibkey", "").strip()
            if bibkey:
                rows[bibkey] = row
    return rows


def extract_entries(
    bib_path: Path,
    cited_bibkeys: set[str],
    paper_pool_path: Path | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Extract or backfill BibTeX entries for cited keys.

    Returns (entries, missing_in_bib, backfilled_keys).
    """
    parsed_entries = parse_bib_entries(bib_path)
    entries: list[str] = []
    missing_in_bib: list[str] = []
    backfilled: list[str] = []
    fallback_rows = load_paper_pool_rows(paper_pool_path) if paper_pool_path else {}

    for bibkey in sorted(cited_bibkeys):
        entry = parsed_entries.get(bibkey)
        if entry:
            entries.append(sanitize_bib_entry(entry))
            continue
        row = fallback_rows.get(bibkey)
        if row:
            entries.append(sanitize_bib_entry(build_fallback_entry(row)))
            backfilled.append(bibkey)
        else:
            missing_in_bib.append(bibkey)
    return entries, missing_in_bib, backfilled


def write_used_bib(entries: list[str], output_path: Path) -> None:
    """Write used_references.bib."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(entries) + "\n", encoding="utf-8")


def run() -> dict:
    """Execute bib export. Returns stats."""
    cfg = load_config()
    sections_dir = resolve_path(cfg, "sections_dir")
    bib_path = resolve_path(cfg, "bib_file")
    paper_pool_path = resolve_path(cfg, "paper_pool")
    output_dir = resolve_path(cfg, "output_dir")

    cited = collect_cited_bibkeys(sections_dir, output_dir=output_dir)
    print(f"Found {len(cited)} unique cited bibkeys")

    entries, missing, backfilled = extract_entries(bib_path, cited, paper_pool_path=paper_pool_path)
    print(f"Extracted {len(entries) - len(backfilled)} matching BibTeX entries")
    if backfilled:
        print(f"Backfilled {len(backfilled)} entries from papers_master.csv")
    if missing:
        print(f"WARNING: still missing {len(missing)} cited keys from all sources")

    used_bib_path = output_dir / "used_references.bib"
    write_used_bib(entries, used_bib_path)
    print(f"Wrote {used_bib_path}")

    return {
        "cited": len(cited),
        "extracted": len(entries),
        "backfilled": len(backfilled),
        "missing": len(missing),
    }


def main():
    parser = argparse.ArgumentParser(description="Stage 5e: Export used references")
    parser.parse_args()
    stats = run()
    print(
        f"\nCited: {stats['cited']}, Extracted: {stats['extracted']}, "
        f"Backfilled: {stats['backfilled']}, Missing: {stats['missing']}"
    )


if __name__ == "__main__":
    main()

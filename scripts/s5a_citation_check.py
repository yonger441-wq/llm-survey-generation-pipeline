"""Stage 5a: Citation validity check and density report.

Scan all final.md files for [@bibkey] patterns, verify each bibkey exists
in references.bib, compute per-section citation density, and generate
reports/citation_report.md.

Usage:
    python scripts/s5a_citation_check.py [--chapter N]
"""

import argparse
import json
import re
from pathlib import Path

from llm_utils import PROJECT_ROOT, load_config, resolve_path


# ---------------------------------------------------------------------------
# Citation scanning
# ---------------------------------------------------------------------------

def extract_bibkeys(text: str) -> list[str]:
    """Extract all bibkeys from [@bibkey] patterns in text."""
    bibkeys = []
    for m in re.finditer(r"\[@([^\]]+)\]", text):
        content = m.group(1)
        for part in content.split(";"):
            part = part.strip().lstrip("@")
            if part:
                bibkeys.append(part)
    return bibkeys


def unique_bibkeys(text: str) -> set[str]:
    """Extract unique bibkeys from text."""
    return set(extract_bibkeys(text))


def scan_section(section_dir: Path) -> dict:
    """Scan one section for citation stats."""
    info_path = section_dir / "section_info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))

    final_path = section_dir / "final.md"
    draft_path = section_dir / "draft.md"
    source = final_path if final_path.exists() else draft_path

    text = source.read_text(encoding="utf-8") if source.exists() else ""
    bibkeys = unique_bibkeys(text)
    budget = info.get("budget") or 0

    return {
        "chapter": info["chapter"],
        "section": info["section"],
        "title": info["title"],
        "bibkeys": sorted(bibkeys),
        "count": len(bibkeys),
        "budget": budget,
        "density": len(bibkeys) / budget if budget > 0 else 0.0,
    }


def scan_all_citations(sections_dir: Path) -> list[dict]:
    """Scan all sections for citations."""
    results = []
    for info_path in sorted(sections_dir.rglob("section_info.json")):
        results.append(scan_section(info_path.parent))
    return results


# ---------------------------------------------------------------------------
# Bibkey verification
# ---------------------------------------------------------------------------

def load_bib_bibkeys(bib_path: Path) -> set[str]:
    """Load all bibkeys from a .bib file."""
    bibkeys = set()
    text = bib_path.read_text(encoding="utf-8")
    for m in re.finditer(r"@\w+\{(\s*)([^,\s]+)", text):
        bk = m.group(2).strip()
        if bk:
            bibkeys.add(bk)
    return bibkeys


def verify_bibkeys(cited_bibkeys: set[str], bib_path: Path) -> tuple[set[str], set[str]]:
    """Verify cited bibkeys exist in the bibliography.

    Returns (valid, missing).
    """
    if not bib_path.exists():
        return set(), cited_bibkeys
    bib_bibkeys = load_bib_bibkeys(bib_path)
    valid = cited_bibkeys & bib_bibkeys
    missing = cited_bibkeys - bib_bibkeys
    return valid, missing


def compute_density(cited: int, budget: int) -> float:
    """Compute citation density ratio."""
    return cited / budget if budget > 0 else 0.0


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(results: list[dict], missing_bibkeys: set[str],
                    reports_dir: Path) -> None:
    """Generate citation_report.md."""
    reports_dir.mkdir(parents=True, exist_ok=True)

    lines = ["# Citation Report\n"]
    lines.append(f"Sections scanned: {len(results)}\n")

    total_cited = sum(r["count"] for r in results)
    total_budget = sum(r["budget"] for r in results)
    overall_density = total_cited / total_budget if total_budget > 0 else 0.0
    lines.append(f"Total citations: {total_cited} / {total_budget} ({overall_density:.1%})\n")

    if missing_bibkeys:
        lines.append(f"\n## Missing Bibkeys ({len(missing_bibkeys)})\n")
        for bk in sorted(missing_bibkeys):
            lines.append(f"- `{bk}`\n")
    else:
        lines.append("\nNo missing bibkeys.\n")

    lines.append("\n## Per-Section Details\n")
    for r in results:
        status = "PASS" if r["density"] >= 0.8 else ("LOW" if r["density"] >= 0.6 else "FAIL")
        lines.append(f"### {r['section']} {r['title']}\n")
        lines.append(f"- Citations: {r['count']} / {r['budget']} ({r['density']:.1%}) — {status}\n")
        if r["bibkeys"]:
            lines.append(f"- Bibkeys: {', '.join(r['bibkeys'])}\n")

    (reports_dir / "citation_report.md").write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(sections_dir: Path | None = None, bib_path: Path | None = None,
        reports_dir: Path | None = None, chapter: int | None = None) -> dict:
    """Execute citation check. Returns stats."""
    cfg = load_config()
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")
    if bib_path is None:
        bib_path = resolve_path(cfg, "bib_file")
    if reports_dir is None:
        reports_dir = PROJECT_ROOT / "reports"

    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    results = scan_all_citations(sections_dir)

    # Filter by chapter if specified
    if chapter is not None:
        results = [r for r in results if r["chapter"] == chapter]

    # Collect all cited bibkeys
    all_cited = set()
    for r in results:
        all_cited.update(r["bibkeys"])

    # Verify against bib
    valid, missing = verify_bibkeys(all_cited, bib_path)

    # Generate report
    generate_report(results, missing, reports_dir)

    stats = {
        "sections_scanned": len(results),
        "total_citations": len(all_cited),
        "valid_bibkeys": len(valid),
        "missing_bibkeys": len(missing),
    }

    print(f"Scanned {stats['sections_scanned']} sections")
    print(f"Total unique citations: {stats['total_citations']}")
    if missing:
        print(f"WARNING: {len(missing)} missing bibkeys")
    else:
        print("All bibkeys valid")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 5a: Citation check")
    parser.add_argument("--chapter", type=int, default=None)
    args = parser.parse_args()
    run(chapter=args.chapter)


if __name__ == "__main__":
    main()

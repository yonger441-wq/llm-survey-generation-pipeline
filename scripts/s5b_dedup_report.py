"""Stage 5b: Dedup report — detect over-cited papers.

Count bibkey frequency across all sections, flag papers appearing in > N
sections, and generate reports/dedup_report.md.

Usage:
    python scripts/s5b_dedup_report.py [--chapter N]
"""

import argparse
import json
import re
from pathlib import Path

from llm_utils import PROJECT_ROOT, load_config, resolve_path


def extract_bibkeys(text: str) -> set[str]:
    """Extract unique bibkeys from text."""
    bibkeys = set()
    for m in re.finditer(r"\[@([^\]]+)\]", text):
        content = m.group(1)
        for part in content.split(";"):
            part = part.strip().lstrip("@")
            if part:
                bibkeys.add(part)
    return bibkeys


def count_frequency(sections_dir: Path, chapter: int | None = None) -> dict[str, int]:
    """Count how many sections each bibkey appears in."""
    freq: dict[str, int] = {}
    for info_path in sorted(sections_dir.rglob("section_info.json")):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        if chapter is not None and info["chapter"] != chapter:
            continue

        sec_dir = info_path.parent
        final_path = sec_dir / "final.md"
        draft_path = sec_dir / "draft.md"
        source = final_path if final_path.exists() else draft_path

        if not source.exists():
            continue

        text = source.read_text(encoding="utf-8")
        bibkeys = extract_bibkeys(text)
        for bk in bibkeys:
            freq[bk] = freq.get(bk, 0) + 1

    return freq


def flag_overused(freq: dict[str, int], threshold: int = 5) -> list[tuple[str, int]]:
    """Return bibkeys appearing in more than threshold sections, sorted by frequency."""
    flagged = [(bk, count) for bk, count in freq.items() if count > threshold]
    flagged.sort(key=lambda x: x[1], reverse=True)
    return flagged


def generate_report(freq: dict[str, int], flagged: list[tuple[str, int]],
                    reports_dir: Path, flag_threshold: int,
                    remove_threshold: int) -> None:
    """Generate dedup_report.md."""
    reports_dir.mkdir(parents=True, exist_ok=True)

    lines = ["# Dedup Report\n\n"]
    lines.append(f"Total unique bibkeys: {len(freq)}\n")
    lines.append(f"Papers cited in > {flag_threshold} sections: {len([f for f in flagged if f[1] <= remove_threshold])}\n")
    lines.append(f"Papers cited in > {remove_threshold} sections (candidates for removal): "
                 f"{len([f for f in flagged if f[1] > remove_threshold])}\n\n")

    if flagged:
        lines.append("## Flagged Papers\n\n")
        lines.append("| Bibkey | Sections | Status |\n")
        lines.append("|--------|----------|--------|\n")
        for bk, count in flagged:
            status = "REMOVE" if count > remove_threshold else "FLAG"
            lines.append(f"| `{bk}` | {count} | {status} |\n")
    else:
        lines.append("No over-cited papers found.\n")

    # Top 20 most-cited papers (even if not flagged)
    lines.append("\n## Top 20 Most-Cited Papers\n\n")
    top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:20]
    lines.append("| Bibkey | Sections |\n")
    lines.append("|--------|----------|\n")
    for bk, count in top:
        lines.append(f"| `{bk}` | {count} |\n")

    (reports_dir / "dedup_report.md").write_text("".join(lines), encoding="utf-8")


def run(sections_dir: Path | None = None, reports_dir: Path | None = None,
        chapter: int | None = None, flag_threshold: int = 5,
        remove_threshold: int = 8) -> dict:
    """Execute dedup report. Returns stats."""
    cfg = load_config()
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")
    if reports_dir is None:
        reports_dir = PROJECT_ROOT / "reports"

    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    freq = count_frequency(sections_dir, chapter)
    flagged = flag_overused(freq, flag_threshold)

    generate_report(freq, flagged, reports_dir, flag_threshold, remove_threshold)

    stats = {
        "total_unique_bibkeys": len(freq),
        "flagged": len([f for f in flagged if f[1] <= remove_threshold]),
        "to_remove": len([f for f in flagged if f[1] > remove_threshold]),
    }

    print(f"Total unique bibkeys: {stats['total_unique_bibkeys']}")
    print(f"Flagged (>{flag_threshold} sections): {stats['flagged']}")
    print(f"To remove (>{remove_threshold} sections): {stats['to_remove']}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 5b: Dedup report")
    parser.add_argument("--chapter", type=int, default=None)
    args = parser.parse_args()
    run(chapter=args.chapter)


if __name__ == "__main__":
    main()

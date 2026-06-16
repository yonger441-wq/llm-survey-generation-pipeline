"""Stage 5c: LLM-based quality evaluation of section drafts.

For each section, send final.md to LLM with quality_check_prompt.md,
parse structured JSON response, and generate reports/quality_report.md
with per-section scores and issues.

Usage:
    python scripts/s5c_quality_check.py [--chapter N] [--model MODEL]
"""

import argparse
import json
from pathlib import Path

from llm_utils import (
    PROJECT_ROOT,
    call_llm,
    extract_json,
    load_config,
    render_prompt_file,
    resolve_path,
)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def parse_quality_response(raw_text: str) -> dict:
    """Parse LLM quality evaluation JSON response."""
    # Try to extract a JSON object ({}) first, not array
    import re as _re
    match = _re.search(r"```(?:json)?\s*\n?(.*?)```", raw_text, _re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # Find the outermost { } object
        start = raw_text.find("{")
        if start < 0:
            raise ValueError("No JSON object found in quality check response")
        depth = 0
        for i in range(start, len(raw_text)):
            if raw_text[i] == "{":
                depth += 1
            elif raw_text[i] == "}":
                depth -= 1
            if depth == 0:
                json_str = raw_text[start:i + 1]
                break
        else:
            raise ValueError("No JSON object found in quality check response")

    data = json.loads(json_str)

    if not isinstance(data, dict):
        raise ValueError("Expected JSON object from quality check")

    return {
        "citation_count": data.get("citation_count", 0),
        "citation_budget": data.get("citation_budget", 0),
        "coverage_rate": data.get("coverage_rate", 0.0),
        "structural_completeness": data.get("structural_completeness", "partial"),
        "missing_sub_items": data.get("missing_sub_items", []),
        "quality_issues": data.get("quality_issues", []),
        "overall_score": data.get("overall_score", 0),
        "needs_revision": data.get("needs_revision", False),
    }


# ---------------------------------------------------------------------------
# Score aggregation
# ---------------------------------------------------------------------------

def aggregate_scores(results: list[dict]) -> dict:
    """Compute aggregate statistics from per-section results."""
    if not results:
        return {"avg_score": 0.0, "avg_coverage": 0.0, "total_sections": 0}

    n = len(results)
    avg_score = sum(r.get("overall_score", 0) for r in results) / n
    avg_coverage = sum(r.get("coverage_rate", 0) for r in results) / n

    return {
        "avg_score": avg_score,
        "avg_coverage": avg_coverage,
        "total_sections": n,
    }


def flag_sections(results: list[dict]) -> list[dict]:
    """Return sections that need revision (score < 6 or needs_revision=true)."""
    flagged = []
    for r in results:
        if r.get("needs_revision", False) or r.get("overall_score", 10) < 6:
            flagged.append(r)
    return flagged


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def find_section_dirs(sections_dir: Path, chapter: int | None = None) -> list[Path]:
    dirs = []
    for info_path in sorted(sections_dir.rglob("section_info.json")):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        if chapter is not None and info["chapter"] != chapter:
            continue
        dirs.append(info_path.parent)
    return dirs


def load_section_info(section_dir: Path) -> dict:
    return json.loads((section_dir / "section_info.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(results: list[dict], reports_dir: Path) -> None:
    """Generate quality_report.md."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    agg = aggregate_scores(results)
    flagged = flag_sections(results)

    lines = ["# Quality Report\n\n"]
    lines.append(f"Sections evaluated: {agg['total_sections']}\n")
    lines.append(f"Average score: {agg['avg_score']:.1f} / 10\n")
    lines.append(f"Average coverage: {agg['avg_coverage']:.1%}\n")
    lines.append(f"Sections needing revision: {len(flagged)}\n\n")

    if flagged:
        lines.append("## Flagged Sections\n\n")
        for r in flagged:
            lines.append(f"- **{r.get('section', '?')} {r.get('title', '')}**: "
                         f"score={r.get('overall_score', 0)}, "
                         f"coverage={r.get('coverage_rate', 0):.0%}\n")
        lines.append("\n")

    lines.append("## Per-Section Results\n\n")
    for r in results:
        score = r.get("overall_score", 0)
        status = "PASS" if score >= 6 and not r.get("needs_revision") else "NEEDS REVISION"
        lines.append(f"### {r.get('section', '?')} {r.get('title', '')} — {status}\n\n")
        lines.append(f"- Score: {score} / 10\n")
        lines.append(f"- Coverage: {r.get('coverage_rate', 0):.0%}\n")
        lines.append(f"- Completeness: {r.get('structural_completeness', '?')}\n")

        issues = r.get("quality_issues", [])
        if issues:
            lines.append(f"- Issues ({len(issues)}):\n")
            for issue in issues[:5]:
                lines.append(f"  - [{issue.get('type', '?')}] {issue.get('detail', '')}\n")

        missing = r.get("missing_sub_items", [])
        if missing:
            lines.append(f"- Missing sub-items: {', '.join(str(m) for m in missing)}\n")
        lines.append("\n")

    (reports_dir / "quality_report.md").write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(sections_dir: Path | None = None, reports_dir: Path | None = None,
        chapter: int | None = None, model: str | None = None) -> dict:
    """Execute quality evaluation. Returns summary stats."""
    cfg = load_config()
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")
    if reports_dir is None:
        reports_dir = PROJECT_ROOT / "reports"

    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    section_dirs = find_section_dirs(sections_dir, chapter)
    if not section_dirs:
        raise ValueError("No matching sections found")

    prompts_dir = resolve_path(cfg, "prompts_dir") if "prompts_dir" in cfg else None
    results = []
    errors = 0

    for sec_dir in section_dirs:
        info = load_section_info(sec_dir)
        section_id = info["section"]
        title = info["title"]

        final_path = sec_dir / "final.md"
        draft_path = sec_dir / "draft.md"
        source = final_path if final_path.exists() else draft_path

        if not source.exists():
            continue

        final_text = source.read_text(encoding="utf-8")
        print(f"  {section_id} {title}: evaluating...")

        replacements = {
            "SECTION_TITLE": title,
            "SECTION_GOAL": info.get("goal", ""),
            "BUDGET": str(info.get("budget", 0)),
            "FINAL_TEXT": final_text,
            "SUB_ITEMS": json.dumps(info.get("sub_items", []), ensure_ascii=False),
        }
        prompt = render_prompt_file("quality_check_prompt", replacements,
                                    prompts_dir=prompts_dir)

        try:
            raw = call_llm(prompt, cfg=cfg, model=model)
            result = parse_quality_response(raw)
        except Exception as e:
            print(f"    ERROR: {e}")
            result = {
                "overall_score": 0, "coverage_rate": 0.0,
                "needs_revision": True, "quality_issues": [],
                "missing_sub_items": [], "citation_count": 0,
                "citation_budget": info.get("budget", 0),
                "structural_completeness": "error",
            }
            errors += 1

        result["section"] = section_id
        result["title"] = title
        results.append(result)
        print(f"    Score: {result['overall_score']}/10, "
              f"coverage: {result['coverage_rate']:.0%}")

    # Generate report
    generate_report(results, reports_dir)

    agg = aggregate_scores(results)
    stats = {
        "sections_evaluated": len(results),
        "avg_score": agg["avg_score"],
        "avg_coverage": agg["avg_coverage"],
        "flagged": len(flag_sections(results)),
        "errors": errors,
    }

    print(f"\nEvaluated {stats['sections_evaluated']} sections")
    print(f"Average score: {stats['avg_score']:.1f}")
    print(f"Average coverage: {stats['avg_coverage']:.1%}")
    print(f"Flagged: {stats['flagged']}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 5c: Quality check")
    parser.add_argument("--chapter", type=int, default=None)
    parser.add_argument("--model", type=str, default=None)
    args = parser.parse_args()
    run(chapter=args.chapter, model=args.model)


if __name__ == "__main__":
    main()

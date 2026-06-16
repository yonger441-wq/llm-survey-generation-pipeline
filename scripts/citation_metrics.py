"""Unified citation metrics and gate reporting."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from citation_growth_utils import (
    count_citation_mentions,
    extract_cited_bibkeys,
    find_section_dirs,
    load_selected_bibkeys,
    load_selected_rows,
    load_section_info,
)
from llm_utils import load_config, resolve_path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_aux_bibcites(path: Path) -> set[str]:
    return set(re.findall(r"\\bibcite\{([^}]+)\}", _read_text(path)))


def build_metrics(cfg: dict | None = None, sections_dir: Path | None = None, output_dir: Path | None = None) -> dict:
    """Build citation growth metrics from the current workspace state."""
    cfg = cfg or load_config()
    sections_dir = sections_dir or resolve_path(cfg, "sections_dir")
    output_dir = output_dir or resolve_path(cfg, "output_dir")
    targets = cfg.get("targets", {})
    coverage_cfg = cfg.get("coverage", {})

    selected_unique = set()
    final_unique_cited = set()
    selected_usage: dict[str, set[str]] = defaultdict(set)
    section_metrics = []
    selected_rows = 0
    final_total_mentions = 0
    missing_final_count = 0
    missing_final_sections = []
    missing_draft_sections = []
    below_80 = 0
    below_70 = 0
    below_60 = 0

    for sec_dir in find_section_dirs(sections_dir):
        info = load_section_info(sec_dir)
        section_id = info["section"]
        selected_path = sec_dir / "selected.csv"
        draft_path = sec_dir / "draft.md"
        final_path = sec_dir / "final.md"
        selected_rows_list = load_selected_rows(selected_path) if selected_path.exists() else []
        selected_keys = {
            row.get("bibkey", "").strip()
            for row in selected_rows_list
            if row.get("bibkey", "").strip()
        }
        final_keys = extract_cited_bibkeys(_read_text(final_path)) if final_path.exists() else set()

        selected_rows += len(selected_rows_list)
        selected_unique.update(selected_keys)
        final_unique_cited.update(final_keys)
        for bibkey in selected_keys:
            selected_usage[bibkey].add(section_id)
        if final_path.exists():
            final_total_mentions += count_citation_mentions(_read_text(final_path))
        else:
            missing_final_count += 1
            missing_final_sections.append(section_id)
        if not draft_path.exists():
            missing_draft_sections.append(section_id)

        selected_count = len(selected_keys)
        cited_count = len(final_keys & selected_keys)
        coverage_rate = cited_count / selected_count if selected_count else 0.0
        if selected_count:
            if coverage_rate < 0.8:
                below_80 += 1
            if coverage_rate < 0.7:
                below_70 += 1
            if coverage_rate < 0.6:
                below_60 += 1

        section_metrics.append({
            "chapter": info["chapter"],
            "section": section_id,
            "title": info.get("title", ""),
            "selected": selected_count,
            "cited": cited_count,
            "potential_gain": max(selected_count - cited_count, 0),
            "rate": round(coverage_rate, 4),
            "has_draft": draft_path.exists(),
            "has_final": final_path.exists(),
        })

    compiled_unique_cited = None
    aux_path = output_dir / "paper.aux"
    if aux_path.exists():
        compiled_unique_cited = len(_load_aux_bibcites(aux_path))

    selected_unique_count = len(selected_unique)
    final_unique_cited_count = len(final_unique_cited)
    effective_compiled_cited = compiled_unique_cited if compiled_unique_cited is not None else final_unique_cited_count
    compiled_gap = max(final_unique_cited_count - effective_compiled_cited, 0)
    global_coverage = (
        final_unique_cited_count / selected_unique_count if selected_unique_count else 0.0
    )

    repeated_gt_5 = sum(1 for sections in selected_usage.values() if len(sections) > 5)
    repeated_gt_8 = sum(1 for sections in selected_usage.values() if len(sections) > 8)
    repeated_gt_10 = sum(1 for sections in selected_usage.values() if len(sections) > 10)

    metrics = {
        "selected_rows": selected_rows,
        "selected_unique": selected_unique_count,
        "final_unique_cited": final_unique_cited_count,
        "compiled_unique_cited": compiled_unique_cited,
        "compiled_gap": compiled_gap,
        "final_total_mentions": final_total_mentions,
        "selected_to_cited_coverage": round(global_coverage, 4),
        "missing_final_count": missing_final_count,
        "missing_final_sections": missing_final_sections,
        "missing_draft_count": len(missing_draft_sections),
        "missing_draft_sections": missing_draft_sections,
        "reuse_distribution": {
            "gt_5_sections": repeated_gt_5,
            "gt_8_sections": repeated_gt_8,
            "gt_10_sections": repeated_gt_10,
        },
        "coverage_buckets": {
            "lt_80": below_80,
            "lt_70": below_70,
            "lt_60": below_60,
        },
        "targets": {
            "phase1_unique_cited": targets.get("phase1_unique_cited"),
            "unique_cited": targets.get("unique_cited"),
            "selected_unique_floor": targets.get("selected_unique_floor"),
            "min_draft_rate": coverage_cfg.get("min_draft_rate"),
            "target_final_rate": coverage_cfg.get("target_final_rate"),
        },
        "gates": {
            "phase1_ready": effective_compiled_cited >= targets.get("phase1_unique_cited", 0),
            "phase2_ready": effective_compiled_cited >= targets.get("unique_cited", 0),
            "selected_pool_ready": selected_unique_count >= targets.get("selected_unique_floor", 0),
        },
        "per_section": section_metrics,
    }
    return metrics


def _build_markdown(metrics: dict) -> str:
    top_sections = sorted(metrics["per_section"], key=lambda item: item["rate"])[:10]
    lines = [
        "# Citation Metrics",
        "",
        f"- selected_rows: {metrics['selected_rows']}",
        f"- selected_unique: {metrics['selected_unique']}",
        f"- final_unique_cited: {metrics['final_unique_cited']}",
        f"- compiled_unique_cited: {metrics['compiled_unique_cited']}",
        f"- compiled_gap: {metrics['compiled_gap']}",
        f"- final_total_mentions: {metrics['final_total_mentions']}",
        f"- selected_to_cited_coverage: {metrics['selected_to_cited_coverage']:.2%}",
        f"- missing_final_count: {metrics['missing_final_count']}",
        f"- missing_draft_count: {metrics['missing_draft_count']}",
        f"- reuse >5 sections: {metrics['reuse_distribution']['gt_5_sections']}",
        f"- reuse >8 sections: {metrics['reuse_distribution']['gt_8_sections']}",
        f"- reuse >10 sections: {metrics['reuse_distribution']['gt_10_sections']}",
        f"- coverage <80%: {metrics['coverage_buckets']['lt_80']}",
        f"- coverage <70%: {metrics['coverage_buckets']['lt_70']}",
        f"- coverage <60%: {metrics['coverage_buckets']['lt_60']}",
        "",
        "## Gates",
        "",
        f"- phase1_ready: {metrics['gates']['phase1_ready']}",
        f"- phase2_ready: {metrics['gates']['phase2_ready']}",
        f"- selected_pool_ready: {metrics['gates']['selected_pool_ready']}",
        "",
        "## Lowest Coverage Sections",
        "",
    ]
    for section in top_sections:
        lines.append(
            f"- {section['section']} {section['title']}: selected={section['selected']}, "
            f"cited={section['cited']}, potential_gain={section['potential_gain']}, "
            f"rate={section['rate']:.2%}, final={section['has_final']}"
        )
    return "\n".join(lines) + "\n"


def run(cfg: dict | None = None, reports_dir: Path | None = None) -> dict:
    """Generate citation metrics JSON and Markdown reports."""
    cfg = cfg or load_config()
    reports_dir = reports_dir or resolve_path(cfg, "reports_dir")
    reports_dir.mkdir(parents=True, exist_ok=True)
    metrics = build_metrics(cfg=cfg)
    json_path = reports_dir / "citation_metrics.json"
    md_path = reports_dir / "citation_metrics.md"
    json_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(_build_markdown(metrics), encoding="utf-8")
    print(
        f"Citation metrics: selected_unique={metrics['selected_unique']}, "
        f"final_unique_cited={metrics['final_unique_cited']}, "
        f"compiled_unique_cited={metrics['compiled_unique_cited']}"
    )
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Generate citation metrics report")
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()

"""Batch runner for growing compiled unique citations toward 10k+."""

from __future__ import annotations

import argparse
import copy

import citation_metrics
import compile_pdf
import s1_build_candidates
import s2_annotate
import s3_generate_draft
import s4a_revise
import s4c_merge
import s5d_export_latex
import s5e_bib_export
from llm_utils import load_config


def _growth_cfg(cfg: dict) -> dict:
    growth = cfg.get("growth", {})
    return {
        "batch_size": int(growth.get("batch_size", 6)),
        "min_compiled_delta": int(growth.get("min_compiled_delta", 80)),
        "high_gain_gap_threshold": int(growth.get("high_gain_gap_threshold", 50)),
        "high_gain_selected_threshold": int(growth.get("high_gain_selected_threshold", 140)),
        "high_gain_rate_threshold": float(growth.get("high_gain_rate_threshold", 0.8)),
        "expansion_priority": list(growth.get("expansion_priority", [])),
    }


def _queue_groups(section: dict, growth_cfg: dict) -> tuple[int, int]:
    selected = int(section.get("selected", 0))
    rate = float(section.get("rate", 1.0))
    high_selected = selected >= growth_cfg["high_gain_selected_threshold"]
    if not section.get("has_final", False):
        return (0, 0)
    if high_selected and rate < 0.70:
        return (1, 0)
    if high_selected and 0.70 <= rate < 0.85:
        return (2, 0)
    if rate < 0.70:
        return (3, 0)
    if 0.70 <= rate < 0.80:
        return (4, 0)
    return (99, 0)


def build_priority_queue(metrics: dict, cfg: dict | None = None) -> list[str]:
    """Build the coverage + potential-gain rerun queue."""
    cfg = cfg or load_config()
    growth_cfg = _growth_cfg(cfg)
    ranked: list[tuple[tuple, str]] = []
    for item in metrics["per_section"]:
        group, _ = _queue_groups(item, growth_cfg)
        if group == 99:
            continue
        ranked.append(
            (
                (
                    group,
                    -int(item.get("potential_gain", 0)),
                    float(item.get("rate", 1.0)),
                    -int(item.get("selected", 0)),
                    item["section"],
                ),
                item["section"],
            )
        )
    ranked.sort(key=lambda pair: pair[0])
    return [section_id for _, section_id in ranked]


def build_expansion_queue(metrics: dict, cfg: dict | None = None) -> list[str]:
    """Build the targeted S1/S2 expansion queue."""
    cfg = cfg or load_config()
    growth_cfg = _growth_cfg(cfg)
    per_section = {item["section"]: item for item in metrics["per_section"]}
    queue: list[str] = []

    for section_id in growth_cfg["expansion_priority"]:
        item = per_section.get(section_id)
        if not item:
            continue
        if item.get("selected", 0) < growth_cfg["high_gain_selected_threshold"] or item.get("rate", 1.0) < 0.80:
            queue.append(section_id)

    remaining = sorted(
        (
            item for item in metrics["per_section"]
            if item["section"] not in queue
            and item.get("rate", 1.0) < 0.80
            and item.get("selected", 0) < growth_cfg["high_gain_selected_threshold"]
        ),
        key=lambda item: (
            float(item.get("rate", 1.0)),
            -int(item.get("potential_gain", 0)),
            item["section"],
        ),
    )
    queue.extend(item["section"] for item in remaining)
    return queue


def _expand_section(section_id: str, expanded_cfg: dict, model: str | None) -> None:
    s1_build_candidates.run(section=section_id, cfg=expanded_cfg)
    s2_annotate.run(section=section_id, model=model, force=True, cfg=expanded_cfg)


def _refresh_outputs() -> dict:
    s4c_merge.run()
    s5d_export_latex.run()
    s5e_bib_export.run()
    compile_stats = compile_pdf.run()
    metrics = citation_metrics.run()
    return {
        "compile_stats": compile_stats,
        "metrics": metrics,
    }


def _print_batch_summary(batch_no: int, mode: str, batch: list[str], before: dict, after: dict) -> int:
    before_compiled = before.get("compiled_unique_cited") or before.get("final_unique_cited") or 0
    after_compiled = after.get("compiled_unique_cited") or after.get("final_unique_cited") or 0
    delta = after_compiled - before_compiled
    print(
        f"\nBatch {batch_no} [{mode}] {batch}: "
        f"selected_unique={after['selected_unique']}, "
        f"final_unique_cited={after['final_unique_cited']}, "
        f"compiled_unique_cited={after['compiled_unique_cited']}, "
        f"delta={delta:+d}"
    )
    return delta


def run(
    dry_run: bool = False,
    limit: int | None = None,
    model: str | None = None,
    expand_selection: bool = False,
) -> dict:
    """Run the citation growth workflow in batched closed loops."""
    cfg = load_config()
    growth_cfg = _growth_cfg(cfg)
    metrics = citation_metrics.build_metrics(cfg=cfg)
    priority_queue = build_priority_queue(metrics, cfg=cfg)
    expansion_queue = build_expansion_queue(metrics, cfg=cfg)
    if limit is not None:
        priority_queue = priority_queue[:limit]
        expansion_queue = expansion_queue[:limit]

    print(
        f"Queue size: revise={len(priority_queue)}, expand={len(expansion_queue)} "
        f"(lt_60={metrics['coverage_buckets']['lt_60']}, "
        f"lt_70={metrics['coverage_buckets']['lt_70']}, "
        f"lt_80={metrics['coverage_buckets']['lt_80']})"
    )
    print(
        f"Current selected_unique={metrics['selected_unique']}, "
        f"final_unique_cited={metrics['final_unique_cited']}, "
        f"compiled_unique_cited={metrics['compiled_unique_cited']}"
    )

    if dry_run:
        print("Expansion queue:")
        for idx, section_id in enumerate(expansion_queue[:growth_cfg["batch_size"]], 1):
            print(f"  E{idx}. {section_id}")
        print("Revision queue:")
        for idx, section_id in enumerate(priority_queue[:growth_cfg["batch_size"]], 1):
            print(f"  R{idx}. {section_id}")
        return {
            "dry_run": True,
            "expansion_queue": expansion_queue,
            "revision_queue": priority_queue,
        }

    expanded_cfg = copy.deepcopy(cfg)
    expanded_cfg["budget"]["target_total"] = expanded_cfg["budget"].get(
        "phase2_target_total",
        expanded_cfg["budget"]["target_total"],
    )

    processed: list[str] = []
    batch_results: list[dict] = []
    batch_no = 0
    next_mode = "expand" if expand_selection or metrics["selected_unique"] < cfg.get("targets", {}).get("selected_unique_floor", 11800) else "revise"

    while True:
        metrics = citation_metrics.build_metrics(cfg=cfg)
        priority_queue = [section_id for section_id in build_priority_queue(metrics, cfg=cfg) if section_id not in processed]
        expansion_queue = [section_id for section_id in build_expansion_queue(metrics, cfg=cfg) if section_id not in processed]
        if limit is not None:
            remaining = max(limit - len(processed), 0)
            priority_queue = priority_queue[:remaining]
            expansion_queue = expansion_queue[:remaining]
        if limit is not None and len(processed) >= limit:
            break
        if not priority_queue and not expansion_queue:
            break

        if next_mode == "expand" and expansion_queue:
            batch = expansion_queue[:growth_cfg["batch_size"]]
            mode = "expand"
        elif priority_queue:
            batch = priority_queue[:growth_cfg["batch_size"]]
            mode = "revise"
        elif expansion_queue:
            batch = expansion_queue[:growth_cfg["batch_size"]]
            mode = "expand"
        else:
            break

        before_metrics = citation_metrics.build_metrics(cfg=cfg)
        batch_no += 1
        print(f"\n=== Batch {batch_no} [{mode}] ===")
        for section_id in batch:
            print(f"  -> {section_id}")
            if mode == "expand":
                _expand_section(section_id, expanded_cfg, model)
            s3_generate_draft.run(section=section_id, model=model, force=True)
            s4a_revise.run(section=section_id, model=model, force=True)

        refresh = _refresh_outputs()
        after_metrics = refresh["metrics"]
        delta = _print_batch_summary(batch_no, mode, batch, before_metrics, after_metrics)
        batch_results.append({
            "batch": batch,
            "mode": mode,
            "delta": delta,
            "metrics": after_metrics,
            "healthy": refresh["compile_stats"].get("healthy", False),
        })
        processed.extend(batch)

        if delta < growth_cfg["min_compiled_delta"] and after_metrics["selected_unique"] < cfg.get("targets", {}).get("selected_unique_floor", 11800):
            next_mode = "expand"
        else:
            next_mode = "revise"

        if after_metrics["gates"]["phase2_ready"]:
            break

    final_metrics = citation_metrics.build_metrics(cfg=cfg)
    return {
        "processed_sections": processed,
        "batches": batch_results,
        "metrics": final_metrics,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the 10k+ citation growth workflow")
    parser.add_argument("--dry-run", action="store_true", help="Show the rerun queues without executing")
    parser.add_argument("--limit", type=int, default=None, help="Only process up to N queued sections")
    parser.add_argument("--model", type=str, default=None, help="Override the LLM model")
    parser.add_argument(
        "--expand-selection",
        action="store_true",
        help="Start from expansion batches before revision batches",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run, limit=args.limit, model=args.model, expand_selection=args.expand_selection)


if __name__ == "__main__":
    main()

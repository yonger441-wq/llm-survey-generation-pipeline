"""Pipeline orchestrator for a long-form LLM survey workflow.

Runs stages 0-5 in order, with optional chapter filtering and stage range
selection. Supports ``--dry-run`` for planning.

Usage:
    python scripts/run_pipeline.py --from-stage 0 --to-stage 5 --chapter 2
    python scripts/run_pipeline.py --from-stage 3 --chapter 5
    python scripts/run_pipeline.py --from-stage 5 --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from llm_utils import load_config, resolve_path


STAGE_NAMES = {
    0: "s0_setup",
    1: "s1_build_candidates",
    2: "s2_annotate",
    3: "s3_generate_draft",
    4: "s4_revise_and_merge",
    5: "s5_checks_and_compile",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LLM Survey Pipeline Orchestrator"
    )
    parser.add_argument(
        "--from-stage",
        type=int,
        default=0,
        help="Start from stage N (default: 0)",
    )
    parser.add_argument(
        "--to-stage",
        type=int,
        default=5,
        help="End at stage N (default: 5)",
    )
    parser.add_argument(
        "--chapter",
        type=int,
        default=None,
        help="Only process chapter N",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show plan without executing",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model override for LLM-backed stages",
    )
    return parser.parse_args(argv)


def resolve_stages(from_stage: int, to_stage: int) -> list[int]:
    """Determine which stages to run."""
    return list(range(from_stage, to_stage + 1))


def verify_stage(
    stage: int,
    sections_dir: Path,
    chapter: int | None = None,
) -> bool:
    """Quick verification that a stage's outputs exist."""
    if stage == 0:
        manifest = sections_dir / "sections_manifest.json"
        return manifest.exists()

    if stage == 1:
        for info_path in sections_dir.rglob("section_info.json"):
            info = json.loads(info_path.read_text(encoding="utf-8"))
            if chapter is not None and info["chapter"] != chapter:
                continue
            if not (info_path.parent / "candidates.csv").exists():
                return False
        return True

    return sections_dir.exists()


def run(
    from_stage: int = 0,
    to_stage: int = 5,
    chapter: int | None = None,
    dry_run: bool = False,
    sections_dir: Path | None = None,
    model: str | None = None,
) -> dict:
    """Execute the pipeline and return summary stats."""
    cfg = load_config()
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")

    stages = resolve_stages(from_stage, to_stage)

    print(f"LLM Survey Pipeline: stages {from_stage}->{to_stage}")
    if chapter:
        print(f"  Chapter filter: {chapter}")
    print()

    if dry_run:
        for stage in stages:
            print(f"  [{stage}] {STAGE_NAMES.get(stage, 'unknown')}")
        print("\n[DRY RUN] No stages executed.")
        return {"dry_run": True, "stages_planned": len(stages)}

    stats = {"stages_run": 0, "errors": 0}

    for stage in stages:
        name = STAGE_NAMES.get(stage, f"stage_{stage}")
        print(f"\n{'=' * 60}")
        print(f"Stage {stage}: {name}")
        print(f"{'=' * 60}")

        try:
            if stage == 0:
                import s0_setup

                s0_setup.run(chapter=chapter)
            elif stage == 1:
                import s1_build_candidates

                s1_build_candidates.run(chapter=chapter)
            elif stage == 2:
                import s2_annotate

                s2_annotate.run(chapter=chapter, model=model)
            elif stage == 3:
                import s3_generate_draft

                s3_generate_draft.run(chapter=chapter, model=model)
            elif stage == 4:
                import s4a_revise
                import s4b_chapter_intro
                import s4c_merge

                s4a_revise.run(chapter=chapter, model=model)
                s4b_chapter_intro.run(chapter=chapter, model=model)
                s4c_merge.run(chapter=chapter)
            elif stage == 5:
                import citation_metrics
                import s5a_citation_check
                import s5b_dedup_report
                import s5c_quality_check
                import s5d_export_latex
                import s5e_bib_export
                import s5f_compile

                s5a_citation_check.run(chapter=chapter)
                s5b_dedup_report.run(chapter=chapter)
                s5c_quality_check.run(chapter=chapter, model=model)
                s5d_export_latex.run(chapter=chapter)
                s5e_bib_export.run()
                s5f_compile.run()
                citation_metrics.run()
            else:
                print(f"  Unknown stage: {stage}")
                continue

            stats["stages_run"] += 1
            print(f"  Stage {stage} complete.")

        except Exception as exc:
            print(f"  ERROR in stage {stage}: {exc}")
            stats["errors"] += 1
            break

    print(f"\n{'=' * 60}")
    print(f"Pipeline complete: {stats['stages_run']} stages run")
    if stats["errors"]:
        print(f"Errors: {stats['errors']}")
    return stats


def main() -> None:
    args = parse_args()
    stats = run(
        from_stage=args.from_stage,
        to_stage=args.to_stage,
        chapter=args.chapter,
        dry_run=args.dry_run,
        model=args.model,
    )
    if stats.get("errors", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

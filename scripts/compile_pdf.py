#!/usr/bin/env python3
"""Compile the survey paper to PDF using a single XeLaTeX + BibTeX pipeline."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from citation_compile_utils import (
    filter_citations_file,
    generate_citation_health_report,
    normalize_bbl_natexlab,
)
from llm_utils import PROJECT_ROOT, load_config, resolve_path


def build_compile_commands(
    latex_cmd: str,
    bibtex_cmd: str,
    tex_file: str,
    work_dir: str,
) -> list[tuple[list[str], str]]:
    """Build the xelatex/bibtex command sequence."""
    return [
        ([latex_cmd, "-interaction=nonstopmode", tex_file], work_dir),
        ([bibtex_cmd, "paper"], work_dir),
        ([latex_cmd, "-interaction=nonstopmode", tex_file], work_dir),
        ([latex_cmd, "-interaction=nonstopmode", tex_file], work_dir),
    ]


def find_executables() -> tuple[str, str]:
    """Find ``xelatex`` and ``bibtex`` from environment variables or PATH."""
    xelatex = os.environ.get("XELATEX_CMD") or shutil.which("xelatex") or ""
    bibtex = os.environ.get("BIBTEX_CMD") or shutil.which("bibtex") or ""

    return xelatex, bibtex


def clean_artifacts(output_dir: Path, stem: str = "paper") -> None:
    """Remove stale compile artifacts before a clean rebuild."""
    for ext in ["aux", "bbl", "blg", "log", "out", "fls", "fdb_latexmk", "synctex.gz", "pdf"]:
        path = output_dir / f"{stem}.{ext}"
        if path.exists():
            path.unlink()


def ensure_used_references_bibliography(tex_path: Path, output_dir: Path) -> None:
    """Switch bibliography target to ``used_references`` when available."""
    used_bib = output_dir / "used_references.bib"
    if not used_bib.exists() or not tex_path.exists():
        return
    text = tex_path.read_text(encoding="utf-8")
    updated = text.replace(r"\bibliography{references}", r"\bibliography{used_references}")
    if updated != text:
        tex_path.write_text(updated, encoding="utf-8")


def run_cmd(cmd: list[str], cwd: str, step_name: str, timeout: int = 600) -> subprocess.CompletedProcess:
    """Run one compile command and print a compact summary."""
    print(f"\n{step_name}...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        cwd=cwd,
        timeout=timeout,
        encoding="utf-8",
        errors="ignore",
    )
    print(f"  rc={result.returncode}, stdout={len(result.stdout or '')} chars")
    stderr = (result.stderr or "").strip()
    if result.returncode != 0 and stderr:
        for line in [line for line in stderr.splitlines() if "error" in line.lower()][:5]:
            print(f"  ERROR: {line}")
    return result


def normalize_bbl_file(bbl_path: Path) -> dict:
    """Normalize natbib suffixes inside ``paper.bbl``."""
    if not bbl_path.exists():
        return {"entries": 0, "groups": 0, "suffixes_assigned": 0, "parse_failures": 0, "changed_entries": 0}

    original = bbl_path.read_text(encoding="utf-8", errors="ignore")
    normalized, stats = normalize_bbl_natexlab(original)
    if normalized != original:
        bbl_path.write_text(normalized, encoding="utf-8")
        print(
            "  Normalized .bbl:"
            f" {stats['changed_entries']} entries updated across {stats['groups']} author-year groups"
        )
    else:
        print("  Normalized .bbl: no changes needed")
    return stats


def _summarize_health(health: dict) -> None:
    print("\nCitation health summary:")
    print(f"  cited keys: {health['cited_key_count']}")
    print(f"  .bbl bibitems: {health['bibitem_count']}")
    print(f"  .aux bibcites: {health['aux_bibcite_count']}")

    if health["missing_bibcites"]:
        sample = ", ".join(health["missing_bibcites"][:10])
        print(f"  ERROR: missing \\bibcite entries for {len(health['missing_bibcites'])} keys: {sample}")
    if health["missing_bibitems"]:
        sample = ", ".join(health["missing_bibitems"][:10])
        print(f"  ERROR: missing \\bibitem entries for {len(health['missing_bibitems'])} keys: {sample}")
    if health["invalid_natexlab_labels"]:
        sample = ", ".join(repr(x) for x in health["invalid_natexlab_labels"][:10])
        print(f"  ERROR: invalid \\natexlab labels remain: {sample}")
    if health["undefined_citations"]:
        sample = ", ".join(health["undefined_citations"][:10])
        print(f"  ERROR: undefined citations remain: {sample}")
    if health["question_mark_warnings"]:
        print(f"  ERROR: natbib still reports question-mark warnings ({len(health['question_mark_warnings'])})")


def run(output_dir: Path | None = None, sections_dir: Path | None = None) -> dict:
    """Execute the unified PDF compile pipeline."""
    cfg = load_config()
    if output_dir is None:
        output_dir = resolve_path(cfg, "output_dir")
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")

    tex_path = output_dir / "paper.tex"
    if not tex_path.exists():
        raise FileNotFoundError(f"paper.tex not found at {tex_path}")

    xelatex, bibtex = find_executables()
    if not xelatex or not bibtex:
        raise RuntimeError(f"xelatex or bibtex not found. xelatex={xelatex}, bibtex={bibtex}")

    print("Step 0: Filtering hallucinated citations and fixing wrapped cites...")
    filter_stats = filter_citations_file(tex_path, sections_dir)
    ensure_used_references_bibliography(tex_path, output_dir)
    print(
        f"  Valid bibkeys: {filter_stats['valid_bibkeys']}, "
        f"removed invalid cite keys: {filter_stats['removed_citations']}"
    )

    clean_artifacts(output_dir, "paper")

    commands = build_compile_commands(xelatex, bibtex, "paper.tex", str(output_dir))
    run_cmd(commands[0][0], commands[0][1], "Step 1: xelatex (first pass)")
    run_cmd(commands[1][0], commands[1][1], "Step 2: bibtex")

    bbl_stats = normalize_bbl_file(output_dir / "paper.bbl")

    run_cmd(commands[2][0], commands[2][1], "Step 3: xelatex (second pass)")
    run_cmd(commands[3][0], commands[3][1], "Step 4: xelatex (third pass)")

    pdf_path = output_dir / "paper.pdf"
    stats = {
        "pdf_exists": pdf_path.exists(),
        "filter_stats": filter_stats,
        "bbl_stats": bbl_stats,
    }
    if pdf_path.exists():
        stats["pdf_size_mb"] = pdf_path.stat().st_size / (1024 * 1024)

    health = generate_citation_health_report(
        tex_path=tex_path,
        bbl_path=output_dir / "paper.bbl",
        aux_path=output_dir / "paper.aux",
        log_path=output_dir / "paper.log",
    )
    stats["health"] = health

    if (
        not health["healthy"]
        and health["cited_key_count"] > 0
        and health["bibitem_count"] == 0
        and health["aux_bibcite_count"] == 0
    ):
        print("\nDetected empty bibliography state after first compile pass; retrying bibtex and final LaTeX passes once...")
        run_cmd(commands[1][0], commands[1][1], "Retry 1: bibtex")
        bbl_stats = normalize_bbl_file(output_dir / "paper.bbl")
        run_cmd(commands[2][0], commands[2][1], "Retry 2: xelatex (second pass)")
        run_cmd(commands[3][0], commands[3][1], "Retry 3: xelatex (third pass)")
        health = generate_citation_health_report(
            tex_path=tex_path,
            bbl_path=output_dir / "paper.bbl",
            aux_path=output_dir / "paper.aux",
            log_path=output_dir / "paper.log",
        )
        stats["health"] = health
        stats["bbl_stats"] = bbl_stats

    _summarize_health(health)

    if stats["pdf_exists"]:
        print(f"\npaper.pdf created ({stats['pdf_size_mb']:.1f} MB)")
    else:
        print("\nFAILED: paper.pdf not created")

    stats["healthy"] = bool(stats["pdf_exists"] and health["healthy"])
    if stats["healthy"]:
        print("All citation checks passed.")
    else:
        print("Citation pipeline is still unhealthy.")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile PDF with citation cleanup and health checks")
    args = parser.parse_args()
    stats = run()
    if not stats.get("healthy"):
        raise SystemExit(1)


if __name__ == "__main__":
    os.chdir(PROJECT_ROOT)
    main()

"""Stage 5f: Compile PDF via the unified XeLaTeX + BibTeX pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

import compile_pdf
from citation_compile_utils import find_undefined_citations


def build_compile_commands(pdflatex: str, bibtex: str, tex_file: str, work_dir: str) -> list[tuple[list[str], str]]:
    """Backward-compatible command builder used by tests."""
    return compile_pdf.build_compile_commands(pdflatex, bibtex, tex_file, work_dir)


def check_missing_citations(log_path: Path) -> list[str]:
    """Return unresolved cite keys from the LaTeX log."""
    if not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    return find_undefined_citations(text)


def run() -> dict:
    """Execute the unified compile pipeline."""
    return compile_pdf.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 5f: Compile PDF")
    args = parser.parse_args()
    stats = run()
    if not stats.get("healthy"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

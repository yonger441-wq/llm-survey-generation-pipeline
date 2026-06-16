"""Stage 5d: Export to LaTeX via Pandoc.

Merge all chapter files into full_paper.md, convert to LaTeX with
Pandoc (--natbib), and post-process for natbib round style.

Usage:
    python scripts/s5d_export_latex.py [--chapter N]
"""

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

from llm_utils import PROJECT_ROOT, load_config, resolve_path

PAPER_TITLE = r"LLM$^2$: All You Need to Know About Large Language Models"
PAPER_AUTHOR = r"""\author{
  {\large Project Maintainers}\\[0.7em]
  Public demo configuration; replace with manuscript metadata before submission.
}"""
PAPER_ABSTRACT = (
    "Large language models (LLMs) have rapidly evolved from large-scale text generators into "
    "general-purpose foundation models that support reasoning, multimodal understanding, tool use, "
    "agentic workflows, scientific discovery, and domain-specific deployment. At the same time, the "
    "literature has expanded into a highly fragmented ecosystem spanning architectural evolution, "
    "alignment and post-training, retrieval-augmented generation, knowledge editing, evaluation, "
    "safety, efficiency, and real-world systems. This survey provides a comprehensive and structured "
    "synthesis of that landscape. We organize the field around the full LLM lifecycle, tracing the "
    "development of model architectures, scaling practices, adaptation paradigms, inference-time "
    "reasoning, multimodal extensions, agent systems, and specialized applications, while also "
    "surveying the benchmarks, reliability challenges, and governance concerns that shape trustworthy "
    "deployment. Beyond cataloging methods, we highlight recurring design tensions, including breadth "
    "versus depth, capability versus controllability, and scaling versus efficiency, and we connect "
    "technical progress to the broader methodological problem of how such a vast literature can be "
    "systematically synthesized. The resulting survey offers a unified map of contemporary LLM "
    "research, clarifies core terminology and boundaries, identifies persistent open problems, and "
    "provides a foundation for future work on robust, interpretable, and practically deployable large "
    "model systems."
)
PAPER_KEYWORDS = [
    "Large language models",
    "Foundation models",
    "Literature survey",
    "Architectural evolution",
    "Alignment",
    "Reasoning",
    "Agents",
    "Multimodality",
    "Retrieval-augmented generation",
    "Knowledge editing",
    "Scientific discovery",
    "Evaluation",
    "Safety and trustworthiness",
    "Efficient inference",
    "Deployment",
]
FRONT_MATTER_START = "% FRONT_MATTER_START"
FRONT_MATTER_END = "% FRONT_MATTER_END"


def find_pandoc(pandoc_cmd: str = "") -> str:
    """Resolve Pandoc from PATH or common local install locations."""
    if pandoc_cmd:
        return pandoc_cmd
    found = shutil.which("pandoc")
    if found:
        return found
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(local_appdata) / "Pandoc" / "pandoc.exe" if local_appdata else None,
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)
    return ""


def normalize_inline_math(text: str) -> str:
    """Repair common Pandoc inline-math breakage in generated survey text."""
    text = re.sub(
        r"\\mathbb\{([A-Za-z])\}\\\^\{\}\\\{([^}]*)\\\}",
        lambda m: rf"\mathbb{{{m.group(1)}}}^{{{m.group(2)}}}",
        text,
    )

    def wrap_math_parenthetical(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        inner = re.sub(
            r"\\mathbb\{([A-Za-z])\}\\\^\{\}\\\{([^}]*)\\\}",
            lambda m: rf"\mathbb{{{m.group(1)}}}^{{{m.group(2)}}}",
            inner,
        )
        inner = re.sub(r"\s+", " ", inner).strip()
        return rf"\( {inner} \)"

    mathish_parenthetical = re.compile(
        r"(?<!\\)\(\s*((?:(?:[^()]|\([^()]*\)){0,240}?"
        r"(?:\\mathbb|\\Delta|\\times|\\min|\\ll|\\in|=)"
        r"(?:[^()]|\([^()]*\)){0,240}?))\s*\)",
        flags=re.DOTALL,
    )
    return mathish_parenthetical.sub(wrap_math_parenthetical, text)


def merge_chapters(chapters_dir: Path, output_path: Path) -> None:
    """Merge chapter files (ch01.md, ch02.md, ...) into full_paper.md."""
    parts = []
    chapter_files = sorted(chapters_dir.glob("ch*.md"))
    for cf in chapter_files:
        text = cf.read_text(encoding="utf-8").strip()
        if text:
            parts.append(text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(parts) + "\n" if parts else "",
                           encoding="utf-8")


def build_front_matter_block() -> str:
    """Build the injected title/author/abstract/keywords block."""
    keywords = "; ".join(PAPER_KEYWORDS)
    return (
        FRONT_MATTER_START + "\n"
        + r"\begin{center}" + "\n"
        + r"{\fontsize{24}{28}\selectfont\sffamily\bfseries " + PAPER_TITLE + r"\par}" + "\n"
        + r"\vspace{1.2em}" + "\n"
        + r"{\large Project Maintainers\par}" + "\n"
        + r"\vspace{0.8em}" + "\n"
        + r"{\normalsize Public demo configuration; replace with manuscript metadata before submission.\par}" + "\n"
        + r"\vspace{0.45em}" + "\n"
        + r"\end{center}" + "\n\n"
        + r"\begin{abstract}" + "\n"
        + f"{PAPER_ABSTRACT}\n"
        + r"\end{abstract}" + "\n\n"
        + r"\noindent\textbf{Keywords:} " + keywords + "\n\n"
        + FRONT_MATTER_END + "\n\n"
    )


def replace_between_markers(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    """Replace the slice from start_marker up to end_marker with replacement."""
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker)) if start != -1 else -1
    if start == -1 or end == -1:
        return text
    return text[:start] + replacement + text[end:]


def inject_front_matter(text: str) -> str:
    """Inject title, author, abstract, and keywords into Pandoc LaTeX output."""
    if r"\title{" not in text:
        author_match = re.search(r"\\author\{\}", text)
        if author_match:
            text = text[:author_match.start()] + rf"\title{{{PAPER_TITLE}}}" + "\n\n" + text[author_match.start():]
        else:
            text = text.replace(r"\begin{document}", rf"\title{{{PAPER_TITLE}}}" + "\n\n" + r"\begin{document}", 1)
    else:
        text = re.sub(r"\\title\{.*?\}", rf"\title{{{PAPER_TITLE}}}", text, count=1, flags=re.DOTALL)

    if r"\author{}" in text:
        text = text.replace(r"\author{}", PAPER_AUTHOR, 1)
    else:
        updated = replace_between_markers(text, r"\author{", r"\date{", PAPER_AUTHOR + "\n")
        text = updated if updated != text else text

    if r"\date{}" not in text:
        updated = replace_between_markers(text, r"\date{", r"\begin{document}", r"\date{}" + "\n\n")
        text = updated if updated != text else text

    front_matter = build_front_matter_block()
    if FRONT_MATTER_START in text and FRONT_MATTER_END in text:
        start = text.find(FRONT_MATTER_START)
        end = text.find(FRONT_MATTER_END, start)
        if start != -1 and end != -1:
            text = text[:start] + front_matter + text[end + len(FRONT_MATTER_END):]
    elif r"\maketitle" in text:
        text = re.sub(
            r"\\maketitle.*?(?=(\\section|\\subsection|\\bibliographystyle|\\bibliography|\\end\{document\}))",
            lambda _: front_matter,
            text,
            count=1,
            flags=re.DOTALL,
        )
    else:
        text = text.replace(r"\begin{document}", r"\begin{document}" + "\n\n" + front_matter, 1)
    return text


def run_pandoc(input_path: Path, output_path: Path, bib_path: Path,
               pandoc_cmd: str = "") -> bool:
    """Run Pandoc to convert Markdown to LaTeX with natbib."""
    pandoc = find_pandoc(pandoc_cmd)
    if not pandoc:
        print("ERROR: Pandoc not found. Install Pandoc and ensure it's in PATH.")
        return False

    cmd = [
        pandoc,
        str(input_path),
        "--from", "markdown",
        "--to", "latex",
        "--standalone",
        "--natbib",
        "--output", str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore")
    if result.returncode != 0:
        print(f"Pandoc error: {result.stderr.strip() or result.stdout.strip()}")
        return False

    # Post-process
    text = output_path.read_text(encoding="utf-8")

    # Fix natbib to use [round] style
    text = text.replace(r"\usepackage[]{natbib}", r"\usepackage[round]{natbib}")

    # Fix hypersetup
    text = re.sub(
        r"\\hypersetup\{.*?\}\}",
        r"\\hypersetup{colorlinks=true, citecolor=teal, linkcolor=blue, urlcolor=magenta}",
        text, flags=re.DOTALL,
    )
    text = normalize_inline_math(text)
    text = inject_front_matter(text)

    bibliography_name = bib_path.stem

    # Add \bibliography{...} before \end{document}
    if rf"\bibliography{{{bibliography_name}}}" not in text:
        text = text.replace(r"\end{document}",
                            rf"\bibliography{{{bibliography_name}}}" + "\n" + r"\end{document}")

    # Ensure \bibliographystyle{plainnat}
    if r"\bibliographystyle{plainnat}" not in text:
        text = text.replace(
            rf"\bibliography{{{bibliography_name}}}",
            r"\bibliographystyle{plainnat}" + "\n" + rf"\bibliography{{{bibliography_name}}}",
        )

    output_path.write_text(text, encoding="utf-8")
    return True


def run(chapter: int | None = None) -> bool:
    """Execute LaTeX export."""
    cfg = load_config()
    output_dir = resolve_path(cfg, "output_dir")
    chapters_dir = output_dir / "chapters"

    if not chapters_dir.exists():
        print(f"ERROR: No chapters directory at {chapters_dir}")
        return False

    # Merge chapters
    full_paper_path = output_dir / "full_paper.md"
    merge_chapters(chapters_dir, full_paper_path)
    print(f"Merged chapters → {full_paper_path}")

    # Run Pandoc
    tex_path = output_dir / "paper.tex"
    used_bib_path = output_dir / "used_references.bib"
    bib_path = used_bib_path if used_bib_path.exists() else resolve_path(cfg, "bib_file")

    success = run_pandoc(full_paper_path, tex_path, bib_path)
    if success:
        print(f"Exported LaTeX → {tex_path}")
    return success


def main():
    parser = argparse.ArgumentParser(description="Stage 5d: Export to LaTeX")
    parser.add_argument("--chapter", type=int, default=None)
    args = parser.parse_args()
    success = run(chapter=args.chapter)
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

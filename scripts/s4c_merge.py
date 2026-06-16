"""Stage 4c: Merge chapter intro + section finals into chapter files.

For each chapter, concatenate chapter_intro.md + all section final.md files
in order, adjust heading levels, and save as 4_output/chapters/chXX.md.

Usage:
    python scripts/s4c_merge.py [--chapter N]
"""

import argparse
import json
import re
from pathlib import Path

from llm_utils import PROJECT_ROOT, load_config, resolve_path


def find_chapter_dirs(sections_dir: Path, chapter: int | None = None) -> list[tuple[int, Path]]:
    """Find chapter directories with their numbers."""
    chapters = {}
    for info_path in sections_dir.rglob("section_info.json"):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        ch = info["chapter"]
        if chapter is not None and ch != chapter:
            continue
        ch_dir = info_path.parent.parent
        if ch not in chapters:
            chapters[ch] = ch_dir
    return [(k, chapters[k]) for k in sorted(chapters.keys())]


def get_section_dirs(chapter_dir: Path) -> list[Path]:
    """Get section directories within a chapter, ordered by section number."""
    dirs = []
    for info_path in chapter_dir.rglob("section_info.json"):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        sec = info.get("section", "")
        # Parse "5.10" -> (5, 10) for proper numeric sorting
        parts = sec.split(".")
        key = (int(parts[0]) if parts else 0, int(parts[1]) if len(parts) > 1 else 0)
        dirs.append((key, info_path.parent))
    dirs.sort(key=lambda x: x[0])
    return [d[1] for d in dirs]


def fix_section_headings(text: str, ch_num: int, sec_num: int) -> str:
    """Fix heading levels and add section numbers.

    Transforms:
      ## Title -> ## N.M Title
      ##### X.Y.Z Sub -> ### N.M.Z Sub  (renumber to match assigned sec_num)
    """
    lines = text.split("\n")
    result = []
    new_prefix = f"{ch_num}.{sec_num}"
    for line in lines:
        # ##### X.Y.Z style -> promote to ### and renumber
        m4 = re.match(r"^#####\s+(\d+)\.(\d+)\.(\d+)\s+(.+)$", line)
        if m4:
            result.append(f"### {new_prefix}.{m4.group(3)} {m4.group(4)}")
            continue
        # ##### without proper number -> promote
        if line.startswith("##### "):
            result.append("### " + line[6:])
            continue
        # #### without number -> promote (shouldn't happen but handle)
        if line.startswith("#### "):
            result.append("### " + line[5:])
            continue
        # ## Section title -> ## N.M Title
        if line.startswith("## ") and not line.startswith("### "):
            title = line[3:]
            if not re.match(r"\d+\.\d+", title):
                result.append(f"## {ch_num}.{sec_num} {title}")
            else:
                result.append(line)
            continue
        result.append(line)
    return "\n".join(result)


def run(chapter: int | None = None,
        sections_dir: Path | None = None,
        output_dir: Path | None = None) -> dict:
    """Merge chapters. Returns summary stats."""
    cfg = load_config()
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")
    if output_dir is None:
        output_dir = resolve_path(cfg, "output_dir")

    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    chapter_list = find_chapter_dirs(sections_dir, chapter)
    if not chapter_list:
        raise ValueError("No matching chapters found")

    stats = {"chapters_merged": 0, "sections_included": 0}

    output_chapters = output_dir / "chapters"
    output_chapters.mkdir(parents=True, exist_ok=True)

    for ch_num, ch_dir in chapter_list:
        section_dirs = get_section_dirs(ch_dir)
        parts = []

        # Chapter intro (if exists)
        intro_path = ch_dir / "chapter_intro.md"
        if intro_path.exists():
            intro_text = intro_path.read_text(encoding="utf-8").strip()
            if intro_text:
                # Fix chapter heading: # Title -> # N Title
                lines = intro_text.split("\n")
                fixed_lines = []
                for line in lines:
                    if line.startswith("# ") and not line.startswith("## "):
                        title = line[2:]
                        if not re.match(r"\d+\s", title):
                            fixed_lines.append(f"# {ch_num} {title}")
                        else:
                            fixed_lines.append(line)
                    else:
                        fixed_lines.append(line)
                parts.append("\n".join(fixed_lines))

        # Section finals in order
        for sd in section_dirs:
            final_path = sd / "final.md"
            draft_path = sd / "draft.md"
            source = final_path if final_path.exists() else draft_path

            if not source.exists():
                continue

            text = source.read_text(encoding="utf-8").strip()
            if text:
                # Read actual section number from section_info.json
                info_path = sd / "section_info.json"
                if info_path.exists():
                    info = json.loads(info_path.read_text(encoding="utf-8"))
                    sec_parts = info.get("section", "").split(".")
                    sec_num = int(sec_parts[-1]) if len(sec_parts) == 2 else 0
                else:
                    sec_num = 0
                text = fix_section_headings(text, ch_num, sec_num)
                parts.append(text)
                stats["sections_included"] += 1

        if not parts:
            print(f"  SKIP Ch {ch_num}: no content to merge")
            continue

        # Write merged chapter file
        merged_path = output_chapters / f"ch{ch_num:02d}.md"
        merged_path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
        print(f"  Ch {ch_num}: merged {len(parts)} parts → {merged_path.name}")
        stats["chapters_merged"] += 1

    print(f"\nMerged {stats['chapters_merged']} chapters "
          f"({stats['sections_included']} sections)")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 4c: Merge sections into chapters")
    parser.add_argument("--chapter", type=int, default=None, help="Only process chapter N")
    args = parser.parse_args()

    stats = run(chapter=args.chapter)
    print(f"\nMerged {stats['chapters_merged']} chapters")


if __name__ == "__main__":
    main()

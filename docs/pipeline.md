# Pipeline

The workflow is organized as six stages. Each stage writes intermediate files so the survey can be inspected, repaired, or regenerated chapter by chapter.

## Stages

| Stage | Script | Purpose |
| --- | --- | --- |
| 0 | `s0_setup.py` | Build the section workspace from the outline. |
| 1 | `s1_build_candidates.py` | Select candidate papers for each section. |
| 2 | `s2_annotate.py` | Annotate candidates with LLM-readable notes. |
| 3 | `s3_generate_draft.py` | Generate section and chapter drafts. |
| 4 | `s4a_revise.py`, `s4b_chapter_intro.py`, `s4c_merge.py` | Revise sections, add chapter introductions, and merge chapter outputs. |
| 5 | `s5a`-`s5f` scripts | Check citations, deduplicate, quality-check, export LaTeX, export BibTeX, and compile. |

## Typical Commands

Plan the full run:

```powershell
python scripts/run_pipeline.py --dry-run
```

Regenerate one chapter from drafting onward:

```powershell
python scripts/run_pipeline.py --from-stage 3 --to-stage 5 --chapter 7
```

Run only final export and checks:

```powershell
python scripts/run_pipeline.py --from-stage 5
```

## Expected Inputs

- A Markdown outline with stable chapter and section IDs.
- A paper metadata CSV containing citation keys, titles, abstracts, years, venues, and keywords.
- Prompt templates for annotation, drafting, revision, citation supplementation, and quality review.
- Optional BibTeX metadata for final bibliography export.

## Expected Outputs

- Per-section candidates and annotations.
- Chapter-level Markdown drafts.
- Merged Markdown manuscript.
- LaTeX source.
- BibTeX bibliography.
- Citation and quality reports.

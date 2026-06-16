# Repository Structure

```text
scripts/
  run_pipeline.py              Main orchestrator
  s0_setup.py                  Build section workspace
  s1_build_candidates.py       Candidate paper selection
  s2_annotate.py               LLM annotation stage
  s3_generate_draft.py         Draft generation stage
  s4a_revise.py                Revision stage
  s4b_chapter_intro.py         Chapter introduction stage
  s4c_merge.py                 Merge section outputs
  s5a_citation_check.py        Citation coverage checks
  s5b_dedup_report.py          Deduplication report
  s5c_quality_check.py         LLM quality review
  s5d_export_latex.py          Markdown to LaTeX export
  s5e_bib_export.py            BibTeX export
  s5f_compile.py               PDF compile wrapper
  llm_utils.py                 Shared config, prompt, and API helpers

prompts/
  Prompt templates used by the LLM-backed stages.

config/
  Public demo config with sample paths and safe defaults.

docs/
  Human-readable project documentation.

examples/
  Small synthetic inputs and outputs for previewing the workflow.

assets/
  README and social preview graphics.
```

The public repository does not include the private full paper, raw paper PDFs, or the full metadata pool.

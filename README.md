# LLM Survey Generation Pipeline

![Pipeline overview](assets/pipeline_overview.png)

A reproducible workflow for building long-form LLM survey drafts from structured outlines, prompt templates, paper metadata, chapter-level intermediate outputs, and LaTeX export steps.

This public repository is a showcase and reproducibility scaffold. It demonstrates the pipeline design, core scripts, prompts, and example artifacts without publishing the full private manuscript, raw paper corpus, or credential-bearing configuration.

## What It Does

- Builds a section workspace from a survey outline.
- Selects and annotates candidate papers for each section.
- Generates chapter-level Markdown drafts with citation keys.
- Revises, merges, and checks chapter outputs.
- Exports Markdown to LaTeX and BibTeX-ready paper artifacts.
- Produces citation coverage, deduplication, and quality reports.

## Pipeline

```text
Outline
  -> section workspace
  -> candidate retrieval
  -> LLM annotation
  -> chapter draft generation
  -> revision and merge
  -> citation and quality checks
  -> LaTeX/BibTeX export
```

The main orchestrator is:

```powershell
python scripts/run_pipeline.py --from-stage 0 --to-stage 5 --dry-run
```

For a single chapter:

```powershell
python scripts/run_pipeline.py --from-stage 3 --to-stage 5 --chapter 7
```

## Quickstart

```powershell
git clone https://github.com/yonger441-wq/llm-survey-generation-pipeline.git
cd llm-survey-generation-pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/run_pipeline.py --dry-run
```

LLM-backed stages use an OpenAI-compatible chat API. Set the provider and model in `config/pipeline_config.json`, then export the required API key:

```powershell
$env:DEEPSEEK_API_KEY="your_api_key_here"
```

Do not commit `.env` files or real API keys.

## Repository Map

```text
scripts/      Core stage scripts and shared helpers
prompts/      Prompt templates used by annotation, drafting, revision, and quality checks
config/       Public demo configuration
docs/         Pipeline notes, privacy notes, and structure guide
examples/     Small synthetic examples for previewing expected inputs and outputs
assets/       Social preview and pipeline overview graphics
```

## Public Demo Scope

This repository intentionally excludes:

- the complete private manuscript,
- the full generated PDF and LaTeX source,
- raw paper PDFs,
- large paper metadata pools,
- local machine paths,
- API keys, tokens, and `.env` files,
- obsolete compile artifacts and archived snapshots.

See [docs/privacy_and_data.md](docs/privacy_and_data.md) for the public/private split.

## Example Output

Start with:

- [examples/sample_chapter.md](examples/sample_chapter.md)
- [examples/sample_section.tex](examples/sample_section.tex)
- [examples/sample_references.bib](examples/sample_references.bib)
- [examples/sample_output_preview.md](examples/sample_output_preview.md)

These files are synthetic and shortened. They show the expected style and structure without exposing the full private manuscript.

## Citation

Use [CITATION.cff](CITATION.cff) if this project helps your research workflow.

## License

MIT License. See [LICENSE](LICENSE).

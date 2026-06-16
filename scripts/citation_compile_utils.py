"""Helpers for compiling LaTeX with large natbib bibliographies.

This module centralizes the citation cleanup, ``.bbl`` normalization, and
post-compile health checks used by the PDF pipeline.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


CITE_PATTERN = re.compile(r"\\cite([pt])?\{([^}]+)\}")
NATEXLAB_PATTERN = re.compile(r"\{\\natexlab\{([^}]*)\}\}")
_BIBITEM_PATTERN = re.compile(
    r"\\bibitem\[(?P<label>.*?)\]\{(?P<key>[^}]+)\}",
    re.DOTALL,
)


@dataclass
class BibEntry:
    """Parsed ``\\bibitem`` entry from a ``.bbl`` file."""

    key: str
    author_label: str
    year: str
    rest_label: str
    body: str
    original_label: str
    parse_ok: bool


def fix_multiline_citations(tex: str) -> str:
    """Join lines that break inside ``\\cite{}`` commands."""
    result: list[str] = []
    i = 0
    cite_prefixes = ("\\cite{", "\\citep{", "\\citet{")
    while i < len(tex):
        matched_prefix = None
        for prefix in cite_prefixes:
            if tex.startswith(prefix, i):
                matched_prefix = prefix
                break
        if matched_prefix is None:
            result.append(tex[i])
            i += 1
            continue

        i += len(matched_prefix)
        depth = 1
        chars = [matched_prefix]
        while i < len(tex) and depth > 0:
            ch = tex[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            chars.append(ch)
            i += 1

        block = "".join(chars).replace("\n", " ")
        block = re.sub(r"\s+", " ", block)
        result.append(block)
    return "".join(result)


def collect_valid_bibkeys(sections_dir: Path) -> set[str]:
    """Collect valid citation keys from all ``selected.csv`` files."""
    valid: set[str] = set()
    for selected_path in sections_dir.rglob("selected.csv"):
        with selected_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                bibkey = row.get("bibkey", "").strip()
                if bibkey:
                    valid.add(bibkey)
    return valid


def filter_citations_in_text(text: str, valid_bibkeys: set[str]) -> tuple[str, int]:
    """Drop cite keys that are not in ``valid_bibkeys``."""
    removed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal removed
        suffix = match.group(1) or ""
        keys = [part.strip() for part in match.group(2).split(",")]
        kept = [key for key in keys if key in valid_bibkeys]
        removed += len(keys) - len(kept)
        if not kept:
            return ""
        return rf"\cite{suffix}" + "{" + ", ".join(kept) + "}"

    cleaned = CITE_PATTERN.sub(replace, text)
    cleaned = re.sub(r"\\cite[pt]?\{\s*\}", "", cleaned)
    return cleaned, removed


def filter_citations_file(tex_path: Path, sections_dir: Path) -> dict:
    """Normalize multi-line cites and drop hallucinated cite keys in-place."""
    valid_bibkeys = collect_valid_bibkeys(sections_dir)
    text = tex_path.read_text(encoding="utf-8")
    fixed_text = fix_multiline_citations(text)
    fixed_text, removed = filter_citations_in_text(fixed_text, valid_bibkeys)
    tex_path.write_text(fixed_text, encoding="utf-8")
    return {
        "valid_bibkeys": len(valid_bibkeys),
        "removed_citations": removed,
    }


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _parse_optional_label(label: str) -> tuple[str, str, str] | None:
    match = re.match(
        r"^(?P<author>.+?)\((?P<year>\d{4})(?P<middle>[^)]*)\)(?P<rest>.*)$",
        label,
        re.DOTALL,
    )
    if not match:
        return None

    author_label = _collapse_ws(match.group("author"))
    rest_label = _collapse_ws(match.group("rest").lstrip("}"))
    return author_label, match.group("year"), rest_label


def _split_bbl_entries(text: str) -> tuple[str, list[BibEntry]]:
    matches = list(_BIBITEM_PATTERN.finditer(text))
    if not matches:
        return text, []

    preamble = text[:matches[0].start()]
    entries: list[BibEntry] = []

    for index, match in enumerate(matches):
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[body_start:body_end]
        parsed = _parse_optional_label(match.group("label"))
        if parsed is None:
            entries.append(
                BibEntry(
                    key=match.group("key"),
                    author_label="",
                    year="",
                    rest_label="",
                    body=body,
                    original_label=match.group("label"),
                    parse_ok=False,
                )
            )
            continue

        author_label, year, rest_label = parsed
        entries.append(
            BibEntry(
                key=match.group("key"),
                author_label=author_label,
                year=year,
                rest_label=rest_label,
                body=body,
                original_label=match.group("label"),
                parse_ok=True,
            )
        )

    return preamble, entries


def _suffix_for_index(index: int) -> str:
    letters: list[str] = []
    current = index
    while True:
        current, remainder = divmod(current, 26)
        letters.append(chr(ord("a") + remainder))
        if current == 0:
            break
        current -= 1
    return "".join(reversed(letters))


def _render_natexlab(suffix: str | None) -> str:
    if not suffix:
        return ""
    return r"{\natexlab{" + suffix + "}}"


def _rewrite_body_year(body: str, year: str, suffix: str | None) -> str:
    replacement = year + _render_natexlab(suffix)
    venue_pattern = re.compile(
        rf"(\\newblock\s+\\emph\{{[^}}]+\}},\s*){re.escape(year)}(?:\{{\\natexlab\{{[^}}]*\}}\}})?\}}?",
        re.DOTALL,
    )
    rewritten, count = venue_pattern.subn(lambda match: match.group(1) + replacement, body, count=1)
    if count:
        return rewritten

    # Some BibTeX entries omit the venue line and leave the year directly at the
    # end of the title sentence, often with malformed trailing braces. Repair the
    # final year-like tail in those cases so natbib can produce stable labels.
    generic_pattern = re.compile(
        rf"{re.escape(year)}(?:\{{\\natexlab\{{[^}}]*\}}\}})?\}}?(?=[.,])",
        re.DOTALL,
    )
    matches = list(generic_pattern.finditer(body))
    if not matches:
        return body
    last = matches[-1]
    return body[: last.start()] + replacement + body[last.end() :]


def normalize_bbl_natexlab(text: str) -> tuple[str, dict]:
    """Normalize ``\\natexlab`` suffixes into a stable natbib-safe form."""
    preamble, entries = _split_bbl_entries(text)
    if not entries:
        return text, {
            "entries": 0,
            "groups": 0,
            "suffixes_assigned": 0,
            "parse_failures": 0,
            "changed_entries": 0,
        }

    groups: dict[tuple[str, str], list[int]] = {}
    parse_failures = 0
    for index, entry in enumerate(entries):
        if not entry.parse_ok:
            parse_failures += 1
            continue
        groups.setdefault((_collapse_ws(entry.author_label), entry.year), []).append(index)

    desired_suffixes: dict[int, str | None] = {}
    suffixes_assigned = 0
    for indices in groups.values():
        if len(indices) == 1:
            desired_suffixes[indices[0]] = None
            continue
        for order, entry_index in enumerate(indices):
            suffix = _suffix_for_index(order)
            desired_suffixes[entry_index] = suffix
            suffixes_assigned += 1

    rebuilt: list[str] = [preamble]
    changed_entries = 0
    for index, entry in enumerate(entries):
        if not entry.parse_ok:
            rebuilt.append(r"\bibitem[" + entry.original_label + "]{" + entry.key + "}" + entry.body)
            continue

        suffix = desired_suffixes.get(index)
        new_label = (
            f"{entry.author_label}({entry.year}{_render_natexlab(suffix)})"
            f"{entry.rest_label}"
        )
        new_body = _rewrite_body_year(entry.body, entry.year, suffix)
        original_header = r"\bibitem[" + entry.original_label + "]{" + entry.key + "}"
        new_header = r"\bibitem[" + new_label + "]{" + entry.key + "}"
        if new_header != original_header or new_body != entry.body:
            changed_entries += 1
        rebuilt.append(new_header + new_body)

    return "".join(rebuilt), {
        "entries": len(entries),
        "groups": len(groups),
        "suffixes_assigned": suffixes_assigned,
        "parse_failures": parse_failures,
        "changed_entries": changed_entries,
    }


def find_undefined_citations(log_text: str) -> list[str]:
    """Find cite keys reported as undefined in the LaTeX log."""
    return re.findall(r"Citation `([^']+)' on page \d+ undefined", log_text)


def find_question_mark_warnings(log_text: str) -> list[str]:
    """Find natbib warnings that result in ``?`` labels."""
    return re.findall(
        r"same authors and year.*?appears as question mark",
        log_text,
        re.IGNORECASE | re.DOTALL,
    )


def extract_cited_bibkeys_from_tex(text: str) -> set[str]:
    """Collect unique cite keys from LaTeX source."""
    text = fix_multiline_citations(text)
    cited: set[str] = set()
    for match in CITE_PATTERN.finditer(text):
        for part in match.group(2).split(","):
            key = part.strip()
            if key:
                cited.add(key)
    return cited


def extract_bibitem_keys_from_bbl(text: str) -> set[str]:
    """Collect keys defined by ``\\bibitem`` entries."""
    return {match.group("key") for match in _BIBITEM_PATTERN.finditer(text)}


def extract_aux_bibcites(text: str) -> set[str]:
    """Collect cite keys that received ``\\bibcite`` entries in ``.aux``."""
    return set(re.findall(r"\\bibcite\{([^}]+)\}", text))


def find_invalid_natexlab_labels(text: str) -> list[str]:
    """Return invalid ``\\natexlab`` labels found in ``.bbl`` text."""
    invalid = []
    for label in NATEXLAB_PATTERN.findall(text):
        if not re.fullmatch(r"[a-z]+", label or ""):
            invalid.append(label)
    return invalid


def generate_citation_health_report(
    tex_path: Path,
    bbl_path: Path,
    aux_path: Path,
    log_path: Path,
) -> dict:
    """Inspect all compile artifacts and summarize citation health."""
    tex_text = tex_path.read_text(encoding="utf-8", errors="ignore") if tex_path.exists() else ""
    bbl_text = bbl_path.read_text(encoding="utf-8", errors="ignore") if bbl_path.exists() else ""
    aux_text = aux_path.read_text(encoding="utf-8", errors="ignore") if aux_path.exists() else ""
    log_text = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""

    cited_keys = extract_cited_bibkeys_from_tex(tex_text)
    bibitem_keys = extract_bibitem_keys_from_bbl(bbl_text)
    aux_bibcites = extract_aux_bibcites(aux_text)
    undefined = find_undefined_citations(log_text)
    question_mark = find_question_mark_warnings(log_text)
    invalid_natexlab = find_invalid_natexlab_labels(bbl_text)

    missing_in_aux = sorted(cited_keys - aux_bibcites)
    missing_in_bbl = sorted(cited_keys - bibitem_keys)

    return {
        "cited_key_count": len(cited_keys),
        "cited_keys": sorted(cited_keys),
        "bibitem_count": len(bibitem_keys),
        "aux_bibcite_count": len(aux_bibcites),
        "missing_bibcites": missing_in_aux,
        "missing_bibitems": missing_in_bbl,
        "invalid_natexlab_labels": invalid_natexlab,
        "undefined_citations": undefined,
        "question_mark_warnings": question_mark,
        "healthy": not (
            undefined or question_mark or invalid_natexlab or missing_in_aux
        ),
    }

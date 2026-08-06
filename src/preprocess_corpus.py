"""Phase 2 only: deterministic sentence segmentation with raw-file provenance."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from src.audit_corpus import FILES, ROOT, decode_utf8, extract_scope


OUT = ROOT / "data" / "processed"
RESULTS = ROOT / "results" / "phase2_preprocessing"
PREFIX = {"chinese": "zh", "english": "en", "spanish": "es"}
ABBREVIATIONS = {
    "english": {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e", "a.m", "p.m", "u.s", "no", "vol", "fig"},
    "spanish": {"sr", "sra", "srta", "dr", "dra", "prof", "ud", "uds", "etc", "p.ej", "núm", "n.º", "d", "día"},
}
LATIN_WORD_BEFORE_PERIOD = re.compile(r"([\w.º]+)$", re.UNICODE)
TRAILING_CLOSERS = set('"\'’”»)]}')


@dataclass
class SentenceRecord:
    sentence_id: str
    language: str
    paragraph_id: str
    sentence_number: int
    char_start: int
    char_end: int
    sentence_text: str
    raw_text: str
    is_lexical: bool
    has_candidate: bool
    candidate_hits_json: str


def paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans, offset, start, end = [], 0, None, None
    for line in text.splitlines(keepends=True):
        content_end = offset + len(line.rstrip("\r\n"))
        if line.strip():
            if start is None:
                start = offset + len(line) - len(line.lstrip())
            end = content_end
            while end > start and text[end - 1].isspace():
                end -= 1
        elif start is not None:
            spans.append((start, end))
            start = end = None
        offset += len(line)
    if start is not None:
        spans.append((start, end))
    return spans


def latin_period_is_boundary(paragraph: str, position: int, language: str) -> bool:
    if 0 < position < len(paragraph) - 1 and paragraph[position - 1].isdigit() and paragraph[position + 1].isdigit():
        return False
    match = LATIN_WORD_BEFORE_PERIOD.search(paragraph[:position])
    token = match.group(1).casefold() if match else ""
    return token not in ABBREVIATIONS[language] and not (len(token) == 1 and token.isalpha())


def sentence_spans(paragraph: str, language: str) -> list[tuple[int, int]]:
    spans, start, i = [], 0, 0
    while i < len(paragraph):
        char = paragraph[i]
        boundary = False
        if language == "chinese":
            boundary = char in "。！？!?"
            if char == "…":
                run_end = i + 1
                while run_end < len(paragraph) and paragraph[run_end] == "…":
                    run_end += 1
                boundary = run_end - i >= 2
                i = run_end - 1
        elif char in "!?":
            boundary = True
        elif char == ".":
            ellipsis = re.match(r"\.(?:\s*\.)+", paragraph[i:])
            if ellipsis:
                i += len(ellipsis.group(0)) - 1
                boundary = True
            else:
                boundary = latin_period_is_boundary(paragraph, i, language)

        if boundary:
            end = i + 1
            while end < len(paragraph) and paragraph[end] in TRAILING_CLOSERS:
                end += 1
            left = start
            while left < end and paragraph[left].isspace():
                left += 1
            if left < end:
                spans.append((left, end))
            start = end
        i += 1
    left = start
    while left < len(paragraph) and paragraph[left].isspace():
        left += 1
    if left < len(paragraph):
        spans.append((left, len(paragraph)))
    return spans


def normalized_sentence(text: str) -> str:
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", text).strip())


def candidate_hits(text: str, language: str, terms: list[str]) -> dict[str, int]:
    value = unicodedata.normalize("NFC", text)
    hits = {}
    for term in terms:
        target = unicodedata.normalize("NFC", term)
        if language == "chinese":
            count = len(re.findall(f"(?={re.escape(target)})", value))
        else:
            count = len(re.findall(rf"(?<!\w){re.escape(target)}(?!\w)", value, flags=re.IGNORECASE | re.UNICODE))
        if count:
            hits[term] = count
    return hits


def write_csv(path: Path, records: list[SentenceRecord]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(records[0])))
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def main() -> int:
    scope = json.loads((ROOT / "config" / "corpus_scope.json").read_text(encoding="utf-8"))
    terms = json.loads((ROOT / "config" / "candidate_terms.json").read_text(encoding="utf-8"))
    phase1 = json.loads((ROOT / "results" / "phase1_audit" / "audit_details.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary = {"phase": 2, "scope": "deterministic preprocessing only", "corpora": {}}

    for language, path in FILES.items():
        source_text, _, _ = decode_utf8(path.read_bytes())
        analysis, validation = extract_scope(source_text, language, scope[language])
        base_offset = validation["raw_char_start"]
        records = []
        paragraphs = paragraph_spans(analysis)
        for paragraph_number, (paragraph_start, paragraph_end) in enumerate(paragraphs, 1):
            paragraph = analysis[paragraph_start:paragraph_end]
            for local_start, local_end in sentence_spans(paragraph, language):
                start = base_offset + paragraph_start + local_start
                end = base_offset + paragraph_start + local_end
                raw_sentence = source_text[start:end]
                hits = candidate_hits(raw_sentence, language, terms[language])
                number = len(records) + 1
                records.append(SentenceRecord(
                    sentence_id=f"{PREFIX[language]}-{number:06d}",
                    language=language,
                    paragraph_id=f"{PREFIX[language]}-p{paragraph_number:05d}",
                    sentence_number=number,
                    char_start=start,
                    char_end=end,
                    sentence_text=normalized_sentence(raw_sentence),
                    raw_text=raw_sentence,
                    is_lexical=any(ch.isalnum() for ch in raw_sentence),
                    has_candidate=bool(hits),
                    candidate_hits_json=json.dumps(hits, ensure_ascii=False, sort_keys=True),
                ))

        if not records or len({record.sentence_id for record in records}) != len(records):
            raise RuntimeError(f"Invalid sentence records for {language}")
        if not all(source_text[r.char_start:r.char_end] == r.raw_text for r in records):
            raise RuntimeError(f"Offset validation failed for {language}")
        analysis_nonspace = sum(not ch.isspace() for ch in analysis)
        covered_nonspace = sum(sum(not ch.isspace() for ch in record.raw_text) for record in records)
        if analysis_nonspace != covered_nonspace:
            raise RuntimeError(f"Coverage validation failed for {language}: {covered_nonspace}/{analysis_nonspace}")

        aggregate = {term: 0 for term in terms[language]}
        for record in records:
            for term, count in json.loads(record.candidate_hits_json).items():
                aggregate[term] += count
        expected = phase1["corpora"][language]["candidate_frequencies"]
        if aggregate != expected:
            raise RuntimeError(f"Candidate preservation failed for {language}: {aggregate} != {expected}")

        write_csv(OUT / f"{language}_sentences.csv", records)
        lengths = sorted(len(record.sentence_text) for record in records)
        summary["corpora"][language] = {
            "paragraphs": len(paragraphs),
            "sentences": len(records),
            "sentences_with_candidate": sum(record.has_candidate for record in records),
            "analysis_nonwhitespace_characters": analysis_nonspace,
            "covered_nonwhitespace_characters": covered_nonspace,
            "coverage": covered_nonspace / analysis_nonspace,
            "median_sentence_length": lengths[len(lengths) // 2],
            "maximum_sentence_length": max(lengths),
            "punctuation_only_records": sum(not record.is_lexical for record in records),
            "candidate_frequencies_preserved": True,
            "serialized_offsets_verified": True,
            "output": f"data/processed/{language}_sentences.csv",
        }

    (RESULTS / "preprocessing_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Phase 2 Preprocessing Report", "",
        "> Sentence segmentation and provenance only. No collocation or semantic interpretation is included.", "",
        "|Language|Paragraphs|Sentences|Candidate sentences|Coverage|Median length|Maximum length|Offsets verified|",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for language, item in summary["corpora"].items():
        lines.append(f"|{language}|{item['paragraphs']}|{item['sentences']}|{item['sentences_with_candidate']}|{item['coverage']:.2%}|{item['median_sentence_length']}|{item['maximum_sentence_length']}|yes|")
    lines += [
        "", "## Validation", "",
        "- Raw ebook files were not modified.",
        "- Every sentence retains an exact raw substring and zero-based half-open offsets into the complete supplied file.",
        "- Sentence records cover 100% of non-whitespace characters in each validated literary-text slice.",
        "- Candidate frequencies re-aggregated from sentence records exactly match Phase 1.",
        "- Sentence boundaries are deterministic rules rather than manually annotated gold boundaries.",
    ]
    (RESULTS / "PHASE2_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Phase 2 complete: {RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Phase 1 only: corpus integrity, scope, size, and candidate frequencies."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import jieba


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "results" / "phase1_audit"
FILES = {
    "chinese": RAW / "chinese.txt",
    "english": RAW / "english.txt",
    "spanish": RAW / "spanish.txt",
}
EXPECTED_COUNTS = [9, 11, 9, 9, 10]
LATIN_TOKEN_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)


def decode_utf8(raw: bytes) -> tuple[str, str, str]:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="strict"), "utf-8-sig", "BOM plus strict decode"
    return raw.decode("utf-8", errors="strict"), "utf-8", "strict UTF-8 decode"


def find_boundary(lines: list[str], marker: str, prefix: bool, start: int = 0) -> int:
    for index in range(start, len(lines)):
        value = lines[index].strip()
        if (value.startswith(marker) if prefix else value == marker):
            return index
    raise RuntimeError(f"Boundary marker not found: {marker!r}")


def extract_scope(text: str, language: str, settings: dict) -> tuple[str, dict]:
    lines = text.splitlines(keepends=True)
    start = find_boundary(lines, settings["start_marker"], True)
    end = find_boundary(lines, settings["end_marker"], settings["end_prefix"], start + 1)
    analysis = "".join(lines[start:end])
    analysis_lines = analysis.splitlines()

    positions = []
    cursor = 0
    for title in settings["section_titles"]:
        matches = [i for i in range(cursor, len(analysis_lines)) if analysis_lines[i].strip() == title]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one ordered section heading {title!r}; found {len(matches)}")
        positions.append(matches[0])
        cursor = matches[0] + 1

    subsection_re = re.compile(settings["subsection_pattern"])
    counts = []
    for i, position in enumerate(positions):
        next_position = positions[i + 1] if i + 1 < len(positions) else len(analysis_lines)
        counts.append(sum(bool(subsection_re.fullmatch(line.strip())) for line in analysis_lines[position + 1:next_position]))
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"Unexpected subsection structure for {language}: {counts}")

    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    return analysis, {
        "source_start_line": start + 1,
        "source_end_line": end,
        "raw_char_start": offsets[start],
        "raw_char_end": offsets[end],
        "section_count": 5,
        "subsection_counts": counts,
        "analysis_sha256": hashlib.sha256(analysis.encode("utf-8")).hexdigest(),
    }


def token_count(text: str, language: str) -> int:
    if language == "chinese":
        return sum(1 for token in jieba.cut(text, cut_all=False) if token.strip() and any(ch.isalnum() for ch in token))
    return len(LATIN_TOKEN_RE.findall(text))


def provisional_sentence_count(text: str, language: str) -> int:
    if language == "chinese":
        return len([part for part in re.split(r"(?<=[。！？!?])", text) if part.strip()])
    return len([part for part in re.split(r"(?<=[.!?])(?:[\"'’”»)]*)\s+", text) if part.strip()])


def term_frequency(text: str, language: str, term: str) -> int:
    text = unicodedata.normalize("NFC", text)
    term = unicodedata.normalize("NFC", term)
    if language == "chinese":
        return len(re.findall(f"(?={re.escape(term)})", text))
    return len(re.findall(rf"(?<!\w){re.escape(term)}(?!\w)", text, flags=re.IGNORECASE | re.UNICODE))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    scope = json.loads((ROOT / "config" / "corpus_scope.json").read_text(encoding="utf-8"))
    terms = json.loads((ROOT / "config" / "candidate_terms.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    audit_rows, frequency_rows = [], []
    details = {"phase": 1, "scope": "observed corpus evidence only", "corpora": {}}

    for language, path in FILES.items():
        raw = path.read_bytes()
        raw_text, encoding, method = decode_utf8(raw)
        analysis, validation = extract_scope(raw_text, language, scope[language])
        row = {
            "language": language,
            "encoding": encoding,
            "encoding_method": method,
            "raw_bytes": len(raw),
            "raw_characters": len(raw_text),
            "analysis_characters": len(analysis),
            "analysis_nonwhitespace_characters": sum(not ch.isspace() for ch in analysis),
            "analysis_tokens": token_count(analysis, language),
            "sentences_provisional": provisional_sentence_count(analysis, language),
            "source_lines": f"{validation['source_start_line']}-{validation['source_end_line']}",
            "section_structure": "9/11/9/9/10",
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "analysis_sha256": validation["analysis_sha256"],
        }
        audit_rows.append(row)
        observed = {}
        for term in terms[language]:
            count = term_frequency(analysis, language, term)
            observed[term] = count
            frequency_rows.append({"language": language, "term": term, "frequency": count})
        details["corpora"][language] = {**row, "scope_validation": validation, "candidate_frequencies": observed}

    write_csv(OUT / "corpus_audit.csv", audit_rows)
    write_csv(OUT / "candidate_term_frequencies.csv", frequency_rows)
    (OUT / "audit_details.json").write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Phase 1 Corpus Audit",
        "",
        "> Observed corpus properties only. No cultural meaning, translation quality, or semantic shift is inferred.",
        "",
        "## Validated corpus scope",
        "",
        "|Language|Encoding|Analysis non-space characters|Analysis tokens|Provisional sentences|Retained lines|Structure|",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in audit_rows:
        lines.append(f"|{row['language']}|{row['encoding']}|{row['analysis_nonwhitespace_characters']}|{row['analysis_tokens']}|{row['sentences_provisional']}|{row['source_lines']}|{row['section_structure']}|")
    lines += ["", "## Candidate-term frequencies", "", "|Language|Term|Observed frequency|", "|---|---|---:|"]
    lines += [f"|{row['language']}|{row['term']}|{row['frequency']}|" for row in frequency_rows]
    lines += [
        "",
        "## Audit boundary",
        "",
        "- All three files decoded with strict UTF-8 rules.",
        "- All three retained texts contain five corresponding parts with 9/11/9/9/10 subsections.",
        "- Shared literary dedications are retained; ebook metadata, contents pages, copyright matter, and author biographies are excluded.",
        "- Chinese token counts use jieba; English and Spanish counts use Unicode word tokens.",
        "- Sentence counts are provisional rule-based audit measures and will be replaced by traceable Phase 2 segmentation.",
        "- Candidate frequencies are observations, not evidence of cultural meaning.",
        "- Chinese candidate strings may overlap and must not be summed directly.",
    ]
    (OUT / "PHASE1_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Phase 1 complete: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


"""Phase 3: reproducible window-based collocation statistics."""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

import jieba

from src.audit_corpus import LATIN_TOKEN_RE, ROOT


PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "results" / "phase3_collocations"


def chinese_tokens(text: str, candidates: list[str]) -> list[str]:
    """Tokenize Chinese while preserving candidate strings with longest-match priority."""
    normalized = unicodedata.normalize("NFC", text)
    pattern = re.compile("(" + "|".join(re.escape(term) for term in sorted(candidates, key=len, reverse=True)) + ")")
    tokens: list[str] = []
    for part in pattern.split(normalized):
        if not part:
            continue
        if part in candidates:
            tokens.append(part)
        else:
            tokens.extend(
                token.strip()
                for token in jieba.cut(part, cut_all=False)
                if token.strip() and any(character.isalnum() for character in token)
            )
    return tokens


def tokenize(text: str, language: str, candidates: list[str]) -> list[str]:
    if language == "chinese":
        return chinese_tokens(text, candidates)
    normalized = unicodedata.normalize("NFC", text).casefold()
    candidate_set = {term.casefold() for term in candidates}
    tokens = []
    for match in LATIN_TOKEN_RE.finditer(normalized):
        token = match.group(0)
        base = token[:-2] if token.endswith(("'s", "’s")) else token
        tokens.append(base if base in candidate_set else token)
    return tokens


def g2(a: int, b: int, c: int, d: int) -> float:
    """Dunning-style log-likelihood for a 2x2 table, using natural logs."""
    observed = ((a, b), (c, d))
    rows = (a + b, c + d)
    columns = (a + c, b + d)
    total = sum(rows)
    value = 0.0
    for row_index, row in enumerate(observed):
        for column_index, cell in enumerate(row):
            expected = rows[row_index] * columns[column_index] / total
            if cell > 0 and expected > 0:
                value += cell * math.log(cell / expected)
    return 2.0 * value


def analyse_language(language: str, candidates: list[str], parameters: dict) -> tuple[list[dict], list[dict], dict]:
    path = PROCESSED / f"{language}_sentences.csv"
    if not path.exists():
        raise FileNotFoundError(f"Run Phase 2 first: {path}")

    sentence_tokens: list[tuple[str, str, list[str]]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            sentence_tokens.append((
                row["sentence_id"],
                row["sentence_text"],
                tokenize(row["sentence_text"], language, candidates),
            ))

    candidate_set = set(term if language == "chinese" else term.casefold() for term in candidates)
    corpus_frequency: Counter[str] = Counter()
    context_frequency: Counter[str] = Counter()
    target_frequency: Counter[str] = Counter()
    context_size = 0
    target_sentence_count = 0
    target_windows: list[dict] = []
    window = parameters["window_size"]

    for sentence_id, sentence_text, tokens in sentence_tokens:
        corpus_frequency.update(tokens)
        targets = [index for index, token in enumerate(tokens) if token in candidate_set]
        target_frequency.update(tokens[index] for index in targets)
        if targets:
            target_sentence_count += 1
        context_positions: set[int] = set()
        for index in targets:
            context_positions.update(range(max(0, index - window), min(len(tokens), index + window + 1)))
            target_windows.append({
                "language": language,
                "sentence_id": sentence_id,
                "target_number": len(target_windows) + 1,
                "target_term": tokens[index],
                "token_index_zero_based": index,
                "left_context": " ".join(tokens[max(0, index - window):index]),
                "right_context": " ".join(tokens[index + 1:index + window + 1]),
                "sentence_text": sentence_text,
            })
        context_positions.difference_update(targets)
        context_size += len(context_positions)
        context_frequency.update(tokens[index] for index in context_positions if tokens[index] not in candidate_set)

    corpus_size = sum(corpus_frequency.values())
    if corpus_size == 0 or context_size == 0:
        raise RuntimeError(f"No analyzable tokens or target contexts for {language}")

    rows = []
    for collocate, observed in context_frequency.items():
        total_frequency = corpus_frequency[collocate]
        outside_frequency = total_frequency - observed
        outside_size = corpus_size - context_size
        if outside_frequency < 0 or outside_size < outside_frequency:
            raise RuntimeError(f"Invalid contingency table for {language}:{collocate}")
        expected = context_size * total_frequency / corpus_size
        pmi = math.log2((observed / context_size) / (total_frequency / corpus_size))
        statistic = g2(observed, context_size - observed, outside_frequency, outside_size - outside_frequency)
        signed_statistic = statistic if observed >= expected else -statistic
        rows.append({
            "language": language,
            "collocate": collocate,
            "context_frequency": observed,
            "corpus_frequency": total_frequency,
            "context_rate_per_1000": round(observed / context_size * 1000, 6),
            "corpus_rate_per_1000": round(total_frequency / corpus_size * 1000, 6),
            "pmi": round(pmi, 6),
            "signed_log_likelihood_g2": round(signed_statistic, 6),
            "association": "overrepresented" if observed >= expected else "underrepresented",
            "meets_minimum_frequency": observed >= parameters["minimum_context_frequency"],
        })

    eligible = [row for row in rows if row["meets_minimum_frequency"]]
    for rank, row in enumerate(sorted(eligible, key=lambda item: (-item["pmi"], -item["context_frequency"], item["collocate"])), 1):
        row["pmi_rank"] = rank
    for rank, row in enumerate(sorted(eligible, key=lambda item: (-item["signed_log_likelihood_g2"], -item["context_frequency"], item["collocate"])), 1):
        row["log_likelihood_rank"] = rank
    for row in rows:
        row.setdefault("pmi_rank", "")
        row.setdefault("log_likelihood_rank", "")
    rows.sort(key=lambda item: (item["pmi_rank"] == "", item["pmi_rank"] if item["pmi_rank"] != "" else 10**9, item["collocate"]))

    summary = {
        "sentences": len(sentence_tokens),
        "sentences_with_candidate": target_sentence_count,
        "corpus_tokens_phase3": corpus_size,
        "target_occurrences_nonoverlapping": sum(target_frequency.values()),
        "target_frequency_nonoverlapping": dict(target_frequency),
        "unique_context_positions": context_size,
        "unique_collocates": len(context_frequency),
        "eligible_collocates": len(eligible),
    }
    return rows, target_windows, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"No rows to write: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    candidates = json.loads((ROOT / "config" / "candidate_terms.json").read_text(encoding="utf-8"))
    parameters = json.loads((ROOT / "config" / "collocation_parameters.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "phase": 3,
        "scope": "observed window-based lexical association; no cultural interpretation",
        "parameters": parameters,
        "corpora": {},
    }

    tables: dict[str, list[dict]] = {}
    for language, terms in candidates.items():
        rows, target_windows, summary = analyse_language(language, terms, parameters)
        tables[language] = rows
        result["corpora"][language] = summary
        write_csv(OUT / f"{language}_collocations.csv", rows)
        write_csv(PROCESSED / f"{language}_candidate_windows.csv", target_windows)

    (OUT / "collocation_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Phase 3 Collocation Report", "",
        "> Observed lexical association only. This report does not infer cultural meaning or translation quality.", "",
        "## Method", "",
        f"- Symmetrical lexical-token window: ±{parameters['window_size']} within sentence boundaries.",
        "- Overlapping windows are merged into unique context-token positions, preventing double counting.",
        "- Chinese candidate overlaps use leftmost-longest matching (for example, 血红 is one target rather than simultaneous 血 and 红 targets).",
        "- English candidate possessives (for example, red’s) are normalized to the declared candidate while remaining one token position.",
        f"- PMI and signed log-likelihood ranks require context frequency ≥ {parameters['minimum_context_frequency']}.",
        "- PMI measures effect strength; signed G² indicates statistical salience and direction relative to the rest of the same-language corpus.",
        "- Rankings are language-internal. Raw scores are not treated as directly comparable across tokenization systems.", "",
        "## Corpus and context totals", "",
        "|Language|Corpus tokens|Target occurrences|Target sentences|Unique context positions|Eligible collocates|",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for language, item in result["corpora"].items():
        lines.append(f"|{language}|{item['corpus_tokens_phase3']}|{item['target_occurrences_nonoverlapping']}|{item['sentences_with_candidate']}|{item['unique_context_positions']}|{item['eligible_collocates']}|")

    for language, rows in tables.items():
        top = sorted(
            (row for row in rows if row["meets_minimum_frequency"] and row["association"] == "overrepresented"),
            key=lambda item: item["pmi_rank"],
        )[:15]
        lines += ["", f"## {language.title()}: top PMI collocates", "", "|Rank|Collocate|Context frequency|Corpus frequency|PMI|Signed G²|", "|---:|---|---:|---:|---:|---:|"]
        lines += [f"|{row['pmi_rank']}|{row['collocate']}|{row['context_frequency']}|{row['corpus_frequency']}|{row['pmi']:.3f}|{row['signed_log_likelihood_g2']:.3f}|" for row in top]

    lines += [
        "", "## Interpretation boundary", "",
        "- These tables show statistical proximity to the declared candidate set, not semantic equivalence across languages.",
        "- High PMI with low counts remains unstable; the minimum-frequency threshold reduces but does not eliminate this risk.",
        "- Function words remain in the full tables so that filtering choices are transparent; downstream comparison should justify any exclusions.",
        "- Chinese one-character collocates can be fragments of compounds under target-preserving segmentation; concordance lines must be checked before interpretation.",
        "- Private KWIC tables link every target occurrence back to its Phase 2 sentence ID; they are excluded from Git with the source texts.",
        "- No claim of cultural semantic shift is made at this stage.",
    ]
    (OUT / "PHASE3_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Phase 3 complete: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

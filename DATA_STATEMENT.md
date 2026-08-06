# Data statement

## Corpus

This project analyses three researcher-supplied complete-text versions of *Red Sorghum*: Chinese, English, and Spanish. The literary-text boundaries and structural checks are documented in `config/corpus_scope.json` and `results/phase1_audit/`.

## Copyright and access

The novels and derived sentence-level excerpts are copyrighted and are not redistributed. The following remain local and are excluded from Git:

- `data/raw/*.txt`
- `data/processed/*` except the placeholder file
- sentence-level KWIC tables
- sentence embeddings (`.npz`)
- cross-language nearest-neighbor records
- downloaded model weights and local dependency caches

Aggregate counts, association statistics, methodological metadata, reports, and figures are included because they do not reproduce the novels.

## Reproduction

To reproduce the complete analysis, an authorized researcher must provide their own copies as:

```text
data/raw/chinese.txt
data/raw/english.txt
data/raw/spanish.txt
```

The supplied texts must match the editions and structure expected by `config/corpus_scope.json`. Phase 1 fails rather than silently continuing when structural boundaries do not match.

## Responsible interpretation

This is a single-work case study. Candidate lists are operational research choices, not universal multilingual equivalence classes. Aggregate differences should not be generalized to languages, cultures, translators, or translation quality without additional corpora and human validation.

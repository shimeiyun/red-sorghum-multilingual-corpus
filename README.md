# Red Sorghum Multilingual Corpus Study

**A corpus-based and computational analysis of the representation of red in the Chinese, English, and Spanish versions of *Red Sorghum*.**

This reproducible computational-linguistics portfolio project combines corpus auditing, traceable preprocessing, collocation statistics, cross-language profile comparison, and multilingual sentence embeddings. It uses only three researcher-supplied complete novel files as corpus data and separates observed evidence from interpretation.

## Research questions

1. How frequent are the declared red-related candidates in each validated text?
2. Which lexical items are associated with those candidates inside each language?
3. How do the association-profile structures differ across languages?
4. Are candidate-bearing contexts more similar across languages than matched non-candidate contexts?

## Results snapshot

|Pair|Candidate cosine|Matched baseline|Difference|
|---|---:|---:|---:|
|Chinese–English|0.969|0.956|+0.013|
|Chinese–Spanish|0.967|0.950|+0.017|
|English–Spanish|0.985|0.973|+0.012|

The baseline-adjusted differences are positive but small. They are treated as evidence of modest cross-language contextual concentration—not proof of cultural preservation, loss, or translation quality.

Read the [full research report](FINAL_REPORT.md).

## Pipeline

|Phase|Purpose|Main output|
|---:|---|---|
|1|Encoding, scope, integrity, counts, actual candidate frequencies|`results/phase1_audit/`|
|2|Traceable sentence segmentation with raw-file offsets|`results/phase2_preprocessing/`|
|3|±5-token frequency, PMI, and signed G² collocation analysis|`results/phase3_collocations/`|
|4|Association-profile comparison and SVG figures|`results/phase4_comparison/`|
|5|384-dimensional multilingual sentence embeddings with matched controls|`results/phase5_embeddings/`|
|6|Bootstrap interval figures and integrated report|`results/phase6_final/`|

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run all phases:

```powershell
python run_pipeline.py
```

Run a selected range:

```powershell
python run_pipeline.py --from-phase 3 --to-phase 6
```

Each phase also has an individual `run_phaseN.py` entry point. Phase 5 downloads `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` on first use. On Windows, set `RED_SORGHUM_MODEL_CACHE` to a short writable path if needed.

Verify completed outputs:

```powershell
python verify_project.py
```

## Repository structure

```text
config/                  Declared candidates and analysis parameters
data/raw/                Private supplied novels (Git-ignored)
data/processed/          Private sentences, KWIC, embeddings (Git-ignored)
results/                 Shareable aggregate tables, metadata, reports, figures
src/                     Analysis implementation
FINAL_REPORT.md          Integrated research-style report
run_pipeline.py          Consecutive phase runner
verify_project.py        Cross-phase integrity checks
```

## Data and copyright

The novels are copyrighted and are not redistributed. Raw texts, sentence-level excerpts, vectors, and nearest-neighbor records are excluded through `.gitignore`. A repository clone can reproduce the study only when the researcher supplies the same three input files under `data/raw/`.

## Methodological boundary

- Candidate lists operationalize the research question but are not exact translation dictionaries.
- Chinese and Latin-script tokenization are not identical measurement systems.
- The corpus contains one novel, so conclusions are case-specific.
- Embedding similarity is not sentence alignment or translation-quality evaluation.
- Cultural interpretation is explicitly marked as exploratory.

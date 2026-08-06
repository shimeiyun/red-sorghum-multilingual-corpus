# Phase 5 Multilingual Sentence-Embedding Report

> Corpus-level semantic similarity evidence only. The results do not establish sentence alignment, translation quality, or cultural causation.

## Model

- Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions; multilingual; Apache-2.0).
- Runtime: FastEmbed 0.8.0 quantized ONNX, mean pooling, followed by explicit L2 normalization.
- Bootstrap: 500 iterations; seed 42.
- Baseline: one same-language non-candidate sentence per candidate sentence, greedily matched on character length.

## Pairwise centroid results

|Language pair|Candidate cosine|Distance|95% bootstrap CI|Control cosine|Candidate − control|Delta 95% CI|
|---|---:|---:|---|---:|---:|---|
|chinese-english|0.969|0.031|[0.957, 0.970]|0.956|0.013|[0.004, 0.025]|
|chinese-spanish|0.967|0.033|[0.956, 0.969]|0.950|0.017|[0.007, 0.030]|
|english-spanish|0.985|0.015|[0.975, 0.984]|0.973|0.012|[0.005, 0.024]|

## Interpretation boundary

- Candidate centroids summarize all candidate-bearing sentences in each language; they do not align translated sentences.
- The matched baseline helps distinguish candidate-context similarity from general similarity caused by all three texts being versions of the same novel.
- A positive candidate-minus-control value is descriptive evidence of greater cross-language concentration, not proof of semantic preservation.
- A negative value is not proof of cultural loss; candidate selection, translation choices, segmentation, and model behavior remain alternative explanations.
- Nearest-neighbor sentence IDs and sentence embeddings are private intermediate data and are excluded from Git.

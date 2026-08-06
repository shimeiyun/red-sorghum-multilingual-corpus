# Phase 2 Preprocessing Report

> Sentence segmentation and provenance only. No collocation or semantic interpretation is included.

|Language|Paragraphs|Sentences|Candidate sentences|Coverage|Median length|Maximum length|Offsets verified|
|---|---:|---:|---:|---:|---:|---:|---|
|chinese|2766|8176|620|100.00%|25|330|yes|
|english|2855|8812|446|100.00%|73|843|yes|
|spanish|3612|9491|465|100.00%|82|838|yes|

## Validation

- Raw ebook files were not modified.
- Every sentence retains an exact raw substring and zero-based half-open offsets into the complete supplied file.
- Sentence records cover 100% of non-whitespace characters in each validated literary-text slice.
- Candidate frequencies re-aggregated from sentence records exactly match Phase 1.
- Sentence boundaries are deterministic rules rather than manually annotated gold boundaries.
- Phase 1 reported provisional punctuation-based counts; the language-aware Phase 2 counts supersede them for downstream sentence-level analysis.

# Phase 4 Cross-language Association Comparison

> This is a structural comparison of observed association profiles. It does not claim that same-ranked words are translations or semantic equivalents.

## Comparable descriptive measures

|Language|Targets per 10k tokens|Eligible positive collocates|Normalized entropy|Top-10 frequency share|Median positive PMI|
|---|---:|---:|---:|---:|---:|
|Chinese|59.16|105|0.767|0.579|1.681|
|English|37.66|89|0.808|0.574|1.400|
|Spanish|31.90|84|0.786|0.626|1.316|

## Figures

1. `figures/figure_1_target_rate.svg`: normalized frequency of the declared target sets.
2. `figures/figure_2_distribution_structure.svg`: concentration and normalized entropy of eligible positive collocates.
3. `figures/figure_3_top_pmi_collocates.svg`: language-internal top-PMI profiles shown side by side.

## Evidence boundary

- Candidate sets differ in size and lexical composition, so normalized target rates are descriptive rather than proof of translation shift.
- Entropy and concentration summarize distribution shape after the same frequency threshold; they do not identify cultural categories.
- Chinese segmentation and Latin word tokenization are not identical measurement systems; raw PMI and G² values are not interpreted as directly equivalent across languages.
- Side-by-side rank positions are visual alignment only, not word-level translation alignment.
- Semantic equivalence and distance require the explicitly separate multilingual embedding stage.

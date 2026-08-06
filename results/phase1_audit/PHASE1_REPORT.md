# Phase 1 Corpus Audit

> Observed corpus properties only. No cultural meaning, translation quality, or semantic shift is inferred.

## Validated corpus scope

|Language|Encoding|Analysis non-space characters|Analysis tokens|Provisional sentences|Retained lines|Structure|
|---|---|---:|---:|---:|---|---|
|chinese|utf-8|230707|123853|7642|1-5782|9/11/9/9/10|
|english|utf-8|619615|133569|9555|174-6171|9/11/9/9/10|
|spanish|utf-8|777370|167104|9003|42-7529|9/11/9/9/10|

## Candidate-term frequencies

|Language|Term|Observed frequency|
|---|---|---:|
|chinese|红|431|
|chinese|血|307|
|chinese|鲜红|19|
|chinese|赤|23|
|chinese|血红|25|
|english|red|269|
|english|blood|196|
|english|bloody|19|
|english|crimson|2|
|english|scarlet|17|
|spanish|rojo|169|
|spanish|roja|63|
|spanish|rojos|31|
|spanish|rojas|31|
|spanish|sangre|239|

## Audit boundary

- All three files decoded with strict UTF-8 rules.
- All three retained texts contain five corresponding parts with 9/11/9/9/10 subsections.
- Shared literary dedications are retained; ebook metadata, contents pages, copyright matter, and author biographies are excluded.
- Chinese token counts use jieba; English and Spanish counts use Unicode word tokens.
- Sentence counts are provisional rule-based audit measures and will be replaced by traceable Phase 2 segmentation.
- Candidate frequencies are observations, not evidence of cultural meaning.
- Chinese candidate strings may overlap and must not be summed directly.

# Phase 3 Collocation Report

> Observed lexical association only. This report does not infer cultural meaning or translation quality.

## Method

- Symmetrical lexical-token window: ±5 within sentence boundaries.
- Overlapping windows are merged into unique context-token positions, preventing double counting.
- Chinese candidate overlaps use leftmost-longest matching (for example, 血红 is one target rather than simultaneous 血 and 红 targets).
- English candidate possessives (for example, red’s) are normalized to the declared candidate while remaining one token position.
- PMI and signed log-likelihood ranks require context frequency ≥ 5.
- PMI measures effect strength; signed G² indicates statistical salience and direction relative to the rest of the same-language corpus.
- Rankings are language-internal. Raw scores are not treated as directly comparable across tokenization systems.

## Corpus and context totals

|Language|Corpus tokens|Target occurrences|Target sentences|Unique context positions|Eligible collocates|
|---|---:|---:|---:|---:|---:|
|chinese|124403|736|620|5792|142|
|english|133569|503|446|3844|121|
|spanish|167104|533|465|4079|109|

## Chinese: top PMI collocates

|Rank|Collocate|Context frequency|Corpus frequency|PMI|Signed G²|
|---:|---|---:|---:|---:|---:|
|1|通|12|12|4.425|73.633|
|2|迹|8|8|4.425|49.083|
|3|染|6|6|4.425|36.811|
|4|色|52|54|4.370|302.500|
|5|鲜|18|19|4.347|102.727|
|6|暗|20|23|4.223|105.221|
|7|腥味|16|20|4.103|78.552|
|8|布|11|14|4.077|53.232|
|9|管|6|8|4.010|28.004|
|10|粉|6|8|4.010|28.004|
|11|紫|17|23|3.989|78.495|
|12|腥|10|14|3.939|44.987|
|13|咕嘟|7|10|3.910|31.015|
|14|流着|5|8|3.747|20.375|
|15|深|8|14|3.617|30.533|

## English: top PMI collocates

|Rank|Collocate|Context frequency|Corpus frequency|PMI|Signed G²|
|---:|---|---:|---:|---:|---:|
|1|vessels|5|5|5.119|35.487|
|2|seeping|5|7|4.633|27.228|
|3|spattered|5|7|4.633|27.228|
|4|fiery|6|9|4.534|31.304|
|5|satin|5|8|4.441|25.077|
|6|stained|8|13|4.418|39.754|
|7|silk|8|16|4.119|35.071|
|8|oozed|6|16|3.704|21.999|
|9|fresh|10|27|3.686|36.384|
|10|bright|15|41|3.668|54.162|
|11|setting|5|15|3.534|16.975|
|12|sea|5|17|3.353|15.590|
|13|taste|5|17|3.353|15.590|
|14|sticky|5|19|3.193|14.403|
|15|lantern|7|28|3.119|19.419|

## Spanish: top PMI collocates

|Rank|Collocate|Context frequency|Corpus frequency|PMI|Signed G²|
|---:|---|---:|---:|---:|---:|
|1|coagulada|8|8|5.356|59.420|
|2|inyectados|7|7|5.356|51.990|
|3|manaba|8|12|4.771|44.341|
|4|chorros|5|9|4.508|24.966|
|5|satén|5|9|4.508|24.966|
|6|chorro|7|16|4.164|30.504|
|7|fresca|10|23|4.155|43.428|
|8|oscura|18|43|4.100|76.501|
|9|heridas|8|21|3.964|32.151|
|10|pardo|9|28|3.719|32.622|
|11|seda|7|23|3.640|24.513|
|12|hedor|6|20|3.619|20.818|
|13|espesa|6|21|3.549|20.175|
|14|velo|5|18|3.508|16.505|
|15|caliente|8|29|3.498|26.293|

## Interpretation boundary

- These tables show statistical proximity to the declared candidate set, not semantic equivalence across languages.
- High PMI with low counts remains unstable; the minimum-frequency threshold reduces but does not eliminate this risk.
- Function words remain in the full tables so that filtering choices are transparent; downstream comparison should justify any exclusions.
- Chinese one-character collocates can be fragments of compounds under target-preserving segmentation; concordance lines must be checked before interpretation.
- Private KWIC tables link every target occurrence back to its Phase 2 sentence ID; they are excluded from Git with the source texts.
- No claim of cultural semantic shift is made at this stage.

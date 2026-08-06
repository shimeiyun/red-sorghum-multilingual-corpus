"""Phase 6: integrated uncertainty estimates, figures, and final report."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

import numpy as np

from src.audit_corpus import ROOT


OUT = ROOT / "results" / "phase6_final"
FIGURES = OUT / "figures"
PROCESSED = ROOT / "data" / "processed"
LANGUAGES = ("chinese", "english", "spanish")
PAIRS = (("chinese", "english"), ("chinese", "spanish"), ("english", "spanish"))
PAIR_LABELS = {"chinese-english": "Chinese–English", "chinese-spanish": "Chinese–Spanish", "english-spanish": "English–Spanish"}


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise RuntimeError("Zero-length vector encountered")
    return matrix / norms


def bootstrap_centroids(matrix: np.ndarray, iterations: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    output = np.empty((iterations, matrix.shape[1]), dtype=np.float32)
    chunk = 25
    for start in range(0, iterations, chunk):
        end = min(start + chunk, iterations)
        indices = rng.integers(0, len(matrix), size=(end - start, len(matrix)))
        output[start:end] = l2_normalize(matrix[indices].mean(axis=1))
    return output


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def svg_header(width: int, height: int, title: str, description: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(title)}</title>',
        f'<desc id="desc">{html.escape(description)}</desc>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Arial,"Microsoft YaHei",sans-serif;fill:#20242a}.title{font-size:21px;font-weight:700}.subtitle{font-size:12px;fill:#5b6470}.label{font-size:14px}.value{font-size:12px;font-weight:700}.tick{font-size:11px;fill:#68717c}.grid{stroke:#e4e7eb;stroke-width:1}.axis{stroke:#8d96a0;stroke-width:1}.zero{stroke:#505963;stroke-width:1.5}</style>',
    ]


def similarity_figure(rows: list[dict]) -> None:
    width, height = 900, 420
    left, right, top, bottom = 185, 60, 120, 65
    plot_width = width - left - right
    x_min, x_max = 0.90, 1.00
    x = lambda value: left + (value - x_min) / (x_max - x_min) * plot_width
    lines = svg_header(width, height, "Cross-language centroid similarity", "Candidate and matched-control centroid cosine similarities with bootstrap confidence intervals.")
    lines += [
        '<text x="38" y="42" class="title">Cross-language centroid similarity</text>',
        '<text x="38" y="67" class="subtitle">Dots show centroid cosine; lines show 95% percentile-bootstrap intervals; axis truncated to 0.90–1.00</text>',
    ]
    for tick in range(90, 101):
        value = tick / 100
        xpos = x(value)
        lines.append(f'<line x1="{xpos:.1f}" y1="95" x2="{xpos:.1f}" y2="{height-bottom}" class="grid"/>')
        lines.append(f'<text x="{xpos:.1f}" y="{height-28}" text-anchor="middle" class="tick">{value:.2f}</text>')
    for index, row in enumerate(rows):
        center = top + index * 78
        label = PAIR_LABELS[row["language_pair"]]
        lines.append(f'<text x="{left-18}" y="{center+16}" text-anchor="end" class="label">{label}</text>')
        for offset, prefix, color, shape in ((0, "candidate", "#B23A48", "circle"), (30, "control", "#707983", "square")):
            y = center + offset
            value = float(row[f"{prefix}_cosine"])
            low, high = float(row[f"{prefix}_ci_low"]), float(row[f"{prefix}_ci_high"])
            lines.append(f'<line x1="{x(low):.1f}" y1="{y}" x2="{x(high):.1f}" y2="{y}" stroke="{color}" stroke-width="3"/>')
            lines.append(f'<line x1="{x(low):.1f}" y1="{y-5}" x2="{x(low):.1f}" y2="{y+5}" stroke="{color}"/>')
            lines.append(f'<line x1="{x(high):.1f}" y1="{y-5}" x2="{x(high):.1f}" y2="{y+5}" stroke="{color}"/>')
            if shape == "circle":
                lines.append(f'<circle cx="{x(value):.1f}" cy="{y}" r="6" fill="{color}"/>')
            else:
                lines.append(f'<rect x="{x(value)-5:.1f}" y="{y-5}" width="10" height="10" fill="{color}"/>')
            lines.append(f'<text x="{x(value)+9:.1f}" y="{y-8}" class="value">{value:.3f}</text>')
    lines += [
        '<circle cx="650" cy="80" r="5" fill="#B23A48"/><text x="663" y="84" class="tick">Candidate contexts</text>',
        '<rect x="770" y="75" width="10" height="10" fill="#707983"/><text x="787" y="84" class="tick">Matched controls</text>',
        '</svg>',
    ]
    (FIGURES / "figure_4_embedding_similarity.svg").write_text("\n".join(lines), encoding="utf-8")


def effect_figure(rows: list[dict]) -> None:
    width, height = 880, 360
    left, right, top, bottom = 185, 70, 105, 62
    plot_width = width - left - right
    x_min, x_max = -0.01, 0.04
    x = lambda value: left + (value - x_min) / (x_max - x_min) * plot_width
    lines = svg_header(width, height, "Candidate-context similarity above baseline", "Candidate-minus-control cosine differences with bootstrap confidence intervals.")
    lines += [
        '<text x="38" y="42" class="title">Candidate-context similarity above baseline</text>',
        '<text x="38" y="67" class="subtitle">Candidate centroid cosine minus matched-control cosine; lines show 95% bootstrap intervals</text>',
    ]
    for tick in range(-1, 5):
        value = tick / 100
        xpos = x(value)
        klass = "zero" if value == 0 else "grid"
        lines.append(f'<line x1="{xpos:.1f}" y1="88" x2="{xpos:.1f}" y2="{height-bottom}" class="{klass}"/>')
        lines.append(f'<text x="{xpos:.1f}" y="{height-28}" text-anchor="middle" class="tick">{value:+.2f}</text>')
    for index, row in enumerate(rows):
        y = top + index * 62
        value = float(row["candidate_minus_control"])
        low, high = float(row["delta_ci_low"]), float(row["delta_ci_high"])
        lines.append(f'<text x="{left-18}" y="{y+5}" text-anchor="end" class="label">{PAIR_LABELS[row["language_pair"]]}</text>')
        lines.append(f'<line x1="{x(low):.1f}" y1="{y}" x2="{x(high):.1f}" y2="{y}" stroke="#B23A48" stroke-width="3"/>')
        lines.append(f'<line x1="{x(low):.1f}" y1="{y-6}" x2="{x(low):.1f}" y2="{y+6}" stroke="#B23A48"/>')
        lines.append(f'<line x1="{x(high):.1f}" y1="{y-6}" x2="{x(high):.1f}" y2="{y+6}" stroke="#B23A48"/>')
        lines.append(f'<circle cx="{x(value):.1f}" cy="{y}" r="6" fill="#B23A48"/>')
        lines.append(f'<text x="{x(value)+10:.1f}" y="{y-9}" class="value">{value:+.3f}</text>')
    lines.append('</svg>')
    (FIGURES / "figure_5_embedding_delta.svg").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    parameters = json.loads((ROOT / "config/embedding_parameters.json").read_text(encoding="utf-8"))
    phase1 = json.loads((ROOT / "results/phase1_audit/audit_details.json").read_text(encoding="utf-8"))
    phase3 = json.loads((ROOT / "results/phase3_collocations/collocation_summary.json").read_text(encoding="utf-8"))
    phase4 = read_csv(ROOT / "results/phase4_comparison/structural_comparison.csv")
    phase5_rows = {row["language_pair"]: row for row in read_csv(ROOT / "results/phase5_embeddings/centroid_similarity.csv")}

    embeddings = {
        language: {
            group: np.load(PROCESSED / f"{language}_{group}_embeddings.npz")["embeddings"]
            for group in ("candidate", "control")
        }
        for language in LANGUAGES
    }
    bootstraps = {
        language: {
            group: bootstrap_centroids(
                embeddings[language][group],
                parameters["bootstrap_iterations"],
                parameters["random_seed"] + index * 10 + group_index,
            )
            for group_index, group in enumerate(("candidate", "control"))
        }
        for index, language in enumerate(LANGUAGES)
    }

    integrated = []
    for first, second in PAIRS:
        key = f"{first}-{second}"
        existing = phase5_rows[key]
        target_samples = np.sum(bootstraps[first]["candidate"] * bootstraps[second]["candidate"], axis=1)
        control_samples = np.sum(bootstraps[first]["control"] * bootstraps[second]["control"], axis=1)
        delta_samples = target_samples - control_samples
        integrated.append({
            "language_pair": key,
            "candidate_cosine": existing["candidate_centroid_cosine"],
            "candidate_distance": existing["candidate_semantic_distance"],
            "candidate_ci_low": round(float(np.percentile(target_samples, 2.5)), 6),
            "candidate_ci_high": round(float(np.percentile(target_samples, 97.5)), 6),
            "control_cosine": existing["matched_control_centroid_cosine"],
            "control_ci_low": round(float(np.percentile(control_samples, 2.5)), 6),
            "control_ci_high": round(float(np.percentile(control_samples, 97.5)), 6),
            "candidate_minus_control": existing["candidate_minus_control"],
            "delta_ci_low": round(float(np.percentile(delta_samples, 2.5)), 6),
            "delta_ci_high": round(float(np.percentile(delta_samples, 97.5)), 6),
        })
    write_csv(OUT / "embedding_comparison_with_intervals.csv", integrated)
    similarity_figure(integrated)
    effect_figure(integrated)

    audit = phase1["corpora"]
    target_rates = {row["language"]: float(row["target_occurrences_per_10000_tokens"]) for row in phase4}
    report = f"""# A Corpus-based and Computational Analysis of Cultural Semantic Shift in Chinese–English–Spanish Translation

## The representation of red in *Red Sorghum*

## Abstract

This portfolio study examines how a declared set of red-related lexical items is represented in the Chinese, English, and Spanish versions of *Red Sorghum*. It combines corpus auditing, reproducible sentence preprocessing, ±5-token collocation statistics, structural comparison, and multilingual sentence embeddings. The validated literary-text slices share five parts with 9/11/9/9/10 subsections. Collocation strength is measured with frequency, PMI, and signed log-likelihood, while semantic context is represented with 384-dimensional multilingual MiniLM embeddings. Candidate-bearing sentences are compared with same-language, length-matched non-candidate controls, and uncertainty is estimated through 500 bootstrap iterations. The declared candidates occur at 59.16, 37.66, and 31.90 non-overlapping instances per 10,000 tokens in Chinese, English, and Spanish respectively, but these rates are not direct translation-equivalence measures. Candidate-context centroids are highly similar across languages (cosine 0.967–0.985) and exceed matched baselines by only 0.012–0.017. The results support a cautious claim of modest cross-language concentration in red-related contexts, while lexical differences, candidate design, tokenization, and the shared narrative remain important alternative explanations. Corpus evidence and interpretation are kept explicitly separate throughout.

## 1. Research questions

1. How frequent are the declared red-related candidates in each validated text?
2. Which lexical items are statistically associated with those candidates within each language?
3. How do the distributional structures of these association profiles differ across languages?
4. Are candidate-bearing sentence contexts more similar across languages than length-matched non-candidate contexts from the same novels?

## 2. Data and scope

Only the three researcher-supplied complete novel files are used as corpus data. The raw files decode under strict UTF-8 rules and are preserved unchanged. Ebook metadata, contents pages, copyright matter, and author biographies are excluded through documented boundary markers; shared literary dedications remain. Structural validation found the same five-part organization and subsection pattern in all three retained texts.

|Language|Analysis tokens|Phase 2 sentences|Declared candidate set|
|---|---:|---:|---|
|Chinese|{audit['chinese']['analysis_tokens']}|8176|红, 血, 鲜红, 赤, 血红|
|English|{audit['english']['analysis_tokens']}|8812|red, blood, bloody, crimson, scarlet|
|Spanish|{audit['spanish']['analysis_tokens']}|9491|rojo, roja, rojos, rojas, sangre|

The candidate sets are operational definitions, not claims of exact lexical equivalence. Chinese strings overlap, while Spanish includes grammatical gender and number forms. Phase 3 therefore uses non-overlapping longest-match targets.

## 3. Methods

### 3.1 Audit and preprocessing

Phase 1 records encoding, hashes, corpus size, provisional sentence counts, structural boundaries, and observed candidate frequencies. Phase 2 creates deterministic sentence records containing stable IDs, paragraph IDs, normalized analysis text, exact raw substrings, and complete-file character offsets. All retained non-whitespace characters are covered, and serialized offsets were independently verified.

### 3.2 Collocation analysis

Candidate contexts are measured within symmetrical ±5 lexical-token windows bounded by sentence boundaries. Overlapping windows are merged into unique token positions. PMI represents association strength; signed G² log-likelihood represents salience and direction relative to the remainder of the same-language corpus. Ranked results require at least five context occurrences. Raw scores are interpreted within languages because Chinese and Latin-script tokenization are not identical measurement systems.

### 3.3 Multilingual semantic analysis

Candidate-bearing sentences are encoded with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` through FastEmbed 0.8.0 using mean pooling and explicit L2 normalization. One non-candidate sentence is greedily matched to each candidate sentence on normalized character length. Cross-language comparisons use normalized group centroids. Percentile intervals are estimated with 500 bootstrap resamples using seed 42.

## 4. Results

### 4.1 Candidate frequency and association structure

Non-overlapping target rates are {target_rates['chinese']:.2f}, {target_rates['english']:.2f}, and {target_rates['spanish']:.2f} per 10,000 tokens for Chinese, English, and Spanish. These differences describe the declared candidate sets; they do not by themselves show semantic loss or gain.

![Target occurrences per 10,000 tokens](results/phase4_comparison/figures/figure_1_target_rate.svg)

Eligible positive association profiles contain 105 Chinese, 89 English, and 84 Spanish collocates. Their normalized entropy values are 0.767, 0.808, and 0.786. The profiles are therefore broadly distributed rather than dominated by one collocate, although Spanish has the largest top-ten frequency share (0.626).

![Association distribution structure](results/phase4_comparison/figures/figure_2_distribution_structure.svg)

The highest-PMI lists contain observable bodily-fluid, visual-intensity, and material-context vocabulary: Chinese includes 色, 鲜, 暗, 腥味, and 紫; English includes vessels, seeping, spattered, stained, fresh, bright, silk, and satin; Spanish includes coagulada, manaba, chorros, fresca, oscura, heridas, seda, and satén. This is an exploratory description of the ranked words, not a manually validated semantic taxonomy. Chinese one-character collocates may also be compound fragments and require concordance checking.

![Top PMI collocates](results/phase4_comparison/figures/figure_3_top_pmi_collocates.svg)

### 4.2 Multilingual sentence-context similarity

|Language pair|Candidate cosine|Distance|Control cosine|Candidate − control|Delta 95% CI|
|---|---:|---:|---:|---:|---|
|Chinese–English|0.969|0.031|0.956|+0.013|[0.004, 0.025]|
|Chinese–Spanish|0.967|0.033|0.950|+0.017|[0.007, 0.030]|
|English–Spanish|0.985|0.015|0.973|+0.012|[0.005, 0.024]|

![Candidate and control centroid similarities](results/phase6_final/figures/figure_4_embedding_similarity.svg)

All three candidate-context comparisons exceed their matched baselines by a small amount, and all three bootstrap delta intervals remain above zero. The strongest candidate centroid similarity is English–Spanish; the largest baseline-adjusted difference is Chinese–Spanish. These are corpus-level centroid observations, not sentence alignments or evaluations of translation quality.

![Candidate similarity above baseline](results/phase6_final/figures/figure_5_embedding_delta.svg)

## 5. Discussion

The lexical and embedding results answer different questions. Collocation tables show which forms occur near the declared candidates inside each language. The embedding comparison shows whether the overall sentence contexts containing those candidates occupy similar multilingual vector regions. High raw centroid similarity is expected in part because all three texts share a narrative. The matched baseline is therefore crucial: after accounting for general same-novel similarity, candidate contexts retain a modest positive difference of approximately one to two cosine points.

The safest conclusion is that red-related contexts show measurable cross-language concentration alongside language-specific lexical realization. This does not establish a unidirectional cultural semantic shift. A stronger shift claim would require reliable sentence or passage alignment, manual semantic annotation, and sensitivity analysis using narrower and alternative candidate sets.

## 6. Limitations

- The study contains one novel and cannot support population-level claims about Chinese, English, or Spanish translation generally.
- Candidate sets differ in morphology and include blood-related terms as well as color terms; frequency totals are therefore not direct equivalents.
- Chinese candidate substrings overlap, and target-preserving segmentation can create one-character compound fragments.
- Sentence segmentation is deterministic rather than manually gold-annotated.
- The translations are not aligned at sentence level; centroid and nearest-neighbor analyses are exploratory.
- Multilingual MiniLM is a pretrained, quantized model with its own training-domain and cross-language biases.
- The bootstrap measures sampling variability within this corpus, not uncertainty about candidate design or model choice.
- No independent human annotation or inter-annotator agreement is included.

## 7. Reproducibility and research integrity

All thresholds, candidate forms, corpus boundaries, model settings, random seeds, and software dependencies are stored in versioned configuration or requirements files. Each phase writes machine-readable intermediate summaries. `run_pipeline.py` runs any consecutive phase range, while `verify_project.py` checks cross-phase invariants. Aggregate results and figures can be shared; copyrighted novels, sentence excerpts, embeddings, and nearest-neighbor tables remain excluded from Git.

Observed corpus measurements, exploratory interpretation, and unsupported claims are explicitly separated. No cultural meaning is inferred solely from frequency, PMI, or cosine similarity.

## 8. References

- Dunning, T. (1993). Accurate methods for the statistics of surprise and coincidence. *Computational Linguistics, 19*(1), 61–74.
- Church, K. W., & Hanks, P. (1990). Word association norms, mutual information, and lexicography. *Computational Linguistics, 16*(1), 22–29.
- Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. *EMNLP-IJCNLP*.
- Sentence Transformers. `paraphrase-multilingual-MiniLM-L12-v2` model card: https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- Qdrant. FastEmbed documentation: https://qdrant.github.io/fastembed/
"""
    (ROOT / "FINAL_REPORT.md").write_text(report, encoding="utf-8")
    summary = {
        "phase": 6,
        "status": "complete",
        "figures": 5,
        "language_pairs": len(integrated),
        "final_report": "FINAL_REPORT.md",
        "evidence_interpretation_separated": True,
    }
    (OUT / "phase6_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Phase 6 complete: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Phase 4: cautious cross-language comparison of association structure."""

from __future__ import annotations

import csv
import html
import json
import math
import statistics
from pathlib import Path

from src.audit_corpus import ROOT


PHASE3 = ROOT / "results" / "phase3_collocations"
OUT = ROOT / "results" / "phase4_comparison"
FIGURES = OUT / "figures"
LANGUAGES = ("chinese", "english", "spanish")
LABELS = {"chinese": "Chinese", "english": "English", "spanish": "Spanish"}
COLORS = {"chinese": "#B23A48", "english": "#35618C", "spanish": "#C98228"}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def normalized_entropy(frequencies: list[int]) -> float:
    if len(frequencies) <= 1:
        return 0.0
    total = sum(frequencies)
    entropy = -sum((value / total) * math.log2(value / total) for value in frequencies)
    return entropy / math.log2(len(frequencies))


def svg_start(width: int, height: int, title: str, description: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(title)}</title>',
        f'<desc id="desc">{html.escape(description)}</desc>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Arial,"Microsoft YaHei",sans-serif;fill:#20242a}.title{font-size:21px;font-weight:700}.subtitle{font-size:12px;fill:#5b6470}.label{font-size:14px}.value{font-size:13px;font-weight:700}.axis{stroke:#aeb5bd;stroke-width:1}.grid{stroke:#e4e7eb;stroke-width:1}.tick{font-size:11px;fill:#68717c}</style>',
    ]


def target_rate_figure(metrics: list[dict]) -> None:
    width, height = 820, 360
    values = [float(row["target_occurrences_per_10000_tokens"]) for row in metrics]
    maximum = max(values) * 1.12
    left, right, top, bar_height, gap = 155, 60, 115, 44, 28
    plot_width = width - left - right
    lines = svg_start(width, height, "Declared candidate-set rate", "Target occurrences per ten thousand lexical tokens in each corpus.")
    lines += [
        '<text x="40" y="42" class="title">Declared candidate-set rate</text>',
        '<text x="40" y="67" class="subtitle">Non-overlapping occurrences per 10,000 lexical tokens</text>',
    ]
    for tick in range(0, 6):
        value = maximum * tick / 5
        x = left + plot_width * tick / 5
        lines.append(f'<line x1="{x:.1f}" y1="92" x2="{x:.1f}" y2="{height-42}" class="grid"/>')
        lines.append(f'<text x="{x:.1f}" y="{height-22}" text-anchor="middle" class="tick">{value:.1f}</text>')
    for index, row in enumerate(metrics):
        y = top + index * (bar_height + gap)
        value = float(row["target_occurrences_per_10000_tokens"])
        length = value / maximum * plot_width
        language = row["language"]
        lines.append(f'<text x="{left-14}" y="{y+28}" text-anchor="end" class="label">{LABELS[language]}</text>')
        lines.append(f'<rect x="{left}" y="{y}" width="{length:.1f}" height="{bar_height}" rx="3" fill="{COLORS[language]}"/>')
        lines.append(f'<text x="{left+length+10:.1f}" y="{y+28}" class="value">{value:.2f}</text>')
    lines.append('</svg>')
    (FIGURES / "figure_1_target_rate.svg").write_text("\n".join(lines), encoding="utf-8")


def structure_figure(metrics: list[dict]) -> None:
    width, height = 860, 430
    left, right, top, bottom = 105, 45, 110, 70
    plot_width, plot_height = width - left - right, height - top - bottom
    group_width = plot_width / 3
    lines = svg_start(width, height, "Association distribution structure", "Normalized entropy and top-ten concentration among eligible overrepresented collocates.")
    lines += [
        '<text x="40" y="42" class="title">Association distribution structure</text>',
        '<text x="40" y="67" class="subtitle">Eligible overrepresented collocates only; both measures range from 0 to 1</text>',
    ]
    for tick in range(0, 6):
        value = tick / 5
        y = top + plot_height * (1 - value)
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
        lines.append(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" class="tick">{value:.1f}</text>')
    for index, row in enumerate(metrics):
        center = left + group_width * (index + 0.5)
        values = (
            ("Entropy", float(row["normalized_entropy"]), COLORS[row["language"]]),
            ("Top-10 share", float(row["top10_frequency_share"]), "#777f89"),
        )
        for offset, (name, value, color) in zip((-34, 34), values):
            x = center + offset - 25
            y = top + plot_height * (1 - value)
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="50" height="{top+plot_height-y:.1f}" rx="2" fill="{color}"/>')
            lines.append(f'<text x="{x+25:.1f}" y="{y-8:.1f}" text-anchor="middle" class="value">{value:.3f}</text>')
        lines.append(f'<text x="{center:.1f}" y="{height-38}" text-anchor="middle" class="label">{LABELS[row["language"]]}</text>')
    lines += [
        f'<rect x="{width-265}" y="28" width="12" height="12" fill="{COLORS["chinese"]}"/><text x="{width-246}" y="39" class="tick">Normalized entropy</text>',
        f'<rect x="{width-130}" y="28" width="12" height="12" fill="#777f89"/><text x="{width-111}" y="39" class="tick">Top-10 share</text>',
        '</svg>',
    ]
    (FIGURES / "figure_2_distribution_structure.svg").write_text("\n".join(lines), encoding="utf-8")


def top_collocates_figure(top_rows: dict[str, list[dict]]) -> None:
    width, height = 1120, 610
    margin, panel_gap, panel_width = 35, 35, 326
    top, row_height = 100, 45
    global_max = max(float(row["pmi"]) for rows in top_rows.values() for row in rows)
    lines = svg_start(width, height, "Top PMI collocates by language", "Three language-internal panels showing the ten highest PMI collocates meeting the frequency threshold.")
    lines += [
        '<text x="35" y="40" class="title">Top PMI collocates by language</text>',
        '<text x="35" y="65" class="subtitle">Context frequency ≥ 5; shared visual scale, but scores remain language-internal</text>',
    ]
    for panel, language in enumerate(LANGUAGES):
        x0 = margin + panel * (panel_width + panel_gap)
        lines.append(f'<text x="{x0}" y="88" class="label">{LABELS[language]}</text>')
        label_width, chart_width = 82, panel_width - 122
        for index, row in enumerate(top_rows[language]):
            y = top + index * row_height
            value = float(row["pmi"])
            length = value / global_max * chart_width
            label = html.escape(row["collocate"])
            lines.append(f'<text x="{x0+label_width-8}" y="{y+20}" text-anchor="end" class="label">{label}</text>')
            lines.append(f'<rect x="{x0+label_width}" y="{y+5}" width="{length:.1f}" height="20" rx="2" fill="{COLORS[language]}"/>')
            lines.append(f'<text x="{x0+label_width+length+6:.1f}" y="{y+20}" class="tick">{value:.2f}</text>')
    lines.append('</svg>')
    (FIGURES / "figure_3_top_pmi_collocates.svg").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    summary_path = PHASE3 / "collocation_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError("Run Phase 3 first")
    phase3 = json.loads(summary_path.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    metrics: list[dict] = []
    top_rows: dict[str, list[dict]] = {}
    for language in LANGUAGES:
        rows = read_csv(PHASE3 / f"{language}_collocations.csv")
        positive = [row for row in rows if row["meets_minimum_frequency"] == "True" and row["association"] == "overrepresented"]
        frequencies = [int(row["context_frequency"]) for row in positive]
        total_frequency = sum(frequencies)
        largest = sorted(frequencies, reverse=True)[:10]
        corpus = phase3["corpora"][language]
        pmi_values = [float(row["pmi"]) for row in positive]
        metrics.append({
            "language": language,
            "corpus_tokens": corpus["corpus_tokens_phase3"],
            "target_occurrences": corpus["target_occurrences_nonoverlapping"],
            "target_occurrences_per_10000_tokens": round(corpus["target_occurrences_nonoverlapping"] / corpus["corpus_tokens_phase3"] * 10000, 6),
            "eligible_overrepresented_collocates": len(positive),
            "normalized_entropy": round(normalized_entropy(frequencies), 6),
            "top10_frequency_share": round(sum(largest) / total_frequency, 6),
            "median_positive_pmi": round(statistics.median(pmi_values), 6),
        })
        top_rows[language] = sorted(positive, key=lambda row: int(row["pmi_rank"]))[:10]

    rank_rows = []
    for rank in range(10):
        row = {"rank": rank + 1}
        for language in LANGUAGES:
            item = top_rows[language][rank]
            row[f"{language}_collocate"] = item["collocate"]
            row[f"{language}_context_frequency"] = item["context_frequency"]
            row[f"{language}_pmi"] = item["pmi"]
            row[f"{language}_signed_g2"] = item["signed_log_likelihood_g2"]
        rank_rows.append(row)

    write_csv(OUT / "structural_comparison.csv", metrics)
    write_csv(OUT / "top_collocates_side_by_side.csv", rank_rows)
    target_rate_figure(metrics)
    structure_figure(metrics)
    top_collocates_figure(top_rows)

    lines = [
        "# Phase 4 Cross-language Association Comparison", "",
        "> This is a structural comparison of observed association profiles. It does not claim that same-ranked words are translations or semantic equivalents.", "",
        "## Comparable descriptive measures", "",
        "|Language|Targets per 10k tokens|Eligible positive collocates|Normalized entropy|Top-10 frequency share|Median positive PMI|",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in metrics:
        lines.append(f"|{LABELS[row['language']]}|{row['target_occurrences_per_10000_tokens']:.2f}|{row['eligible_overrepresented_collocates']}|{row['normalized_entropy']:.3f}|{row['top10_frequency_share']:.3f}|{row['median_positive_pmi']:.3f}|")
    lines += [
        "", "## Figures", "",
        "1. `figures/figure_1_target_rate.svg`: normalized frequency of the declared target sets.",
        "2. `figures/figure_2_distribution_structure.svg`: concentration and normalized entropy of eligible positive collocates.",
        "3. `figures/figure_3_top_pmi_collocates.svg`: language-internal top-PMI profiles shown side by side.",
        "", "## Evidence boundary", "",
        "- Candidate sets differ in size and lexical composition, so normalized target rates are descriptive rather than proof of translation shift.",
        "- Entropy and concentration summarize distribution shape after the same frequency threshold; they do not identify cultural categories.",
        "- Chinese segmentation and Latin word tokenization are not identical measurement systems; raw PMI and G² values are not interpreted as directly equivalent across languages.",
        "- Side-by-side rank positions are visual alignment only, not word-level translation alignment.",
        "- Semantic equivalence and distance require the explicitly separate multilingual embedding stage.",
    ]
    (OUT / "PHASE4_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Phase 4 complete: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

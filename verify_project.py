"""Verify cross-phase invariants without altering analysis outputs."""

from __future__ import annotations

import csv
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    checks: list[tuple[str, bool]] = []
    phase1 = json.loads((ROOT / "results/phase1_audit/audit_details.json").read_text(encoding="utf-8"))
    checks.append(("phase1_three_corpora", set(phase1["corpora"]) == {"chinese", "english", "spanish"}))
    checks.append(("phase1_validated_structure", all(item["section_structure"] == "9/11/9/9/10" for item in phase1["corpora"].values())))

    phase2 = json.loads((ROOT / "results/phase2_preprocessing/preprocessing_summary.json").read_text(encoding="utf-8"))
    checks.append(("phase2_full_coverage", all(item["coverage"] == 1.0 for item in phase2["corpora"].values())))
    checks.append(("phase2_offsets", all(item["serialized_offsets_verified"] for item in phase2["corpora"].values())))

    for language in ("chinese", "english", "spanish"):
        collocations = rows(ROOT / f"results/phase3_collocations/{language}_collocations.csv")
        checks.append((f"phase3_{language}_finite", all(math.isfinite(float(row["pmi"])) and math.isfinite(float(row["signed_log_likelihood_g2"])) for row in collocations)))
        checks.append((f"phase3_{language}_frequency", all(0 < int(row["context_frequency"]) <= int(row["corpus_frequency"]) for row in collocations)))

    comparison = rows(ROOT / "results/phase4_comparison/structural_comparison.csv")
    checks.append(("phase4_metric_ranges", all(0 <= float(row["normalized_entropy"]) <= 1 and 0 <= float(row["top10_frequency_share"]) <= 1 for row in comparison)))
    svg_files = list((ROOT / "results/phase4_comparison/figures").glob("*.svg")) + list((ROOT / "results/phase6_final/figures").glob("*.svg"))
    for path in svg_files:
        ET.parse(path)
    checks.append(("svg_xml_valid", len(svg_files) == 5))

    phase5 = json.loads((ROOT / "results/phase5_embeddings/embedding_summary.json").read_text(encoding="utf-8"))
    checks.append(("phase5_model_revision_recorded", bool(phase5["model"]["revision"])))
    for language in ("chinese", "english", "spanish"):
        for group in ("candidate", "control"):
            path = ROOT / f"data/processed/{language}_{group}_embeddings.npz"
            if path.exists():
                vectors = np.load(path)["embeddings"]
                checks.append((f"phase5_{language}_{group}_norms", bool(np.isfinite(vectors).all() and np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5))))

    final_metrics = rows(ROOT / "results/phase6_final/embedding_comparison_with_intervals.csv")
    checks.append(("phase6_three_language_pairs", len(final_metrics) == 3))
    checks.append(("phase6_report_present", (ROOT / "FINAL_REPORT.md").exists()))
    failed = [name for name, passed in checks if not passed]
    print(f"{len(checks) - len(failed)}/{len(checks)} checks passed")
    if failed:
        print("Failed: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

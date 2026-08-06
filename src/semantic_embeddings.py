"""Phase 5: multilingual sentence embeddings with a matched-corpus baseline."""

from __future__ import annotations

import bisect
import csv
import json
import os
import statistics
import tempfile
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

from src.audit_corpus import ROOT


PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "results" / "phase5_embeddings"
LANGUAGES = ("chinese", "english", "spanish")
PAIRS = (("chinese", "english"), ("chinese", "spanish"), ("english", "spanish"))


def read_sentences(language: str) -> list[dict]:
    with (PROCESSED / f"{language}_sentences.csv").open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def matched_controls(candidates: list[dict], pool: list[dict]) -> list[dict]:
    """Greedy one-to-one nearest-length matching with deterministic ID tie breaks."""
    available = sorted((len(row["sentence_text"]), row["sentence_id"], row) for row in pool)
    controls = []
    for candidate in sorted(candidates, key=lambda row: (len(row["sentence_text"]), row["sentence_id"])):
        target = len(candidate["sentence_text"])
        position = bisect.bisect_left(available, (target, "", {}))
        options = []
        if position < len(available):
            options.append(position)
        if position > 0:
            options.append(position - 1)
        chosen = min(options, key=lambda index: (abs(available[index][0] - target), available[index][1]))
        controls.append(available.pop(chosen)[2])
    return sorted(controls, key=lambda row: row["sentence_id"])


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise RuntimeError("Zero-length embedding encountered")
    return matrix / norms


def centroid(matrix: np.ndarray) -> np.ndarray:
    value = matrix.mean(axis=0)
    norm = np.linalg.norm(value)
    if norm == 0:
        raise RuntimeError("Zero-length centroid encountered")
    return value / norm


def bootstrap_centroids(matrix: np.ndarray, iterations: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    output = np.empty((iterations, matrix.shape[1]), dtype=np.float32)
    chunk = 25
    for start in range(0, iterations, chunk):
        end = min(start + chunk, iterations)
        indices = rng.integers(0, len(matrix), size=(end - start, len(matrix)))
        means = matrix[indices].mean(axis=1)
        output[start:end] = l2_normalize(means)
    return output


def cache_directory() -> Path:
    configured = os.environ.get("RED_SORGHUM_MODEL_CACHE")
    if configured:
        return Path(configured)
    # A short Windows path avoids legacy MAX_PATH failures in Hugging Face caches.
    return Path(tempfile.gettempdir()) / "rsm"


def model_revision(cache: Path) -> str | None:
    revisions = sorted(path.name for path in cache.rglob("snapshots/*") if path.is_dir())
    return revisions[-1] if revisions else None


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parameters = json.loads((ROOT / "config" / "embedding_parameters.json").read_text(encoding="utf-8"))
    cache = cache_directory()
    cache.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    groups: dict[str, dict[str, list[dict]]] = {}
    for language in LANGUAGES:
        rows = read_sentences(language)
        candidates = [row for row in rows if row["has_candidate"] == "True" and row["is_lexical"] == "True"]
        pool = [row for row in rows if row["has_candidate"] == "False" and row["is_lexical"] == "True"]
        controls = matched_controls(candidates, pool)
        if len(candidates) != len(controls):
            raise RuntimeError(f"Control matching failed for {language}")
        groups[language] = {"candidate": candidates, "control": controls}

    model = TextEmbedding(
        model_name=parameters["model_name"],
        cache_dir=str(cache),
        threads=parameters["threads"],
    )
    embeddings: dict[str, dict[str, np.ndarray]] = {}
    for language in LANGUAGES:
        embeddings[language] = {}
        for group_name in ("candidate", "control"):
            rows = groups[language][group_name]
            vectors = np.asarray(list(model.embed(
                [row["sentence_text"] for row in rows],
                batch_size=parameters["batch_size"],
            )), dtype=np.float32)
            if vectors.shape != (len(rows), parameters["embedding_dimension"]) or not np.isfinite(vectors).all():
                raise RuntimeError(f"Invalid embeddings for {language}:{group_name}: {vectors.shape}")
            vectors = l2_normalize(vectors).astype(np.float32)
            embeddings[language][group_name] = vectors
            np.savez_compressed(
                PROCESSED / f"{language}_{group_name}_embeddings.npz",
                sentence_ids=np.asarray([row["sentence_id"] for row in rows]),
                embeddings=vectors,
            )

    bootstraps: dict[str, dict[str, np.ndarray]] = {}
    for language_index, language in enumerate(LANGUAGES):
        bootstraps[language] = {}
        for group_index, group_name in enumerate(("candidate", "control")):
            bootstraps[language][group_name] = bootstrap_centroids(
                embeddings[language][group_name],
                parameters["bootstrap_iterations"],
                parameters["random_seed"] + language_index * 10 + group_index,
            )

    similarity_rows = []
    for first, second in PAIRS:
        candidate_similarity = float(centroid(embeddings[first]["candidate"]) @ centroid(embeddings[second]["candidate"]))
        control_similarity = float(centroid(embeddings[first]["control"]) @ centroid(embeddings[second]["control"]))
        target_samples = np.sum(bootstraps[first]["candidate"] * bootstraps[second]["candidate"], axis=1)
        control_samples = np.sum(bootstraps[first]["control"] * bootstraps[second]["control"], axis=1)
        delta_samples = target_samples - control_samples
        similarity_rows.append({
            "language_pair": f"{first}-{second}",
            "candidate_centroid_cosine": round(candidate_similarity, 6),
            "candidate_semantic_distance": round(1 - candidate_similarity, 6),
            "candidate_bootstrap_ci_low": round(float(np.percentile(target_samples, 2.5)), 6),
            "candidate_bootstrap_ci_high": round(float(np.percentile(target_samples, 97.5)), 6),
            "matched_control_centroid_cosine": round(control_similarity, 6),
            "candidate_minus_control": round(candidate_similarity - control_similarity, 6),
            "delta_bootstrap_ci_low": round(float(np.percentile(delta_samples, 2.5)), 6),
            "delta_bootstrap_ci_high": round(float(np.percentile(delta_samples, 97.5)), 6),
        })
    write_csv(OUT / "centroid_similarity.csv", similarity_rows)

    neighbor_rows = []
    chinese_vectors = embeddings["chinese"]["candidate"]
    chinese_rows = groups["chinese"]["candidate"]
    for target_language in ("english", "spanish"):
        target_vectors = embeddings[target_language]["candidate"]
        scores = chinese_vectors @ target_vectors.T
        best = scores.argmax(axis=1)
        for index, target_index in enumerate(best):
            neighbor_rows.append({
                "source_language": "chinese",
                "source_sentence_id": chinese_rows[index]["sentence_id"],
                "target_language": target_language,
                "nearest_sentence_id": groups[target_language]["candidate"][int(target_index)]["sentence_id"],
                "cosine_similarity": round(float(scores[index, target_index]), 6),
            })
    write_csv(PROCESSED / "cross_language_nearest_contexts.csv", neighbor_rows)

    summary = {
        "phase": 5,
        "scope": "multilingual sentence-embedding evidence with matched non-candidate baseline",
        "model": {
            "model_name": parameters["model_name"],
            "fastembed_version": "0.8.0",
            "onnx_repository": "qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q",
            "revision": model_revision(cache),
            "dimension": parameters["embedding_dimension"],
            "pooling": parameters["pooling"],
            "license": "Apache-2.0",
        },
        "parameters": parameters,
        "corpora": {},
        "similarities": similarity_rows,
    }
    for language in LANGUAGES:
        candidate_lengths = [len(row["sentence_text"]) for row in groups[language]["candidate"]]
        control_lengths = [len(row["sentence_text"]) for row in groups[language]["control"]]
        summary["corpora"][language] = {
            "candidate_sentences": len(candidate_lengths),
            "matched_control_sentences": len(control_lengths),
            "candidate_median_characters": statistics.median(candidate_lengths),
            "control_median_characters": statistics.median(control_lengths),
            "embedding_norms_verified": bool(np.allclose(np.linalg.norm(embeddings[language]["candidate"], axis=1), 1.0, atol=1e-5)),
        }
    (OUT / "embedding_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Phase 5 Multilingual Sentence-Embedding Report", "",
        "> Corpus-level semantic similarity evidence only. The results do not establish sentence alignment, translation quality, or cultural causation.", "",
        "## Model", "",
        f"- Model: `{parameters['model_name']}` (384 dimensions; multilingual; Apache-2.0).",
        "- Runtime: FastEmbed 0.8.0 quantized ONNX, mean pooling, followed by explicit L2 normalization.",
        f"- Bootstrap: {parameters['bootstrap_iterations']} iterations; seed {parameters['random_seed']}.",
        "- Baseline: one same-language non-candidate sentence per candidate sentence, greedily matched on character length.", "",
        "## Pairwise centroid results", "",
        "|Language pair|Candidate cosine|Distance|95% bootstrap CI|Control cosine|Candidate − control|Delta 95% CI|",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for row in similarity_rows:
        lines.append(
            f"|{row['language_pair']}|{row['candidate_centroid_cosine']:.3f}|{row['candidate_semantic_distance']:.3f}|"
            f"[{row['candidate_bootstrap_ci_low']:.3f}, {row['candidate_bootstrap_ci_high']:.3f}]|"
            f"{row['matched_control_centroid_cosine']:.3f}|{row['candidate_minus_control']:.3f}|"
            f"[{row['delta_bootstrap_ci_low']:.3f}, {row['delta_bootstrap_ci_high']:.3f}]|"
        )
    lines += [
        "", "## Interpretation boundary", "",
        "- Candidate centroids summarize all candidate-bearing sentences in each language; they do not align translated sentences.",
        "- The matched baseline helps distinguish candidate-context similarity from general similarity caused by all three texts being versions of the same novel.",
        "- A positive candidate-minus-control value is descriptive evidence of greater cross-language concentration, not proof of semantic preservation.",
        "- A negative value is not proof of cultural loss; candidate selection, translation choices, segmentation, and model behavior remain alternative explanations.",
        "- Nearest-neighbor sentence IDs and sentence embeddings are private intermediate data and are excluded from Git.",
    ]
    (OUT / "PHASE5_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Phase 5 complete: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run a selected consecutive range of project phases."""

from __future__ import annotations

import argparse
import importlib


PHASES = {
    1: "src.audit_corpus",
    2: "src.preprocess_corpus",
    3: "src.collocation_analysis",
    4: "src.compare_associations",
    5: "src.semantic_embeddings",
    6: "src.finalize_portfolio",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Red Sorghum corpus-analysis pipeline.")
    parser.add_argument("--from-phase", type=int, default=1, choices=PHASES)
    parser.add_argument("--to-phase", type=int, default=6, choices=PHASES)
    args = parser.parse_args()
    if args.from_phase > args.to_phase:
        parser.error("--from-phase must not exceed --to-phase")
    for phase in range(args.from_phase, args.to_phase + 1):
        print(f"Running Phase {phase}...")
        result = importlib.import_module(PHASES[phase]).main()
        if result:
            return int(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

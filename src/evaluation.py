# src/evaluation.py

from __future__ import annotations

from src.analysis.proxy_summary_and_validation import main as run_proxy_summary


def run_full_evaluation() -> None:
    """
    Run the full evaluation / visualization pipeline.

    Currently this just delegates to proxy_summary_and_validation.main(),
    which reads the proxy CSVs and produces summary tables & figures.
    """
    print("Running evaluation: proxy summary and validation ...")
    run_proxy_summary()
    print("Evaluation finished.")

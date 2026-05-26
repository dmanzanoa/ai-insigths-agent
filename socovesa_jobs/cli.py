from __future__ import annotations

import argparse

from .config import DATA_SOURCES, settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Socovesa agentic insights pipeline")
    parser.add_argument("--labels", nargs="+", default=["subsidio"])
    args = parser.parse_args()

    from .aws_clients import create_aws_clients
    from .pipeline import run_agentic_pipeline

    clients = create_aws_clients(settings)
    for label in args.labels:
        if label not in DATA_SOURCES:
            print(f"Unknown label: {label}")
            continue
        run_agentic_pipeline(label, clients, settings)

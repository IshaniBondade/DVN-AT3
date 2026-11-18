"""Rebuild the processed snapshot and validate without launching Streamlit."""
from __future__ import annotations

import argparse
import json
import runpy
import pandas as pd
from .data import file_sha256, load_models, validate_dataset
from .settings import ROOT, data_path, load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "validate"])
    args = parser.parse_args()
    config = load_settings()
    if args.action == "build":
        runpy.run_path(str(ROOT / "scripts/make_processed.py"), run_name="__main__")
    models = load_models(data_path(config, "processed"), config.get("columns"))
    report = validate_dataset(models, config["analysis"]["periods"])
    report["raw_sha256"] = file_sha256(data_path(config, "raw"))
    report["processed_sha256"] = file_sha256(data_path(config, "processed"))
    raw = pd.read_csv(data_path(config, "raw"))
    processed = pd.read_csv(data_path(config, "processed"))
    report["snapshot_date"] = config["data"]["snapshot_date"]
    metadata_path = ROOT / "data" / "source-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update({
        "snapshot_date": config["data"]["snapshot_date"],
        "raw_records": len(raw),
        "raw_columns": len(raw.columns),
        "raw_sha256": report["raw_sha256"],
        "processed_records": len(processed),
        "processed_columns": len(processed.columns),
        "processed_file": "processed/models_clean.csv",
        "processed_sha256": report["processed_sha256"],
        "latest_observation": models["publication_date"].max().date().isoformat(),
        "transform": "scripts/make_processed.py",
    })
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    output = ROOT / "data" / "validation-report.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

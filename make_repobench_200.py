#!/usr/bin/env python3
"""
make_repobench_200.py
Creates repobench_200.jsonl by sampling 200 items from RepoBench Java v1.1 (in_file split).

Each line is a JSON object with:
- input: OpenAI-style messages
- ideal: the ground-truth next line from the dataset
"""

import os
import json
import sys

# ✅ Disable Hugging Face checksum / metadata validation globally
os.environ["HF_DATASETS_IGNORE_VERIFICATION"] = "1"
os.environ["HF_DATASETS_IGNORE_CHECKSUMS"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "0"

from datasets import load_dataset

N = 200
SEED = 42
OUTFILE = "repobench_200.jsonl"


def main() -> int:
    try:
        # Force re-download and skip verification
        ds = load_dataset(
            "tianyang/repobench_java_v1.1",
            download_mode="force_redownload",
            verification_mode="no_checks",
        )["in_file"]
    except Exception as e:
        print(
            "Failed to load dataset.\n"
            "Fixes to try:\n"
            "  1) Ensure you have internet access\n"
            "  2) Upgrade: python -m pip install -U datasets huggingface_hub\n"
            "  3) Delete cache: rm -rf ~/.cache/huggingface/datasets/tianyang___parquet\n",
            file=sys.stderr,
        )
        print(str(e), file=sys.stderr)
        return 1

    if len(ds) < N:
        print(f"Dataset split has only {len(ds)} rows, cannot sample {N}.", file=sys.stderr)
        return 1

    ds = ds.shuffle(seed=SEED).select(range(N))

    with open(OUTFILE, "w", encoding="utf-8") as f:
        for ex in ds:
            import_stmt = ex.get("import_statement") or ""
            cropped_code = ex.get("cropped_code") or ""
            next_line = ex.get("next_line")

            if next_line is None:
                continue  # skip weird rows

            prompt = (
                "Output ONLY the next line of Java code. No markdown, no explanation.\n\n"
                f"{import_stmt}\n"
                f"{cropped_code}"
            )

            rec = {
                "input": [{"role": "user", "content": prompt}],
                "ideal": next_line,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"✅ Wrote {N} samples to {OUTFILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


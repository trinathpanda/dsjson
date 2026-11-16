"""Compare dsjson output with reference Dataset-JSON files (e.g. CDISC pilot).

Checks per dataset: top-level name/label/itemGroupOID/records, column metadata
(itemOID, name, label, dataType, length, keySequence) and every row cell.
Numbers compare within 1e-9. Missing-value spelling (null vs "") is counted
separately so it does not hide real value differences.

Usage:
    python scripts/compare_with_reference.py <our_dir> <reference_dir> [--out comparison.json]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

TOP_KEYS = ("name", "label", "itemGroupOID", "records")
COLUMN_KEYS = ("itemOID", "name", "label", "dataType", "length", "keySequence")
MAX_EXAMPLES = 5


def _same_value(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b) <= 1e-9
    return a == b


def compare_dataset(ours: dict, ref: dict) -> dict:
    result = {"top": {}, "columns": [], "missing_style": 0, "cells": 0, "cell_examples": [], "cells_by_column": {}}

    for key in TOP_KEYS:
        if ours.get(key) != ref.get(key):
            result["top"][key] = [ours.get(key), ref.get(key)]

    our_names = [c.get("name") for c in ours["columns"]]
    ref_names = [c.get("name") for c in ref["columns"]]
    if our_names != ref_names:
        result["columns"].append({"column_order": [our_names, ref_names]})
    for oc, rc in zip(ours["columns"], ref["columns"]):
        for key in COLUMN_KEYS:
            if oc.get(key) != rc.get(key):
                result["columns"].append({"column": oc.get("name"), "key": key, "ours": oc.get(key), "ref": rc.get(key)})

    by_column = Counter()
    for i, (orow, rrow) in enumerate(zip(ours["rows"], ref["rows"])):
        for j, (a, b) in enumerate(zip(orow, rrow)):
            if _same_value(a, b):
                continue
            if a in (None, "") and b in (None, ""):
                result["missing_style"] += 1
                continue
            result["cells"] += 1
            by_column[our_names[j]] += 1
            if len(result["cell_examples"]) < MAX_EXAMPLES:
                result["cell_examples"].append({"row": i, "column": our_names[j], "ours": a, "ref": b})
    result["cells_by_column"] = dict(by_column)

    result["match"] = not (result["top"] or result["columns"] or result["cells"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("our_dir")
    parser.add_argument("reference_dir")
    parser.add_argument("--out", default=None, help="Write details as JSON (default: <our_dir>/comparison.json)")
    args = parser.parse_args()

    ref_files = {p.stem.upper(): p for p in Path(args.reference_dir).glob("*.json")}
    results = {}
    print(f"{'Dataset':<9}{'Match':<7}{'Records':>9}{'Top':>5}{'ColDiff':>9}{'CellDiff':>10}{'NullVsEmpty':>13}  Columns with cell diffs")
    for ds, ref_path in sorted(ref_files.items()):
        ours_path = Path(args.our_dir) / f"{ds}.json"
        if not ours_path.exists():
            results[ds] = {"match": False, "error": "no output file"}
            print(f"{ds:<9}{'MISSING':<7}")
            continue
        ours = json.loads(ours_path.read_text(encoding="utf-8"))
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
        r = compare_dataset(ours, ref)
        results[ds] = r
        cols = ", ".join(f"{k}({v})" for k, v in r["cells_by_column"].items())
        print(
            f"{ds:<9}{'YES' if r['match'] else 'NO':<7}{ours.get('records', 0):>9}{len(r['top']):>5}"
            f"{len(r['columns']):>9}{r['cells']:>10}{r['missing_style']:>13}  {cols}"
        )

    matched = sum(1 for r in results.values() if r.get("match"))
    print(f"\n{matched}/{len(results)} datasets match the reference")

    out = Path(args.out) if args.out else Path(args.our_dir) / "comparison.json"
    out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"Details: {out}")
    return 0 if matched == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

from dsjson.readers.xpt_reader import XPTReader
import os
import json


def main():
    # ------------------------------------------------------------------
    # Step 1: Path to your XPT file
    # ------------------------------------------------------------------
    xpt_path = "demo/input/sdtm/dm.xpt"

    print("✅ File exists:", os.path.exists(xpt_path))
    print("✅ Absolute path:", os.path.abspath(xpt_path))

    # ------------------------------------------------------------------
    # Step 2: Initialize reader
    # ------------------------------------------------------------------
    reader = XPTReader(xpt_path)

    # ------------------------------------------------------------------
    # Step 3: Read file
    # ------------------------------------------------------------------
    reader.read()

    # ------------------------------------------------------------------
    # Step 4: Get columns
    # ------------------------------------------------------------------
    columns = reader.get_dataset_json_columns()

    print("\n✅ Columns (sample):")
    print(json.dumps(columns[:5], indent=4))

    # ------------------------------------------------------------------
    # Step 5: Get records
    # ------------------------------------------------------------------
    records = reader.get_records()

    print("\n✅ First 2 rows:")
    print(json.dumps(records[:2], indent=4))

    # ------------------------------------------------------------------
    # Step 6: Full dataset (optional)
    # ------------------------------------------------------------------
    cols, rows = reader.get_dataset()

    print("\n✅ Summary:")
    print(f"Columns: {len(cols)}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
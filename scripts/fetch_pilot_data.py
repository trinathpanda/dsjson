"""Download CDISC pilot study (CDISCPILOT01) SDTM test data.

Fetches the SDTM XPT files, define.xml and CDISC's reference Dataset-JSON files from
https://github.com/cdisc-org/sdtm-adam-pilot-project into demo/input/cdiscpilot01/.
Files that already exist are skipped.

Usage:
    python scripts/fetch_pilot_data.py
"""

import sys
import urllib.request
from pathlib import Path

BASE_URL = (
    "https://raw.githubusercontent.com/cdisc-org/sdtm-adam-pilot-project/master/"
    "updated-pilot-submission-package/900172/m5/datasets/cdiscpilot01/tabulations/sdtm"
)

DATASETS = [
    "ae", "cm", "dm", "ds", "ex", "lb", "mh", "qs", "relrec", "sc", "se",
    "suppae", "suppdm", "suppds", "supplb", "sv", "ta", "te", "ti", "ts", "tv", "vs",
]

ROOT = Path(__file__).resolve().parent.parent / "demo" / "input" / "cdiscpilot01"


def _download(file_name: str, target: Path) -> None:
    if target.exists():
        print(f"skip   {target.relative_to(ROOT)}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    urllib.request.urlretrieve(f"{BASE_URL}/{file_name}", tmp)
    tmp.replace(target)  # only complete files get the final name
    print(f"saved  {target.relative_to(ROOT)}")


def main() -> int:
    _download("define.xml", ROOT / "define.xml")
    for name in DATASETS:
        _download(f"{name}.xpt", ROOT / "sdtm" / f"{name}.xpt")
        _download(f"{name}.json", ROOT / "reference" / f"{name}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

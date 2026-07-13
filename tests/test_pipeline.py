from dsjson.services.conversion_service import ConversionService
from dsjson.logging_config import setup_logger

import json
import os

# Setup logger once ✅
setup_logger(output_dir="demo/output/logs")

def main():

    service = ConversionService()

    dataset_json = service.convert(
        dataset_name="DM",
        define_path="demo/input/define.xml",
        xpt_path="demo/input/sdtm/dm.xpt"
    )

    os.makedirs("demo/output", exist_ok=True)

    with open("demo/output/dm.json", "w") as f:
        json.dump(dataset_json, f, indent=4)


if __name__ == "__main__":
    main()

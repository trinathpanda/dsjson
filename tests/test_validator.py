from dsjson.validation.schema_validator import SchemaValidator
from dsjson.reports.validation_report import ValidationReportBuilder

import json


def main():
    dataset_name = "DM"
    file_path = "demo/output/dm.json"

    with open(file_path, "r") as f:
        dataset = json.load(f)

    validator = SchemaValidator()

    # Run validations
    full_report = validator.validate_dataset(dataset)
    metadata_report = validator.validate_metadata(dataset)
    row_report = validator.validate_rows(dataset)

    # Build report ✅
    final_report = ValidationReportBuilder.build(
        dataset_name,
        full_report,
        metadata_report,
        row_report
    )

    # Save report ✅
    output_path = "demo/output/dm_validation_report.json"

    with open(output_path, "w") as f:
        json.dump(final_report, f, indent=4)

    print("\n✅ Validation Report Generated:")
    print(output_path)


if __name__ == "__main__":
    main()
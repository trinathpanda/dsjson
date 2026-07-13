# dsjson

**dsjson** is a submission-focused Python library and CLI tool for creating CDISC Dataset-JSON from SDTM datasets and metadata.

## Hackathon MVP

The pilot scope focuses on converting SDTM domains into Dataset-JSON:

- DM

## Planned workflow

```text
SDTM datasets + Define-XML
        ↓
Metadata extraction
        ↓
Dataset-JSON creation
        ↓
Schema validation
        ↓
Submission-ready JSON + logs + report
```

## Example CLI

```bash
dsjson convert   --data ./demo/input/sdtm   --define ./demo/input/define.xml   --domains AE DM IE CO   --out ./demo/output   --validate   --log-level INFO
```

## Development install

```bash
pip install -e .
```

## Current status

This repository scaffold contains the professional package structure. Functional implementation will be added step by step.
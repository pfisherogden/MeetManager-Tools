# mm_to_json

This is a Python reimplementation of the C++ logic to convert Meet Manager `.mdb` database files into a JSON format.

## Prior Art & Inspiration

This code was originally inspired by and ported from the C++ repository:

*   **Original Repository**: [https://github.com/turner301/mm-to-json](https://github.com/turner301/mm-to-json)
*   **Author**: turner301 (or as appropriate from source)

While this project has evolved and diverges significantly in implementation (Python vs C++), the core logic for parsing the proprietary MDB schema remains rooted in the original work.

## Extraction for Mobile Judge App

The library now includes `JudgeAppExtractor` (in `mm_to_json/judge_app_extractor.py`), which specifically prepares a simplified, offline-first JSON dataset for the [Mobile Judge App](../mobile-judge-app). This extractor collapses complex meet hierarchies into a flat `events -> heats -> swimmers` structure optimized for mobile performance.

## Usage

This tool is primarily used as a library by the `backend` service but can also be run standalone for testing or data generation (see `generate_judge_sample.py` in the root).

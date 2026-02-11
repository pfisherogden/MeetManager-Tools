# mm_to_json

This is a Python reimplementation of the C++ logic to convert Meet Manager `.mdb` database files into a JSON format.

## Prior Art & Inspiration

This code was originally inspired by and ported from the C++ repository:

*   **Original Repository**: [https://github.com/turner301/mm-to-json](https://github.com/turner301/mm-to-json)
*   **Author**: turner301 (or as appropriate from source)

While this project has evolved and diverges significantly in implementation (Python vs C++), the core logic for parsing the proprietary MDB schema remains rooted in the original work.

## Structure

*   `mm_to_json_py/`: The main Python package.
*   `tests/`: Unit tests.
*   `verify_meet_program.py`: Verification scripts.

## Usage

This tool is primarily used as a library by the `backend` service but can also be run standalone for testing.

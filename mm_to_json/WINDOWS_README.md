# Windows Build & Verification Instructions

This document provides instructions for compiling the C++ `mm_to_json` application on Windows and verifying its output against the Python version.

## Getting Started (Git)

Run these commands in PowerShell or Command Prompt to get the code and switch to the verification branch:

```powershell
# 1. Clone the repository (if you haven't already)
git clone <your-repo-url>
cd MeetManager-Tools/mm_to_json

# 2. Fetch the latest branches
git fetch origin

# 3. Switch to the Windows verification branch
git checkout windows-verification
```

## Prerequisites

## Prerequisites

1.  **Compiler / Build Tools**:
    *   **Recommended**: Install **Visual Studio Build Tools** (free) with the "Desktop development with C++" workload. This provides the MSVC compiler and Windows SDKs needed for ODBC.
    *   *Note*: You do **not** need the full Visual Studio IDE if you prefer VS Code, but you **do** need the Build Tools.
2.  **Editors**:
    *   **Visual Studio 2019/2022** (Full IDE): Easiest "out of the box" experience.
    *   **VS Code**: Requires "C/C++" and "CMake Tools" extensions + the Build Tools above.
3.  **Microsoft Access Database Engine**:
    *   You need the ODBC driver for `.mdb` files (`Microsoft Access Driver (*.mdb)`).
    *   **Architecture Warning**: If you have 64-bit Office installed, your ODBC driver is 64-bit. If 32-bit Office, it's 32-bit.
    *   You must compile `mm_to_json` to match this architecture (x64 or x86).

## Building with Visual Studio (Full IDE)

1.  Open Visual Studio.
...

## Building with VS Code

1.  Open the folder in VS Code.
2.  Install the **CMake Tools** extension.
3.  When prompted to select a Kit, choose **Visual Studio Community 2019/2022 Release - amd64** (for 64-bit) or **x86** (for 32-bit) matching your ODBC driver.
4.  Open the Command Palette (`Ctrl+Shift+P`) and run `CMake: Configure`.
5.  Run `CMake: Build`.
6.  The executable will be in `build/Debug/` (or similar).

2.  Select **Open a local folder** and choose `MeetManager-Tools/mm_to_json`.
3.  Visual Studio should detect `CMakeLists.txt`.
4.  Select your configuration (e.g., `x64-Debug` or `x86-Debug`) from the top toolbar dropdown. matches your Access Driver architecture.
    *   To check your driver architecture, search for "ODBC Data Sources" in Windows Start Menu. If you see "Microsoft Access Driver" in the 64-bit administrator, build for x64.
5.  Select **Build > Build All**.
6.  The executable `mm_to_json.exe` will be generated in `out/build/x64-Debug/mm_to_json/` (or similar path).

## Running the C++ Version

Open a **Command Prompt** or **PowerShell** and navigate to the build output directory.

```powershell
# Example path
cd out/build/x64-Debug/mm_to_json

# Run conversion
.\mm_to_json.exe "C:\path\to\Singers23.mdb"
```

This will generate `Singers23.json` in the same directory.

## Running Verification

To compare the C++ output with the Python output:

1.  Generate JSON using Python (on Mac or Windows):
    ```bash
    cd mm_to_json_py
    # Generate schema dump or convert
    uv run src/mm_to_json/mm_to_json.py ../Singers23.mdb
    ```
3.  **Comprehensive Verification**:
    You can now run the full data generation and restoration pipeline on Windows as well (requires Java 11+ for MDB write support):
    ```bash
    cd mm_to_json_py
    uv run tests/test_comprehensive.py
    ```
2.  Generate JSON using C++ (as above).
3.  Use the comparison script:
    ```bash
    python compare_json.py path/to/python/Singers23.json path/to/cpp/Singers23.json
    ```

## Common Issues

*   **"Data source name not found and no default driver specified"**: This means the ODBC driver string in `mmToJsonConverter.cpp` doesn't match your installed driver, or (more likely) you are running a 64-bit exe against 32-bit drivers (or vice versa). Switch the build architecture in Visual Studio.

from __future__ import annotations

import os

from mm_to_json.mdb_writer import get_potential_jvm_paths


def test_get_potential_jvm_paths():
    local_jre = os.path.join("fake", "path", "jre")

    # 1. Darwin/macOS
    darwin_paths = get_potential_jvm_paths(local_jre, "Darwin")
    assert any("libjvm.dylib" in p for p in darwin_paths)
    assert any("Contents" in p for p in darwin_paths)

    # 2. Windows
    windows_paths = get_potential_jvm_paths(local_jre, "Windows")
    assert any("jvm.dll" in p for p in windows_paths)
    assert any("bin" in p for p in windows_paths)

    # 3. Linux/Other
    linux_paths = get_potential_jvm_paths(local_jre, "Linux")
    assert any("libjvm.so" in p for p in linux_paths)
    assert any("lib" in p for p in linux_paths)

from __future__ import annotations

import logging
import os
import sys
import threading

logger = logging.getLogger(__name__)


def setup_platform_env():
    """Initializes platform-specific environment settings (e.g. DLL paths, ctypes patches, process monitors)."""
    # 1. Platform-Specific Library / DLL Resolution
    if os.name == "nt":
        # Windows WeasyPrint DLL Resolution (Cairo / Pango / GObject)
        lib_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
        if os.path.exists(lib_dir):
            logger.info(f"Windows target detected: adding bundled DLL folder to environment: {lib_dir}")
            os.environ["WEASYPRINT_DLL_DIRECTORIES"] = lib_dir
            os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")
    elif sys.platform == "darwin":
        # macOS Homebrew library resolution fallback under SIP
        homebrew_lib = "/opt/homebrew/lib"
        if os.path.exists(homebrew_lib):
            import ctypes.util

            if ctypes.util.find_library.__name__ != "new_find_library":
                orig_find_library = ctypes.util.find_library

                def new_find_library(name):
                    res = orig_find_library(name)
                    if not res:
                        base_name = name
                        if name.startswith("lib"):
                            base_name = name[3:]
                        if "-" in base_name and not base_name.startswith("harfbuzz-subset"):
                            base_name = base_name.split("-")[0]
                        exact_path = os.path.join(homebrew_lib, f"lib{base_name}.dylib")
                        if os.path.exists(exact_path):
                            res = exact_path
                        else:
                            try:
                                for f in os.listdir(homebrew_lib):
                                    if f.startswith(f"lib{base_name}") and f.endswith(".dylib"):
                                        res = os.path.join(homebrew_lib, f)
                                        break
                            except Exception:
                                pass
                    return res

                ctypes.util.find_library = new_find_library
                logger.info("macOS target detected: patched ctypes.util.find_library for Homebrew SIP support.")

    # 2. Orphaning Process Prevention (Self-Termination Monitor)
    # Start a daemon thread that blocks on sys.stdin.read(1). If the parent
    # process (Tauri) terminates, the OS closes stdin, read(1) returns EOF,
    # and this thread terminates the Python sidecar.
    if os.environ.get("MONITOR_PARENT_PROCESS") != "false":
        stdin_thread = threading.Thread(target=_monitor_parent_stdin, daemon=True)
        stdin_thread.start()


def _monitor_parent_stdin():
    logger.debug("Starting parent process stdin monitor thread...")
    try:
        sys.stdin.read(1)
    except Exception as e:
        logger.debug(f"Parent process stdin monitor read exception: {e}")
    finally:
        logger.warning("Parent process stream closed (EOF detected). Terminating sidecar immediately...")
        # Force immediate exit of the process without throwing exceptions or cleaning up handlers
        os._exit(0)

import time
import sys
import os

def profile_import(module_name):
    start = time.time()
    try:
        if module_name in sys.modules:
            del sys.modules[module_name]
        __import__(module_name)
        end = time.time()
        print(f"Import {module_name} took {end - start:.4f} seconds")
    except Exception as e:
        print(f"Failed to import {module_name}: {e}")

if __name__ == "__main__":
    # Add src to path
    sys.path.append(os.path.abspath("backend/src"))
    
    profile_import("grpc")
    profile_import("pandas")
    profile_import("firebase_admin")
    profile_import("auth_interceptor")
    profile_import("server")

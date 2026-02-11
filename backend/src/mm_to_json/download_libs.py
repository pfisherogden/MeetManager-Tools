import os
import urllib.request

# JARs required for UCanAccess 5.0.1
LIBS = {
    "ucanaccess-5.0.1.jar": "https://repo1.maven.org/maven2/net/sf/ucanaccess/ucanaccess/5.0.1/ucanaccess-5.0.1.jar",
    "jackcess-3.0.1.jar": "https://repo1.maven.org/maven2/com/healthmarketscience/jackcess/jackcess/3.0.1/jackcess-3.0.1.jar",
    "hsqldb-2.5.0.jar": "https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.5.0/hsqldb-2.5.0.jar",
    "commons-lang3-3.8.1.jar": "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.8.1/commons-lang3-3.8.1.jar",
    "commons-logging-1.2.jar": "https://repo1.maven.org/maven2/commons-logging/commons-logging/1.2/commons-logging-1.2.jar",
    "commons-codec-1.15.jar": "https://repo1.maven.org/maven2/commons-codec/commons-codec/1.15/commons-codec-1.15.jar",
    "bcprov-jdk15on-1.68.jar": "https://repo1.maven.org/maven2/org/bouncycastle/bcprov-jdk15on/1.68/bcprov-jdk15on-1.68.jar",
}


def download_libs(target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Created directory: {target_dir}")

    for filename, url in LIBS.items():
        path = os.path.join(target_dir, filename)
        if os.path.exists(path):
            print(f"Skipping {filename} (already exists at {path})")
            continue

        print(f"Downloading {filename} from {url} to {path}...")
        try:
            urllib.request.urlretrieve(url, path)
            print(f"Successfully downloaded {filename}")
        except Exception as e:
            if os.path.exists(path):
                print(f"Error downloading {filename} but file exists, continuing: {e}")
            else:
                print(f"Error downloading {filename}: {e}")
                # Don't exit, try next file, but track error
                # actually for critical dependencies maybe we should exit?
                # But let's try to proceed if one fails.
                pass


if __name__ == "__main__":
    # Target directory relative to this script: mm_to_json/lib/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.join(base_dir, "lib")
    download_libs(lib_dir)

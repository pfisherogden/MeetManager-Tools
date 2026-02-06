import os
import urllib.request

JARS = [
    (
        "https://repo1.maven.org/maven2/net/sf/ucanaccess/ucanaccess/5.0.1/ucanaccess-5.0.1.jar",
        "ucanaccess-5.0.1.jar",
    ),
    ("https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.5.0/hsqldb-2.5.0.jar", "hsqldb-2.5.0.jar"),
    (
        "https://repo1.maven.org/maven2/com/healthmarketscience/jackcess/jackcess/3.0.1/jackcess-3.0.1.jar",
        "jackcess-3.0.1.jar",
    ),
    (
        "https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.8.1/commons-lang3-3.8.1.jar",
        "commons-lang3-3.8.1.jar",
    ),
    (
        "https://repo1.maven.org/maven2/commons-logging/commons-logging/1.2/commons-logging-1.2.jar",
        "commons-logging-1.2.jar",
    ),
    (
        "https://repo1.maven.org/maven2/commons-codec/commons-codec/1.15/commons-codec-1.15.jar",
        "commons-codec-1.15.jar",
    ),
    (
        "https://repo1.maven.org/maven2/org/bouncycastle/bcprov-jdk15on/1.68/bcprov-jdk15on-1.68.jar",
        "bcprov-jdk15on-1.68.jar",
    ),
]

LIB_DIR = "lib"

if __name__ == "__main__":
    if not os.path.exists(LIB_DIR):
        os.makedirs(LIB_DIR)

    for url, filename in JARS:
        dest = os.path.join(LIB_DIR, filename)
        if not os.path.exists(dest):
            print(f"Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, dest)
                print(f"Downloaded {filename}")
            except Exception as e:
                print(f"Failed to download {filename}: {e}")
        else:
            pass

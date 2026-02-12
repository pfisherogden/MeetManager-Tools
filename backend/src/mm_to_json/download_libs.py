import logging
import os
import platform
import tarfile
import urllib.request

logger = logging.getLogger(__name__)

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

# JRE download constants
ADOPTIUM_API = "https://api.adoptium.net/v3/binary/latest/21/ga/{os}/{arch}/jre/hotspot/normal/eclipse?project=jdk"


def download_libs(target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        logger.info(f"Created directory: {target_dir}")

    for filename, url in LIBS.items():
        path = os.path.join(target_dir, filename)
        if os.path.exists(path):
            continue

        logger.info(f"Downloading {filename}...")
        try:
            urllib.request.urlretrieve(url, path)
        except Exception as e:
            logger.error(f"Error downloading {filename}: {e}")


def check_and_download_jre(base_dir):
    # Check if a JVM is already found by jpype
    import jpype

    try:
        # If this returns a path, jpype found a system-wide or environment Java
        if jpype.getDefaultJVMPath():
            logger.info("System JVM found, skipping JRE download.")
            return
    except Exception:
        pass

    jre_dir = os.path.join(base_dir, "jre")
    if os.path.exists(jre_dir):
        logger.info(f"Local JRE already exists at {jre_dir}")
        return

    sys_plat = platform.system().lower()
    if sys_plat == "darwin":
        os_name = "mac"
    elif sys_plat == "linux":
        os_name = "linux"
    else:
        logger.warning(f"Unsupported platform for portable JRE: {sys_plat}")
        return

    arch = platform.machine().lower()
    if arch in ["arm64", "aarch64"]:
        arch_name = "aarch64"
    elif arch in ["x86_64", "amd64"]:
        arch_name = "x64"
    else:
        logger.warning(f"Unsupported architecture for portable JRE: {arch}")
        return

    url = ADOPTIUM_API.format(os=os_name, arch=arch_name)
    logger.info(f"Downloading portable JRE for {os_name}/{arch_name} from Adoptium...")

    jre_archive = os.path.join(base_dir, "jre_temp.tar.gz")
    try:
        # Use a proper User-Agent to avoid some API blocks
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response, open(jre_archive, "wb") as out_file:
            out_file.write(response.read())

        logger.info("Extracting JRE...")
        with tarfile.open(jre_archive, "r:gz") as tar:
            tar.extractall(path=base_dir)

        # Temurin folders usually look like 'jdk-21.0.6+7-jre'
        # Let's find the new directory that isn't 'lib', 'jre', or other known ones
        extracted_dirs = [
            d
            for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d)) and (d.startswith("jdk") or d.startswith("OpenJDK"))
        ]

        if extracted_dirs:
            # Sort by modification time to find the newest one
            extracted_dirs.sort(key=lambda x: os.path.getmtime(os.path.join(base_dir, x)), reverse=True)
            new_jre_path = os.path.join(base_dir, extracted_dirs[0])
            os.rename(new_jre_path, jre_dir)
            logger.info(f"JRE installed successfully to {jre_dir}")
        else:
            logger.error("Failed to identify extracted JRE directory.")

        if os.path.exists(jre_archive):
            os.remove(jre_archive)
    except Exception as e:
        logger.error(f"Error installing JRE: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.join(base_dir, "lib")
    download_libs(lib_dir)
    check_and_download_jre(base_dir)

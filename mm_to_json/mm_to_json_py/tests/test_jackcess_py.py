import os

import jpype
import jpype.imports

# Path to the local JDK we installed
JDK_HOME = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "jdk-17.0.2.jdk",
    "Contents",
    "Home",
)


def get_classpath():
    """Returns the classpath list."""
    lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
    jars = [os.path.join(lib_dir, f) for f in os.listdir(lib_dir) if f.endswith(".jar")]
    return jars


def test_jackcess():
    if os.path.exists(JDK_HOME):
        os.environ["JAVA_HOME"] = JDK_HOME

    jars = get_classpath()
    classpath = ":".join(jars)  # Mac separator

    print(f"Starting JVM with classpath: {classpath}")
    try:
        if not jpype.isJVMStarted():
            jpype.startJVM(jpype.getDefaultJVMPath(), "-Djava.class.path=" + classpath)

        from com.healthmarketscience.jackcess import DatabaseBuilder
        from java.io import File

        mdb_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Singers23.mdb"
        )
        print(f"Opening {mdb_path}...")

        db = DatabaseBuilder.open(File(mdb_path))
        print("Database opened successfully!")

        table = db.getTable("CUSTOMRPTS")
        if table:
            print(f"CUSTOMRPTS Table found. Rows: {table.getRowCount()}")

            # Try Writing?
            # We need to know schema or just add a row if we can?
            # Safe test: Create a new table if possible, but creating table via Jackcess is verbose.
            # Let's just try to read metadata as proof of robust access, or
            # if CUSTOMRPTS is empty, maybe we can add a row?
            # Column Map?
            # print(table.getColumns())
            pass
        else:
            print("CUSTOMRPTS Table not found.")

        db.close()
        print("Success.")

    except Exception as e:
        print(f"Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_jackcess()

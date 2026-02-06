import os
import sys

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from mm_to_json import mdb_writer


def check_dtypes():
    mdb_writer.ensure_jvm_started()
    from com.healthmarketscience.jackcess import DataType

    print("Valid DataTypes:")
    for dt in DataType.values():
        print(dt.toString())


if __name__ == "__main__":
    check_dtypes()

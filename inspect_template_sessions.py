import json
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter

TEMPLATE_MDB = "../template_unzip/swmeets7/Summer League Meet Template.mdb"

def to_python(obj):
    """Recursively convert Java/Pandas objects to standard Python types."""
    if "java.lang.String" in str(type(obj)):
        return str(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {to_python(k): to_python(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_python(x) for x in obj]
    return obj

def inspect():
    if not os.path.exists(TEMPLATE_MDB):
        print(f"Template not found: {TEMPLATE_MDB}")
        return

    with MmToJsonConverter(mdb_path=str(TEMPLATE_MDB)) as conv:
        full_schema = conv.export_full_schema()
    full_schema = to_python(full_schema)
    
    # Filter for session-related tables
    session_data = {
        k: v for k, v in full_schema["tables"].items() 
        if "session" in str(k).lower() or "sessitem" in str(k).lower()
    }
    
    print(json.dumps(session_data, indent=2))

if __name__ == "__main__":
    inspect()

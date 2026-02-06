
import json
import sys
import difflib

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def compare_dicts(d1, d2, path=""):
    errors = []
    
    # Check keys
    keys1 = set(d1.keys())
    keys2 = set(d2.keys())
    
    if keys1 != keys2:
        missing_in_2 = keys1 - keys2
        missing_in_1 = keys2 - keys1
        if missing_in_2:
            errors.append(f"{path}: Missing keys in file 2: {missing_in_2}")
        if missing_in_1:
            errors.append(f"{path}: Missing keys in file 1: {missing_in_1}")
            
    # Check values
    common_keys = keys1.intersection(keys2)
    for k in common_keys:
        val1 = d1[k]
        val2 = d2[k]
        new_path = f"{path}.{k}" if path else k
        
        if type(val1) != type(val2):
            errors.append(f"{new_path}: Type mismatch ({type(val1)} vs {type(val2)})")
            continue
            
        if isinstance(val1, dict):
            errors.extend(compare_dicts(val1, val2, new_path))
        elif isinstance(val1, list):
            errors.extend(compare_lists(val1, val2, new_path))
        else:
            if val1 != val2:
                # Allow minor floating point diffs or string formatting diffs?
                # For now strict
                errors.append(f"{new_path}: Mismatch '{val1}' vs '{val2}'")

    return errors

def compare_lists(l1, l2, path=""):
    errors = []
    if len(l1) != len(l2):
        errors.append(f"{path}: Length mismatch ({len(l1)} vs {len(l2)})")
        
    # Assume lists are sorted or order matters for now
    # If not, we'd need a key function
    for i, (item1, item2) in enumerate(zip(l1, l2)):
        new_path = f"{path}[{i}]"
        if type(item1) != type(item2):
             errors.append(f"{new_path}: Type mismatch")
             continue
             
        if isinstance(item1, dict):
             errors.extend(compare_dicts(item1, item2, new_path))
        elif isinstance(item1, list):
             errors.extend(compare_lists(item1, item2, new_path))
        else:
             if item1 != item2:
                 errors.append(f"{new_path}: Mismatch '{item1}' vs '{item2}'")
                 
    return errors

def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_json.py <file1.json> <file2.json>")
        sys.exit(1)
        
    f1 = sys.argv[1]
    f2 = sys.argv[2]
    
    print(f"Comparing {f1} vs {f2}...")
    
    try:
        j1 = load_json(f1)
        j2 = load_json(f2)
        
        errors = compare_dicts(j1, j2, "root")
        
        if errors:
            print(f"Found {len(errors)} discrepancies:")
            for e in errors[:50]:
                print(f" - {e}")
            if len(errors) > 50:
                print(f"... and {len(errors)-50} more.")
            sys.exit(1)
        else:
            print("Files are identical!")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

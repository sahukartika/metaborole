import pickle

# File paths for the 4 pickle parts
pkl_files = [
    "hmdb_name_to_id_part1.pkl",
    "hmdb_name_to_id_part2.pkl",
    "hmdb_name_to_id_part3.pkl",
    "hmdb_name_to_id_part4.pkl"
]

# Load and merge all dictionaries
name_to_hmdb = {}

for file in pkl_files:
    with open(file, "rb") as f:
        part = pickle.load(f)
        for name, ids in part.items():
            if name in name_to_hmdb:
                name_to_hmdb[name].update(ids)  # Merge sets
            else:
                name_to_hmdb[name] = set(ids)  # Ensure type is set

# Annotation function
def annotate_metabolites(names):
    results = []
    seen = set()

    for name in names:
        key = name.strip().lower()

        if key in seen:
            continue  # Skip duplicates
        seen.add(key)

        hmdb_ids = name_to_hmdb.get(key)
        if hmdb_ids:
            for hmdb_id in hmdb_ids:
                results.append({
                    "Original Name": name,
                    "HMDB IDs": hmdb_id
                })

    return results

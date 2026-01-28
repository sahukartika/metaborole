import json
import re
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional

import pandas as pd

DEFAULT_JSON_DB = Path(__file__).parent / "metabolite_kegg_mapping_complete.json"


def extract_kegg_id_from_text(text: str) -> Optional[str]:
    """If the text already contains a KEGG ID, extract it."""
    if not text:
        return None
    m = re.search(r"\bC\d{5}\b", str(text), re.IGNORECASE)
    if m:
        return m.group(0).upper()
    m = re.search(r"cpd:(C\d{5})", str(text), re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


@lru_cache(maxsize=1)
def load_kegg_name_to_id(json_file: str = str(DEFAULT_JSON_DB)) -> Dict[str, str]:
    """Load name->KEGG mapping from JSON (keys are stored lowercase/stripped)."""
    json_path = Path(json_file)
    if not json_path.exists():
        raise FileNotFoundError(f"KEGG mapping JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    name_to_kegg = data.get("name_to_kegg", {})
    # Ensure keys are normalized similarly to how the DB was built (lower + strip)
    return {str(k).lower().strip(): v for k, v in name_to_kegg.items() if k is not None}


def annotate_metabolites(
    names: List[str],
    json_db_file: str = str(DEFAULT_JSON_DB),
    deduplicate: bool = True,
) -> List[dict]:
    """
    Strict annotation:
      - does NOT remove LCMS prefixes
      - does NOT change hyphens/underscores
      - does NOT remove L-/D-
      - does NOT remove brackets/parentheses text
    Only matching behavior:
      - case-insensitive (lowercasing)
      - strips leading/trailing whitespace for lookup (because DB keys were stripped)
    """
    name_to_kegg = load_kegg_name_to_id(json_db_file)

    results = []
    seen = set()

    for name in names:
        if name is None or (isinstance(name, float) and pd.isna(name)):
            original = ""
        else:
            original = str(name)

        key = original.lower().strip()  # exact match after lowercase + outer-strip

        if deduplicate:
            if key in seen:
                continue
            seen.add(key)

        # If the user already provided a KEGG ID in the cell, keep it
        kegg_in_text = extract_kegg_id_from_text(original)
        if kegg_in_text:
            kegg_id = kegg_in_text
            source = "in_name"
        else:
            kegg_id = name_to_kegg.get(key)
            source = "exact" if kegg_id else "not_found"

        results.append({
            "Original Name": original,
            "KEGG ID": kegg_id if kegg_id else "Not Found",
            "Match Source": source,
        })

    return results

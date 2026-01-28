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


def remove_stereo_prefix(s: str) -> str:
    """
    Remove leading stereoisomer prefixes:
      'l-', 'd-', 'dl-' (also with spaces: 'l ', 'd ', 'dl ')
    Only removes if it appears at the START of the string.
    """
    if s is None:
        return ""
    return re.sub(r"^(?:dl|d|l)[-\s]+", "", s, flags=re.IGNORECASE).strip()


@lru_cache(maxsize=1)
def load_kegg_name_to_id(json_file: str = str(DEFAULT_JSON_DB)) -> Dict[str, str]:
    """Load name->KEGG mapping from JSON (keys are stored lowercase/stripped)."""
    json_path = Path(json_file)
    if not json_path.exists():
        raise FileNotFoundError(f"KEGG mapping JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    name_to_kegg = data.get("name_to_kegg", {})
    # normalize keys the same way the DB was built
    return {str(k).lower().strip(): v for k, v in name_to_kegg.items() if k is not None}


def annotate_metabolites(
    names: List[str],
    json_db_file: str = str(DEFAULT_JSON_DB),
    deduplicate: bool = True,
) -> List[dict]:
    """
    Annotation logic:
      1) If KEGG ID already present in the string -> return it
      2) Exact match on (lower + strip)
      3) If not found, try removing leading d-/l-/dl- and match again
      4) Else "Not Found"
    """
    name_to_kegg = load_kegg_name_to_id(json_db_file)

    results = []
    seen = set()

    for name in names:
        if name is None or (isinstance(name, float) and pd.isna(name)):
            original = ""
        else:
            original = str(name)

        key = original.lower().strip()

        if deduplicate:
            if key in seen:
                continue
            seen.add(key)

        # If user already has a KEGG ID inside the name, keep it
        kegg_in_text = extract_kegg_id_from_text(original)
        if kegg_in_text:
            results.append({
                "Original Name": original,
                "KEGG ID": kegg_in_text,
                "Match Source": "in_name",
                "Matched Query": kegg_in_text,
            })
            continue

        # 1) exact
        kegg_id = name_to_kegg.get(key)
        if kegg_id:
            results.append({
                "Original Name": original,
                "KEGG ID": kegg_id,
                "Match Source": "exact",
                "Matched Query": key,
            })
            continue

        # 2) stereo-prefix removed
        key2 = remove_stereo_prefix(key)
        if key2 and key2 != key:
            kegg_id2 = name_to_kegg.get(key2)
            if kegg_id2:
                results.append({
                    "Original Name": original,
                    "KEGG ID": kegg_id2,
                    "Match Source": "stereo_prefix_removed",
                    "Matched Query": key2,
                })
                continue

        # not found
        results.append({
            "Original Name": original,
            "KEGG ID": "Not Found",
            "Match Source": "not_found",
            "Matched Query": key,
        })

    return results

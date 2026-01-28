import json
import re
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import pandas as pd


DEFAULT_JSON_DB = Path(__file__).parent / "metabolite_kegg_mapping_complete.json"


def strip_lcms_prefix(name: str) -> str:
    """Remove common LC-MS prefixes."""
    prefixes = ("fwd_pos_", "fwd_neg_", "rev_pos_", "rev_neg_")
    s = str(name)
    s_lower = s.lower()
    for p in prefixes:
        if s_lower.startswith(p):
            return s[len(p):]
    return s


def extract_kegg_id_from_text(text: str) -> Optional[str]:
    """If the metabolite string already contains a KEGG ID, extract it."""
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
    """Load name->KEGG mapping from JSON. Cached to avoid re-loading in Streamlit reruns."""
    json_path = Path(json_file)
    if not json_path.exists():
        raise FileNotFoundError(
            f"KEGG mapping JSON not found at: {json_path}\n"
            f"Place 'metabolite_kegg_mapping_complete.json' next to annotator.py "
            f"or change DEFAULT_JSON_DB."
        )

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    name_to_kegg = data.get("name_to_kegg", {})
    # ensure keys are normalized (lower/strip)
    normalized = {}
    for k, v in name_to_kegg.items():
        if k is None:
            continue
        kk = str(k).lower().strip()
        if kk:
            normalized[kk] = v
    return normalized


def _lookup_with_variations(raw_name: str, name_to_kegg: Dict[str, str]) -> Tuple[Optional[str], str, str]:
    """
    Returns: (kegg_id or None, match_source, matched_query)
    """
    if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
        return None, "empty", ""

    original = str(raw_name).strip()
    if not original:
        return None, "empty", ""

    # 1) Already contains a KEGG ID
    kegg_in_text = extract_kegg_id_from_text(original)
    if kegg_in_text:
        return kegg_in_text, "in_name", kegg_in_text

    # 2) Normalize / clean
    cleaned = strip_lcms_prefix(original).strip()

    # direct exact match
    key = cleaned.lower().strip()
    if key in name_to_kegg:
        return name_to_kegg[key], "exact", cleaned

    # 3) Variations (helps with dash/underscore/stereo prefixes)
    variations = [
        cleaned.replace("-", " "),
        cleaned.replace("_", " "),
        cleaned.replace("-", ""),
        cleaned.replace("_", ""),
        re.sub(r"^(l-|d-|dl-)", "", cleaned, flags=re.IGNORECASE),
        re.sub(r"^(l-|d-|dl-)", "", cleaned, flags=re.IGNORECASE).replace("-", " "),
        re.sub(r"\s*\(.*?\)\s*", "", cleaned),  # remove parentheses content
        re.sub(r"\s*\[.*?\]\s*", "", cleaned),  # remove bracket content
    ]

    for v in variations:
        v_key = v.lower().strip()
        if v_key and v_key in name_to_kegg:
            return name_to_kegg[v_key], "variant", v

    return None, "not_found", cleaned


def annotate_metabolites(
    names: List[str],
    json_db_file: str = str(DEFAULT_JSON_DB),
    deduplicate: bool = True,
    include_details: bool = True,
) -> List[dict]:
    """
    Annotate metabolite names with KEGG IDs using local JSON mapping.

    Output rows contain:
      - Original Name
      - KEGG ID (or "Not Found")
      - (optional) Match Source, Matched Query
    """
    name_to_kegg = load_kegg_name_to_id(json_db_file)

    results = []
    seen = set()

    for name in names:
        s = "" if name is None else str(name)
        key = s.strip().lower()

        if deduplicate:
            if key in seen:
                continue
            seen.add(key)

        kegg_id, source, matched_query = _lookup_with_variations(s, name_to_kegg)

        row = {
            "Original Name": s,
            "KEGG ID": kegg_id if kegg_id else "Not Found",
        }
        if include_details:
            row["Match Source"] = source
            row["Matched Query"] = matched_query

        results.append(row)

    return results

"""
annotator.py

Dual metabolite annotation: KEGG (from JSON) + HMDB (from pickle files).
Both run on every input name. Output has columns for both databases.
"""

import json
import re
import pickle
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional, Set

import pandas as pd

# Default database file paths (adjust as needed)
DEFAULT_JSON_DB = Path(__file__).parent / "metabolite_kegg_mapping_complete.json"
DEFAULT_HMDB_PKLS = [
    Path(__file__).parent / "hmdb_name_to_id_part1.pkl",
    Path(__file__).parent / "hmdb_name_to_id_part2.pkl",
    Path(__file__).parent / "hmdb_name_to_id_part3.pkl",
    Path(__file__).parent / "hmdb_name_to_id_part4.pkl",
]


# ============================================================================
# KEGG HELPERS
# ============================================================================

def extract_kegg_id_from_text(text: str) -> Optional[str]:
    """If the text already contains a KEGG compound ID, extract it."""
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
    """Remove leading stereoisomer prefixes: l-, d-, dl- (with dash or space)."""
    if s is None:
        return ""
    return re.sub(r"^(?:dl|d|l)[-\s]+", "", s, flags=re.IGNORECASE).strip()


@lru_cache(maxsize=1)
def load_kegg_name_to_id(json_file: str = str(DEFAULT_JSON_DB)) -> Dict[str, str]:
    """Load name->KEGG mapping from JSON."""
    json_path = Path(json_file)
    if not json_path.exists():
        raise FileNotFoundError(f"KEGG mapping JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    name_to_kegg = data.get("name_to_kegg", {})
    return {str(k).lower().strip(): v for k, v in name_to_kegg.items() if k is not None}


def lookup_kegg(key: str, name_to_kegg: Dict[str, str], original: str) -> dict:
    """
    Try to find KEGG ID for a single name.
    Returns dict with KEGG ID, Match Source, Matched Query.
    """
    # 1) KEGG ID already in the string
    kegg_in_text = extract_kegg_id_from_text(original)
    if kegg_in_text:
        return {
            "KEGG ID": kegg_in_text,
            "KEGG Match Source": "in_name",
            "KEGG Matched Query": kegg_in_text,
        }

    # 2) Exact match
    kegg_id = name_to_kegg.get(key)
    if kegg_id:
        return {
            "KEGG ID": kegg_id,
            "KEGG Match Source": "exact",
            "KEGG Matched Query": key,
        }

    # 3) Stereo-prefix removed
    key2 = remove_stereo_prefix(key)
    if key2 and key2 != key:
        kegg_id2 = name_to_kegg.get(key2)
        if kegg_id2:
            return {
                "KEGG ID": kegg_id2,
                "KEGG Match Source": "stereo_prefix_removed",
                "KEGG Matched Query": key2,
            }

    # Not found
    return {
        "KEGG ID": "Not Found",
        "KEGG Match Source": "not_found",
        "KEGG Matched Query": key,
    }


# ============================================================================
# HMDB HELPERS
# ============================================================================

@lru_cache(maxsize=1)
def load_hmdb_name_to_id(pkl_files_tuple: tuple = None) -> Dict[str, Set[str]]:
    """Load name->HMDB ID mapping from pickle files. Keys are lowercase/stripped."""
    if pkl_files_tuple is None:
        pkl_files_tuple = tuple(str(p) for p in DEFAULT_HMDB_PKLS)

    name_to_hmdb: Dict[str, Set[str]] = {}

    for file_path in pkl_files_tuple:
        p = Path(file_path)
        if not p.exists():
            print(f"  WARNING: HMDB pickle not found: {p}")
            continue
        with open(p, "rb") as f:
            part = pickle.load(f)
            for name, ids in part.items():
                key = str(name).lower().strip()
                if key in name_to_hmdb:
                    name_to_hmdb[key].update(ids)
                else:
                    name_to_hmdb[key] = set(ids)

    return name_to_hmdb


def lookup_hmdb(key: str, name_to_hmdb: Dict[str, Set[str]]) -> dict:
    """
    Try to find HMDB ID(s) for a single name.
    Returns dict with HMDB IDs (semicolon-separated if multiple).
    """
    # 1) Exact match
    hmdb_ids = name_to_hmdb.get(key)
    if hmdb_ids:
        return {
            "HMDB IDs": "; ".join(sorted(hmdb_ids)),
            "HMDB Match Source": "exact",
        }

    # 2) Stereo-prefix removed
    key2 = remove_stereo_prefix(key)
    if key2 and key2 != key:
        hmdb_ids2 = name_to_hmdb.get(key2)
        if hmdb_ids2:
            return {
                "HMDB IDs": "; ".join(sorted(hmdb_ids2)),
                "HMDB Match Source": "stereo_prefix_removed",
            }

    # Not found
    return {
        "HMDB IDs": "Not Found",
        "HMDB Match Source": "not_found",
    }


# ============================================================================
# MAIN ANNOTATION FUNCTION — BOTH KEGG AND HMDB
# ============================================================================

def annotate_metabolites(
    names: List[str],
    json_db_file: str = str(DEFAULT_JSON_DB),
    hmdb_pkl_files: List[str] = None,
    deduplicate: bool = True,
) -> List[dict]:
    """
    Annotate metabolite names against BOTH KEGG and HMDB databases.

    For each name, returns:
      - Original Name
      - KEGG ID, KEGG Match Source, KEGG Matched Query
      - HMDB IDs, HMDB Match Source

    Parameters:
        names: list of metabolite name strings
        json_db_file: path to KEGG JSON mapping
        hmdb_pkl_files: list of paths to HMDB pickle files (None = use defaults)
        deduplicate: if True, skip duplicate names (case-insensitive)
    """
    # Load both databases
    name_to_kegg = load_kegg_name_to_id(json_db_file)

    if hmdb_pkl_files is not None:
        hmdb_tuple = tuple(hmdb_pkl_files)
    else:
        hmdb_tuple = tuple(str(p) for p in DEFAULT_HMDB_PKLS)
    name_to_hmdb = load_hmdb_name_to_id(hmdb_tuple)

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

        # Look up in both databases
        kegg_result = lookup_kegg(key, name_to_kegg, original)
        hmdb_result = lookup_hmdb(key, name_to_hmdb)

        # Combine into single row
        row = {"Original Name": original}
        row.update(kegg_result)
        row.update(hmdb_result)
        results.append(row)

    return results

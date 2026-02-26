#!/usr/bin/env python3
"""
Build a single JSON file from database CSVs for the student search frontend.
Run from repo root: python scripts/build_search_data.py
Output: docs/data.json
"""
import csv
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATABASE = REPO_ROOT / "database"
STUDENTS_CSV = DATABASE / "students" / "students.csv"
CONTESTS_DIR = DATABASE / "contests"
CONTESTS_CSV = CONTESTS_DIR / "contests.csv"
OUTPUT_JSON = REPO_ROOT / "docs" / "data.json"

# Contest slugs to exclude from data.json (still kept in database).
CONTESTS_SKIP_FOR_SEARCH = {"mathcounts-national"}


def humanize_contest(slug: str) -> str:
    """Turn contest slug into title, e.g. hmmt-feb-geometry -> HMMT Feb Geometry."""
    parts = slug.split("-")
    known_acronyms = {"hmmt", "pumac", "arml", "amc", "aime", "usamo", "mathcounts", "cmimc", "imo"}
    out = []
    for p in parts:
        if p.lower() in known_acronyms:
            out.append(p.upper())
        else:
            out.append(p.capitalize())
    return " ".join(out)


def load_contests() -> dict:
    """Load contests.csv -> { folder_name: { contest_name, description, website } }."""
    by_slug = {}
    if not CONTESTS_CSV.exists():
        return by_slug
    with open(CONTESTS_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            folder = (row.get("folder_name") or "").strip()
            if not folder:
                continue
            by_slug[folder] = {
                "contest_name": (row.get("contest_name") or "").strip(),
                "description": (row.get("description") or "").strip(),
                "website": (row.get("website") or "").strip(),
            }
    return by_slug


def load_students() -> dict:
    """Load students.csv -> { student_id: { name, aliases: [] } }."""
    by_id = {}
    with open(STUDENTS_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sid = row["student_id"].strip()
            if not sid:
                continue
            try:
                sid = int(sid)
            except ValueError:
                continue
            name = (row.get("student_name") or "").strip()
            alias = (row.get("alias") or "").strip()
            aliases = [a.strip() for a in alias.split("|") if a.strip()] if alias else []
            by_id[sid] = {"name": name, "aliases": aliases}
    return by_id


def collect_result_files() -> list:
    """Return list of (contest_slug, year, path) for every result/competitors CSV.
    Includes all contest dirs (e.g. mathcounts-national-rank, hmmt-feb, pumac, etc.)."""
    out = []
    for contest_dir in sorted(CONTESTS_DIR.iterdir()):
        if not contest_dir.is_dir():
            continue
        slug = contest_dir.name
        for year_dir in sorted(contest_dir.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.startswith("year="):
                continue
            year = year_dir.name.replace("year=", "")
            for csv_path in sorted(year_dir.glob("*.csv")):
                out.append((slug, year, csv_path))
    return out


def main() -> None:
    students = load_students()
    contests = load_contests()
    records_by_id = {}
    contest_year_files = {}  # slug -> { year -> filename }

    for slug, year, csv_path in collect_result_files():
        if slug in CONTESTS_SKIP_FOR_SEARCH:
            continue
        contest_info = contests.get(slug, {})
        contest_title = (contest_info.get("contest_name") or "").strip() or humanize_contest(slug)
        if slug not in contest_year_files:
            contest_year_files[slug] = {}
        contest_year_files[slug][year] = csv_path.name
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            continue
        for row in rows:
            sid = row.get("student_id") or row.get("student_id ")
            if sid is not None:
                sid = str(sid).strip()
            if not sid:
                continue
            try:
                sid = int(sid)
            except ValueError:
                continue
            record = {
                "contest": contest_title,
                "year": year,
                "contest_slug": slug,
            }
            for k, v in row.items():
                if k is None:
                    continue
                k = k.strip()
                if k and k not in ("student_id", "student_id "):
                    if v is not None and str(v).strip() != "":
                        record[k] = v.strip() if isinstance(v, str) else v
            if sid not in records_by_id:
                records_by_id[sid] = []
            records_by_id[sid].append(record)
            if sid not in students:
                name = (row.get("student_name") or "").strip()
                students[sid] = {"name": name or f"Student {sid}", "aliases": []}

    result_students = []
    for sid in sorted(records_by_id.keys()):
        recs = records_by_id[sid]
        recs.sort(key=lambda r: (r.get("year", ""), r.get("contest", "")), reverse=True)
        info = students.get(sid, {"name": f"Student {sid}", "aliases": []})
        result_students.append({
            "id": sid,
            "name": info["name"],
            "aliases": info["aliases"],
            "records": recs,
        })

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "students": result_students,
            "contests": contests,
            "contest_year_files": contest_year_files,
        }, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(result_students)} students with records to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

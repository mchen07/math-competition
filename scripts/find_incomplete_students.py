#!/usr/bin/env python3
"""
Find incomplete records in database/students/students.csv:
  1. Students missing state
  2. Students missing gender
  3. Students missing grade (grade_in_2026)

Writes results to incomplete_students.json (repo root) and prints a summary.

Run from the repo root:

    python scripts/find_incomplete_students.py
"""

import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STUDENTS_CSV = REPO_ROOT / "database" / "students" / "students.csv"
OUTPUT_JSON = REPO_ROOT / "incomplete_students.json"


def is_blank(value: str) -> bool:
    """Return True if value is missing or blank (empty/whitespace)."""
    return not (value or "").strip()


def main() -> None:
    if not STUDENTS_CSV.exists():
        raise SystemExit(f"Students file not found: {STUDENTS_CSV}")

    missing_state: list[tuple[str, str]] = []
    missing_gender: list[tuple[str, str]] = []
    missing_grade: list[tuple[str, str]] = []

    with open(STUDENTS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "student_id" not in (reader.fieldnames or []):
            raise SystemExit(f"'student_id' column not found in {STUDENTS_CSV}")

        for row in reader:
            sid = (row.get("student_id") or "").strip()
            name = (row.get("student_name") or "").strip()
            if not sid:
                continue

            if is_blank(row.get("state")):
                missing_state.append((sid, name))
            if is_blank(row.get("gender")):
                missing_gender.append((sid, name))
            if is_blank(row.get("grade_in_2026")):
                missing_grade.append((sid, name))

    # Summary
    # Count unique students with at least one missing field
    all_incomplete_ids = set()
    for sid, _ in missing_state + missing_gender + missing_grade:
        all_incomplete_ids.add(sid)
    unique_incomplete = len(all_incomplete_ids)

    def sort_by_id(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return sorted(items, key=lambda x: int(x[0]) if x[0].isdigit() else 0)

    payload = {
        "summary": {
            "missing_state_count": len(missing_state),
            "missing_gender_count": len(missing_gender),
            "missing_grade_count": len(missing_grade),
            "unique_incomplete_count": unique_incomplete,
        },
        "missing_state": [{"student_id": sid, "student_name": name} for sid, name in sort_by_id(missing_state)],
        "missing_gender": [{"student_id": sid, "student_name": name} for sid, name in sort_by_id(missing_gender)],
        "missing_grade": [{"student_id": sid, "student_name": name} for sid, name in sort_by_id(missing_grade)],
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("INCOMPLETE STUDENTS SUMMARY")
    print("=" * 60)
    print(f"Students missing state:     {len(missing_state):>5}")
    print(f"Students missing gender:    {len(missing_gender):>5}")
    print(f"Students missing grade:     {len(missing_grade):>5}")
    print("-" * 60)
    print(f"Unique students with ≥1 missing field: {unique_incomplete}")
    print(f"\nOutput written to: {OUTPUT_JSON}")
    print()

    # Details: missing state
    print("=" * 60)
    print("1. STUDENTS MISSING STATE")
    print("=" * 60)
    if missing_state:
        for sid, name in sort_by_id(missing_state):
            print(f"  {sid:>6}  {name}")
    else:
        print("  (none)")
    print()

    # Details: missing gender
    print("=" * 60)
    print("2. STUDENTS MISSING GENDER")
    print("=" * 60)
    if missing_gender:
        for sid, name in sort_by_id(missing_gender):
            print(f"  {sid:>6}  {name}")
    else:
        print("  (none)")
    print()

    # Details: missing grade
    print("=" * 60)
    print("3. STUDENTS MISSING GRADE (grade_in_2026)")
    print("=" * 60)
    if missing_grade:
        for sid, name in sort_by_id(missing_grade):
            print(f"  {sid:>6}  {name}")
    else:
        print("  (none)")


if __name__ == "__main__":
    main()

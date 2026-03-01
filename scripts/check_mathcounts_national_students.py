#!/usr/bin/env python3
"""
Check students with "MATHCOUNTS National — Rankings":
- Each such student must have NO MORE than 3 appearances (i.e. <= 3).
- All appearances must have different grade values (no duplicate grades).
"""

import json
from pathlib import Path

DATA_JSON = Path(__file__).resolve().parent.parent / "docs" / "data.json"
CONTEST_NAME = "MATHCOUNTS National — Rankings"


def main():
    with open(DATA_JSON) as f:
        data = json.load(f)

    violations = []  # (student, issue)
    valid = []

    for student in data["students"]:
        mc_records = [
            r for r in student.get("records", [])
            if r.get("contest") == CONTEST_NAME
        ]
        if not mc_records:
            continue

        count = len(mc_records)
        grades = [r.get("grade") for r in mc_records if r.get("grade") is not None]
        # Treat missing grade as a distinct "value" for uniqueness
        grades_with_missing = [r.get("grade", "__MISSING__") for r in mc_records]
        unique_grades = len(set(grades_with_missing)) == len(grades_with_missing)

        if count > 3:
            violations.append({
                "id": student["id"],
                "name": student["name"],
                "issue": ">3 appearances",
                "count": count,
                "grades": sorted(grades_with_missing),
            })
        elif not unique_grades:
            from collections import Counter
            dupes = {g: c for g, c in Counter(grades_with_missing).items() if c > 1}
            violations.append({
                "id": student["id"],
                "name": student["name"],
                "issue": "duplicate grade values",
                "count": count,
                "grades": sorted(grades_with_missing),
                "duplicates": dupes,
            })
        else:
            valid.append({
                "id": student["id"],
                "name": student["name"],
                "count": count,
                "grades": sorted(grades_with_missing),
            })

    print("=== MATHCOUNTS National — Rankings validation ===\n")
    print(f"Students with at least one MATHCOUNTS National — Rankings record: "
          f"{len(violations) + len(valid)}")
    print(f"Valid (count <= 3 and all grades distinct): {len(valid)}")
    print(f"Violations: {len(violations)}\n")

    if violations:
        print("--- Violations ---")
        for v in sorted(violations, key=lambda x: (x["name"], x["id"])):
            print(f"  id={v['id']}  {v['name']}")
            print(f"    {v['issue']}  (appearances: {v['count']})  grades: {v['grades']}")
            if "duplicates" in v:
                print(f"    duplicate counts: {v['duplicates']}")
            print()

    if valid:
        print("--- Valid students (first 20) ---")
        for v in sorted(valid, key=lambda x: (-x["count"], x["name"]))[:20]:
            print(f"  id={v['id']}  {v['name']}  appearances={v['count']}  grades={v['grades']}")

    return 0 if not violations else 1


if __name__ == "__main__":
    exit(main())

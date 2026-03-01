#!/usr/bin/env python3
"""
Find all students who appear in JMO or AMO contest tables but never appear
in any other contest results.

Run from repo root:
    # JMO or AMO only (default, all years)
    python scripts/find_jmo_amo_only_students.py

    # AMO only (all years)
    python scripts/find_jmo_amo_only_students.py amo

    # JMO only (all years)
    python scripts/find_jmo_amo_only_students.py jmo

    # JMO or AMO only for a specific year
    python scripts/find_jmo_amo_only_students.py --year 2024

    # AMO only for a specific year
    python scripts/find_jmo_amo_only_students.py amo --year 2024

    # Write output to file
    python scripts/find_jmo_amo_only_students.py -o jmo_amo_only.csv

You can also pass multiple years, e.g.:
    python scripts/find_jmo_amo_only_students.py --year 2023 --year 2024
"""

import csv
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DATABASE = REPO_ROOT / "database"
STUDENTS_CSV = DATABASE / "students" / "students.csv"
CONTESTS_DIR = DATABASE / "contests"

DEFAULT_TARGET_SLUGS = {"jmo", "amo"}


def load_students():
    """Return { student_id: {'name': ..., 'state': ..., 'is_alias_duplicate': ...} }.

    Notes:
      * Only non-Canadian students are included (we exclude any row whose
        state field contains "canada", case-insensitive).
      * If a student's *name* matches some other student's alias, we treat this
        row as an alias-duplicate and can optionally skip it in reports.
    """
    rows = []
    alias_names = set()

    with open(STUDENTS_CSV, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            sid = (row.get("student_id") or "").strip()
            if not sid:
                continue
            try:
                sid_int = int(sid)
            except ValueError:
                continue
            name = (row.get("student_name") or "").strip() or f"Student {sid_int}"
            state = (row.get("state") or "").strip()
            # Restrict to US awardees: drop any row whose state mentions Canada.
            state_lc = state.lower()
            if "canada" in state_lc or "canda" in state_lc:
                continue
            alias = (row.get("alias") or "").strip()
            rows.append((sid_int, name, state, alias))
            if alias:
                alias_names.add(alias)

    by_id = {}
    for sid_int, name, state, alias in rows:
        is_alias_duplicate = bool(alias_names and alias == "" and name in alias_names)
        by_id[sid_int] = {
            "name": name,
            "state": state,
            "is_alias_duplicate": is_alias_duplicate,
        }
    return by_id


def collect_result_files():
    """Yield (contest_slug, year, csv_path) for every contest result CSV."""
    for contest_dir in sorted(CONTESTS_DIR.iterdir()):
        if not contest_dir.is_dir():
            continue
        slug = contest_dir.name
        for year_dir in sorted(contest_dir.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.startswith("year="):
                continue
            year = year_dir.name.replace("year=", "")
            for csv_path in sorted(year_dir.glob("*.csv")):
                yield slug, year, csv_path


def build_student_contest_map():
    """Return { student_id: {'slugs': set(...), 'years': set(...), 'awards': {(slug, year): award}} }."""
    by_sid = {}
    for slug, year, csv_path in collect_result_files():
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sid = row.get("student_id") or row.get("student_id ")
                if sid is not None:
                    sid = str(sid).strip()
                if not sid:
                    continue
                try:
                    sid_int = int(sid)
                except ValueError:
                    continue
                entry = by_sid.setdefault(sid_int, {"slugs": set(), "years": set(), "awards": {}})
                entry["slugs"].add(slug)
                entry["years"].add(year)
                award = (row.get("award") or "").strip()
                entry["awards"][(slug, year)] = award
    return by_sid


def parse_target_slugs(argv):
    """Parse CLI args to decide which contest slugs to treat as 'target'.

    Examples:
      []        -> {"jmo", "amo"}
      ["amo"]   -> {"amo"}
      ["jmo"]   -> {"jmo"}
      ["amo,jmo"] -> {"amo", "jmo"}
    """
    if not argv:
        return DEFAULT_TARGET_SLUGS
    arg = (argv[0] or "").strip().lower()
    if not arg:
        return DEFAULT_TARGET_SLUGS
    if arg in {"amo", "usamo"}:
        return {"amo"}
    if arg in {"jmo", "usajmo"}:
        return {"jmo"}
    # Fallback: comma-separated list of slugs
    slugs = {p for p in arg.split(",") if p}
    return slugs or DEFAULT_TARGET_SLUGS


def parse_output_file(argv):
    """Parse -o / --output from argv. Returns (path_or_None, remaining_args)."""
    output_path = None
    remaining = []
    skip_next = False

    for i, arg in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        a = (arg or "").strip()
        if not a:
            continue
        if a.startswith("-o=") or a.startswith("--output="):
            output_path = a.split("=", 1)[1].strip() or None
            continue
        if a in ("-o", "--output"):
            if i + 1 < len(argv):
                output_path = (argv[i + 1] or "").strip() or None
                skip_next = True
            continue
        remaining.append(arg)

    return output_path, remaining


def parse_year_filter(argv):
    """Parse CLI args to find any year filters.

    Supports forms like:
      --year 2024
      --year=2024
      2024               (bare 4-digit year)
    Returns (year_set_or_None, remaining_args).
    """
    year_filter = set()
    remaining = []
    skip_next = False

    for i, arg in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        a = (arg or "").strip()
        if not a:
            continue
        if a.startswith("--year="):
            year = a.split("=", 1)[1].strip()
            if year:
                year_filter.add(year)
            continue
        if a == "--year":
            if i + 1 < len(argv):
                year = (argv[i + 1] or "").strip()
                if year:
                    year_filter.add(year)
                skip_next = True
            continue
        if a.isdigit() and len(a) == 4:
            year_filter.add(a)
            continue
        remaining.append(arg)

    if not year_filter:
        return None, remaining
    return year_filter, remaining


def find_jmo_amo_only_students(target_slugs, year_filter=None):
    students = load_students()
    contests_by_sid = build_student_contest_map()

    result = []
    for sid, info in contests_by_sid.items():
        slugs = info["slugs"]
        years = info["years"]
        if not slugs:
            continue
        if not (slugs & target_slugs):
            continue  # never in any target contest
        if slugs - target_slugs:
            continue  # appeared in some other contest too
        if year_filter is not None and not (years & year_filter):
            continue  # no results in the requested year(s)
        student_info = students.get(sid)
        if student_info is None:
            # Skip students that don't appear in the (filtered) students table.
            # This includes missing records and any we dropped as non‑US.
            continue
        # Skip alias-only duplicate rows (e.g. a "Calvin Wang" row when
        # "Calvin Wang" is already listed as someone else's alias).
        if student_info.get("is_alias_duplicate"):
            continue
        name = student_info["name"]
        state = student_info["state"]
        awards = info.get("awards") or {}
        # Format awards as "slug:year=award" for each (slug, year) the student has
        award_pairs = [f"{s}:{y}={a}" for (s, y), a in sorted(awards.items())]
        award_str = ";".join(award_pairs)
        result.append((name, sid, state, sorted(slugs), sorted(years), award_str))

    result.sort(key=lambda x: (x[0].lower(), x[1]))
    return result


def main():
    argv = sys.argv[1:]
    output_path, argv = parse_output_file(argv)
    year_filter, slug_args = parse_year_filter(argv)
    target_slugs = parse_target_slugs(slug_args)
    matches = find_jmo_amo_only_students(target_slugs, year_filter=year_filter)

    out = open(output_path, "w", newline="", encoding="utf-8") if output_path else sys.stdout
    try:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["name", "student_id", "state", "contests", "years", "award"])
        for name, sid, state, slugs, years, award_str in matches:
            contests_str = ";".join(slugs)
            years_str = ";".join(years)
            writer.writerow([name, sid, state, contests_str, years_str, award_str])
    finally:
        if output_path:
            out.close()

    target_list = ", ".join(sorted(target_slugs))
    # Send human-readable summary to stderr so CSV redirection
    # (e.g. `> jmo_amo_only_students.csv`) doesn't include it.
    if year_filter:
        year_list = ", ".join(sorted(year_filter))
        msg = (
            f"Found {len(matches)} students who are only in: {target_list} "
            f"for year(s): {year_list}."
        )
    else:
        msg = f"Found {len(matches)} students who are only in: {target_list}."
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()


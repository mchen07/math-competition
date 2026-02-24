#!/usr/bin/env python3
"""
Crawler for HMMT February competition individual results.
Fetches data from the official results page and writes students.csv, teams.csv,
and results.csv for the given year. Merges with existing students/teams so
existing students are not duplicated.
"""

import argparse
import csv
import re
import urllib.request
from pathlib import Path


def hmmt_feb_url(year: int) -> str:
    """Return the long results URL for HMMT February for the given year."""
    return f"https://hmmt-archive.s3.amazonaws.com/tournaments/{year}/feb/results/long.htm"

# Line format: O  [rank.]  total | alg geo comb | Name (Team)
# e.g. "O    1. 112.14 | 40.23 39.16 32.74 | Alexander Wang (LV Fire)"
# 2025 has unranked lines: "O       103.72 | ..." (no rank)
INDIVIDUAL_LINE_RE = re.compile(
    r"^O\s+(?:(\d+)\.\s+)?([\d.]+)\s+\|\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\|\s*(.*)$"
)


def strip_html(html: str) -> str:
    """Remove HTML tags and decode common entities to get plain text."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
    return text


def fetch_text(url: str) -> str:
    """Fetch URL and return decoded plain text (HTML stripped if present)."""
    with urllib.request.urlopen(url) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    # If response looks like HTML, strip tags so we can parse section text
    if "<" in raw and ">" in raw:
        raw = strip_html(raw)
    return raw


def parse_name_team(tail: str) -> tuple[str, str]:
    """Parse 'Name (Team)' or empty string into (name, team). Handles nested parens in team (e.g. 'Essential Academy1 (Unranked *)')."""
    tail = tail.strip()
    if not tail:
        return "", ""
    # Format is "Name (Team)" where Team can contain nested parens. Use first "(" and last ")".
    if tail.endswith(")"):
        first_open = tail.find("(")
        if first_open >= 0:
            name = tail[:first_open].strip().rstrip()
            team = tail[first_open + 1 : -1].strip()
            return name, team
    return tail, ""


def extract_individual_section(text: str) -> list[str]:
    """Extract lines belonging to OVERALL INDIVIDUAL AWARDS section."""
    # After HTML strip, section may be in one chunk; find by markers
    start_marker = "OVERALL INDIVIDUAL AWARDS"
    end_marker = "ALGEBRA AND NUMBER THEORY"
    if start_marker in text and end_marker in text:
        start = text.index(start_marker) + len(start_marker)
        end = text.index(end_marker)
        section_text = text[start:end]
    else:
        section_text = text
    lines = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line or line.startswith("===="):
            continue
        # Match ranked "O    1. 112.14 |" or unranked "O       103.72 |" (2025)
        if INDIVIDUAL_LINE_RE.match(line):
            lines.append(line)
    return lines


def parse_individual_lines(lines: list[str]) -> list[dict]:
    """Parse individual result lines into list of dicts."""
    results = []
    for line in lines:
        m = INDIVIDUAL_LINE_RE.match(line)
        if not m:
            continue
        rank = int(m.group(1)) if m.group(1) else 0
        total = float(m.group(2))
        alg = float(m.group(3))
        geo = float(m.group(4))
        comb = float(m.group(5))
        name, team = parse_name_team(m.group(6))
        results.append({
            "rank": rank,
            "total_score": total,
            "algebra_score": alg,
            "geometry_score": geo,
            "combinatorics_score": comb,
            "name": name,
            "team": team,
        })
    return results


def load_existing_students_and_teams(
    students_path: Path, teams_path: Path
) -> tuple[
    dict[tuple[str, str], int],
    dict[str, int],
    list[tuple[int, str, int, str]],
    list[tuple[int, str]],
    int,
    int,
]:
    """
    Load existing students.csv and teams.csv if present.
    Returns (student_key_to_id, team_name_to_id, student_list, team_list, next_sid, next_tid).
    student_key_to_id: (student_name, team_name) -> student_id (one entry per (name, team) for each team in student's team_ids).
    student_list entries: (student_id, student_name, team_ids_str, alias); team_ids_str is e.g. "1" or "1|5".
    """
    team_id_to_name: dict[int, str] = {}
    team_name_to_id: dict[str, int] = {}
    student_list: list[tuple[int, str, str, str]] = []
    student_key_to_id: dict[tuple[str, str], int] = {}
    next_sid, next_tid = 1, 1

    if teams_path.exists():
        with open(teams_path, encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                tid = int(row["team_id"])
                tname = (row.get("team_name") or "").strip()
                team_id_to_name[tid] = tname
                if tname:
                    team_name_to_id[tname] = tid
                next_tid = max(next_tid, tid + 1)

    if students_path.exists():
        with open(students_path, encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                sid = int(row["student_id"])
                name = row.get("student_name", row.get("name", ""))
                # Support both team_id (legacy) and team_ids (pipe-separated list)
                team_ids_raw = row.get("team_ids", row.get("team_id", ""))
                if not team_ids_raw:
                    continue
                team_ids_str = "|".join(str(int(x.strip())) for x in str(team_ids_raw).split("|") if x.strip())
                alias = (row.get("alias") or "").strip()
                student_list.append((sid, name, team_ids_str, alias))
                for tid_str in team_ids_str.split("|"):
                    tname = team_id_to_name.get(int(tid_str), "")
                    if tname or tid_str:
                        student_key_to_id[(name, tname)] = sid
                next_sid = max(next_sid, sid + 1)

    team_list = [(tid, tname) for tname, tid in sorted(team_name_to_id.items(), key=lambda x: x[1])]
    return student_key_to_id, team_name_to_id, student_list, team_list, next_sid, next_tid


def build_teams_and_students(
    parsed: list[dict],
    existing_student_key_to_id: dict[tuple[str, str], int],
    existing_team_name_to_id: dict[str, int],
    existing_student_list: list[tuple[int, str, str, str]],
    existing_team_list: list[tuple[int, str]],
    next_sid: int,
    next_tid: int,
) -> tuple[list[tuple[int, str]], list[tuple[int, str, str, str]], dict[tuple[str, str], int]]:
    """
    Merge parsed results with existing students/teams. Reuse existing (name, team) -> student_id.
    No team alias: (name, team_name) identifies the student. student_list: (sid, name, team_ids_str, alias).
    """
    student_key_to_id = dict(existing_student_key_to_id)
    team_name_to_id = dict(existing_team_name_to_id)
    new_students: list[tuple[int, str, str, str]] = []
    new_team_names: set[str] = set()

    for row in parsed:
        name, team = row["name"], row["team"]
        if not (name or "").strip():
            continue
        if not (team or "").strip():
            continue  # do not create teams or students with empty team name
        key = (name, team)
        if key not in student_key_to_id:
            student_key_to_id[key] = next_sid
            if team not in team_name_to_id:
                team_name_to_id[team] = next_tid
                next_tid += 1
                new_team_names.add(team)
            tid = team_name_to_id[team]
            new_students.append((next_sid, name, str(tid), ""))
            next_sid += 1

    team_list = list(existing_team_list)
    for tname in sorted(new_team_names, key=lambda t: team_name_to_id[t]):
        team_list.append((team_name_to_id[tname], tname))
    student_list = existing_student_list + new_students
    # Only keep teams that are still used by at least one student (team_ids can be "1" or "1|5")
    used_team_ids: set[int] = set()
    for row in student_list:
        for tid_str in row[2].split("|"):
            if tid_str.strip():
                used_team_ids.add(int(tid_str))
    tid_to_name = {tid: tname for tname, tid in team_name_to_id.items()}
    # Only include teams that have a name (never write a team without a name)
    team_list = [
        (tid, tid_to_name[tid])
        for tid in sorted(used_team_ids)
        if tid in tid_to_name and (tid_to_name[tid] or "").strip()
    ]

    return team_list, student_list, student_key_to_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl HMMT February individual results for a given year.")
    parser.add_argument("year", type=int, nargs="?", default=2026, help="Year (e.g. 2025 or 2026)")
    args = parser.parse_args()
    year = args.year

    base = Path(__file__).resolve().parent.parent.parent
    students_path = base / "database" / "students" / "students.csv"
    teams_path = base / "database" / "students" / "teams.csv"
    results_path = base / "database" / "contests" / "hmmt-feb" / f"year={year}" / "results.csv"

    students_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    url = hmmt_feb_url(year)
    print("Fetching", url)
    text = fetch_text(url)

    lines = extract_individual_section(text)
    print(f"Parsed {len(lines)} individual result lines")

    parsed = parse_individual_lines(lines)
    parsed_named = [r for r in parsed if (r["name"] or "").strip()]
    print(f"Parsed {len(parsed)} individual results ({len(parsed_named)} with names)")

    (
        existing_key_to_sid,
        existing_team_name_to_id,
        existing_student_list,
        existing_team_list,
        next_sid,
        next_tid,
    ) = load_existing_students_and_teams(students_path, teams_path)
    print(f"Loaded {len(existing_student_list)} existing students, {len(existing_team_list)} existing teams")

    team_list, student_list, key_to_sid = build_teams_and_students(
        parsed_named,
        existing_key_to_sid,
        existing_team_name_to_id,
        existing_student_list,
        existing_team_list,
        next_sid,
        next_tid,
    )
    print(f"Merged: {len(team_list)} teams, {len(student_list)} students")

    # Write teams.csv and students.csv (merged)
    with open(teams_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["team_id", "team_name"])
        for team_id, team_name in team_list:
            if (team_name or "").strip():
                w.writerow([team_id, team_name])
    print("Wrote", teams_path)

    with open(students_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["student_id", "student_name", "team_ids", "alias"])
        for student_id, name, team_ids_str, alias in student_list:
            w.writerow([student_id, name, team_ids_str or "", alias or ""])
    print("Wrote", students_path)

    # Write results.csv for this year only
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "student_id", "student_name", "year", "rank", "total_score",
            "algebra_score", "geometry_score", "combinatorics_score",
        ])
        for row in parsed_named:
            key = (row["name"], row["team"])
            student_id = key_to_sid[key]
            w.writerow([
                student_id,
                row["name"],
                year,
                row["rank"],
                row["total_score"],
                row["algebra_score"],
                row["geometry_score"],
                row["combinatorics_score"],
            ])
    print("Wrote", results_path)


if __name__ == "__main__":
    main()

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
    """
    Parse 'Name (Team)' or empty string into (name, team).
    Handles:
    - Nested parens in team (e.g. 'Essential Academy1 (Unranked *)')
    - Parens inside the name (e.g. 'Yibo(Tom) Zhang (Florida Beaches)')
    """
    tail = tail.strip()
    if not tail:
        return "", ""
    if not tail.endswith(")"):
        return tail, ""

    # Find the '(' that matches the final ')', correctly handling nested parens.
    depth = 0
    open_idx = -1
    for i in range(len(tail) - 1, -1, -1):
        c = tail[i]
        if c == ")":
            depth += 1
        elif c == "(":
            depth -= 1
            if depth == 0:
                open_idx = i
                break

    if open_idx == -1:
        # Unbalanced parens; fall back to treating whole tail as name.
        return tail, ""

    name = tail[:open_idx].strip()
    team = tail[open_idx + 1 : -1].strip()
    return name, team


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
    list[tuple[int, str, str, str]],
    list[tuple[int, str]],
    int,
    int,
    dict[int, str],
]:
    """
    Load existing students.csv and teams.csv if present.
    Returns (student_key_to_id, team_name_to_id, student_list, team_list, next_sid, next_tid, team_id_to_associated).

    - student_key_to_id: (student_name, team_name) -> student_id (one entry per (name, team) for each team in student's team_ids).
    - student_list entries: (student_id, student_name, team_ids_str, alias); team_ids_str is e.g. "1" or "1|5".
    - team_id_to_associated: team_id -> associated_team_ids string (e.g. "1|32|73"), if present in teams.csv.
    """
    team_id_to_name: dict[int, str] = {}
    team_name_to_id: dict[str, int] = {}
    team_id_to_associated: dict[int, str] = {}
    student_list: list[tuple[int, str, str, str]] = []
    student_key_to_id: dict[tuple[str, str], int] = {}
    next_sid, next_tid = 1, 1

    if teams_path.exists():
        with open(teams_path, encoding="utf-8") as f:
            r = csv.DictReader(f)
            fieldnames = r.fieldnames or []
            has_associated = "associated_team_ids" in fieldnames
            for row in r:
                tid = int(row["team_id"])
                tname = (row.get("team_name") or "").strip()
                team_id_to_name[tid] = tname
                if tname:
                    team_name_to_id[tname] = tid
                if has_associated:
                    assoc_raw = (row.get("associated_team_ids") or "").strip()
                    if assoc_raw:
                        team_id_to_associated[tid] = assoc_raw
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

                # For each team the student already has, register keys for all
                # associated teams in the same group so that future crawls
                # (e.g. LV Fire vs Lehigh Valley Fire vs Lehigh Valley Ice,
                # or Thomas Jefferson A vs TJ-A) map to the SAME student id.
                for tid_str in team_ids_str.split("|"):
                    tid_str = tid_str.strip()
                    if not tid_str:
                        continue
                    try:
                        tid = int(tid_str)
                    except ValueError:
                        continue

                    # Build the full set of associated team_ids for this tid.
                    assoc_ids: set[int] = {tid}
                    assoc_raw = (team_id_to_associated.get(tid) or "").strip()
                    if assoc_raw:
                        for tok in assoc_raw.split("|"):
                            tok = tok.strip()
                            if not tok:
                                continue
                            try:
                                assoc_ids.add(int(tok))
                            except ValueError:
                                continue

                    # Register (name, team_name) for every team in the group.
                    for assoc_tid in assoc_ids:
                        tname = (team_id_to_name.get(assoc_tid) or "").strip()
                        if tname or assoc_tid:
                            student_key_to_id[(name, tname)] = sid

                next_sid = max(next_sid, sid + 1)

    team_list = [(tid, tname) for tname, tid in sorted(team_name_to_id.items(), key=lambda x: x[1])]
    return (
        student_key_to_id,
        team_name_to_id,
        student_list,
        team_list,
        next_sid,
        next_tid,
        team_id_to_associated,
    )


def build_teams_and_students(
    parsed: list[dict],
    existing_student_key_to_id: dict[tuple[str, str], int],
    existing_team_name_to_id: dict[str, int],
    existing_student_list: list[tuple[int, str, str, str]],
    existing_team_list: list[tuple[int, str]],
    existing_team_id_to_associated: dict[int, str],
    next_sid: int,
    next_tid: int,
) -> tuple[
    list[tuple[int, str]],
    list[tuple[int, str, str, str]],
    dict[tuple[str, str], int],
    dict[int, str],
]:
    """
    Merge parsed results with existing students/teams. Reuse existing (name, team) -> student_id.
    No team alias: (name, team_name) identifies the student. student_list: (sid, name, team_ids_str, alias).

    Returns (team_list, student_list, student_key_to_id, team_id_to_associated).
    """
    student_key_to_id = dict(existing_student_key_to_id)
    team_name_to_id = dict(existing_team_name_to_id)
    team_id_to_associated = dict(existing_team_id_to_associated)
    # Work with mutable per-student team-id sets so we can grow team_ids
    # for existing students when they appear on additional (associated) teams.
    sid_to_name_alias: dict[int, tuple[str, str]] = {}
    sid_to_team_ids: dict[int, set[int]] = {}
    for sid, name, team_ids_str, alias in existing_student_list:
        sid_to_name_alias[sid] = (name, alias)
        teams: set[int] = set()
        for tid_str in str(team_ids_str).split("|"):
            tid_str = tid_str.strip()
            if not tid_str:
                continue
            try:
                teams.add(int(tid_str))
            except ValueError:
                continue
        sid_to_team_ids[sid] = teams

    new_team_names: set[str] = set()

    for row in parsed:
        name, team = row["name"], row["team"]
        if not (name or "").strip():
            continue
        if not (team or "").strip():
            continue  # do not create teams or students with empty team name
        key = (name, team)
        if key not in student_key_to_id:
            # New (name, team) combination → possibly new team, definitely new student id.
            if team not in team_name_to_id:
                team_name_to_id[team] = next_tid
                next_tid += 1
                new_team_names.add(team)
            tid = team_name_to_id[team]

            student_key_to_id[key] = next_sid
            sid = next_sid
            next_sid += 1

            # Initialise structures for this brand-new student.
            sid_to_name_alias[sid] = (name, "")
            sid_to_team_ids.setdefault(sid, set())
        else:
            # Existing student; just look up ids.
            sid = student_key_to_id[key]
            if team not in team_name_to_id:
                # Shouldn't normally happen, but be defensive.
                team_name_to_id[team] = next_tid
                next_tid += 1
                new_team_names.add(team)
            tid = team_name_to_id[team]

        # Ensure this student's team_ids contains the full associated group
        # for this team id (e.g. LV Fire / Lehigh Valley Fire / Lehigh Valley Ice).
        teams = sid_to_team_ids.setdefault(sid, set())
        assoc_ids: set[int] = set()
        assoc_ids.add(tid)
        assoc_raw = (team_id_to_associated.get(tid) or "").strip()
        if assoc_raw:
            for tok in assoc_raw.split("|"):
                tok = tok.strip()
                if not tok:
                    continue
                try:
                    assoc_ids.add(int(tok))
                except ValueError:
                    continue
        teams.update(assoc_ids)

    team_list = list(existing_team_list)
    for tname in sorted(new_team_names, key=lambda t: team_name_to_id[t]):
        tid = team_name_to_id[tname]
        team_list.append((tid, tname))
        # Preserve existing associated_team_ids where present; new teams default to empty.
        if tid not in team_id_to_associated:
            team_id_to_associated[tid] = ""

    # Rebuild student_list from the aggregated sid → teams mapping.
    student_list: list[tuple[int, str, str, str]] = []
    for sid in sorted(sid_to_name_alias.keys()):
        name, alias = sid_to_name_alias[sid]
        teams = sid_to_team_ids.get(sid, set())
        team_ids_str = "|".join(str(tid) for tid in sorted(teams)) if teams else ""
        student_list.append((sid, name, team_ids_str, alias))

    # Do NOT drop "unused" teams: keep the full mapping of team ids and names
    # so that team ids remain stable across crawls, which is important for
    # features like associated_team_ids and for hand-curated associations.
    return team_list, student_list, student_key_to_id, team_id_to_associated


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
        existing_team_id_to_associated,
    ) = load_existing_students_and_teams(students_path, teams_path)
    print(f"Loaded {len(existing_student_list)} existing students, {len(existing_team_list)} existing teams")

    (
        team_list,
        student_list,
        key_to_sid,
        team_id_to_associated,
    ) = build_teams_and_students(
        parsed_named,
        existing_key_to_sid,
        existing_team_name_to_id,
        existing_student_list,
        existing_team_list,
        existing_team_id_to_associated,
        next_sid,
        next_tid,
    )
    print(f"Merged: {len(team_list)} teams, {len(student_list)} students")

    # Write teams.csv and students.csv (merged)
    with open(teams_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["team_id", "team_name", "associated_team_ids"])
        for team_id, team_name in team_list:
            if (team_name or "").strip():
                assoc = (team_id_to_associated.get(team_id) or "").strip()
                w.writerow([team_id, team_name, assoc])
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

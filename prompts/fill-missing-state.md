# Fill missing state for students in students.csv

**Goal:** Find the state for every student in `database/students/students.csv` who has a blank or missing `state` field. Update only those rows with a state value you can **derive from existing records**, using **student_id** as the key. Do not guess based on student name.

**Rule:** Always use **student_id** to find a student’s records. Do not match or infer state from name alone; same names in different states are different students.

---

## 1. Identify students with missing state

- Read `database/students/students.csv` (columns include: `student_id`, `student_name`, `state`, `team_ids`, `alias`, etc.).
- List all rows where `state` is empty or missing. These are the only rows you may update.

---

## 2. Look up state in this order

For each student with missing state, try sources in the following order. Use the **first** state you find for that **student_id**; stop once you have one.

### 2.1 State from Mathcounts data

- **`database/contests/mathcounts-national/`**  
  - Per year: `year=<year>/competitors.csv` has columns `student_id`, `state`, `student_name`, `grade`, `city`, `school`.  
  - If the student’s `student_id` appears here, use the `state` value from that row.
- **`database/contests/mathcounts-national-rank/`**  
  - Per year: `year=<year>/results.csv` has columns `student_id`, `student_name`, `state`, `year`, `rank`, `grade`.  
  - If the student’s `student_id` appears here, use the `state` value from that row.

Check all available years in both contest folders. Use the first non-empty state you find for that `student_id`.

### 2.2 State from other contests with school or location information

- Search other contest result files under `database/contests/` that contain **state**, **school**, **team**, or **site** columns.
- For each such file, look up rows where `student_id` matches the student.  
  - If the row has a **state** column, use that state.  
  - If the row has **school** (or similar) but no state, you may infer state from school name/location only when the source clearly indicates state (e.g. “California” in the name or a documented mapping). Prefer explicit state columns over inference.
- Examples of contests that may have state or school: `amo`, `jmo`, `mpfg`, `mpfg-olympiad`, `bamo-8`, `bamo-12`, `arml` (site), `dmm` (team_name), etc. Inspect each file’s header and use only columns that exist.

Again: match only by **student_id**; do not use name alone to assign state.

### 2.3 State from team name

- If state is still missing, check whether the student has **team_ids** in `students.csv` or appears in contest-specific team files (e.g. `database/contests/<contest>-teams/year=<year>/teams.csv` with `team_id`, `team_name`, `student_ids`).
- Look up the **team_name** for that student’s team(s). If the team name clearly indicates a state (e.g. “Texas A&M”, “California Math Club”), you may set state from that. Prefer unambiguous state references in the team name; if ambiguous, leave state blank.

---

## 3. Update students.csv

- For each student with missing state for whom you found a state in steps 2.1–2.3, update **only** the `state` column for that `student_id` in `database/students/students.csv`.
- Do not add or remove rows; do not change `student_id` or infer state from name-only matches.
- Leave `state` blank for any student for whom no state could be found using the rules above.

---

## Summary

1. List students in `students.csv` with empty `state`.
2. For each, use **student_id** only to look up state in: (1) mathcounts-national and mathcounts-national-rank, (2) other contest CSVs with state/school, (3) team name when it clearly indicates state.
3. Update `state` in `students.csv` only when you have a clear, student_id-based source. Never guess based on student name alone.

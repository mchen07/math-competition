# Add contest results for {competition} in {year}

**Input:** You will be given the contest results as text (e.g. copied from a webpage, PDF, or spreadsheet). Use that text as the source of truth for names, awards, ranks, scores, etc.

Add contest results for **{competition}** for the year **{year}**, following the conventions used in this repository.

## 1. Follow existing examples

- Inspect the structure under `database/contests/`:
  - Each contest has a **folder** (e.g. `amo`, `jmo`, `arml`, `mathcounts-national-rank`, `cmimc-algebra`, `pumac`).
  - For each year there is a subfolder `year=<year>` (e.g. `year=2025`).
  - Inside that folder, `results.csv` holds the results.
- Match the **folder name** and **column schema** to existing contests of the same type when possible (see examples below).
- If this contest is new, add a row to `database/contests/contests.csv` with: `folder_name`, `contest_name`, `description`, `website`.

### Example result file layouts

- **JMO-style (awards):** `student_id`, `student_name`, `state`, `award`  
  Example: `database/contests/jmo/year=2025/results.csv`
- **ARML-style (place/site/team):** `student_id`, `student_name`, `place`, `site`, `team`, `tb_corr`, `tb_time`, `prize`  
  Example: `database/contests/arml/year=2025/results.csv`
- **Rank/score style:** `student_id`, `student_name`, `year`, `rank`, `score` (or `grade`, etc. as used elsewhere)  
  Example: `database/contests/cmimc-algebra/year=2025/results.csv`
- **Rankings with grade:** `student_id`, `student_name`, `state`, `year`, `rank`, `grade`  
  Example: `database/contests/mathcounts-national-rank/year=2025/results.csv`

Use the schema that best fits the competition and is consistent with similar contests in `database/contests/`.

## 2. Look up and assign `student_id`

- **Student registry:** `database/students/students.csv`  
Columns: `student_id`, `student_name`, `state`, `team_ids`, `alias`
- **Lookup rule:** Identify a student by **both** `student_name` and `state`.  
  **Students with the same name but different states are different students** — do not treat them as the same person. If state is missing in the source data, use whatever state/region information is available (e.g. from team or site); if none, leave state blank but still treat (name, state) as the matching key.
- Match **case-insensitively** for names if needed, but preserve the canonical `student_name` from `students.csv` in the results.
- Check the `alias` column: values are pipe-separated (`|`); if the source name matches an alias, use that row’s `student_id` and `student_name`.
- You **do not** need to edit `database/students/teams.csv` when adding contest results; team compositions are tracked per contest/year (see below).

## 3. Add new students when not found

- If no row in `students.csv` matches the (name, state) pair (or name when state is blank):
  - Assign the next available `student_id` (max existing `student_id` + 1).
  - **Append** a new row to `database/students/students.csv` with:
    - `student_id` (new id)
    - `student_name` (as in the contest source)
    - `state` (from contest data if available, otherwise blank)
    - `team_ids` (blank unless known)
    - `alias` (blank unless known)
- Then use this new `student_id` and `student_name` in the contest `results.csv`.

## 4. Write the contest results

- Create or update:  
  `database/contests/<contest_folder>/year=<year>/results.csv`
- Use a header row consistent with the chosen schema; include at least `student_id` and `student_name` in every results file.
- Fill each row with the correct `student_id` and `student_name` (and state if the schema includes it), plus contest-specific columns (award, place, rank, score, etc.).

## 5. Record teams for this contest/year (if applicable)

- If the source data includes **teams** (e.g. a `Team` column like in the PUMaC example), also create or update:  
  `database/contests/<contest_folder>-teams/year=<year>/teams.csv`  
  Example: `database/contests/pumac-b-teams/year=2023/teams.csv`.
- This file captures the **team composition specific to that contest and year**. Its schema is:  
  `team_id`, `team_name`, `student_ids`
- **`team_id`**: an integer identifier unique within this contest/year. If a `teams.csv` already exists for this contest/year, reuse the existing `team_id` for any matching `team_name`; otherwise assign the next available integer.
- **`team_name`**: the team or organization name as it appears in the contest results (e.g. `Sierra Canyon School`, `Jericho Mathletes`, `Individuals Team 162`).
- **`student_ids`**: a pipe-separated list of the `student_id` values of students on that team for this contest/year (e.g. `1078|918|2208`). Use the `student_id`s from the corresponding `results.csv`, and include students from all relevant divisions/rounds of this contest/year that share that team.
- You **still do not** need to add or update rows in `database/students/teams.csv`; keep team information localized in the contest-specific `teams.csv` files.

## 6. After updating the database

- Run from repo root:  
  `python scripts/build_search_data.py`  
  so that `docs/data.json` reflects the new results for the website.

---

**Summary:** You will receive the contest results as text. Add results for **{competition}** **{year}** under `database/contests/` using that text; resolve `student_id` from `database/students/students.csv` by **(name, state)** (same name + different state ⇒ different students); add any new students to `students.csv`; if the contest has teams, create or update `database/contests/<contest_folder>-teams/year=<year>/teams.csv` with `team_id`, `team_name`, `student_ids`; you do **not** need to edit `database/students/teams.csv`; then rebuild search data.

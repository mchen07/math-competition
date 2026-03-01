# Find JMO/AMO-only students

The script `scripts/find_jmo_amo_only_students.py` finds students who appear **only** in JMO or AMO contest results and never in any other contest.

## Usage

Run from the repo root:

```bash
# JMO or AMO only (default, all years)
python scripts/find_jmo_amo_only_students.py

# AMO only (all years)
python scripts/find_jmo_amo_only_students.py amo

# JMO only (all years)
python scripts/find_jmo_amo_only_students.py jmo

# Filter by year
python scripts/find_jmo_amo_only_students.py --year 2024

# Multiple years
python scripts/find_jmo_amo_only_students.py --year 2023 --year 2024

# Combine filters: AMO only for 2024
python scripts/find_jmo_amo_only_students.py amo --year 2024

# Write output to file
python scripts/find_jmo_amo_only_students.py -o jmo_amo_only.csv
```

## Output

- **stdout** (default): CSV with columns `name`, `student_id`, `state`, `contests`, `years`, `award`
- **stderr:** Summary line (e.g. `Found 88 students who are only in: amo, jmo.`)

Use `-o` or `--output` to write to a file instead of stdout.

## Notes

- Only US students are included (Canadian students are excluded).
- Students whose names match another student's alias are skipped.
- `amo` and `usamo` are equivalent; `jmo` and `usajmo` are equivalent.

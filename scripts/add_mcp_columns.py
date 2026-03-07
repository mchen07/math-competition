#!/usr/bin/env python3
"""
Add mcp_rank column to all competition result CSVs.

mcp_rank: Normalized rank using the average-rank-for-ties method.
         For award-based competitions, awards are mapped to positional ranks.
         mcp_points is calculated on the fly from mcp_rank when generating data.json.
"""

import csv
import os
import glob



BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'contests')

AWARD_ORDERS = {
    'amo': ['Gold', 'Silver', 'Bronze', 'Honorable Mention'],
    'jmo': ['Top Honors', 'Honors', 'Honorable Mention'],
    'mpfg-olympiad': ['Gold', 'Silver', 'Bronze'],
}

MATHCOUNTS_RANK_ORDER = {
    'S (Semi-finalist)': 'S',
    'Q (Quarter-finalist)': 'Q',
    'C (9-12)': 'C',
}

CONTESTS_CSV = os.path.join(os.path.dirname(BASE_DIR), 'contests', 'contests.csv')


def load_competitions():
    """Load MCP-eligible competitions from contests.csv."""
    competitions = []
    with open(CONTESTS_CSV, 'r', newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not row.get('mcp_tier'):
                continue
            competitions.append({
                'folder': row['folder_name'],
                'mode': row['mcp_mode'],
                'rank_col': row['rank_col'],
            })
    return competitions


def parse_rank_value(val):
    """Try to parse a rank value as a number. Returns (number, is_numeric)."""
    val = val.strip()
    if not val or val == '0':
        return None, False
    cleaned = val.replace(' (tie)', '')
    try:
        return int(cleaned), True
    except ValueError:
        try:
            return float(cleaned), True
        except ValueError:
            return val, False


def assign_mcp_rank_to_groups(groups):
    """
    Given a list of (sort_key, row_indices), assign average-rank positions.
    Returns {row_index: mcp_rank}.
    """
    result = {}
    position = 1
    for _key, indices in groups:
        count = len(indices)
        avg_rank = position + (count - 1) / 2.0
        for idx in indices:
            result[idx] = avg_rank
        position += count
    return result


def process_rank_mode(rows, rank_col):
    """Process competitions with numeric rank column (may have ties)."""
    valid = []
    excluded = []
    for i, row in enumerate(rows):
        raw = row.get(rank_col, '').strip()
        num, is_num = parse_rank_value(raw)
        if is_num and isinstance(num, (int, float)):
            valid.append((num, i))
        else:
            excluded.append(i)

    valid.sort(key=lambda x: x[0])

    groups = []
    if valid:
        current_key = valid[0][0]
        current_indices = [valid[0][1]]
        for rank_val, idx in valid[1:]:
            if rank_val == current_key:
                current_indices.append(idx)
            else:
                groups.append((current_key, current_indices))
                current_key = rank_val
                current_indices = [idx]
        groups.append((current_key, current_indices))

    rank_map = assign_mcp_rank_to_groups(groups)
    N = len(valid)
    return rank_map, N, excluded


def process_rank_mixed_mode(rows, rank_col):
    """Process competitions where rank column has both numbers and 'Honorable Mention'."""
    numeric_rows = []
    hm_rows = []
    excluded = []

    for i, row in enumerate(rows):
        raw = row.get(rank_col, '').strip()
        if raw.lower().startswith('honorable'):
            hm_rows.append(i)
        else:
            num, is_num = parse_rank_value(raw)
            if is_num and isinstance(num, (int, float)):
                numeric_rows.append((num, i))
            else:
                excluded.append(i)

    numeric_rows.sort(key=lambda x: x[0])

    groups = []
    if numeric_rows:
        current_key = numeric_rows[0][0]
        current_indices = [numeric_rows[0][1]]
        for rank_val, idx in numeric_rows[1:]:
            if rank_val == current_key:
                current_indices.append(idx)
            else:
                groups.append((current_key, current_indices))
                current_key = rank_val
                current_indices = [idx]
        groups.append((current_key, current_indices))

    if hm_rows:
        groups.append(('HM', hm_rows))

    rank_map = assign_mcp_rank_to_groups(groups)
    N = len(numeric_rows) + len(hm_rows)
    return rank_map, N, excluded


def process_award_mode(rows, rank_col, folder):
    """Process competitions with award tiers (AMO, JMO, MPFG-Olympiad)."""
    award_order = AWARD_ORDERS.get(folder, [])
    award_to_priority = {a: i for i, a in enumerate(award_order)}

    award_groups = {}
    excluded = []
    for i, row in enumerate(rows):
        award = row.get(rank_col, '').strip()
        if award in award_to_priority:
            priority = award_to_priority[award]
            award_groups.setdefault(priority, []).append(i)
        else:
            excluded.append(i)

    groups = [(p, award_groups[p]) for p in sorted(award_groups.keys())]
    rank_map = assign_mcp_rank_to_groups(groups)
    N = sum(len(indices) for _, indices in groups)
    return rank_map, N, excluded


def process_mathcounts_mode(rows, rank_col):
    """Process MathCounts with special rank codes: S, Q, C between numeric ranks."""
    numeric_before = []  # ranks 1-2 etc (before S)
    s_rows = []
    q_rows = []
    c_rows = []
    numeric_after = []   # ranks 13+ etc (after C)
    excluded = []

    for i, row in enumerate(rows):
        raw = row.get(rank_col, '').strip()
        if 'Semi-finalist' in raw:
            s_rows.append(i)
        elif 'Quarter-finalist' in raw:
            q_rows.append(i)
        elif 'C (' in raw or raw.startswith('C '):
            c_rows.append(i)
        else:
            num, is_num = parse_rank_value(raw)
            if is_num and isinstance(num, (int, float)):
                if num <= 2:
                    numeric_before.append((num, i))
                else:
                    numeric_after.append((num, i))
            else:
                excluded.append(i)

    numeric_before.sort(key=lambda x: x[0])
    numeric_after.sort(key=lambda x: x[0])

    groups = []
    # Numeric ranks before special codes
    for rank_val, idx in numeric_before:
        groups.append((rank_val, [idx]))

    if s_rows:
        groups.append(('S', s_rows))
    if q_rows:
        groups.append(('Q', q_rows))
    if c_rows:
        groups.append(('C', c_rows))

    # Numeric ranks after special codes
    if numeric_after:
        current_key = numeric_after[0][0]
        current_indices = [numeric_after[0][1]]
        for rank_val, idx in numeric_after[1:]:
            if rank_val == current_key:
                current_indices.append(idx)
            else:
                groups.append((current_key, current_indices))
                current_key = rank_val
                current_indices = [idx]
        groups.append((current_key, current_indices))

    rank_map = assign_mcp_rank_to_groups(groups)
    N = sum(len(indices) for _, indices in groups)
    return rank_map, N, excluded


def process_file(filepath, comp):
    """Read a results CSV, compute mcp_rank, write back."""
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    if not rows:
        return 0

    rank_col = comp['rank_col']
    mode = comp['mode']

    if mode == 'rank':
        rank_map, N, excluded = process_rank_mode(rows, rank_col)
    elif mode == 'rank_mixed':
        rank_map, N, excluded = process_rank_mixed_mode(rows, rank_col)
    elif mode == 'award':
        rank_map, N, excluded = process_award_mode(rows, rank_col, comp['folder'])
    elif mode == 'mathcounts':
        rank_map, N, excluded = process_mathcounts_mode(rows, rank_col)
    else:
        print(f"  Unknown mode: {mode}")
        return 0

    if 'mcp_points' in fieldnames:
        fieldnames.remove('mcp_points')
    if 'mcp_rank' not in fieldnames:
        fieldnames.append('mcp_rank')

    for i, row in enumerate(rows):
        row.pop('mcp_points', None)
        if i in rank_map:
            row['mcp_rank'] = f'{rank_map[i]:g}'
        else:
            row['mcp_rank'] = ''

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    return N


def main():
    total_files = 0
    total_students = 0

    competitions = load_competitions()

    for comp in competitions:
        folder = comp['folder']
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(folder_path):
            print(f"SKIP {folder}: folder not found")
            continue

        year_dirs = sorted(glob.glob(os.path.join(folder_path, 'year=*')))
        if not year_dirs:
            print(f"SKIP {folder}: no year directories")
            continue

        for year_dir in year_dirs:
            year = os.path.basename(year_dir).replace('year=', '')
            matched_files = sorted(glob.glob(os.path.join(year_dir, 'results*.csv')))
            for filepath in matched_files:
                fname = os.path.basename(filepath)
                n = process_file(filepath, comp)
                if n > 0:
                    print(f"  {folder}/year={year}/{fname}: {n} students ranked")
                    total_files += 1
                    total_students += n

    print(f"\nDone: {total_files} files processed, {total_students} total student-rankings")


if __name__ == '__main__':
    main()

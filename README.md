# math-competition
Math Competition Records

## Student search (GitHub Pages)

A static frontend lets you search students by name and view their competition records.

### Build data

From the repo root:

```bash
python scripts/build_search_data.py
```

This writes `docs/data.json` from the `database/` CSVs.

### Run locally

Serve the `docs` folder (e.g. `python -m http.server 8000 --directory docs` or any static server). Open the site and use the search box.

### Deploy to GitHub Pages

1. In the repo: **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Choose the branch (e.g. `main`) and set the folder to **/docs**.
4. Save. The site will be at `https://<username>.github.io/math-competition/`.

After updating the database, run `python scripts/build_search_data.py` and commit the updated `docs/data.json`.

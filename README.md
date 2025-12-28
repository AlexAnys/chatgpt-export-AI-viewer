# Chat Archive Atlas

Local-first app for exploring AI conversation exports with search, insights, and clustering.
This repo ships a static dashboard plus a Python data pipeline that turns exports into
markdown + index data for the UI, including a search index.

## Features
- Full-text search across conversation titles + content
- Keyword highlights and topic clusters
- Similar conversation suggestions
- Local notes + stars stored in browser
- Interaction ability report with strengths/gaps and evidence

## Quick start
1) Export your data (see `docs/EXPORTS.md`).
2) Build the app data:
```
python tools/build_data.py --source chatgpt --input /path/to/conversations.json
```
You can also point to the exported ZIP or a folder that contains `conversations.json`.
3) Serve locally:
```
python -m http.server 8766 --directory .
```
4) Open:
```
http://localhost:8766/app/
```

Optional flags:
- `--include-all-nodes` to include all branches in ChatGPT conversations.
- `--skip-interaction` to skip the interaction report.

## Other AI providers
If your provider does not export in ChatGPT format, convert it to the generic JSON
schema in `docs/GENERIC_FORMAT.md`, then run:
```
python tools/build_data.py --source generic --input /path/to/generic.json
```

## Data privacy
All processing is local. The generated data lives in `app/data/` and is ignored by Git.
Do not commit private exports to a public repository.
If you want GitHub Pages, use a small sanitized sample set instead of personal exports.

## GitHub publication
If you want to publish the code:
```
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

To host the app on GitHub Pages, you must include a data set in `app/data/`.
For public repos, use a small, sanitized sample set instead of personal exports.

# Architecture

## Data flow
1) Export data from provider.
2) `tools/build_data.py` converts exports into:
   - `app/data/conversations/*.md`
   - `app/data/index.json`
   - `app/data/search/manifest.json` + shards
   - `app/data/interaction.json`
3) `app/` reads `data/index.json` and lazily loads markdown per conversation.

## Key modules
- `tools/prepare_cursor_browse.py`: ChatGPT export parser -> markdown + index.csv
- `tools/build_insights_index.py`: keyword extraction, clustering, highlights -> index.json
- `tools/build_data.py`: orchestrates the build pipeline
- `app/`: static UI (HTML/CSS/JS)
- `app/interaction.html`: interaction report UI

## Extending to other providers
- Convert their exports to the generic schema in `docs/GENERIC_FORMAT.md`
- Or add a new adapter and emit `index.csv` + `conversations/*.md`

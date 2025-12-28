# Export guide

## ChatGPT (OpenAI)
- Open Settings.
- Navigate to Data Controls.
- Choose Export Data and download the ZIP.
- Extract `conversations.json` from the archive.

Run:
```
python tools/build_data.py --source chatgpt --input /path/to/conversations.json
```

## Other providers
Export your conversation history and convert it to the generic JSON schema in
`docs/GENERIC_FORMAT.md`, then run:
```
python tools/build_data.py --source generic --input /path/to/generic.json
```

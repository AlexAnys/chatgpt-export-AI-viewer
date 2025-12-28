# Generic export format

If your provider does not match the ChatGPT export format, convert to this JSON
schema and pass it to `tools/build_data.py --source generic`.

## JSON schema (array of conversations)
```
[
  {
    "id": "optional-id",
    "title": "Conversation title",
    "created_utc": "2024-01-15 08:30:00Z",
    "updated_utc": "2024-01-15 09:00:00Z",
    "messages": [
      {
        "role": "user",
        "created_utc": "2024-01-15 08:30:00Z",
        "content": "Hello"
      },
      {
        "role": "assistant",
        "created_utc": "2024-01-15 08:30:10Z",
        "content": "Hi!"
      }
    ]
  }
]
```

## Notes
- `created_utc` accepts ISO strings or epoch seconds.
- `content` can be a string or a list of strings; lists are joined with newlines.

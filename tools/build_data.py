#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

from build_insights_index import build_index
from prepare_cursor_browse import build_conversation_files


def format_ts(value):
    if not value:
        return "unknown"
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%SZ"
            )
        except Exception:
            return "unknown"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "unknown"
        if text.endswith("Z") and "T" in text:
            return text.replace("T", " ").replace("+00:00", "Z")
        if re.match(r"\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}Z", text):
            return text
    return "unknown"


def normalize_content(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join([normalize_content(item) for item in content if item])
    return json.dumps(content, ensure_ascii=False)


def iter_generic_conversations(path):
    if path.endswith(".jsonl"):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "conversations" in data:
        data = data["conversations"]
    if not isinstance(data, list):
        raise ValueError("Generic export must be a list of conversations.")
    for item in data:
        yield item


def build_generic_conversation_files(input_path, out_dir):
    conv_dir = os.path.join(out_dir, "conversations")
    os.makedirs(conv_dir, exist_ok=True)

    index_md_path = os.path.join(out_dir, "index.md")
    index_csv_path = os.path.join(out_dir, "index.csv")

    total = 0
    with open(index_md_path, "w", encoding="utf-8") as index_md, open(
        index_csv_path, "w", encoding="utf-8", newline=""
    ) as index_csv:
        writer = csv.writer(index_csv)
        writer.writerow(
            ["index", "title", "created_utc", "updated_utc", "messages", "file", "id"]
        )

        index_md.write("# Conversations Index\n\n")
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        index_md.write(f"Generated: {now}\n\n")
        index_md.write(
            "| # | Title | Created (UTC) | Updated (UTC) | Messages | File |\n"
        )
        index_md.write("|---|---|---|---|---|---|\n")

        for conv in iter_generic_conversations(input_path):
            total += 1
            title = conv.get("title") or "Untitled"
            conv_id = conv.get("id") or conv.get("conversation_id") or ""
            created = format_ts(
                conv.get("created_utc")
                or conv.get("created_at")
                or conv.get("create_time")
            )
            updated = format_ts(
                conv.get("updated_utc")
                or conv.get("updated_at")
                or conv.get("update_time")
            )

            messages = conv.get("messages") or []
            rendered = []
            for msg in messages:
                role = (msg.get("role") or "unknown").strip()
                body = normalize_content(msg.get("content") or msg.get("text"))
                timestamp = format_ts(msg.get("created_utc") or msg.get("created_at"))
                role_label = role
                if timestamp != "unknown":
                    role_label = f"{role} ({timestamp})"
                if body.strip():
                    rendered.append((role_label, body.strip()))

            date_prefix = "unknown"
            if created != "unknown":
                date_prefix = created.split(" ")[0].replace("-", "")

            safe_title = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            safe_title = safe_title or "conv"
            suffix = conv_id.split("-")[-1][:8] if conv_id else f"{total:04d}"
            filename = f"{total:04d}_{date_prefix}_{safe_title}_{suffix}.md"
            rel_path = os.path.join("conversations", filename)
            out_path = os.path.join(conv_dir, filename)

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                if conv_id:
                    f.write(f"- id: {conv_id}\n")
                f.write(f"- created_utc: {created}\n")
                f.write(f"- updated_utc: {updated}\n")
                f.write(f"- messages: {len(rendered)}\n")
                f.write("\n---\n\n")
                for role_label, body in rendered:
                    f.write(f"<!-- MSG role: {role_label} -->\n")
                    f.write(f"### {role_label}\n\n")
                    f.write(f"{body}\n\n")
                    f.write("<!-- /MSG -->\n\n")

            index_md.write(
                f"| {total} | {title} | {created} | {updated} | {len(rendered)} | {rel_path} |\n"
            )
            writer.writerow(
                [total, title, created, updated, len(rendered), rel_path, conv_id]
            )

    return total


def main():
    parser = argparse.ArgumentParser(
        description="Build app data (markdown + index.json) from exports."
    )
    parser.add_argument(
        "--source",
        default="chatgpt",
        choices=["chatgpt", "generic"],
        help="Input export type",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to export file (e.g., conversations.json)",
    )
    parser.add_argument(
        "--out-dir",
        default="app/data",
        help="Output directory for generated data",
    )
    parser.add_argument(
        "--file-root",
        default="data",
        help="File path prefix for app index entries (relative to app root)",
    )
    parser.add_argument(
        "--search-index-dir",
        default=None,
        help="Directory for search index shards (default: <out-dir>/search)",
    )
    parser.add_argument(
        "--search-max-chars",
        type=int,
        default=8000,
        help="Max characters to keep per conversation for search text",
    )
    parser.add_argument(
        "--search-shard-size",
        type=int,
        default=300,
        help="Entries per search shard",
    )
    parser.add_argument(
        "--include-search-text",
        action="store_true",
        help="Include search_text inside index.json (not recommended for large datasets)",
    )
    parser.add_argument(
        "--snippet-len",
        type=int,
        default=240,
        help="Max characters for snippet",
    )
    parser.add_argument(
        "--keep-hidden",
        action="store_true",
        help="Include visually hidden messages (ChatGPT only)",
    )
    parser.add_argument(
        "--keep-system",
        action="store_true",
        help="Include system messages (ChatGPT only)",
    )
    parser.add_argument(
        "--keep-metadata",
        action="store_true",
        help="Include metadata content types like thoughts (ChatGPT only)",
    )
    parser.add_argument(
        "--include-all-nodes",
        action="store_true",
        help="Include all nodes in the conversation tree (ChatGPT only)",
    )
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    if args.source == "chatgpt":
        total = build_conversation_files(
            args.input,
            args.out_dir,
            keep_hidden=args.keep_hidden,
            keep_system=args.keep_system,
            keep_metadata=args.keep_metadata,
            include_all_nodes=args.include_all_nodes,
        )
    else:
        total = build_generic_conversation_files(args.input, args.out_dir)

    csv_path = os.path.join(args.out_dir, "index.csv")
    out_path = os.path.join(args.out_dir, "index.json")
    search_dir = args.search_index_dir
    if search_dir is None:
        search_dir = os.path.join(args.out_dir, "search")
    build_index(
        csv_path,
        args.out_dir,
        out_path,
        args.snippet_len,
        args.file_root,
        search_index_dir=search_dir,
        search_max_chars=args.search_max_chars,
        search_shard_size=args.search_shard_size,
        include_search_text=args.include_search_text,
    )
    print(f"Built {total} conversations into {args.out_dir}")


if __name__ == "__main__":
    main()

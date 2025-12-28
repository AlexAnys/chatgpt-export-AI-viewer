#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone


SKIP_CONTENT_TYPES = {
    "app_pairing_content",
    "reasoning_recap",
    "thoughts",
    "user_editable_context",
}

TOOL_JSON_KEYS = {
    "search_query",
    "response_length",
    "path",
    "args",
    "tool_calls",
    "tool",
    "function",
    "call",
}


def format_ts(ts):
    if not ts:
        return "unknown"
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    except Exception:
        return "unknown"


def slugify(title):
    if not title:
        return "conv"
    text = title.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "conv"


def iter_conversations(path):
    try:
        proc = subprocess.Popen(
            ["jq", "-c", ".[]", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        proc = None

    if proc:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
        err = proc.stderr.read()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"jq failed with code {rc}: {err.strip()}")
        return

    for item in iter_json_array(path):
        yield item


def iter_json_array(path, chunk_size=1024 * 1024):
    decoder = json.JSONDecoder()
    buf = ""
    started = False
    idx = 0
    with open(path, "r", encoding="utf-8") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            buf += chunk
            if not started:
                start = buf.find("[")
                if start == -1:
                    buf = buf[-1:]
                    continue
                idx = start + 1
                started = True

            while True:
                while idx < len(buf) and buf[idx] in " \t\r\n,":
                    idx += 1
                if idx >= len(buf):
                    break
                if buf[idx] == "]":
                    return
                try:
                    obj, end = decoder.raw_decode(buf, idx)
                except json.JSONDecodeError:
                    break
                yield obj
                idx = end
            buf = buf[idx:]

    if not started:
        return
    idx = 0
    while True:
        while idx < len(buf) and buf[idx] in " \t\r\n,":
            idx += 1
        if idx >= len(buf) or buf[idx] == "]":
            break
        try:
            obj, end = decoder.raw_decode(buf, idx)
        except json.JSONDecodeError:
            break
        yield obj
        idx = end


def pick_path(mapping, current_node):
    if current_node in mapping:
        node_id = current_node
    else:
        leaves = [k for k, v in mapping.items() if not v.get("children")]
        if not leaves:
            return []

        def score(node_key):
            msg = mapping.get(node_key, {}).get("message") or {}
            return msg.get("create_time") or 0

        node_id = max(leaves, key=score)

    path = []
    seen = set()
    while node_id and node_id not in seen:
        node = mapping.get(node_id)
        if not node:
            break
        path.append(node)
        seen.add(node_id)
        node_id = node.get("parent")
    path.reverse()
    return path


def render_content(content, keep_metadata=False):
    ctype = content.get("content_type")
    if not ctype:
        return ""

    if ctype in SKIP_CONTENT_TYPES and not keep_metadata:
        return ""

    if ctype == "text":
        parts = content.get("parts") or []
        rendered = []
        for part in parts:
            if isinstance(part, str):
                if part.strip():
                    rendered.append(part)
            else:
                rendered.append(json.dumps(part, ensure_ascii=False))
        return "\n".join(rendered)

    if ctype == "code":
        text = content.get("text") or ""
        if not text.strip():
            return ""
        lang = (content.get("language") or "").strip()
        fence = "```" + (lang if lang else "")
        return f"{fence}\n{text}\n```"

    if ctype == "execution_output":
        return content.get("text") or ""

    if ctype == "multimodal_text":
        parts = content.get("parts") or []
        rendered = []
        for part in parts:
            if isinstance(part, str):
                if part.strip():
                    rendered.append(part)
                continue
            if isinstance(part, dict):
                ptype = part.get("content_type")
                if ptype == "text":
                    text = part.get("text") or ""
                    if text.strip():
                        rendered.append(text)
                elif ptype == "image_asset_pointer":
                    pointer = part.get("asset_pointer") or "image"
                    w = part.get("width")
                    h = part.get("height")
                    dims = f" ({w}x{h})" if w and h else ""
                    rendered.append(f"[image]{dims} {pointer}")
                else:
                    rendered.append(json.dumps(part, ensure_ascii=False))
                continue
            rendered.append(str(part))
        return "\n".join([item for item in rendered if item])

    if keep_metadata:
        return json.dumps(content, ensure_ascii=False, indent=2)

    return ""


def render_message(node, keep_hidden=False, keep_system=False, keep_metadata=False):
    msg = node.get("message")
    if not msg:
        return None
    meta = msg.get("metadata") or {}
    if meta.get("is_visually_hidden_from_conversation") and not keep_hidden:
        return None

    author = msg.get("author") or {}
    role = author.get("role") or "unknown"
    if role == "system" and not keep_system:
        return None

    content = msg.get("content") or {}
    body = render_content(content, keep_metadata=keep_metadata)
    if not body.strip():
        return None
    if is_tool_call_block(body):
        return None

    name = author.get("name")
    role_label = role if not name else f"{role}:{name}"
    ts = msg.get("create_time")
    time_label = format_ts(ts)
    if time_label != "unknown":
        role_label = f"{role_label} ({time_label})"
    return role_label, body


def is_tool_call_block(text):
    stripped = text.strip()
    if not stripped:
        return False
    payload = stripped
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if not lines:
            return False
        fence = lines[0].strip()
        if not fence.startswith("```"):
            return False
        lang = fence[3:].strip().lower()
        if lang and lang != "unknown":
            return False
        if len(lines) < 2:
            return False
        if not lines[-1].strip().startswith("```"):
            return False
        payload = "\n".join(lines[1:-1]).strip()
        if not payload:
            return False
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return False
    if not isinstance(obj, dict):
        return False
    return any(key in obj for key in TOOL_JSON_KEYS)


def build_conversation_files(
    input_path,
    out_dir,
    keep_hidden=False,
    keep_system=False,
    keep_metadata=False,
    include_all_nodes=False,
):
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
        index_md.write(f"Generated: {format_ts(datetime.now(tz=timezone.utc).timestamp())}\n\n")
        index_md.write(
            "| # | Title | Created (UTC) | Updated (UTC) | Messages | File |\n"
        )
        index_md.write("|---|---|---|---|---|---|\n")

        for conv in iter_conversations(input_path):
            total += 1
            title = conv.get("title") or "Untitled"
            conv_id = conv.get("id") or conv.get("conversation_id") or ""
            create_time = format_ts(conv.get("create_time"))
            update_time = format_ts(conv.get("update_time"))

            mapping = conv.get("mapping") or {}
            messages = []
            if include_all_nodes:
                collected = []
                for node_id, node in mapping.items():
                    msg = node.get("message")
                    if not msg:
                        continue
                    rendered = render_message(
                        node,
                        keep_hidden=keep_hidden,
                        keep_system=keep_system,
                        keep_metadata=keep_metadata,
                    )
                    if rendered:
                        created = msg.get("create_time") or 0
                        collected.append((created, node_id, rendered))
                collected.sort(key=lambda item: (item[0], item[1]))
                messages = [entry[2] for entry in collected]
            else:
                path = pick_path(mapping, conv.get("current_node"))
                for node in path:
                    rendered = render_message(
                        node,
                        keep_hidden=keep_hidden,
                        keep_system=keep_system,
                        keep_metadata=keep_metadata,
                    )
                    if rendered:
                        messages.append(rendered)

            date_prefix = "unknown"
            if conv.get("create_time"):
                try:
                    dt = datetime.fromtimestamp(
                        conv["create_time"], tz=timezone.utc
                    )
                    date_prefix = dt.strftime("%Y%m%d")
                except Exception:
                    date_prefix = "unknown"

            slug = slugify(title)
            suffix = conv_id.split("-")[-1][:8] if conv_id else f"{total:04d}"
            filename = f"{total:04d}_{date_prefix}_{slug}_{suffix}.md"
            rel_path = os.path.join("conversations", filename)
            out_path = os.path.join(conv_dir, filename)

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                if conv_id:
                    f.write(f"- id: {conv_id}\n")
                if conv.get("conversation_id"):
                    f.write(f"- conversation_id: {conv.get('conversation_id')}\n")
                f.write(f"- created_utc: {create_time}\n")
                f.write(f"- updated_utc: {update_time}\n")
                f.write(f"- messages: {len(messages)}\n")
                f.write("\n---\n\n")
                for role_label, body in messages:
                    f.write(f"<!-- MSG role: {role_label} -->\n")
                    f.write(f"### {role_label}\n\n")
                    f.write(f"{body}\n\n")
                    f.write("<!-- /MSG -->\n\n")

            index_md.write(
                f"| {total} | {title} | {create_time} | {update_time} | {len(messages)} | {rel_path} |\n"
            )
            writer.writerow(
                [total, title, create_time, update_time, len(messages), rel_path, conv_id]
            )

    return total


def main():
    parser = argparse.ArgumentParser(
        description="Prepare ChatGPT export for browsing in Cursor."
    )
    parser.add_argument(
        "--input",
        default="conversations.json",
        help="Path to conversations.json",
    )
    parser.add_argument(
        "--out-dir",
        default="cursor_browse",
        help="Output directory",
    )
    parser.add_argument(
        "--keep-hidden",
        action="store_true",
        help="Include visually hidden messages",
    )
    parser.add_argument(
        "--keep-system",
        action="store_true",
        help="Include system messages",
    )
    parser.add_argument(
        "--keep-metadata",
        action="store_true",
        help="Include metadata content types like thoughts",
    )
    parser.add_argument(
        "--include-all-nodes",
        action="store_true",
        help="Include all nodes in the conversation tree (not just the current path)",
    )
    args = parser.parse_args()

    total = build_conversation_files(
        args.input,
        args.out_dir,
        keep_hidden=args.keep_hidden,
        keep_system=args.keep_system,
        keep_metadata=args.keep_metadata,
        include_all_nodes=args.include_all_nodes,
    )
    print(f"Processed {total} conversations into {args.out_dir}")


if __name__ == "__main__":
    main()

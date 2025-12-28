#!/usr/bin/env python3
import argparse
import csv
import json
import os
import math
import re
from collections import Counter
from datetime import datetime, timezone


EN_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "to",
    "was",
    "we",
    "were",
    "with",
    "you",
    "your",
    "i",
    "me",
    "my",
    "our",
    "they",
    "them",
    "this",
    "these",
    "those",
    "not",
    "no",
    "yes",
    "can",
    "could",
    "should",
    "would",
    "will",
    "just",
    "also",
    "about",
    "how",
    "what",
    "why",
    "when",
    "where",
    "which",
    "who",
    "whom",
    "more",
    "most",
    "less",
    "least",
    "like",
    "may",
    "time",
    "information",
    "value",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "first",
    "second",
    "third",
    "new",
    "please",
    "thanks",
    "thank",
    "using",
    "used",
    "useful",
    "make",
    "made",
    "get",
    "got",
    "here",
    "key",
    "keys",
    "provide",
    "provided",
    "provides",
    "out",
    "app",
}

ZH_STOPWORDS = {
    "的",
    "了",
    "是",
    "我",
    "你",
    "他",
    "她",
    "它",
    "我们",
    "你们",
    "他们",
    "她们",
    "它们",
    "在",
    "有",
    "和",
    "与",
    "或",
    "以及",
    "并",
    "但",
    "而",
    "就",
    "也",
    "还",
    "很",
    "非常",
    "一个",
    "这个",
    "那个",
    "这些",
    "那些",
    "如果",
    "因为",
    "所以",
    "为什么",
    "如何",
    "什么",
    "怎么",
    "什么样",
    "例如",
    "比如",
    "问题",
    "分钟",
    "小时",
    "时间",
    "以下",
    "是什么",
    "信息",
    "好的",
    "因此",
    "同时",
    "一下",
    "一些",
    "一个人",
    "这种",
    "那种",
    "还有",
    "以及",
    "这里",
    "那里",
    "就是",
    "不会",
    "可以",
    "需要",
    "应该",
    "可能",
    "现在",
    "之前",
    "之后",
    "因为",
    "所以",
    "然后",
    "这样",
    "那样",
}

EN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{1,}")
ZH_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*•]|\d+[\.、])\s*")
HIGHLIGHT_RE = re.compile(
    r"(结论|总结|要点|建议|策略|风险|行动|下一步|计划|目标|决定|复盘|洞察|insight|summary|conclusion|recommend|next step|action|risk|decision)",
    re.IGNORECASE,
)
QUESTION_RE = re.compile(r"[?？]$")
CITE_RE = re.compile(r".*?")
SHORT_ALLOW = {"ai", "ml", "gpt"}
NOISE_TERMS = {
    "null",
    "text",
    "file",
    "content",
    "content_type",
    "expiry_datetime",
    "asset_pointer",
    "metadata",
    "direction",
    "decoding_id",
    "audio",
    "video",
    "tool_audio_direction",
    "search_query",
    "response_length",
    "textdoc_id",
    "loaded",
    "turn",
    "cite",
    "navlist",
    "news",
    "com",
    "www",
    "nan",
    "image",
    "user",
    "team",
    "group",
    "all",
    "only",
    "use",
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

MAX_TEXT_CHARS_FOR_TERMS = 12000
TURN_TOKEN_RE = re.compile(
    r"^turn\d+(?:search|news|view|file|calc|code|media)\d+$", re.IGNORECASE
)
SHORT_ID_RE = re.compile(r"^[a-z]{1,2}\d{1,4}$", re.IGNORECASE)
MIXED_ID_RE = re.compile(r"^[a-z]{1,3}\d{3,}$", re.IGNORECASE)
REQUEST_RE = re.compile(
    r"(请|帮我|帮忙|如何|怎么|为什么|能否|可否|请问|怎么做|how|what|why|can you|could you)",
    re.IGNORECASE,
)
CONTEXT_RE = re.compile(
    r"(背景|情况|我现在|我目前|我在|我是|我的|目标|需求|现状|因为|场景|计划|打算)",
    re.IGNORECASE,
)
CONSTRAINT_RE = re.compile(
    r"(预算|限制|必须|不要|不想|至少|最多|以内|以上|不超过|不高于|不低于|prefer|limit|budget|must|only)",
    re.IGNORECASE,
)
UNIT_RE = re.compile(
    r"\d+\s?(元|美元|￥|¥|%|小时|分钟|天|周|月|年|km|公里|m|mb|gb|k|w|万|usd|rmb|dollar|day|hour|min)",
    re.IGNORECASE,
)
STRUCTURE_RE = re.compile(r"^\s*(?:[-*•]|\d+[\\.、)])", re.MULTILINE)
FEEDBACK_RE = re.compile(
    r"(不对|错误|更正|调整|修改|改成|再|继续|太长|太短|不够|不太|不满意|优化|精简|补充|不是|改一下)",
    re.IGNORECASE,
)
BOUNDARY_RE = re.compile(
    r"(无法|不能|不支持|不便|不会|我不能|我无法|无法访问|无法浏览|没有实时|不具备|无法提供|as an ai|i can't|i cannot|i don't have access|i do not have access)",
    re.IGNORECASE,
)
CLARIFY_RE = re.compile(
    r"(请提供|需要更多|能否提供|请补充|还需要|更多信息|具体一点|进一步说明)",
    re.IGNORECASE,
)

# 这些词可以用于“主题命中”，但不应当作为关键词/主题标签直接展示（太像代码/文件噪声）。
KEYWORD_BLACKLIST = {
    "ts",
    "tsx",
    "js",
    "jsx",
    "json",
    "yml",
    "yaml",
    "md",
    "html",
    "css",
    "svg",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif",
    "const",
    "let",
    "var",
    "import",
    "export",
    "return",
    "async",
    "await",
    "function",
    "class",
    "interface",
    "type",
    "extends",
    "implements",
    "public",
    "private",
    "protected",
    "props",
    "state",
    "node_modules",
    "vite",
    "babel",
    "webpack",
    "eslint",
    "prettier",
}

# 显示友好的别名/归一（会影响主题聚合与关键词展示）
TERM_ALIASES = {
    # AI / 模型
    "ai": "AI",
    "gpt": "GPT",
    "llm": "LLM",
    "openai": "OpenAI",
    "gemini": "Gemini",
    "claude": "Claude",
    "deepseek": "DeepSeek",
    "prompt": "提示词",
    "prompts": "提示词",
    "embedding": "向量",
    "embeddings": "向量",
    "fine-tune": "微调",
    "finetune": "微调",
    "transformer": "Transformer",
    "transformers": "Transformer",
    "人工智能": "AI",
    "大模型": "大模型",
    "机器学习": "机器学习",
    "深度学习": "深度学习",
    "提示词": "提示词",
    # 投资理财
    "investment": "投资",
    "invest": "投资",
    "investing": "投资",
    "portfolio": "投资组合",
    "stock": "股票",
    "stocks": "股票",
    "equity": "股权",
    "bond": "债券",
    "bonds": "债券",
    "etf": "ETF",
    "etfs": "ETF",
    "option": "期权",
    "options": "期权",
    "future": "期货",
    "futures": "期货",
    "finance": "金融",
    "financial": "金融",
    "trading": "交易",
    "trade": "交易",
    "market": "市场",
    "markets": "市场",
    "risk": "风险",
    "returns": "收益",
    "yield": "收益",
    "volatility": "波动",
    "drawdown": "回撤",
    "valuation": "估值",
    "nasdaq": "纳斯达克",
    "sp500": "标普500",
    "s&p": "标普",
    "ibkr": "盈透",
    "data": "数据",
    "dataset": "数据",
    "理财": "理财",
    "投资": "投资",
    "基金": "基金",
    "股票": "股票",
    "债券": "债券",
    "期权": "期权",
    "期货": "期货",
    "资产配置": "资产配置",
    "资本市场": "资本市场",
    "市盈率": "市盈率",
    "现金流": "现金流",
    # 工具/开发
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "python": "Python",
    "react": "React",
    "firebase": "Firebase",
    "github": "GitHub",
    "vscode": "VSCode",
    "cursor": "Cursor",
    "sql": "SQL",
}

# 关键词 chips 希望优先出现的“可筛选入口”
PINNED_KEYWORDS = [
    "投资",
    "理财",
    "基金",
    "股票",
    "债券",
    "ETF",
    "AI",
    "GPT",
    "MBA",
    "编程",
    "开发",
    "运动",
    "睡眠",
]

# 主题规则：把对话稳定聚到“可筛选”的大类里（优先级从上到下）
TOPIC_RULES = [
    (
        "投资理财",
        {
            "投资",
            "理财",
            "基金",
            "股票",
            "债券",
            "ETF",
            "期权",
            "期货",
            "资产配置",
            "收益",
            "风险",
            "回撤",
            "估值",
            "市盈率",
            "现金流",
            "资本市场",
            "金融",
            "交易",
            "纳斯达克",
            "标普500",
            "盈透",
            "美股",
            "港股",
            "A股",
            "比特币",
            "加密",
        },
    ),
    (
        "编程开发",
        {
            "代码",
            "编程",
            "开发",
            "前端",
            "后端",
            "数据库",
            "API",
            "Python",
            "JavaScript",
            "TypeScript",
            "React",
            "Firebase",
            "GitHub",
            "Cursor",
            "VSCode",
            "SQL",
            "Docker",
            "调试",
            "报错",
            "部署",
            "测试",
        },
    ),
    (
        "AI/大模型",
        {
            "AI",
            "GPT",
            "LLM",
            "大模型",
            "机器学习",
            "深度学习",
            "提示词",
            "向量",
            "微调",
            "OpenAI",
            "Gemini",
            "Claude",
            "Transformer",
        },
    ),
    (
        "职场管理",
        {
            "MBA",
            "OKR",
            "管理",
            "领导力",
            "职场",
            "职业",
            "面试",
            "简历",
            "团队",
            "沟通",
            "汇报",
        },
    ),
    (
        "学习教育",
        {
            "学习",
            "课程",
            "作业",
            "论文",
            "考试",
            "申请",
            "学校",
            "大学",
            "留学",
            "课表",
            "学分",
            "项目",
            "study",
            "course",
            "assignment",
            "exam",
            "university",
        },
    ),
    (
        "出行旅行",
        {
            "旅行",
            "行程",
            "路线",
            "攻略",
            "机票",
            "航班",
            "酒店",
            "签证",
            "租车",
            "景点",
            "travel",
            "flight",
            "hotel",
            "visa",
            "itinerary",
        },
    ),
    (
        "生活服务",
        {
            "租房",
            "住房",
            "房东",
            "保险",
            "医疗",
            "银行",
            "税务",
            "购物",
            "餐厅",
            "交通",
            "手机",
            "居住",
            "生活",
            "service",
            "insurance",
            "rent",
            "housing",
            "tax",
        },
    ),
    (
        "健康运动",
        {
            "运动",
            "跑步",
            "健身",
            "训练",
            "睡眠",
            "咖啡",
            "咖啡因",
            "血压",
            "血脂",
            "减脂",
            "心率",
            "营养",
            "HIIT",
        },
    ),
    (
        "软件工具",
        {
            "Mac",
            "Windows",
            "Chrome",
            "Obsidian",
            "Figma",
            "Cursor",
            "VSCode",
            "GitHub",
            "代理",
            "网络",
        },
    ),
]

DOMAIN_ZH_TERMS = {
    # 投资理财核心词，确保能被中文分词命中
    "投资",
    "理财",
    "基金",
    "股票",
    "债券",
    "期权",
    "期货",
    "回撤",
    "估值",
    "市盈率",
    "现金流",
    "资产配置",
    "资本市场",
    "纳斯达克",
    "标普500",
    "美股",
    "港股",
    "A股",
    "加密",
    "比特币",
    # AI/开发常见中文词
    "大模型",
    "提示词",
    "机器学习",
    "深度学习",
    "前端",
    "后端",
    "数据库",
    "调试",
    "报错",
    "部署",
    "测试",
    # 健康
    "咖啡因",
    "血压",
    "血脂",
    "心率",
    # 教育/出行/生活
    "留学",
    "课程",
    "考试",
    "机票",
    "航班",
    "签证",
    "租房",
    "保险",
}

FILE_TOKEN_RE = re.compile(
    r"\b[\w./-]+\.(?:ts|tsx|js|jsx|py|md|json|yml|yaml|css|html|go|rs|java|cpp|c|h)\b",
    re.IGNORECASE,
)


def parse_datetime(value):
    if not value or value == "unknown":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_messages(md_text):
    text = md_text.replace("\r\n", "\n")
    lines = text.split("\n")
    start_idx = 0
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            start_idx = idx + 1
            break
    body = "\n".join(lines[start_idx:])
    messages = []
    if "<!-- MSG role:" in body:
        pattern = re.compile(
            r"<!-- MSG role: (.+?) -->\n(?:### .+?\n\n)?([\s\S]*?)\n<!-- /MSG -->",
            re.MULTILINE,
        )
        for match in pattern.finditer(body):
            role = match.group(1).strip()
            content = match.group(2).strip()
            if content:
                messages.append({"role": role, "body": content})
        return messages

    pattern = re.compile(r"^### (.+?)\n\n([\s\S]*?)(?=\n### |\Z)", re.MULTILINE)
    for match in pattern.finditer(body):
        role = match.group(1).strip()
        content = match.group(2).strip()
        if content:
            messages.append({"role": role, "body": content})
    return messages


def parse_json_line(line):
    if not line or not line.startswith("{") or not line.endswith("}"):
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def normalize_body(text, keep_code=False):
    lines = text.splitlines()
    in_code = False
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code and not keep_code:
            continue
        if not stripped:
            continue
        if stripped.startswith("{") and stripped.endswith("}"):
            obj = parse_json_line(stripped)
            if obj:
                ctype = obj.get("content_type") or ""
                if "transcription" in ctype and obj.get("text"):
                    cleaned_lines.append(str(obj["text"]).strip())
                continue
            continue

        if "sediment://" in stripped:
            continue
        if stripped.startswith("[image]"):
            continue

        cleaned = CITE_RE.sub("", stripped)
        cleaned = LIST_PREFIX_RE.sub("", cleaned).strip()
        if cleaned:
            cleaned_lines.append(cleaned)
    return "\n".join(cleaned_lines)


def extract_text(messages, keep_code=False):
    chunks = []
    for msg in messages:
        normalized = normalize_body(msg["body"], keep_code=keep_code)
        if normalized:
            chunks.append(normalized)
    return "\n".join(chunks)


def ascii_ratio(text):
    if not text:
        return 1.0
    ascii_count = 0
    for ch in text:
        if ord(ch) < 128:
            ascii_count += 1
    return ascii_count / max(1, len(text))


def strip_artifact_lines(text):
    """尽量去除堆栈/补丁摘要/路径等噪声行（不影响 search_text，只影响主题/关键词抽取）。"""
    kept = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        lower = s.lower()
        if "node_modules" in lower or "@babel/parser" in lower:
            continue
        if "<vite-error-overlay" in lower or "plugin:vite" in lower:
            continue
        # 很像“文件改动摘要 / 路径行”
        if FILE_TOKEN_RE.search(s) and (re.search(r"\+\d+", s) or ":" in s):
            continue
        # 超长且几乎全是 ASCII，常见于堆栈/日志/代码输出
        if len(s) >= 160 and ascii_ratio(s) >= 0.85:
            continue
        kept.append(s)
    return "\n".join(kept)


def base_role(role_label):
    if not role_label:
        return ""
    return role_label.split(" ")[0].split(":")[0].strip().lower()


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


def clean_for_metrics(text):
    cleaned = normalize_body(text, keep_code=False)
    cleaned = strip_artifact_lines(cleaned)
    return cleaned.strip()


def analyze_user_message(text):
    compact = re.sub(r"\s+", " ", text).strip()
    char_len = len(compact.replace(" ", ""))
    word_len = len(re.findall(r"[A-Za-z0-9']+", compact))
    has_question = "?" in compact or "？" in compact
    has_request = bool(REQUEST_RE.search(compact))
    has_structure = bool(STRUCTURE_RE.search(compact))
    has_numbers = bool(re.search(r"\d", compact))
    has_constraints = bool(CONSTRAINT_RE.search(compact) or UNIT_RE.search(compact))
    has_context = bool(CONTEXT_RE.search(compact) or char_len >= 35)
    has_feedback = bool(FEEDBACK_RE.search(compact))
    clear = has_question or has_request or has_structure or char_len >= 18 or word_len >= 6
    vague = char_len < 12 and not has_question and not has_constraints and not has_context
    return {
        "text": compact,
        "char_len": char_len,
        "clear": clear,
        "constraint": has_constraints or (has_numbers and char_len >= 12),
        "context": has_context,
        "feedback": has_feedback,
        "vague": vague,
    }


def truncate_text(text, limit=180):
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def push_quote(bucket, quote, limit=60):
    bucket.append(quote)
    if len(bucket) <= limit:
        return
    bucket.sort(key=lambda item: (-item.get("score", 0), item.get("text", "")))
    del bucket[limit:]


def analyze_conversation(messages, file_path, created_utc, totals, quote_buckets, boundary_quotes):
    user_msgs = []
    assistant_msgs = []
    for msg in messages:
        role = base_role(msg.get("role"))
        body = msg.get("body") or ""
        if is_tool_call_block(body):
            continue
        cleaned = clean_for_metrics(body)
        if not cleaned:
            continue
        if role == "user":
            user_msgs.append(cleaned)
        elif role == "assistant":
            assistant_msgs.append(cleaned)

    if not user_msgs and not assistant_msgs:
        return None

    totals["conversations"] += 1
    totals["user_messages"] += len(user_msgs)
    totals["assistant_messages"] += len(assistant_msgs)
    totals["user_chars"] += sum(len(text.replace(" ", "")) for text in user_msgs)
    totals["assistant_chars"] += sum(
        len(text.replace(" ", "")) for text in assistant_msgs
    )

    for text in assistant_msgs:
        if CLARIFY_RE.search(text):
            totals["clarify_hits"] += 1
        if BOUNDARY_RE.search(text):
            push_quote(
                boundary_quotes,
                {
                    "text": truncate_text(text),
                    "file": file_path,
                    "score": len(text),
                },
                limit=40,
            )

    clear_hits = 0
    constraint_hits = 0
    context_hits = 0
    feedback_hits = 0
    vague_hits = 0
    for text in user_msgs:
        metrics = analyze_user_message(text)
        if metrics["clear"]:
            clear_hits += 1
            totals["clarity_hits"] += 1
            push_quote(
                quote_buckets["clarity"],
                {
                    "text": truncate_text(metrics["text"]),
                    "file": file_path,
                    "score": metrics["char_len"],
                },
            )
        if metrics["constraint"]:
            constraint_hits += 1
            totals["constraint_hits"] += 1
            push_quote(
                quote_buckets["constraint"],
                {
                    "text": truncate_text(metrics["text"]),
                    "file": file_path,
                    "score": metrics["char_len"],
                },
            )
        if metrics["context"]:
            context_hits += 1
            totals["context_hits"] += 1
            push_quote(
                quote_buckets["context"],
                {
                    "text": truncate_text(metrics["text"]),
                    "file": file_path,
                    "score": metrics["char_len"],
                },
            )
        if metrics["feedback"]:
            feedback_hits += 1
            totals["feedback_hits"] += 1
            push_quote(
                quote_buckets["feedback"],
                {
                    "text": truncate_text(metrics["text"]),
                    "file": file_path,
                    "score": metrics["char_len"],
                },
            )
        if metrics["vague"]:
            vague_hits += 1
            push_quote(
                quote_buckets["vague"],
                {
                    "text": truncate_text(metrics["text"]),
                    "file": file_path,
                    "score": 100 - metrics["char_len"],
                },
            )

    user_count = max(1, len(user_msgs))
    clarity_rate = clear_hits / user_count
    constraint_rate = constraint_hits / user_count
    context_rate = context_hits / user_count
    feedback_rate = feedback_hits / user_count
    iteration_flag = 1 if len(user_msgs) >= 2 else 0
    if iteration_flag:
        totals["iteration_conversations"] += 1

    score = (
        clarity_rate + constraint_rate + context_rate + feedback_rate + iteration_flag
    ) / 5.0

    return {
        "file": file_path,
        "created_utc": created_utc,
        "user_messages": len(user_msgs),
        "assistant_messages": len(assistant_msgs),
        "clarity_rate": clarity_rate,
        "constraint_rate": constraint_rate,
        "context_rate": context_rate,
        "feedback_rate": feedback_rate,
        "iteration": iteration_flag,
        "score": score,
    }


def compute_cluster_trends(items, interaction_records, min_points=6):
    cluster_points = {}
    for item in items:
        file_path = item.get("file") or ""
        record = interaction_records.get(file_path)
        if not record:
            continue
        dt = parse_datetime(item.get("created_utc") or "")
        if not dt:
            continue
        cluster = item.get("cluster_label") or "其他"
        cluster_points.setdefault(cluster, []).append((dt, record["score"]))

    improving = []
    needs_work = []
    for cluster, points in cluster_points.items():
        if len(points) < min_points:
            continue
        points.sort(key=lambda pair: pair[0])
        mid = len(points) // 2
        if mid == 0 or mid == len(points):
            continue
        early_scores = [score for _, score in points[:mid]]
        late_scores = [score for _, score in points[mid:]]
        early_avg = sum(early_scores) / len(early_scores)
        late_avg = sum(late_scores) / len(late_scores)
        delta = late_avg - early_avg
        entry = {
            "label": cluster,
            "delta": round(delta, 3),
            "early": round(early_avg, 3),
            "recent": round(late_avg, 3),
            "count": len(points),
        }
        if delta >= 0.05:
            improving.append(entry)
        elif delta <= -0.05:
            needs_work.append(entry)

    improving.sort(key=lambda item: (-item["delta"], -item["count"]))
    needs_work.sort(key=lambda item: (item["delta"], -item["count"]))
    return {
        "improving": improving[:4],
        "needs_work": needs_work[:4],
    }


def build_interaction_report(items, interaction_records, totals, quote_buckets, boundary_quotes, generated_utc):
    total_user = totals["user_messages"]
    total_assistant = totals["assistant_messages"]
    total_conversations = totals["conversations"]
    if total_user <= 0:
        return {
            "generated_utc": generated_utc,
            "summary": {},
            "strengths": [],
            "gaps": [],
            "quotes": [],
            "boundaries": [],
            "cluster_trends": {"improving": [], "needs_work": []},
            "method": "未找到可分析的用户消息。",
        }

    summary = {
        "total_conversations": total_conversations,
        "total_user_messages": total_user,
        "clarity_avg": totals["clarity_hits"] / total_user,
        "constraint_rate": totals["constraint_hits"] / total_user,
        "context_rate": totals["context_hits"] / total_user,
        "feedback_rate": totals["feedback_hits"] / total_user,
        "iteration_rate": totals["iteration_conversations"] / max(1, total_conversations),
        "clarification_rate": totals["clarify_hits"] / max(1, total_assistant),
        "avg_user_chars": totals["user_chars"] / total_user,
        "avg_turns": (total_user + total_assistant) / max(1, total_conversations),
    }

    strength_candidates = [
        {
            "label": "问题表达清晰",
            "detail": "多数提问具备明确问题或结构。",
            "metric": summary["clarity_avg"],
            "threshold": 0.55,
        },
        {
            "label": "善于提供约束条件",
            "detail": "经常补充预算、范围或限制。",
            "metric": summary["constraint_rate"],
            "threshold": 0.3,
        },
        {
            "label": "提供背景信息",
            "detail": "能够补充场景与目标。",
            "metric": summary["context_rate"],
            "threshold": 0.3,
        },
        {
            "label": "愿意迭代反馈",
            "detail": "会根据回复提出调整或补充。",
            "metric": summary["feedback_rate"],
            "threshold": 0.12,
        },
        {
            "label": "多轮推进问题",
            "detail": "同一问题会继续追问深化。",
            "metric": summary["iteration_rate"],
            "threshold": 0.4,
        },
    ]
    strengths = [
        {
            "label": item["label"],
            "detail": item["detail"],
            "metric": round(item["metric"], 3),
        }
        for item in strength_candidates
        if item["metric"] >= item["threshold"]
    ]
    strengths.sort(key=lambda item: -item["metric"])
    strengths = strengths[:3]

    gap_candidates = [
        {
            "label": "问题表述偏简略",
            "detail": "可以增加目标或具体场景。",
            "metric": summary["clarity_avg"],
            "threshold": 0.45,
        },
        {
            "label": "约束条件不足",
            "detail": "可补充预算、边界或时间范围。",
            "metric": summary["constraint_rate"],
            "threshold": 0.25,
        },
        {
            "label": "背景信息偏少",
            "detail": "适当补充现状与目标更利于输出。",
            "metric": summary["context_rate"],
            "threshold": 0.25,
        },
        {
            "label": "反馈/迭代不足",
            "detail": "可明确哪些部分需要调整。",
            "metric": summary["feedback_rate"],
            "threshold": 0.1,
        },
        {
            "label": "追问频率偏低",
            "detail": "多轮追问能提升输出质量。",
            "metric": summary["iteration_rate"],
            "threshold": 0.25,
        },
        {
            "label": "AI 需要补充信息",
            "detail": "可一次性提供关键背景。",
            "metric": summary["clarification_rate"],
            "threshold": 0.2,
            "reverse": True,
        },
    ]
    gaps = []
    for item in gap_candidates:
        threshold = item["threshold"]
        metric = item["metric"]
        if item.get("reverse"):
            if metric >= threshold:
                gaps.append(
                    {
                        "label": item["label"],
                        "detail": item["detail"],
                        "metric": round(metric, 3),
                        "delta": round(metric - threshold, 3),
                    }
                )
        else:
            if metric < threshold:
                gaps.append(
                    {
                        "label": item["label"],
                        "detail": item["detail"],
                        "metric": round(metric, 3),
                        "delta": round(threshold - metric, 3),
                    }
                )
    gaps.sort(key=lambda item: item.get("delta", 0), reverse=True)
    gaps = gaps[:3]

    quote_order = [
        ("clarity", "清晰提问"),
        ("constraint", "给出约束"),
        ("context", "补充背景"),
        ("feedback", "迭代反馈"),
        ("vague", "问题偏简略"),
    ]
    quotes = []
    used_files = set()
    for key, label in quote_order:
        bucket = quote_buckets.get(key) or []
        if not bucket:
            continue
        bucket.sort(key=lambda item: (-item.get("score", 0), item.get("text", "")))
        for candidate in bucket:
            if candidate["file"] in used_files:
                continue
            quotes.append(
                {
                    "label": label,
                    "text": candidate["text"],
                    "file": candidate["file"],
                }
            )
            used_files.add(candidate["file"])
            break
        if len(quotes) >= 5:
            break

    boundary_quotes.sort(
        key=lambda item: (-item.get("score", 0), item.get("text", ""))
    )
    boundaries = [
        {"label": "能力边界提示", "text": item["text"], "file": item["file"]}
        for item in boundary_quotes[:4]
    ]

    cluster_trends = compute_cluster_trends(items, interaction_records)

    return {
        "generated_utc": generated_utc,
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "quotes": quotes,
        "boundaries": boundaries,
        "cluster_trends": cluster_trends,
        "method": "启发式分析基于本地对话文本，不上传任何数据。",
    }


def extract_highlights(messages, limit=8):
    candidates = []
    seen = set()
    line_index = 0
    for msg in messages:
        lines = msg["body"].splitlines()
        in_code = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
                line_index += 1
                continue
            if in_code or not stripped:
                line_index += 1
                continue
            if stripped.startswith("{") and stripped.endswith("}"):
                obj = parse_json_line(stripped)
                if obj:
                    ctype = obj.get("content_type") or ""
                    if "transcription" in ctype and obj.get("text"):
                        cleaned = str(obj["text"]).strip()
                    else:
                        line_index += 1
                        continue
                else:
                    line_index += 1
                    continue
            else:
                cleaned = CITE_RE.sub("", stripped)
                cleaned = LIST_PREFIX_RE.sub("", cleaned).strip()
            if len(cleaned) < 6 or len(cleaned) > 180:
                line_index += 1
                continue
            score = 0
            if HIGHLIGHT_RE.search(cleaned):
                score += 2
            if QUESTION_RE.search(cleaned):
                score += 1
            if LIST_PREFIX_RE.match(stripped):
                score += 0.5
            if score > 0 and cleaned not in seen:
                candidates.append((score, line_index, cleaned))
                seen.add(cleaned)
            line_index += 1
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [text for _, _, text in candidates[:limit]]


def tokenize(text):
    # 保留旧接口，改为调用新 tokenizer（兼容其他调用点）
    return tokenize_v2(text, zh_vocab=None)


def normalize_term(term):
    if not term:
        return None
    t = term.strip()
    if not t:
        return None
    # 先统一英文小写做映射，再用映射后的显示形式
    lower = t.lower()
    mapped = TERM_ALIASES.get(lower) or TERM_ALIASES.get(t) or t
    # 归一后再做 stopwords/noise 过滤（英文以 lower 判断）
    mapped_lower = mapped.lower()
    if is_noise_term(mapped):
        return None
    if mapped_lower in EN_STOPWORDS or mapped_lower in NOISE_TERMS:
        return None
    if mapped in ZH_STOPWORDS:
        return None
    if mapped_lower.startswith("http"):
        return None
    if mapped_lower.isdigit():
        return None
    # 太短的英文 token 丢掉（保留白名单）
    if not is_chinese_term(mapped):
        if len(mapped_lower) <= 2 and mapped_lower not in SHORT_ALLOW:
            return None
        if any(ch.isdigit() for ch in mapped_lower) and len(mapped_lower) <= 3:
            return None
    return mapped


def is_noise_term(term):
    if not term:
        return True
    lower = term.lower()
    if lower in NOISE_TERMS:
        return True
    if TURN_TOKEN_RE.match(lower):
        return True
    if SHORT_ID_RE.match(lower):
        return True
    if MIXED_ID_RE.match(lower):
        return True
    return False


def iter_zh_ngrams(seq, min_len=2, max_len=4):
    length = len(seq)
    for n in range(min_len, max_len + 1):
        if length < n:
            continue
        for i in range(0, length - n + 1):
            yield seq[i : i + n]


def build_zh_vocab(texts, min_df=None, max_df_ratio=0.35):
    """用语料自举一个 2~4 字的中文词表，用于最大匹配分词。"""
    df = Counter()
    for text in texts:
        seen = set()
        for seq in ZH_RE.findall(text):
            # 避免超长连续串造成爆炸
            if len(seq) > 180:
                seq = seq[:180]
            for term in iter_zh_ngrams(seq, 2, 4):
                if term in ZH_STOPWORDS:
                    continue
                # 过滤“哈哈哈哈/啊啊啊”这类重复
                if len(set(term)) == 1:
                    continue
                seen.add(term)
        for term in seen:
            df[term] += 1
    total = max(1, len(texts))
    if min_df is None:
        min_df = 2 if total < 80 else 3
    max_df = int(total * max_df_ratio)
    vocab = {t for t, c in df.items() if c >= min_df and c <= max_df}
    vocab |= set(DOMAIN_ZH_TERMS)
    return vocab


def segment_zh(seq, vocab):
    tokens = []
    i = 0
    length = len(seq)
    while i < length:
        matched = None
        for n in (4, 3, 2):
            if i + n > length:
                continue
            cand = seq[i : i + n]
            if cand in vocab and cand not in ZH_STOPWORDS:
                matched = cand
                break
        if matched:
            tokens.append(matched)
            i += len(matched)
        else:
            i += 1
    return tokens


def tokenize_v2(text, zh_vocab):
    tokens = []
    if not text:
        return tokens
    limited = text[:MAX_TEXT_CHARS_FOR_TERMS]

    for word in EN_RE.findall(limited):
        w = normalize_term(word)
        if not w:
            continue
        tokens.append(w)

    # 中文：用语料词表做最大匹配分词（比 4 字切块更稳）
    for seq in ZH_RE.findall(limited):
        if seq in ZH_STOPWORDS:
            continue
        if not zh_vocab:
            # 没有词表时，退化成 n-gram，避免空关键词
            for term in iter_zh_ngrams(seq, 2, 4):
                mapped = normalize_term(term)
                if mapped:
                    tokens.append(mapped)
            continue
        for term in segment_zh(seq, zh_vocab):
            mapped = normalize_term(term)
            if mapped:
                tokens.append(mapped)
    return tokens


def is_chinese_term(term):
    return any("\u4e00" <= ch <= "\u9fff" for ch in term)


def mix_keywords(counter, limit=40):
    terms = [term for term, _ in counter.most_common()]
    zh_terms = [term for term in terms if is_chinese_term(term)]
    en_terms = [term for term in terms if not is_chinese_term(term)]
    combined = []
    zh_idx = 0
    en_idx = 0
    while len(combined) < limit and (zh_idx < len(zh_terms) or en_idx < len(en_terms)):
        if zh_idx < len(zh_terms):
            combined.append(zh_terms[zh_idx])
            zh_idx += 1
        if len(combined) >= limit:
            break
        if en_idx < len(en_terms):
            combined.append(en_terms[en_idx])
            en_idx += 1
    return combined


def is_good_keyword(term, doc_freq, total_docs):
    if not term:
        return False
    lower = term.lower()
    if lower in KEYWORD_BLACKLIST:
        return False
    if is_noise_term(term):
        return False
    if term in ZH_STOPWORDS:
        return False
    if lower in EN_STOPWORDS or lower in NOISE_TERMS:
        return False
    df = doc_freq.get(term, 0)
    if df < 2:
        return False
    # 过于常见也不当关键词（像“可以/应该/问题”那类）
    if df > int(total_docs * 0.6):
        return False
    # 非中文过短也别当关键词（保留白名单）
    if not is_chinese_term(term) and len(lower) <= 2 and lower not in SHORT_ALLOW:
        return False
    # 过滤明显的代码标识符（camelCase / PascalCase / *_service 等）
    if term.isascii():
        if "_" in term and len(term) >= 6:
            return False
        if term and term[0].islower() and any(ch.isupper() for ch in term[1:]):
            return False
        if term.endswith(("Service", "Panel", "Dashboard", "Interface", "Provider", "Controller", "Manager")):
            return False
    return True


def tfidf_keywords(term_counts, idf, doc_freq, total_docs, limit=8):
    scored = []
    for term, tf in term_counts.items():
        if not is_good_keyword(term, doc_freq, total_docs):
            continue
        if tf <= 0:
            continue
        weight = (1.0 + math.log(tf)) * idf.get(term, 1.0)
        scored.append((weight, tf, term))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [term for _, _, term in scored[:limit]]


def assign_topic_label(term_counts, fallback_keywords, doc_freq, total_docs, min_fallback_df=None):
    # 用小规则优先聚合到“大类”
    # 为了兼容大小写，把 term 统一成 lower 做命中
    lower_counts = Counter()
    for term, count in term_counts.items():
        lower_counts[term.lower()] += count

    best_label = None
    best_score = 0
    for label, triggers in TOPIC_RULES:
        score = 0
        for trig in triggers:
            score += lower_counts.get(trig.lower(), 0)
        if score > best_score:
            best_label = label
            best_score = score
    if best_label and best_score >= 2:
        return best_label

    # 否则尝试用一个“比较常见”的关键词当主题（减少“其他”）
    if min_fallback_df is None:
        min_fallback_df = 3 if total_docs < 100 else max(8, int(total_docs * 0.005))
    for kw in fallback_keywords:
        if not kw:
            continue
        if kw.lower() in KEYWORD_BLACKLIST:
            continue
        if not is_good_keyword(kw, doc_freq, total_docs):
            continue
        if doc_freq.get(kw, 0) >= min_fallback_df:
            return kw
    return "其他"


def write_search_index(out_dir, entries, shard_size, generated_utc):
    os.makedirs(out_dir, exist_ok=True)
    shards = []
    if shard_size <= 0:
        shard_size = len(entries) or 1
    for idx in range(0, len(entries), shard_size):
        shard_entries = entries[idx : idx + shard_size]
        name = f"search_{idx // shard_size:04d}.json"
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            json.dump({"items": shard_entries}, f, ensure_ascii=False)
        shards.append({"file": name, "count": len(shard_entries)})
    manifest = {
        "generated_utc": generated_utc,
        "total": len(entries),
        "shards": shards,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def build_index(
    csv_path,
    root_dir,
    out_path,
    snippet_len,
    file_root,
    search_index_dir=None,
    search_max_chars=8000,
    search_shard_size=300,
    include_search_text=False,
    interaction_out=None,
):
    items = []
    month_counts = Counter()
    term_texts = []
    raw_rows = []
    search_entries = []
    interaction_records = {}
    interaction_totals = {
        "conversations": 0,
        "user_messages": 0,
        "assistant_messages": 0,
        "clarity_hits": 0,
        "constraint_hits": 0,
        "context_hits": 0,
        "feedback_hits": 0,
        "clarify_hits": 0,
        "iteration_conversations": 0,
        "user_chars": 0,
        "assistant_chars": 0,
    }
    quote_buckets = {
        "clarity": [],
        "constraint": [],
        "context": [],
        "feedback": [],
        "vague": [],
    }
    boundary_quotes = []
    csv_dir = os.path.dirname(os.path.abspath(csv_path))
    if not root_dir:
        root_dir = csv_dir

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_rows.append(row)
            rel_file = row.get("file") or ""
            abs_file = os.path.join(root_dir, rel_file)
            messages = []
            if os.path.exists(abs_file):
                with open(abs_file, "r", encoding="utf-8") as conv_file:
                    messages = parse_messages(conv_file.read())

            text_plain = extract_text(messages, keep_code=False)
            search_text = extract_text(messages, keep_code=True)
            search_text = re.sub(r"\s+", " ", search_text).lower().strip()
            if search_max_chars and len(search_text) > search_max_chars:
                search_text = search_text[:search_max_chars]
            snippet = text_plain[:snippet_len].strip()
            highlights = extract_highlights(messages)

            created = row.get("created_utc") or ""
            dt = parse_datetime(created)
            if dt:
                month_counts[dt.strftime("%Y-%m")] += 1

            file_path = os.path.join(file_root, rel_file) if rel_file else ""
            record = analyze_conversation(
                messages,
                file_path.replace("\\", "/"),
                created,
                interaction_totals,
                quote_buckets,
                boundary_quotes,
            )
            if record:
                interaction_records[file_path.replace("\\", "/")] = record

            item = {
                "index": int(row.get("index") or 0),
                "title": row.get("title") or "Untitled",
                "created_utc": created,
                "updated_utc": row.get("updated_utc") or "",
                "messages": int(row.get("messages") or 0),
                "file": file_path.replace("\\", "/"),
                "snippet": snippet,
                "keywords": [],
                "highlights": highlights,
            }
            if include_search_text:
                item["search_text"] = search_text
            items.append(item)
            if search_index_dir is not None:
                search_entries.append(
                    {
                        "file": file_path.replace("\\", "/"),
                        "title": item["title"],
                        "search_text": search_text,
                    }
                )
            term_texts.append(strip_artifact_lines(f"{row.get('title') or ''}\n{text_plain}"))

    # 1) 先自举中文词表，改善中文分词
    zh_vocab = build_zh_vocab(term_texts)

    # 2) 文档词频/文档频率（用于 TF-IDF）
    doc_term_counts = []
    doc_freq = Counter()
    for text in term_texts:
        terms = tokenize_v2(text, zh_vocab=zh_vocab)
        counts = Counter(terms)
        doc_term_counts.append(counts)
        doc_freq.update(counts.keys())

    total_docs = max(1, len(items))
    idf = {
        term: (math.log((total_docs + 1) / (df + 1)) + 1.0)
        for term, df in doc_freq.items()
    }

    # 3) 每条对话的关键词（TF-IDF）+ 主题（规则优先，关键词兜底）
    for item, counts in zip(items, doc_term_counts):
        keywords = tfidf_keywords(counts, idf, doc_freq, total_docs, limit=8)
        item["keywords"] = keywords
        item["cluster_label"] = assign_topic_label(counts, keywords, doc_freq, total_docs)

    cluster_counts = Counter(item.get("cluster_label") or "其他" for item in items)
    clusters = [
        {"label": label, "count": count}
        for label, count in cluster_counts.most_common()
    ]

    # 4) 热词：用“出现于多少条对话”更稳（避免某一两条超长对话拉爆）
    #    只保留可作为关键词的词
    keyword_candidates = [
        term
        for term, _ in doc_freq.most_common()
        if is_good_keyword(term, doc_freq, total_docs)
    ]
    top_terms = []
    for pinned in PINNED_KEYWORDS:
        if pinned in doc_freq and is_good_keyword(pinned, doc_freq, total_docs):
            top_terms.append(pinned)
    # 更偏中文：先取中文，再穿插少量英文/缩写
    zh_terms = [t for t in keyword_candidates if is_chinese_term(t)]
    other_terms = [t for t in keyword_candidates if not is_chinese_term(t)]
    zh_idx = 0
    other_idx = 0
    seen_terms = set(top_terms)
    while len(top_terms) < 40 and (zh_idx < len(zh_terms) or other_idx < len(other_terms)):
        for _ in range(2):
            if zh_idx < len(zh_terms) and len(top_terms) < 40:
                term = zh_terms[zh_idx]
                zh_idx += 1
                if term in seen_terms:
                    continue
                top_terms.append(term)
                seen_terms.add(term)
        if other_idx < len(other_terms) and len(top_terms) < 40:
            term = other_terms[other_idx]
            other_idx += 1
            if term in seen_terms:
                continue
            top_terms.append(term)
            seen_terms.add(term)
    insights = {
        "month_counts": dict(sorted(month_counts.items())),
        "top_keywords": [
            {"term": term, "count": doc_freq.get(term, 0)} for term in top_terms
        ],
        "clusters": clusters[:30],
    }

    generated_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    payload = {
        "generated_utc": generated_utc,
        "total": len(items),
        "items": items,
        "insights": insights,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if search_index_dir is not None:
        write_search_index(search_index_dir, search_entries, search_shard_size, generated_utc)
    if interaction_out:
        interaction_payload = build_interaction_report(
            items,
            interaction_records,
            interaction_totals,
            quote_buckets,
            boundary_quotes,
            generated_utc,
        )
        interaction_dir = os.path.dirname(interaction_out)
        if interaction_dir:
            os.makedirs(interaction_dir, exist_ok=True)
        with open(interaction_out, "w", encoding="utf-8") as f:
            json.dump(interaction_payload, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Build insights index for the browser app.")
    parser.add_argument(
        "--csv",
        default="app/data/index.csv",
        help="Path to index.csv",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Root directory containing conversations (defaults to csv dir)",
    )
    parser.add_argument(
        "--out",
        default="app/data/index.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--file-root",
        default="data",
        help="File path prefix for index.json entries (relative to app root)",
    )
    parser.add_argument(
        "--search-index-dir",
        default="app/data/search",
        help="Directory for search index shards (set to empty to skip)",
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
        "--interaction-out",
        default="app/data/interaction.json",
        help="Output path for interaction analysis JSON (set empty to skip)",
    )
    parser.add_argument(
        "--snippet-len",
        type=int,
        default=240,
        help="Max characters for snippet",
    )
    args = parser.parse_args()

    search_dir = args.search_index_dir or None
    interaction_out = args.interaction_out or None
    build_index(
        args.csv,
        args.root,
        args.out,
        args.snippet_len,
        args.file_root,
        search_index_dir=search_dir,
        search_max_chars=args.search_max_chars,
        search_shard_size=args.search_shard_size,
        include_search_text=args.include_search_text,
        interaction_out=interaction_out,
    )
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

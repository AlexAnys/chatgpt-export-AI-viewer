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

MAX_TEXT_CHARS_FOR_TERMS = 12000

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
    lines = md_text.splitlines()
    start_idx = 0
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            start_idx = idx + 1
            break
    body = "\n".join(lines[start_idx:])
    pattern = re.compile(r"^### (.+?)\n\n([\s\S]*?)(?=\n### |\Z)", re.MULTILINE)
    messages = []
    for match in pattern.finditer(body):
        role = match.group(1).strip()
        text = match.group(2).strip()
        if text:
            messages.append({"role": role, "body": text})
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


def iter_zh_ngrams(seq, min_len=2, max_len=4):
    length = len(seq)
    for n in range(min_len, max_len + 1):
        if length < n:
            continue
        for i in range(0, length - n + 1):
            yield seq[i : i + n]


def build_zh_vocab(texts, min_df=3, max_df_ratio=0.35):
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


def assign_topic_label(term_counts, fallback_keywords, doc_freq, min_fallback_df=12):
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
    for kw in fallback_keywords:
        if not kw:
            continue
        if kw.lower() in KEYWORD_BLACKLIST:
            continue
        if doc_freq.get(kw, 0) >= min_fallback_df:
            return kw
    return "其他"


def build_index(csv_path, root_dir, out_path, snippet_len, file_root):
    items = []
    month_counts = Counter()
    term_texts = []
    raw_rows = []
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
            snippet = text_plain[:snippet_len].strip()
            highlights = extract_highlights(messages)

            created = row.get("created_utc") or ""
            dt = parse_datetime(created)
            if dt:
                month_counts[dt.strftime("%Y-%m")] += 1

            file_path = os.path.join(file_root, rel_file) if rel_file else ""

            items.append(
                {
                    "index": int(row.get("index") or 0),
                    "title": row.get("title") or "Untitled",
                    "created_utc": created,
                    "updated_utc": row.get("updated_utc") or "",
                    "messages": int(row.get("messages") or 0),
                    "file": file_path.replace("\\", "/"),
                    "snippet": snippet,
                    "keywords": [],
                    "search_text": re.sub(r"\s+", " ", search_text).lower().strip(),
                    "highlights": highlights,
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
        item["cluster_label"] = assign_topic_label(counts, keywords, doc_freq)

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

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "total": len(items),
        "items": items,
        "insights": insights,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


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
        "--snippet-len",
        type=int,
        default=240,
        help="Max characters for snippet",
    )
    args = parser.parse_args()

    build_index(args.csv, args.root, args.out, args.snippet_len, args.file_root)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

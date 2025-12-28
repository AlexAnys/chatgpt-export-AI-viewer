# Chat Archive Atlas（中文版）

本项目是一个本地化的对话档案浏览器：把 ChatGPT 或其他 AI 的导出记录转换成可搜索、可聚类、可标注的静态看板，并提供「交互能力」分析报告。

## 功能
- 全文搜索（标题 + 内容）
- 关键词与主题聚类
- 相似对话推荐
- 本地标星与备注（仅保存在浏览器）
- 交互能力报告（优势/短板 + 证据引用）

## 快速开始
1) 导出你的数据（见 `docs/EXPORTS.md`）。
2) 构建数据：
```
python tools/build_data.py --source chatgpt --input /path/to/conversations.json
```
也可以直接传 ZIP 或包含 `conversations.json` 的文件夹路径。
3) 启动本地服务器：
```
python -m http.server 8766 --directory .
```
4) 打开：
```
http://localhost:8766/app/
```

## 交互报告
交互报告页面：
```
http://localhost:8766/app/interaction.html
```

## 其他 AI 平台
如果导出格式不同，请先转换为通用 JSON（见 `docs/GENERIC_FORMAT.md`），再执行：
```
python tools/build_data.py --source generic --input /path/to/generic.json
```

## 常用参数
- `--include-all-nodes`：包含 ChatGPT 对话树所有分支。
- `--skip-interaction`：跳过交互报告输出。

## 隐私与发布
所有处理均在本地完成；生成的数据位于 `app/data/`，默认已被 `.gitignore` 忽略。
如果要公开发布，请使用脱敏样本数据，不要提交真实聊天记录。

## GitHub 发布
```
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

如果要用 GitHub Pages 托管，需要在 `app/data/` 放入一份可公开的样本数据。

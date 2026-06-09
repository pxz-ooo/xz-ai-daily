# ai-content-pipeline

这是第二阶段的最小可运行版本：

1. 生成一篇本地 Markdown 文章
2. 解析 Front Matter
3. 同步到 Notion 数据库

## 目录结构

```text
ai-content-pipeline/
├── .env.example
├── requirements.txt
├── sync_to_notion.py
├── output/
│   └── .gitkeep
└── sources/
    └── daily_paper.py
```

## 你需要准备

- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`

注意：

- `NOTION_DATABASE_ID` 是文章数据库的 ID，不是 `NOTION_PAGE_ID`
- Notion 集成需要已经连接到目标数据库所在页面

## NotionNext 数据库字段

请确保你的 NotionNext 数据库至少有这些字段，字段名保持一致：

- `type`：类型，类型 `Select`
- `title`：标题，类型 `Title`
- `summary`：摘要，类型 `Text`
- `status`：状态，类型 `Select`
- `category`：分类，类型 `Select`
- `tags`：标签，类型 `Multi-select`
- `slug`：链接路径，类型 `Text`
- `date`：日期，类型 `Date`

## 安装依赖

在 PowerShell 里进入这个目录后运行：

```powershell
pip install -r requirements.txt
```

## 配置环境变量

当前 PowerShell 会话中运行：

```powershell
$env:NOTION_TOKEN="你的 Notion Integration Token"
$env:NOTION_DATABASE_ID="你的数据库 ID"
```

也可以先复制 `.env.example` 自己保存一份做记录。

## 运行顺序

```powershell
python .\sources\daily_paper.py
python .\sync_to_notion.py
```

成功后：

- `output/` 下会生成一个 `.md` 文件
- Notion 数据库中会新增一篇文章
- 你再去 Vercel 手动触发一次 redeploy，就能验证网站是否显示

## 下一步扩展

等这一步跑通后，再做下面两件事：

1. 把 `daily_paper.py` 的模拟内容替换成真实抓取逻辑
2. 接上 GitHub Actions 定时执行

# xz-ai-daily

一个最小可运行的 AI 日报流水线：

1. 生成当天的 Markdown 文章
2. 解析 Front Matter
3. 同步到 Notion 数据库
4. 通过 Vercel Deploy Hook 触发站点重新部署

## 目录结构

```text
xz-ai-daily/
|-- .env.example
|-- .github/
|   `-- workflows/
|       |-- daily-content-sync.yml
|       `-- validate-pipeline.yml
|-- output/
|-- sources/
|   `-- daily_paper.py
|-- requirements.txt
|-- sync_to_notion.py
`-- README.md
```

## 本地运行

先安装依赖：

```powershell
pip install -r requirements.txt
```

再配置环境变量：

```powershell
$env:NOTION_TOKEN="your_notion_integration_token"
$env:NOTION_DATABASE_ID="your_notion_database_id"
```

运行生成和同步：

```powershell
python .\sources\daily_paper.py
python .\sync_to_notion.py
```

成功后：

- `output/` 下会生成当天的 Markdown 文件
- Notion 数据库中会新增对应文章

## GitHub Actions

仓库已经包含两个 workflow：

- `.github/workflows/daily-content-sync.yml`
  每天定时生成内容、同步 Notion，并在配置了 Hook 后触发 Vercel 重新部署。
- `.github/workflows/validate-pipeline.yml`
  在 `push` / `pull_request` 时做基础校验，确保 Python 脚本和生成流程可运行。

当前定时任务的 cron 是 `0 1 * * *`，这是 UTC 时间的 `01:00`，对应中国标准时间 `09:00`。

## GitHub Secrets

请在仓库的 `Settings > Secrets and variables > Actions` 中配置这 3 个 Repository secrets：

- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`
- `VERCEL_DEPLOY_HOOK_URL`

其中：

- `NOTION_DATABASE_ID` 是目标数据库 ID，不是页面 ID
- `VERCEL_DEPLOY_HOOK_URL` 来自 Vercel 项目的 Deploy Hooks

## Vercel Deploy Hook

在 Vercel 项目中创建一个 Production Deploy Hook，并把生成的 URL 保存到 GitHub Secret `VERCEL_DEPLOY_HOOK_URL`。

完整操作步骤见 [docs/github-actions-vercel-setup.md](docs/github-actions-vercel-setup.md)。

## Notion 数据库字段

请确认你的 Notion 数据库至少包含这些字段：

- `type`：`Select`
- `title`：`Title`
- `summary`：`Text`
- `status`：`Select`
- `category`：`Select`
- `tags`：`Multi-select`
- `slug`：`Text`
- `date`：`Date`

# GitHub Actions、Secrets 和 Vercel Deploy Hook 配置

## 1. 配置 GitHub Repository Secrets

打开 GitHub 仓库：

`Settings > Secrets and variables > Actions > New repository secret`

依次添加以下 3 个 secrets：

- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`
- `VERCEL_DEPLOY_HOOK_URL`

说明：

- `NOTION_TOKEN`：Notion Integration Token
- `NOTION_DATABASE_ID`：NotionNext 内容数据库 ID
- `VERCEL_DEPLOY_HOOK_URL`：Vercel Deploy Hook 的完整 URL

## 2. 获取 Vercel Deploy Hook

打开 Vercel 项目：

`Project > Settings > Deploy Hooks`

创建建议：

- Hook Name：`github-actions-daily-sync`
- Branch：`main`
- Deploy Type：`Production`

创建完成后，复制生成的 URL，保存到 GitHub Secret `VERCEL_DEPLOY_HOOK_URL`。

## 3. 已配置的 GitHub Actions

仓库内已经提供两个 workflow：

- `.github/workflows/daily-content-sync.yml`
- `.github/workflows/validate-pipeline.yml`

其中：

- `daily-content-sync.yml`：
  每天 `UTC 01:00` 运行，也就是中国标准时间 `09:00`
- `validate-pipeline.yml`：
  在 `push` 和 `pull_request` 时校验脚本是否可运行

## 4. 首次验证方式

建议首次配置后手动执行一次：

`GitHub > Actions > Daily Content Sync > Run workflow`

你应该看到这条链路按顺序完成：

1. 安装 Python 依赖
2. 生成 `output/YYYY-MM-DD-daily-paper.md`
3. 同步到 Notion
4. 触发 Vercel redeploy

## 5. 常见问题

`Missing required GitHub Actions secrets`

- 说明 `NOTION_TOKEN` 或 `NOTION_DATABASE_ID` 没有配置，或者 secret 名字写错了

`VERCEL_DEPLOY_HOOK_URL is not configured, skipping Vercel redeploy.`

- 说明 Notion 同步已经完成，但仓库里还没配置 Deploy Hook

Notion 没有新增文章

- 检查 Notion Integration 是否已经连接到目标数据库
- 检查数据库字段名是否与脚本中使用的字段一致

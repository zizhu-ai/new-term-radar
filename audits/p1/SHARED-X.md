# Shared-X 合约（P1）

名字雷达（本仓库）与 trend-radar 推特日报 **共用同一份 X 拉取结果**，只拉一次，两边只读文件。

## 文件

| 路径 | 谁写 | 谁读 |
|---|---|---|
| `out/x_posts-YYYY-MM-DD-HHMM.json` | 快线拉取 agent（带时间戳的分片） | `X_POSTS_GLOB=out/x_posts-*.json` |
| `out/x_posts-YYYY-MM-DD.json` | 同一 agent：每次成功后 **复制/软链** 为「当日最新」 | 兼容旧 `X_POSTS_FILE`；趋势侧也可读 |

形状与 AIsa `get_twitter_user_last_tweets` 批量结果一致：

```json
{
  "SomeHandle": {"data": {"tweets": [{"text": "...", "likeCount": 0, "url": "...", "createdAt": "..."}]}},
  "missing_accounts": ["HandleThatFailed"],
  "fetched_at": "2026-10-20T03:00:00+08:00"
}
```

- 账号键 = config 里的 handle。
- 允许顶层元数据：`missing_accounts` / `fetched_at` / `partial` / `since_ids`（读侧会忽略非账号键）。
- 部分账号失败也要落盘；把没拉到的写入 `missing_accounts`。

## 环境变量（名字雷达）

| 变量 | 含义 |
|---|---|
| `X_POSTS_GLOB` | 优先。匹配分片，**mtime ≤ 约 30h**（`LOOKBACK_HOURS`）的全部合并；同账号推文按 url/text 去重，后写分片覆盖。 |
| `X_POSTS_FILE` | 回退：单个文件。`scripts/run_box.sh` 在存在 `out/x_posts-$D.json` 时仍会设置。 |

`radar.sources.load_x_posts()` 被 `x_new` 与 `usecases.evidence` 共用。未设置且无文件时才走 AIsa 付费拉取。

## 拉取侧（编排 / 快线 routine，不在本仓库内跑）

1. 账号分 **3 批**，批间隔 **60–90 秒**。
2. 429：先退避 **15 分钟** 再试该批，再失败再 **45 分钟** 一次；仍失败则保存已有账号 + `missing_accounts`。
3. 每个账号尽量记 `since_id`，只拉增量。
4. **不要**走哥飞付费 X；公开 x MCP / 已有额度即可。
5. 名字雷达 `sources`：**有「做」级（named）才推送**；仅有错误不推，但仍写 `--out`，并以非 0 退出。

## 盒子入口

```bash
scripts/run_box.sh sources   # 默认 export X_POSTS_GLOB=out/x_posts-*.json
scripts/run_box.sh daily
```

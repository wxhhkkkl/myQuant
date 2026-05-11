# Quickstart: 个股列表与详情模块

**Date**: 2026-05-11

## Prerequisites

- 项目已按 `specs/001-quant-trading-platform/quickstart.md` 配置完毕
- QMT (国金证券) 客户端已安装，xtquant 可用
- DuckDB `daily_kline` 已有历史K线数据（通过 `init_data.py` 和 `download_kline.py` 导入）
- SQLite `stocks` 表已填充股票基础信息

## Quick Verification

启动应用后访问以下页面验证功能：

### 1. 个股列表页

```
http://localhost:8000/stocks
```

确认：
- 表格显示股票代码、名称、最新价、涨跌幅
- 列头点击可排序（涨跌幅、最新价）
- 搜索框可过滤股票
- "仅看自选"筛选可用
- 底部有分页控件

### 2. 个股详情页

```
http://localhost:8000/stocks/000001.SZ
```

确认：
- 页面显示 K 线图（ECharts 渲染，默认日K）
- 支持切换日K/周K/月K
- 左侧或上方显示行情数据面板（最新价、涨跌幅等9个字段）
- 行情面板有"刷新"按钮

### 3. 自选股操作

```
# 在列表页点击"加自选"按钮
# 确认按钮变为"已自选"
# 筛选"仅看自选"确认只显示已添加股票
# 点击"取消自选"确认移除
```

### 4. 批量更新基础信息

```
# 在列表页点击"更新个股基础信息"
# 确认进度条显示
# 完成后确认结果摘要显示（总数/成功/失败）
```

## Key Files for Development

| File | Purpose |
|------|---------|
| `backend/src/api/stocks.py` | 列表/详情/K线/行情 API 路由 |
| `backend/src/api/watchlist.py` | 自选股 API（批量状态查询） |
| `backend/src/api/data.py` | 数据更新触发 API |
| `backend/src/services/data_service.py` | 分页查询、K线聚合、行情快照 |
| `backend/src/templates/pages/stocks.html` | 个股列表页面模板 |
| `backend/src/templates/pages/stock_detail.html` | 个股详情页面模板 |
| `backend/src/templates/components/stock_table.html` | 列表表格 HTMX 组件 |
| `backend/src/templates/components/stock_kline.html` | K线图容器组件 |
| `backend/src/templates/components/stock_quote.html` | 行情面板组件 |

## Testing

```bash
# 运行本模块测试
pytest tests/unit/test_stock_list.py tests/unit/test_watchlist.py -v
pytest tests/integration/test_stocks_api.py tests/integration/test_data_update.py -v
```

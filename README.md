# myQuant - 个人量化交易平台

基于 Python 的本地量化交易平台，覆盖 **AI选股 → 策略回测 → 实盘交易 → 持仓监控** 完整流程。

## 功能

- **AI 选股** - 智能股票筛选，查看基本面、财务报表、舆情分析和板块信息
- **量化模型** - 首个模型：双均线（MA5/MA20），支持扩展更多策略
- **策略回测** - 完整的回测引擎，含收益率曲线、夏普比率、最大回撤等指标
- **在线交易** - 连接 QMT 执行实盘交易，信号通知、订单管理
- **账户监控** - 实时持仓、盈亏、资金曲线

## 技术栈

| 层 | 技术 |
|---|------|
| 后端框架 | FastAPI + Uvicorn |
| 前端 | Jinja2 + HTMX + Alpine.js + Tailwind CSS |
| 时序数据 | DuckDB |
| 元数据 | SQLite |
| 数据源 | QMT xtdata（主）+ akshare（补充） |
| 技术指标 | TA-Lib |
| 定时任务 | APScheduler |
| 测试 | pytest + pytest-asyncio |

## 项目结构

```
myQuant/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/                 # 路由层
│   │   ├── services/            # 业务逻辑
│   │   ├── models/              # 数据模型
│   │   ├── db/                  # 数据库（DuckDB + SQLite）
│   │   ├── scripts/             # 数据初始化 & 同步脚本
│   │   └── templates/           # Jinja2 模板
│   └── tests/
│       ├── unit/                # 单元测试
│       ├── integration/         # 集成测试
│       └── contract/            # 契约测试
├── frontend/static/             # 静态资源
├── specs/001-quant-trading-platform/  # 设计文档
└── README.md
```

## 快速开始

### 环境要求

- Windows 11
- Python 3.11+
- 国金证券 QMT 客户端（数据与交易）

### 安装

```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r backend/requirements.txt

# 安装 xtquant（从 QMT 客户端目录）
# 路径通常为: QMT安装目录/bin/xtquant/
```

### 初始化数据

```bash
# 确保 QMT 客户端已启动，然后依次运行：
python -m backend.src.scripts.init_data           # 股票列表、行业板块
python -m backend.src.scripts.download_kline      # 全量历史K线
python -m backend.src.scripts.download_financials # 财务报表
python -m backend.src.scripts.sync_supplement     # PE/PB/市值 + 舆情

# 后续每日增量更新
python -m backend.src.scripts.daily_sync
```

### 启动

```bash
uvicorn backend.src.main:app --reload --port 8000
```

浏览器访问 `http://localhost:8000` 即可使用。

### 运行测试

```bash
pytest backend/tests/ -v
```

## 许可

MIT

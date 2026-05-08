# Quickstart: 量化交易平台

**Target**: Windows 11, Python 3.11+

## 环境准备

```bash
# 1. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 2. 安装依赖
pip install fastapi uvicorn jinja2 duckdb pandas numpy akshare httpx TA-Lib apscheduler pytest pytest-asyncio

# 3. 安装 xtquant (QMT数据+交易，必须)
# 从国金证券QMT客户端目录找到 xtquant 并安装
# 通常路径: QMT安装目录/bin/xtquant/

# 4. Tailwind CSS
# 下载: https://github.com/tailwindlabs/tailwindcss/releases
# 运行: tailwindcss -i frontend/static/css/input.css -o frontend/static/css/output.css --watch
```

## 初始化数据

```bash
# 前提: QMT客户端已启动（数据下载需要QMT运行）
# 首次运行需下载全量A股数据（耗时较长，约30-40分钟）
python -m backend.scripts.init_data          # 股票列表、行业板块 (QMT xtdata)
python -m backend.scripts.download_kline     # 全量历史K线 → DuckDB (QMT xtdata)
python -m backend.scripts.download_financials # 财务报表 (QMT xtdata)
python -m backend.scripts.sync_supplement    # PE/PB/市值 + 舆情 (akshare补充)

# 后续每日增量更新 (可由APScheduler定时执行)
python -m backend.scripts.daily_sync         # 增量K线 + 估值刷新 + 舆情拉取
```

## 启动服务

```bash
# 开发模式启动
uvicorn backend.src.main:app --reload --host 127.0.0.1 --port 8000
```

打开浏览器访问 `http://localhost:8000`

## 运行测试

```bash
# 单元测试
pytest backend/tests/unit/ -v

# 集成测试
pytest backend/tests/integration/ -v

# 回测精度验证
pytest backend/tests/unit/test_backtest_engine.py -v
```

## QMT 实盘交易

```bash
# 前提: 国金证券QMT客户端已登录并保持运行
# 启动时会自动尝试连接QMT
uvicorn backend.src.main:app --host 127.0.0.1 --port 8000
```

## 定时任务

APScheduler 会在启动时自动注册以下定时任务：
- **每日数据同步**: 每个交易日 18:07 执行（增量K线 + 估值刷新 + 舆情拉取）
- **信号扫描**: 每个交易日 15:37 执行（对已配置策略的股票运行模型生成交易信号）

---

## 项目结构速览

```
backend/
├── src/
│   ├── main.py          # FastAPI 入口
│   ├── api/             # 路由 (pages + api endpoints)
│   ├── services/        # 业务逻辑
│   │   ├── data_service.py      # 数据采集 (xtdata主 + akshare补充)
│   │   ├── model_service.py     # 量化模型引擎
│   │   ├── backtest_service.py  # 回测引擎
│   │   ├── trade_service.py     # 交易执行(QMT)
│   │   └── account_service.py   # 账户/持仓管理
│   ├── db/
│   │   ├── sqlite.py    # SQLite 连接
│   │   └── duckdb.py    # DuckDB 连接
│   ├── models/          # ORM (SQLite)
│   ├── templates/       # Jinja2
│   └── scripts/         # 数据初始化脚本
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
└── data/                # DuckDB 数据文件 & 缓存
    ├── market.duckdb
    └── app.db
frontend/
└── static/
    ├── css/             # Tailwind 输出
    └── js/              # Alpine.js (minimal)
```

## 开发工作流

1. 写测试 → `pytest backend/tests/unit/test_xxx.py`
2. 写实现 → `backend/src/services/xxx.py`
3. 验证 → 全量 `pytest` + 浏览器手动验证
4. 提交 → `git commit -m "feat: xxx"`

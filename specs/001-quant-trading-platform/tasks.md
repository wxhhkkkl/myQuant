# Tasks: 量化交易平台 (Quant Trading Platform)

**Input**: Design documents from `specs/001-quant-trading-platform/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api.md

**Tests**: Tests are MANDATORY per project constitution (TDD principle). Every user story must include test tasks written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and basic structure

- [x] T001 Create project directory structure per plan.md (backend/src/, backend/tests/, frontend/static/, backend/data/)
- [x] T002 [P] Create backend/requirements.txt with dependencies: fastapi, uvicorn, jinja2, duckdb, pandas, numpy, akshare, httpx, TA-Lib, apscheduler, pytest, pytest-asyncio
- [x] T003 [P] Download and configure Tailwind CSS standalone CLI; create frontend/static/css/input.css with @tailwind directives
- [x] T004 [P] Create frontend/static/js/ with empty app.js placeholder; add ECharts CDN reference
- [x] T005 [P] Create backend/src/config.py with environment variables: DB_PATH, DUCKDB_PATH, QMT_PATH, DATA_DIR, LOG_LEVEL
- [x] T006 [P] Create .gitignore with Python, DuckDB, SQLite, Tailwind output, and .venv patterns

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 [P] Implement DuckDB connection manager (read_only pool + write connection) in backend/src/db/duckdb.py
- [x] T008 [P] Implement SQLite connection manager (sqlite3 with WAL mode) in backend/src/db/sqlite.py
- [x] T009 [P] Create stocks SQLite model (stock_code, name, industry, exchange, list_date, is_active) in backend/src/models/stock.py
- [x] T010 [P] Create watchlist SQLite model in backend/src/models/watchlist.py
- [x] T011 [P] Create quant_models SQLite model (model_name, display_name, description, default_params) in backend/src/models/quant_model.py
- [x] T012 [P] Create system_logs SQLite model and logging setup in backend/src/models/log.py; wire Python logging to SQLite
- [x] T013 Create DuckDB schema initialization script: daily_kline table + indexes in backend/src/db/duckdb_schema.py
- [x] T014 Create SQLite table migration runner (init all SQLite tables on startup) in backend/src/db/migrate.py
- [x] T015 Create FastAPI app entry point with static mount, lifespan (DB init), and router includes in backend/src/main.py
- [x] T016 [P] Create Jinja2 base template with Tailwind layout (nav, main content, sidebar) in backend/src/templates/base.html
- [x] T017 [P] Implement global error handler (404/500) and structured JSON error response in backend/src/api/errors.py
- [x] T018 [P] Setup APScheduler for periodic tasks (daily data sync, signal scanning) in backend/src/scheduler.py

**Checkpoint**: Foundation ready — FastAPI app starts, DBs connect, base template renders, user story implementation can begin

---

## Phase 3: User Story 1 — 股票研究与AI选股 (Priority: P1) 🎯 MVP

**Goal**: 用户可搜索股票代码查看基本面/财务/舆情/板块信息，使用AI选股获得推荐列表

**Independent Test**: 启动服务后访问 `/stocks`，搜索 `000001.SZ`，可查看完整股票详情（基本面、财务、舆情、板块四个标签页）；点击"AI选股"获取推荐列表

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T019 [P] [US1] Unit tests for xtdata data fetching functions (get_stock_list, get_kline, get_financials) in backend/tests/unit/test_data_service.py
- [x] T020 [P] [US1] Unit tests for akshare supplement functions (get_valuation, get_news) in backend/tests/unit/test_data_supplement.py
- [x] T021 [P] [US1] Contract test for stock search endpoint GET /api/stocks/search in backend/tests/contract/test_stocks_api.py
- [x] T022 [P] [US1] Contract test for stock detail endpoints (fundamentals/financials/sentiment/sector HTMX) in backend/tests/contract/test_stocks_api.py
- [x] T023 [P] [US1] Unit test for DeepSeek AI client (prompt builder + response parser + mock API) in backend/tests/unit/test_ai_screening.py
- [x] T024 [US1] Integration test: full stock research flow (search → detail → tab navigation) in backend/tests/integration/test_stock_research.py

### Implementation for User Story 1

- [x] T025 [P] [US1] Create stock_fundamentals SQLite model in backend/src/models/fundamental.py
- [x] T026 [P] [US1] Create financial_reports SQLite model in backend/src/models/financial_report.py
- [x] T027 [P] [US1] Create sentiment_news SQLite model in backend/src/models/sentiment_news.py
- [x] T028 [US1] Implement data_service.py: xtdata stock list + K-line + financials + sector fetching in backend/src/services/data_service.py
- [x] T029 [US1] Implement data_service.py supplement: akshare PE/PB/snapshot + news/sentiment fetching in backend/src/services/data_service.py
- [x] T030 [US1] Implement GET /api/stocks/search endpoint (JSON) in backend/src/api/stocks.py
- [x] T031 [US1] Implement GET /stocks page route and GET /stocks/{code} detail page in backend/src/api/stocks.py
- [x] T032 [US1] Implement HTMX partial endpoints: /api/stocks/{code}/fundamentals|financials|sentiment|sector in backend/src/api/stocks.py
- [x] T033 [US1] Implement DeepSeek API client (prompt builder + response parser + recommendation generator) in backend/src/services/ai_screening.py
- [x] T034 [US1] Implement POST /api/stocks/ai-picks endpoint: rule engine pre-filter + DeepSeek LLM multi-dimensional analysis in backend/src/api/stocks.py
- [x] T035 [P] [US1] Create stocks list page template (search bar + AI picks button + results) in backend/src/templates/pages/stocks.html
- [x] T036 [P] [US1] Create stock detail page template with tab navigation in backend/src/templates/pages/stock_detail.html
- [x] T037 [P] [US1] Create HTMX component templates (fundamentals, financials, sentiment, sector tabs) in backend/src/templates/components/
- [x] T038 [US1] Implement POST /api/watchlist/add and DELETE /api/watchlist/{code} and GET /api/watchlist in backend/src/api/watchlist.py
- [x] T039 [US1] Create data sync scripts: init_data.py (stock list + sectors via xtdata) in backend/src/scripts/init_data.py
- [x] T040 [US1] Create data sync scripts: download_kline.py (bulk K-line → DuckDB) in backend/src/scripts/download_kline.py
- [x] T041 [US1] Create data sync scripts: download_financials.py (financial reports via xtdata) in backend/src/scripts/download_financials.py
- [x] T042 [US1] Create data sync scripts: sync_supplement.py (PE/PB/valuation + news via akshare) in backend/src/scripts/sync_supplement.py

**Checkpoint**: At this point, User Story 1 should be fully functional — stock search, detail with 4 tabs, AI screening, watchlist all work

---

## Phase 4: User Story 2 — 双均线量化模型与回测 (Priority: P2)

**Goal**: 用户可运行双均线模型回测，查看收益率、交易明细等结果；模型框架可扩展

**Independent Test**: 访问 `/models` 选择双均线模型，配置参数(5/20)，选股设定时间范围，运行回测，查看收益曲线和交易明细

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T043 [P] [US2] Unit tests for MA5/MA20 calculation and crossover signal logic in backend/tests/unit/test_ma_cross.py
- [x] T044 [P] [US2] Unit tests for backtest engine (single stock, known data, verify return accuracy <1%) in backend/tests/unit/test_backtest_engine.py
- [x] T045 [P] [US2] Contract test for POST /api/backtest/run endpoint in backend/tests/contract/test_backtest_api.py
- [x] T046 [US2] Integration test: full backtest flow (configure → run → view results → view trades) in backend/tests/integration/test_backtest_flow.py

### Implementation for User Story 2

- [x] T047 [P] [US2] Create strategy_configs SQLite model in backend/src/models/strategy_config.py
- [x] T048 [P] [US2] Create backtest_results and backtest_trades DuckDB tables in backend/src/db/duckdb_schema.py (extend T013)
- [x] T049 [US2] Implement model_service.py: base QuantModel class + MaCrossModel (MA5/MA20 window function calc + signal generation) in backend/src/services/model_service.py
- [x] T050 [US2] Implement backtest_service.py: backtest engine (daily iteration with buy/sell state machine) in backend/src/services/backtest_service.py
- [x] T051 [US2] Implement model registry seeder (register ma_cross model with default params) in backend/src/services/model_service.py
- [x] T052 [US2] Implement GET /models page route and GET /api/models (list) in backend/src/api/models.py
- [x] T053 [US2] Implement PUT /api/models/{name}/params endpoint in backend/src/api/models.py
- [x] T054 [US2] Implement POST /api/backtest/run endpoint in backend/src/api/backtest.py
- [x] T055 [US2] Implement GET /api/backtest/{run_id} result and GET /api/backtest/{run_id}/trades in backend/src/api/backtest.py
- [x] T056 [P] [US2] Create models page template (model list + parameter form) in backend/src/templates/pages/models.html
- [x] T057 [P] [US2] Create backtest page template (config form + results + trades table) in backend/src/templates/pages/backtest.html
- [x] T058 [US2] Create HTMX components: backtest result summary, trade detail list, equity curve in backend/src/templates/components/

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently — stock research + MA backtesting

---

## Phase 5: User Story 3 — 在线量化交易 (Priority: P3)

**Goal**: 用户绑定QMT账户，接收模型交易信号，手动确认或手动下单，查看订单状态

**Independent Test**: 连接QMT（模拟盘或实盘），信号产生后确认执行，验证订单完整生命周期（提交→成交）

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T059 [P] [US3] Unit tests for trade_service QMT wrapper (mock xttrader calls) in backend/tests/unit/test_trade_service.py
- [x] T060 [P] [US3] Unit tests for signal generation and confirmation logic in backend/tests/unit/test_trade_signals.py
- [x] T061 [US3] Integration test: signal → confirm → order flow (with mock QMT) in backend/tests/integration/test_trade_flow.py

### Implementation for User Story 3

- [x] T062 [P] [US3] Create trade_signals SQLite model in backend/src/models/trade_signal.py
- [x] T063 [P] [US3] Create orders SQLite model in backend/src/models/order.py
- [x] T064 [US3] Implement QMT connection manager (singleton, heartbeat, auto-reconnect) in backend/src/services/qmt_connector.py
- [x] T065 [US3] Implement trade_service.py: xttrader wrapper (connect, order_stock, cancel, query) with run_in_executor in backend/src/services/trade_service.py
- [x] T066 [US3] Implement signal scanner: run model on subscribed stocks → generate trade_signals rows in backend/src/services/trade_service.py
- [x] T067 [US3] Implement GET /api/signals and POST /api/signals/{id}/confirm|dismiss in backend/src/api/trading.py
- [x] T068 [US3] Implement POST /api/orders (manual order) and GET /api/orders (list) and DELETE /api/orders/{id} in backend/src/api/trading.py
- [x] T069 [US3] Implement GET /trading page route in backend/src/api/trading.py
- [x] T070 [P] [US3] Create trading page template (signals list + order form + order status) in backend/src/templates/pages/trading.html
- [x] T071 [P] [US3] Create HTMX components: signal card, order row, order status badge in backend/src/templates/components/

**Checkpoint**: All user stories 1-3 should now be independently functional — data + backtest + live trading

---

## Phase 6: User Story 4 — 账户持仓与收益监控 (Priority: P4)

**Goal**: 用户查看账户总览、持仓明细、收益曲线，实时监控盈亏

**Independent Test**: 在有持仓数据的情况下，打开 `/account` 页面可看到总资产、持仓列表、收益曲线

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T072 [P] [US4] Unit tests for account_service (position calc, P&L, asset curve) in backend/tests/unit/test_account_service.py
- [x] T073 [US4] Integration test: account overview → positions → curve flow in backend/tests/integration/test_account_flow.py

### Implementation for User Story 4

- [x] T074 [P] [US4] Create positions SQLite model in backend/src/models/position.py
- [x] T075 [P] [US4] Create account_snapshot SQLite model in backend/src/models/account_snapshot.py
- [x] T076 [US4] Implement account_service.py: position sync (from QMT), P&L calc, asset curve aggregation in backend/src/services/account_service.py
- [x] T077 [US4] Implement GET /account page route in backend/src/api/account.py
- [x] T078 [US4] Implement GET /api/account/overview and GET /api/account/positions (HTMX) in backend/src/api/account.py
- [x] T079 [US4] Implement GET /api/account/curve (JSON, asset timeline) in backend/src/api/account.py
- [x] T080 [P] [US4] Create account overview page template in backend/src/templates/pages/account.html
- [x] T081 [P] [US4] Create HTMX components: position table, account summary card, equity curve chart in backend/src/templates/components/

**Checkpoint**: All 4 user stories should now be fully functional — complete quant trading platform

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T082 [P] Handle edge cases: stock suspension/delisting status display, non-trading-hours signal suppression, network error UI feedback
- [x] T083 [P] Add data freshness indicators (last updated timestamp) in stock detail and account pages
- [x] T084 Implement daily_sync.py orchestration script (K-line increment + valuation refresh + news fetch) wired to APScheduler
- [x] T085 Run full test suite and verify all SC-001 through SC-009 success criteria from spec.md
- [x] T086 [P] Code review and simplify: remove dead code, verify no unnecessary abstractions per Constitution II
- [x] T087 Validate quickstart.md instructions by following them in a clean environment

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1) → US2 (P2) → US3 (P3) → US4 (P4) : sequential by priority
  - US3 depends on US2 (needs model signals); US4 depends on US3 (needs trade data)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational — independent (research + data foundation)
- **User Story 2 (P2)**: After US1 — needs stock data and K-line from US1 services
- **User Story 3 (P3)**: After US2 — needs model signals from US2
- **User Story 4 (P4)**: After US3 — needs trade/order data from US3

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Models before services
- Services before API endpoints
- API endpoints before templates
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All tasks marked [P] within a phase can run in parallel
- Phase 2 [P] tasks: T007-T012, T016-T018 (DBs, models, templates, scheduler)
- US1 [P] tests: T019-T022; models: T025-T027; templates: T035-T037
- US2 [P] tests: T043-T045; models: T047-T048; templates: T056-T057

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "Unit tests for data_service.py in backend/tests/unit/test_data_service.py"
Task: "Unit tests for data_supplement.py in backend/tests/unit/test_data_supplement.py"
Task: "Contract tests for stock API in backend/tests/contract/test_stocks_api.py"

# Launch all US1 models together:
Task: "Create stock_fundamentals model in backend/src/models/fundamental.py"
Task: "Create financial_reports model in backend/src/models/financial_report.py"
Task: "Create sentiment_news model in backend/src/models/sentiment_news.py"

# Launch all US1 templates together:
Task: "Create stocks list page template in backend/src/templates/pages/stocks.html"
Task: "Create stock detail page template in backend/src/templates/pages/stock_detail.html"
Task: "Create HTMX component templates in backend/src/templates/components/"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test US1 independently — search stocks, view details with all 4 tabs
5. Can demo/deploy as MVP: stock research tool

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **MVP: Stock Research Tool**
3. Add User Story 2 → Test independently → **v0.2: + Backtesting**
4. Add User Story 3 → Test independently → **v0.3: + Live Trading**
5. Add User Story 4 → Test independently → **v1.0: Full Platform**
6. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests are MANDATORY per Constitution III (TDD): write first → fail → implement → pass
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

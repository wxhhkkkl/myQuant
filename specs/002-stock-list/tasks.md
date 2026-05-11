# Tasks: 个股列表与详情模块

**Input**: Design documents from `specs/002-stock-list/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per project constitution (TDD principle). Every user story must include test tasks written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `backend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure dev environment ready for development

- [x] T001 Verify all existing dependencies installed (FastAPI, xtquant, DuckDB, SQLite, etc.) per `specs/001-quant-trading-platform/quickstart.md`
- [x] T002 Verify DuckDB `daily_kline` and SQLite `stocks`/`watchlist` tables exist by running `backend/src/db/duckdb_schema.py` and `backend/src/db/sqlite.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data service extensions that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Extend `backend/src/services/data_service.py` — add `get_stock_list_with_quotes(page, per_page, sort_by, sort_order, keyword, watchlist_only)` with DuckDB join for latest price and change_pct calculation
- [x] T004 [P] Extend `backend/src/services/data_service.py` — add `get_weekly_kline(code, start, end)` and `get_monthly_kline(code, start, end)` using DuckDB aggregation queries per research.md
- [x] T005 [P] Extend `backend/src/services/data_service.py` — add `get_quote(code)` function using xtdata `get_market_data()` with graceful degradation to latest daily_kline row when xtdata unavailable

**Checkpoint**: Foundation ready — all user stories can now proceed

---

## Phase 3: User Story 1 - 浏览个股列表 (Priority: P1) 🎯 MVP

**Goal**: 用户打开个股列表页面，以分页表格形式浏览所有A股股票（代码、名称、最新价、涨跌幅），支持搜索筛选和按涨跌幅/最新价排序

**Independent Test**: 访问 `/stocks` 页面，能看到分页股票列表表格，包含代码、名称、价格、涨跌幅，列头可点击排序

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T006 [P] [US1] Write unit tests for `get_stock_list_with_quotes` pagination and sorting in `backend/tests/unit/test_stock_list.py`
- [x] T007 [P] [US1] Write integration test for `GET /api/stocks/list` endpoint in `backend/tests/integration/test_stocks_api.py`

### Implementation for User Story 1

- [x] T008 [P] [US1] Add `Stock.list_paginated()` and `Stock.count_all()` methods to `backend/src/models/stock.py`
- [x] T009 [US1] Add `GET /api/stocks/list` endpoint with pagination/sort/search params in `backend/src/api/stocks.py`
- [x] T010 [US1] Rewrite `backend/src/templates/pages/stocks.html` — full stock list page with search box, sortable table headers, pagination controls
- [x] T011 [US1] Create `backend/src/templates/components/stock_table.html` — HTMX partial for table body (returned by `/stocks/table` for sort/page updates)
- [x] T012 [US1] Add `GET /stocks/table` endpoint returning stock_table.html fragment in `backend/src/api/stocks.py`

**Checkpoint**: 个股列表页完整可操作 — 分页浏览、搜索筛选、排序切换全部可用

---

## Phase 4: User Story 2 - 个股详情页 (Priority: P1)

**Goal**: 用户点击股票进入详情页，看到近一年日K线图（ECharts渲染）和实时行情信息（手动刷新），支持切换日K/周K/月K

**Independent Test**: 点击任意股票进入 `/stocks/{code}`，看到 ECharts K线图和行情数据面板

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US2] Write unit tests for `get_weekly_kline` and `get_monthly_kline` aggregation in `backend/tests/unit/test_kline_aggregation.py`
- [ ] T014 [P] [US2] Write integration test for `GET /api/stocks/{code}/kline` with period param in `backend/tests/integration/test_stocks_api.py`

### Implementation for User Story 2

- [ ] T015 [US2] Enhance `GET /api/stocks/{code}/kline` endpoint — add `period` param (daily/weekly/monthly) in `backend/src/api/stocks.py`
- [ ] T016 [US2] Add `GET /api/stocks/{code}/quote` endpoint returning latest market quote JSON in `backend/src/api/stocks.py`
- [ ] T017 [US2] Create `backend/src/templates/components/stock_kline.html` — ECharts candlestick chart container with period selector (日K/周K/月K buttons) and Alpine.js initialization
- [ ] T018 [US2] Create `backend/src/templates/components/stock_quote.html` — market quote data panel (9 fields: 最新价/涨跌幅/涨跌额/成交量/成交额/最高/最低/开盘/昨收) with refresh button
- [ ] T019 [US2] Rewrite `backend/src/templates/pages/stock_detail.html` — integrate K-line chart component, quote panel, stock header, and preserve existing tab components (基本面/财务/舆情/板块)

**Checkpoint**: 详情页完整 — K线图+周期切换+行情面板+手动刷新全部可用

---

## Phase 5: User Story 3 - 自选股管理 (Priority: P2)

**Goal**: 用户在个股列表中可添加/移除自选股，通过"仅看自选"筛选快速查看自选股列表

**Independent Test**: 在列表中对股票执行加自选→切换筛选→取消自选，确认状态正确且持久化

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T020 [P] [US3] Write unit tests for watchlist add/remove/contains_batch in `backend/tests/unit/test_watchlist.py`
- [ ] T021 [US3] Write integration test for watchlist flow (add → list contains → remove → list excludes) in `backend/tests/integration/test_stocks_api.py`

### Implementation for User Story 3

- [ ] T022 [US3] Add `GET /api/watchlist/contains?codes=` batch endpoint in `backend/src/api/watchlist.py`
- [ ] T023 [US3] Update `get_stock_list_with_quotes` in `backend/src/services/data_service.py` — add `in_watchlist` field to each row when watchlist_only filter active
- [ ] T024 [US3] Update `backend/src/templates/components/stock_table.html` — add "加自选/已自选" toggle button per row with HTMX POST/DELETE to existing watchlist API, add "仅看自选" filter checkbox above table
- [ ] T025 [US3] Update `backend/src/templates/pages/stocks.html` — ensure watchlist filter checkbox is wired and list refresh works with watchlist_only param

**Checkpoint**: 自选股功能完整 — 加/删自选、仅看自选筛选、重启后持久化

---

## Phase 6: User Story 4 - 更新个股基础信息 (Priority: P2)

**Goal**: 用户可点击按钮批量更新所有个股基础信息（代码、名称、行业分类），系统后台执行并显示进度和结果摘要

**Independent Test**: 点击"更新个股基础信息"按钮，看到进度状态，完成后显示成功/失败统计

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T026 [US4] Write integration test for update flow (trigger → poll status → check completed result) in `backend/tests/integration/test_data_update.py`

### Implementation for User Story 4

- [x] T027 [US4] Add `run_stock_update()` background function in `backend/src/services/data_service.py` — calls xtdata `get_stock_list_in_sector("沪深A股")` + `get_instrument_detail()` for industry, upserts to `stocks`, tracks progress in module-level dict `_update_status`
- [x] T028 [US4] Create `backend/src/api/data.py` with `POST /api/data/update-stocks` (triggers background thread) and `GET /api/data/update-stocks/status` (returns progress JSON)
- [x] T029 [US4] Register data router in `backend/src/main.py` and mount at root
- [x] T030 [US4] Add update button, progress bar, and result summary UI to `backend/src/templates/pages/stocks.html` using HTMX polling on `/api/data/update-stocks/status`

**Checkpoint**: 批量更新功能完整 — 触发→进度→结果摘要全流程可用

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration verification and edge case handling

- [x] T031 [P] Handle delisted stocks — mark `is_active=0` stocks with "已退市" badge in list table in `backend/src/templates/components/stock_table.html`
- [x] T032 [P] Handle non-trading hours — show "当前为非交易日" notice in `backend/src/templates/components/stock_quote.html` when latest data is from a past trading day
- [x] T033 Verify all spec edge cases: rapid watchlist toggle (debounce), data source unavailable (graceful error), empty watchlist (empty state message)
- [x] T034 Run quickstart.md validation — visit all pages and confirm each acceptance scenario per spec

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 and US2 are both P1, can proceed in parallel or sequentially
  - US3 and US4 are P2, can start after Foundational
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: No dependencies on other stories — pure list functionality
- **US2 (P1)**: No dependencies on other stories — pure detail page functionality
- **US3 (P2)**: Depends on US1 (needs list page UI to add watchlist buttons)
- **US4 (P2)**: Depends on US1 (needs list page UI to add update button)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Data service functions before API endpoints
- API endpoints before templates
- Core implementation before UI integration
- Story complete before moving to next priority

### Parallel Opportunities

- T003, T004, T005 can all run in parallel (different functions, same file — caution with merge conflicts)
- T006, T007 (US1 tests) can run in parallel
- T008 can run in parallel with T006/T007
- T013, T014 (US2 tests) can run in parallel
- T020, T021 (US3 tests) can run in parallel
- After Foundational phase, US1 and US2 can be developed in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for US1 together:
Task: "Write unit tests for get_stock_list_with_quotes in backend/tests/unit/test_stock_list.py"
Task: "Write integration test for GET /api/stocks/list in backend/tests/integration/test_stocks_api.py"

# After tests fail, implement in parallel:
Task: "Add Stock.list_paginated() in backend/src/models/stock.py"
Task: "Create stock_table.html component"
```

---

## Parallel Example: User Story 2

```bash
# Launch all tests for US2 together:
Task: "Write unit tests for kline aggregation in backend/tests/unit/test_kline_aggregation.py"
Task: "Write integration test for kline endpoint in backend/tests/integration/test_stocks_api.py"

# After tests fail, implement components in parallel:
Task: "Create stock_kline.html component"
Task: "Create stock_quote.html component"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (个股列表)
4. **STOP and VALIDATE**: Visit `/stocks`, verify pagination, sorting, search
5. Deploy/demo if ready

### MVP+ (US1 + US2 — both P1, core module)

1. Complete Setup + Foundational
2. Complete US1 (列表) + US2 (详情) in parallel or sequence
3. **STOP and VALIDATE**: Full browse → click → detail flow works
4. This delivers the core "个股列表" module

### Full Delivery

1. MVP+ (US1 + US2)
2. Add US3 (自选股) → Test → Deploy
3. Add US4 (更新基础信息) → Test → Deploy
4. Polish edge cases → Final validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD red-green-refactor)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Existing code paths (fundamentals tabs, AI picks) must remain functional after changes

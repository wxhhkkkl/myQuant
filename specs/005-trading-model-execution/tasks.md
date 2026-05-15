# Tasks: 交易模块模型化执行与监控

**Input**: Design documents from `specs/005-trading-model-execution/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per project constitution (TDD principle). Every user story must include test tasks written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration infrastructure — add new columns to existing tables

- [x] T001 [P] Add `is_running` and `capital` columns to `strategy_configs` table in `backend/src/models/strategy_config.py` (ALTER TABLE + create_table update)
- [x] T002 [P] Add `model_name` column to `positions` table in `backend/src/models/position.py` (ALTER TABLE + create_table update with new UNIQUE constraint on `(stock_code, model_name)`)
- [x] T003 [P] Add `model_name`, `retry_count`, `original_price` columns to `orders` table in `backend/src/models/order.py` (ALTER TABLE + create_table update)
- [x] T004 [P] Add `status` and `stock_name` columns to `trade_signals` table in `backend/src/models/trade_signal.py` (ALTER TABLE + create_table update)
- [x] T005 Register all new model columns in `backend/src/db/migrate.py` (ensure create_table methods are called in order)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data access methods that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Add `set_running(model_name, is_running)` and `get_running_models()` methods to StrategyConfig in `backend/src/models/strategy_config.py`
- [x] T007 Add `upsert_with_model(stock_code, model_name, ...)` and `get_by_model(model_name)` methods to Position in `backend/src/models/position.py`
- [x] T008 Add `all_by_model(model_name)` and status update methods (`fill`, `cancel`, `mark_failed`) to Order in `backend/src/models/order.py`
- [x] T009 Add `update_status(signal_id, status)` method to TradeSignal in `backend/src/models/trade_signal.py`

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 模型展示与启停管理 (Priority: P1)

**Goal**: 用户在交易页面看到所有量化模型列表，点击展开配置面板，编辑参数，启动/停止模型。启动后模型状态持久化，资金和持仓延续。

**Independent Test**: 打开 `/trading` 页面，验证模型卡片显示名称、描述、状态，点击展开配置面板，修改参数并保存，点击启动后状态变为"运行中"，刷新页面后状态保持。

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T010 [P] [US1] Unit test for model listing with run state in `tests/test_trading.py` — test `GET /api/trading/models` returns all models with is_running and capital fields
- [x] T011 [P] [US1] Unit test for model start/stop in `tests/test_trading.py` — test `POST /api/trading/models/{name}/start` and `/stop` toggle is_running and persist config
- [x] T012 [P] [US1] Unit test for model config update in `tests/test_trading.py` — test `PUT /api/trading/models/{name}/config` saves params and validates short < long

### Implementation for User Story 1

- [x] T013 [US1] Add model listing endpoint `GET /api/trading/models` in `backend/src/api/trading.py` (join quant_models + strategy_configs, return model list with run state and capital)
- [x] T014 [US1] Add start endpoint `POST /api/trading/models/{model_name}/start` in `backend/src/api/trading.py` (save config to strategy_configs, set is_running=1)
- [x] T015 [US1] Add stop endpoint `POST /api/trading/models/{model_name}/stop` in `backend/src/api/trading.py` (set is_running=0, preserve capital/positions)
- [x] T016 [US1] Add config update endpoint `PUT /api/trading/models/{model_name}/config` in `backend/src/api/trading.py` (validate params, save without starting)
- [x] T017 [US1] Rewrite trading page template `backend/src/templates/pages/trading.html` — model list layout with Alpine.js for expand/collapse, start/stop buttons, config form
- [x] T018 [US1] Create model config panel component `backend/src/templates/components/model_config_panel.html` — inline expandable form with short/long/position_pct/time_range fields

**Checkpoint**: 模型列表展示、展开配置、启停功能完整可用

---

## Phase 4: User Story 2 - 扫描买入/卖出信号 (Priority: P1)

**Goal**: 用户点击"扫描买入信号"从无持仓标的中筛选金叉信号，点击"扫描卖出信号"从持仓标的中筛选死叉信号。扫描时可选择范围（全量/自选股/行业）。结果列表展示信号详情。

**Independent Test**: 启动双均线模型后，点击"扫描买入信号"（选择自选股范围），验证返回结果为非持仓股的金叉信号；点击"扫描卖出信号"，验证返回结果为持仓股的死叉信号。

### Tests for User Story 2

- [x] T019 [P] [US2] Unit test for scan buy signals in `tests/test_trading.py` — test `POST /api/trading/models/{name}/scan` with signal_type=BUY returns only non-position stocks with golden cross
- [x] T020 [P] [US2] Unit test for scan sell signals in `tests/test_trading.py` — test `POST /api/trading/models/{name}/scan` with signal_type=SELL returns only position stocks with death cross
- [x] T021 [P] [US2] Unit test for scan scope filtering in `tests/test_trading.py` — test scope=watchlist/all/industry returns correct stock subsets

### Implementation for User Story 2

- [x] T022 [US2] Implement `scan_signals(model_name, signal_type, scope, industry)` in `backend/src/services/trade_service.py` — determine stock pool by scope, run MaCrossModel on each, return signals filtered by position/non-position criteria
- [x] T023 [US2] Add scan endpoint `POST /api/trading/models/{model_name}/scan` in `backend/src/api/trading.py` — parse scope param, call scan_signals, return HTML or JSON
- [x] T024 [US2] Create scan results component `backend/src/templates/components/scan_results.html` — list of signals with stock_code, stock_name, signal_price, signal_reason, trade_date, and confirm/ignore buttons
- [x] T025 [US2] Add scan controls (scope selector dropdown + scan buttons) to trading page in `backend/src/templates/pages/trading.html`

**Checkpoint**: 扫描买入/卖出信号功能完整，范围选择可用，结果列表展示正确

---

## Phase 5: User Story 3 - 手动决策与快速下单 (Priority: P1)

**Goal**: 用户在扫描结果中点击"确认买入/卖出"，系统自动创建订单（预填信号价格、计算数量）。已确认信号标记为已确认，防止重复下单。可忽略不需要的信号。

**Independent Test**: 在扫描结果中点击一条买入信号的"确认买入"，验证订单自动创建（价格=信号价，数量=根据可用资金计算），信号状态变为已确认。

### Tests for User Story 3

- [x] T026 [P] [US3] Unit test for confirm signal → create order in `tests/test_trading.py` — test `POST /api/trading/signals/{id}/confirm` creates order with auto-filled price/quantity
- [x] T027 [P] [US3] Unit test for duplicate confirm prevention in `tests/test_trading.py` — test confirming an already-confirmed signal returns error
- [x] T028 [P] [US3] Unit test for ignore signal in `tests/test_trading.py` — test `POST /api/trading/signals/{id}/ignore` marks signal as ignored

### Implementation for User Story 3

- [x] T029 [US3] Implement `confirm_signal(signal_id, quantity_override)` in `backend/src/services/trade_service.py` — calculate buy quantity (available_cash * position_pct / price, round to 100 shares) or sell quantity (full position), create order, update signal status
- [x] T030 [US3] Update confirm endpoint `POST /api/trading/signals/{signal_id}/confirm` in `backend/src/api/trading.py` — wire to confirm_signal service, return order details JSON
- [x] T031 [US3] Update ignore endpoint `POST /api/trading/signals/{signal_id}/ignore` in `backend/src/api/trading.py` — set signal status=ignored
- [x] T032 [US3] Wire confirm/ignore buttons in scan results component `backend/src/templates/components/scan_results.html` — HTMX POST on click, swap row to confirmed/removed state

**Checkpoint**: 信号→订单一键转换，买入卖出自动计算数量，防重复确认

---

## Phase 6: User Story 4 - 订单执行监控与失败重试 (Priority: P2)

**Goal**: 订单提交后持续监控状态。超时未成交自动撤单并以最新价重新下单。重试最多 3 次，超过偏差阈值暂停并提示用户。用户可手动触发重试。

**Independent Test**: 提交订单后观察状态从 submitted → filled；模拟超时场景，验证自动撤单并创建新订单，retry_count 递增。

### Tests for User Story 4

- [x] T033 [P] [US4] Unit test for order monitoring in `tests/test_trading.py` — test orders exceeding 60s in submitted status get cancelled and retried
- [x] T034 [P] [US4] Unit test for max retry limit in `tests/test_trading.py` — test order with retry_count=3 is marked failed instead of retried
- [x] T035 [P] [US4] Unit test for price deviation check in `tests/test_trading.py` — test retry pauses when new price deviates >3% from original

### Implementation for User Story 4

- [x] T036 [US4] Implement `monitor_orders(model_name)` in `backend/src/services/trade_service.py` — query submitted orders, check elapsed time, cancel & retry if >60s, increment retry_count, check price deviation, mark failed if >3 retries
- [x] T037 [US4] Implement `retry_order(order_id)` in `backend/src/services/trade_service.py` — cancel order, get latest price, check deviation, create new order with retry_count+1
- [x] T038 [US4] Add order monitoring endpoint `GET /api/trading/orders/monitor` in `backend/src/api/trading.py` — call monitor_orders, return updated orders HTML
- [x] T039 [US4] Add manual retry endpoint `POST /api/trading/orders/{order_id}/retry` in `backend/src/api/trading.py` — call retry_order, return result JSON
- [x] T040 [US4] Add model-scoped orders endpoint `GET /api/trading/models/{model_name}/orders` in `backend/src/api/trading.py` — return orders HTML filtered by model
- [x] T041 [US4] Update orders component `backend/src/templates/components/orders.html` — show model_name, retry_count, elapsed time, status badges, retry button for failed orders

**Checkpoint**: 订单状态实时更新，超时自动撤单重试，超次/超偏差停止并提示

---

## Phase 7: User Story 5 - 模型收益实时展示 (Priority: P2)

**Goal**: 每个启动模型展示累计收益率、持仓市值、可用资金、总资产。数据随行情更新。模型间资金和持仓独立计算。

**Independent Test**: 启动模型并执行几笔交易后，验证收益面板数据（累计收益、持仓市值等）正确反映交易结果和当前行情。

### Tests for User Story 5

- [x] T042 [P] [US5] Unit test for per-model performance aggregation in `tests/test_trading.py` — test `GET /api/trading/models/{name}/performance` returns correct capital, market_value, total_return
- [x] T043 [P] [US5] Unit test for position P&L calculation in `tests/test_trading.py` — test floating P&L updates with current price changes

### Implementation for User Story 5

- [x] T044 [US5] Implement `get_model_performance(model_name)` in `backend/src/services/trade_service.py` — query strategy_configs for capital, aggregate positions with current prices, calculate total_asset, total_return
- [x] T045 [US5] Add performance endpoint `GET /api/trading/models/{model_name}/performance` in `backend/src/api/trading.py` — return HTML or JSON with capital, market_value, total_asset, total_return, positions list
- [x] T046 [US5] Create model performance component `backend/src/templates/components/model_performance.html` — P&L summary cards (累计收益率, 持仓市值, 可用资金, 总资产) + position list
- [x] T047 [US5] Add performance panel (HTMX-polled, 30s interval) to trading page in `backend/src/templates/pages/trading.html` — shown below each running model's config panel

**Checkpoint**: 每模型独立收益展示，数据随行情刷新

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integration validation and edge case handling

- [x] T048 [P] End-to-end workflow test in `tests/test_trading.py` — full flow: start model → scan buy → confirm signal → verify order → check performance
- [x] T049 [P] Edge case: empty scan results display "暂未发现符合条件的交易信号" in `backend/src/templates/components/scan_results.html`
- [x] T050 [P] Edge case: non-trading-hours alert banner in `backend/src/templates/pages/trading.html` (show warning when outside 9:30-15:00 weekdays)
- [x] T051 Run quickstart.md validation — verify all manual test steps pass in browser
- [x] T052 [P] Remove redundant manual order form from old trading page (kept in `trading.html` only if needed as fallback)
- [x] T053 Update scheduler `_signal_scan_job` in `backend/src/scheduler.py` to use new model instance running state (only scan models with is_running=1)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 → US2 → US3 must be sequential (each builds on the previous)
  - US4 depends on US3 (needs orders to monitor)
  - US5 depends on US1 (needs model instance state) and US3 (needs orders to calculate P&L)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — No dependencies on other stories. **This is the MVP.**
- **User Story 2 (P2)**: Depends on US1 (needs model running state, config panel). Can be independently tested with scan results.
- **User Story 3 (P1)**: Depends on US2 (needs scan results to confirm/ignore). Can be independently tested by confirming signals → checking orders.
- **User Story 4 (P2)**: Depends on US3 (needs orders from confirm flow). Can be independently tested by checking order state transitions.
- **User Story 5 (P2)**: Depends on US1 + US3 (needs model state and orders). Can be independently tested by checking P&L numbers.

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Endpoints before templates
- Story complete before moving to next priority

### Parallel Opportunities

- T001-T004 (all ALTER TABLE additions) can run in parallel
- T010-T012 (US1 tests) can run in parallel
- T019-T021 (US2 tests) can run in parallel
- T026-T028 (US3 tests) can run in parallel
- T033-T035 (US4 tests) can run in parallel
- T042-T043 (US5 tests) can run in parallel
- T049-T050 (Polish edge cases) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for model listing with run state in tests/test_trading.py"
Task: "Unit test for model start/stop in tests/test_trading.py"
Task: "Unit test for model config update in tests/test_trading.py"

# Launch independent implementation tasks:
Task: "Add model listing endpoint GET /api/trading/models in backend/src/api/trading.py"
Task: "Rewrite trading page template backend/src/templates/pages/trading.html"
Task: "Create model config panel component backend/src/templates/components/model_config_panel.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (DB migrations)
2. Complete Phase 2: Foundational (data access methods)
3. Complete Phase 3: User Story 1 (model list + start/stop + config)
4. **STOP and VALIDATE**: Open `/trading`, verify model cards, config panel, start/stop
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → DB ready
2. Add User Story 1 → Model management (MVP!)
3. Add User Story 2 → Signal scanning → Test independently → Deploy/Demo
4. Add User Story 3 → One-click trading → Test independently → Deploy/Demo
5. Add User Story 4 → Order monitoring → Test independently → Deploy/Demo
6. Add User Story 5 → P&L display → Test independently → Deploy/Demo
7. Each story adds value without breaking previous stories

### Recommended Execution Order

Due to sequential dependencies (US1→US2→US3, US4 and US5 parallel after US3):

```
Phase 1 (Setup) → Phase 2 (Foundational) → US1 → US2 → US3 → US4 + US5 (parallel) → Phase 8 (Polish)
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The existing scheduler `_signal_scan_job` in `backend/src/scheduler.py` runs `model.run()` which MaCrossModel does not have — it uses `scan_stock()` instead. T053 addresses this.

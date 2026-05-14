# Tasks: 量化模型模块

**Input**: Design documents from `/specs/004-quant-models/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per project constitution (TDD principle). Every user story must include test tasks written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (DB Schema + Seed Data)

**Purpose**: Extend existing tables for the new feature and register the MA Cross model

- [x] T001 Extend trade_signals table with trade_date and config_id columns in backend/src/models/trade_signal.py
- [x] T002 [P] Extend strategy_configs table with stock_code, position_pct, time_range columns in backend/src/models/strategy_config.py
- [x] T003 [P] Add register_defaults() static method to seed ma_cross model in backend/src/models/quant_model.py
- [x] T004 Register new columns in db/migrate.py (call updated create_table methods)

---

## Phase 2: Foundational (Core MA Logic + Tests)

**Purpose**: Core business logic that ALL user stories depend on. Write tests FIRST, ensure they FAIL, then implement.

**⚠️ CRITICAL**: No user story UI/API work can begin until this phase is complete

### Tests for Core Logic

- [x] T005 [P] Write unit tests for calc_ma (SMA calculation correctness, edge cases) in tests/unit/test_ma_cross.py
- [x] T006 [P] Write unit tests for detect_crossover (golden cross, death cross, no-cross periods) in tests/unit/test_ma_cross.py
- [x] T007 [P] Write unit tests for performance stats (win rate, cumulative return, empty signals) in tests/unit/test_ma_cross.py

### Implementation

- [x] T008 Extend MaCrossModel with scan_full_range() method supporting time_range in backend/src/services/model_service.py
- [x] T009 Implement compute_performance() function (signal count, trade pairs, win rate, cumulative return) in backend/src/services/model_service.py
- [x] T010 Register MaCrossModel on app startup via lifespan event in backend/src/main.py

**Checkpoint**: All unit tests pass. Core MA logic is ready for use by API/UI layers.

---

## Phase 3: User Story 1 - 模型库浏览 (Priority: P1) 🎯 MVP

**Goal**: User visits /models and sees a grid of model cards with name, description, and tags

**Independent Test**: Navigate to /models, verify at least one model card renders with display name and description text

### Implementation for User Story 1

- [x] T011 [US1] Rewrite models.html with card grid layout showing model name, description, default params preview in backend/src/templates/pages/models.html
- [x] T012 [US1] Enhance GET /api/models to return parsed default_params (JSON → dict) in backend/src/api/models.py
- [x] T013 [US1] Add GET /models/{model_name} page route with model intro + config placeholder in backend/src/api/models.py

**Checkpoint**: Model library page shows MA Cross card. Clicking card navigates to /models/ma_cross with model description visible.

---

## Phase 4: User Story 2 - 双均线模型配置与信号生成 (Priority: P1)

**Goal**: User configures stock code, MA periods, position size, time range; system validates and generates BUY/SELL signals

**Independent Test**: POST /api/models/ma_cross/signals with valid params, verify JSON response contains signals array and kline data

### Tests for User Story 2

- [x] T014 [P] [US2] Write integration test for POST /api/models/{name}/signals (valid params, invalid short≥long, insufficient data) in tests/integration/test_model_api.py
- [x] T015 [P] [US2] Write integration test for PUT /api/models/{name}/config (save and retrieve config) in tests/integration/test_model_api.py

### Implementation for User Story 2

- [x] T016 [US2] Create model_detail.html with model intro section, stock picker, MA period inputs, position slider, time range buttons in backend/src/templates/pages/model_detail.html
- [x] T017 [US2] Implement POST /api/models/{name}/signals endpoint (validate params, call MaCrossModel, return kline + MA series + signals + performance) in backend/src/api/models.py
- [x] T018 [US2] Implement PUT /api/models/{name}/config endpoint (save user config to strategy_configs) in backend/src/api/models.py
- [x] T019 [US2] Implement GET /api/models/{name}/detail endpoint (return model metadata + saved config) in backend/src/api/models.py
- [x] T020 [US2] Add stock search/select endpoint integration (use existing /api/stocks for dropdown) in backend/src/templates/pages/model_detail.html

**Checkpoint**: User can select stock, set MA periods (5/20), choose time range, click generate, and see JSON response with signals.

---

## Phase 5: User Story 3 - 信号可视化与统计 (Priority: P2)

**Goal**: K-line chart with MA overlay + buy/sell markers, plus performance stats summary

**Independent Test**: After generating signals, verify chart renders with candlesticks, two MA lines, and buy/sell markers at correct positions

### Implementation for User Story 3

- [x] T021 [US3] Add Alpine.js + ECharts chart rendering in model_detail.html: candlestick + MA lines + scatter markers, following sector_trend.html pattern in backend/src/templates/pages/model_detail.html
- [x] T022 [US3] Add performance stats display section (total signals, trade pairs, win rate %, cumulative return %) in backend/src/templates/pages/model_detail.html
- [x] T023 [US3] Create model_signals.html HTMX component for signal list table with trade_date, signal_type, price in backend/src/templates/components/model_signals.html (inline in model_detail.html)

**Checkpoint**: Full user flow works end-to-end: browse models → select MA Cross → configure → generate → see chart with markers + stats.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, validation, and final verification

- [x] T024 Handle edge cases: insufficient K-line data alert, no signals in time range message, invalid stock code error in backend/src/services/model_service.py and backend/src/api/models.py
- [x] T025 Run quickstart.md verification checklist end-to-end
- [ ] T026 [P] Verify all signal dates align with crossover points (manual check on 1-2 known stocks)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion (can follow US1)
- **User Story 3 (Phase 5)**: Depends on Phase 4 completion (needs signal data to visualize)
- **Polish (Phase 6)**: Depends on all user stories

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2 — no dependency on US2/US3
- **US2 (P1)**: Independent after Phase 2 — can run parallel with US1
- **US3 (P2)**: Depends on US2 (needs signal generation working first)

### Within Each Phase

- Tests MUST be written and FAIL before implementation
- Phase 2: T005-T007 (tests) before T008-T009 (implementation)
- Phase 4: T014-T015 (tests) before T017-T019 (implementation)

### Parallel Opportunities

- T001 & T002 & T003: Different files, can run together
- T005 & T006 & T007: Different test functions in same file (parallel writing)
- T014 & T015: Different test endpoints
- US1 and US2 can be implemented in parallel after Phase 2

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all tests together (write first, ensure they FAIL):
Task: "Write unit tests for calc_ma in tests/unit/test_ma_cross.py"
Task: "Write unit tests for detect_crossover in tests/unit/test_ma_cross.py"
Task: "Write unit tests for performance stats in tests/unit/test_ma_cross.py"

# Then implement together:
Task: "Extend MaCrossModel with scan_full_range() in backend/src/services/model_service.py"
Task: "Implement compute_performance() in backend/src/services/model_service.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup (DB schema changes)
2. Complete Phase 2: Foundational (core MA logic with tests passing)
3. Complete Phase 3: US1 (model library page)
4. Complete Phase 4: US2 (signal generation API + config)
5. **STOP and VALIDATE**: Test US1 + US2 independently
6. Deploy/demo — users can browse models and generate signals

### Incremental Delivery

1. Setup + Foundational → Core logic ready, tests passing
2. Add US1 → Model library visible, MA Cross card clickable
3. Add US2 → Signal generation working via API
4. Add US3 → Full visual experience with chart + stats
5. Polish → Edge cases handled, quickstart verified

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each phase
- Stop at any checkpoint to validate story independently
- Reuse existing QuantModel, StrategyConfig, TradeSignal tables (extend, don't recreate)
- Follow sector_trend.html chart pattern for model_detail.html ECharts

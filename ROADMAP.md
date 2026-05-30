# Roadmap

Trade is an actively developed open-source project for AI-assisted trading research, review, and workflow automation. This roadmap describes the current direction from an internal demo toward a Web-first, deliverable OSS system.

## Phase 1 - Web MVP

Goal: provide a usable Web-first workflow for core research and review tasks.

- Profile-based configuration management
- Article ingestion and processing workspace
- Strategy workspace for pre-market and post-market workflows
- Basic rule pool management
- Basic backtest entry points
- System management for database migration, backup, restore, and operational tasks
- Removal of legacy workflow-only navigation in favor of user-facing product modules

## Phase 2 - Data Platform

Goal: make market data reliable, queryable, and reusable across strategy, backtest, and reporting workflows.

- Store market data and snapshots in database-backed structures
- Support Kaipan data fetch, normalization, and scheduled updates
- Support OHLCV data fetch, backfill, and scheduled updates
- Build reusable market snapshots for strategy review and backtesting
- Improve data validation and recovery workflows

## Phase 3 - Rule Pool and Strategy Review

Goal: improve how rules are generated, reviewed, evaluated, and applied.

- Extract trading rules from public trader articles and research notes
- Allow human review and approval before rules enter the active rule pool
- Track rule versions and strategy versions
- Link rules to candidate snapshots and strategy outputs
- Provide explainable signal attribution and post-market review outputs

## Phase 4 - Backtesting and Regime-aware Evaluation

Goal: make backtest results more transparent and context-aware.

- Add rule-level and strategy-level backtesting workflows
- Compare performance across market regimes
- Evaluate rule applicability under different market conditions
- Avoid diluting regime-specific rule performance with full-period-only evaluation
- Generate reproducible backtest summaries and reports

## Phase 5 - OSS Readiness and Delivery

Goal: make the project easier to understand, maintain, and contribute to.

- Improve documentation and onboarding guides
- Add architecture documentation and workflow diagrams
- Add issue and pull request templates
- Add development setup and contribution instructions
- Improve test coverage and CI workflows
- Perform security review for backend, frontend, workflow automation, and secrets handling

## Current Status

The project is under active development. The current focus is to consolidate existing CLI and workflow capabilities into a clearer Web-first product structure while preserving the existing job and workflow infrastructure where it remains useful.

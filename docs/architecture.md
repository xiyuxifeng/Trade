# Trade Architecture Overview

## High-Level Workflow

```text
Articles / Research Notes
            |
            v
     Article Processing
            |
            v
      Rule Generation
            |
            v
         Rule Pool
            |
            v
 Candidate Snapshot Build
            |
            v
          Strategy
      (Pre/Post Market)
            |
            v
         Backtest
            |
            v
      Reports & Review
```

## Market Data Layer

```text
Market Data
 ├─ Kaipan Data
 │   ├─ Fetch
 │   ├─ Normalize
 │   └─ Scheduled Update
 │
 ├─ OHLCV Data
 │   ├─ Fetch
 │   ├─ Backfill
 │   └─ Scheduled Update
 │
 └─ Market Snapshots
```

## Main Product Modules

- Profiles
- Articles
- Strategy
- Rule Pool
- Backtest
- System Management

## Design Principles

1. Web-first user experience
2. Profile-based configuration management
3. Reproducible research workflows
4. Human review before rule activation
5. Database-backed market data and snapshots
6. Reuse existing job and workflow infrastructure where appropriate
7. Transparent and explainable strategy evaluation

## Future Direction

- Regime-aware backtesting
- Strategy versioning
- Rule applicability analysis
- Improved reporting and review workflows
- Security review and automation support

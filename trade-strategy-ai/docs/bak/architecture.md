# Data Architecture

## Scope

This document covers the Phase 1 data architecture tasks:

- PostgreSQL schema for `blog_articles`, `trade_logs`, `market_data`, and `article_metadata`
- indexing strategy for article crawling, trade replay, and time-series queries
- validation and anomaly detection rules that protect downstream feature extraction

The current article source requirement includes full article content plus user comments. To keep the Phase 1 schema compact, raw comments are stored in `blog_articles.comments_payload`, while comment-derived insights are stored in `article_metadata.comment_insights`.

## Schema Design

### `blog_articles`

Primary use:

- store raw article body from the source site
- preserve crawl-time engagement metrics
- keep a comment snapshot for later NLP and crowd-sentiment analysis

Key fields:

- `source`, `source_article_id`, `source_url`
- `title`, `author_name`, `author_id`
- `published_at`, `crawled_at`
- `content_text`, `content_html`, `summary`
- `view_count`, `like_count`, `bookmark_count`, `comment_count`
- `comments_payload`, `raw_payload`, `content_hash`

Important constraints:

- `source_url` unique to prevent duplicate ingestion
- non-negative engagement metrics
- non-empty title and body

### `article_metadata`

Primary use:

- store normalized outputs from NLP / LLM extraction
- bridge article text and strategy generation
- aggregate comment insights without creating a second comment table in Phase 1

Key fields:

- `article_id` one-to-one reference to `blog_articles`
- `extracted_concepts`, `trading_symbols`, `strategy_rules`, `preconditions`
- `comment_insights`, `raw_llm_output`
- `sentiment_score`, `confidence_score`, `schema_version`, `processed_at`

Important constraints:

- `article_id` unique to guarantee one metadata snapshot per article version
- score ranges bounded to `[-1, 1]` and `[0, 1]`

### `trade_logs`

Primary use:

- store broker or manually imported trades
- align discretionary decisions with article-derived strategy rules

Key fields:

- `source`, `external_id`, `account_id`
- `symbol`, `market`, `side`, `position_side`
- `executed_at`, `quantity`, `price`, `amount`, `fee`
- `strategy_tag`, `rationale`, `article_id`, `raw_payload`

Important constraints:

- positive quantity and price
- non-negative amount and fee
- controlled values for `side` and `position_side`
- optional reference to source article for attribution and alignment analysis

### `market_data`

Primary use:

- store OHLCV candles from AKShare / TuShare
- provide feature engineering and backtest inputs

Key fields:

- `source`, `symbol`, `market`, `timeframe`, `traded_at`
- `open`, `high`, `low`, `close`, `volume`, `turnover`
- `adj_factor`, `is_adjusted`, `indicators`, `raw_payload`

Important constraints:

- uniqueness on `(symbol, market, timeframe, traded_at, source)`
- OHLC consistency rules
- non-negative price and volume fields

## Index Strategy

### Time-series queries

- `market_data(symbol, timeframe, traded_at)` supports candle replay and factor calculation
- `market_data(market, traded_at)` supports broad market scans by session

### Article lookups

- `blog_articles(source, published_at)` supports incremental crawl and backfill
- `blog_articles(author_id, published_at)` supports author-level profiling
- `blog_articles(content_hash)` supports deduplication when mirrored URLs exist

### Trade analysis

- `trade_logs(symbol, executed_at)` supports symbol-centric replay
- `trade_logs(account_id, executed_at)` supports account journals
- `trade_logs(article_id, executed_at)` supports article-to-trade alignment

### Metadata refresh

- `article_metadata(processed_at)` supports reprocessing queues
- `article_metadata(schema_version)` supports staged extractor upgrades

## Validation and Anomaly Detection

### Article validation

- title and body cannot be empty
- body shorter than 80 characters is downgraded for weak extraction quality
- `published_at` cannot be later than `crawled_at`
- `comment_count` and `comments_payload` must stay consistent
- missing `content_hash` is allowed but logged as reduced dedup reliability

### Trade validation

- `amount ~= quantity * price`
- execution time cannot be in the future
- zero fee is informational, not fatal
- if both `external_id` and `raw_payload` are absent, duplicate detection confidence drops

### Market validation

- future candle timestamps are rejected
- flat OHLC with non-zero volume is suspicious
- a price gap above 20% versus previous close is flagged for verification
- volume above 5x recent average is flagged as an anomaly

## Why Comments Stay In `blog_articles`

The upstream requirement is to crawl a single article page and its associated comments. In Phase 1, comments are primarily a contextual signal for:

- crowd sentiment
- disagreement / confirmation intensity
- references to follow-up trades or market catalysts

Because downstream tasks care more about comment-derived signals than relational comment CRUD, storing the raw comment list as a JSON snapshot keeps ingestion simple and resilient to source-site HTML changes. If later phases require thread-level analytics, `comments_payload` can be split into a dedicated `article_comments` table without breaking the current extraction pipeline.

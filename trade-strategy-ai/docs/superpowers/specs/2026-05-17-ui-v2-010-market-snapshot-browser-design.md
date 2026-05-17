# UI-V2-010 Market Snapshot Browser Design

## Goal

Build a formal Market Snapshot Browser for the V2 web workbench so users can inspect snapshots, quality status, sections, and regime features in the browser instead of reading local files or jumping between debug pages.

This task must stay aligned with the final-delivery direction of `UI-V2-002`:

- web-first
- light workbench styling
- Chinese UI copy
- no CLI-centric wording
- no demo-style exploration surface

The browser should make the primary market workflow simple:

1. filter snapshots,
2. select one snapshot,
3. inspect detail in place,
4. jump to Job or Artifact when needed.

## Scope

### In scope

- the canonical `/market` page
- snapshot list browsing
- snapshot detail browsing
- data quality report viewing
- section drill-down
- regime feature viewing when API is available
- links to Job Detail and Artifact Center
- list/detail loading, empty, partial, permission, API unavailable, and invalid query states

### Out of scope

- direct file-path browsing
- provider calls from the browser
- in-browser snapshot computation
- dataset SQL composition in the frontend
- CLI surfaces
- V1 page migration
- new market data generation logic
- changing the existing provider / workflow contract

## Recommended Approach

Use a single browser-style page at `/market` with a two-pane layout:

- left/main pane: filter bar + snapshot list
- right pane: selected snapshot detail drawer / side panel

This is the best fit for the current codebase because:

- the existing `/market` route already acts as the canonical market entry point
- the current market API already returns list/detail/quality/section/regime feature data
- a list + detail panel keeps the interaction flow short and avoids repeated navigation
- it preserves the current workbench style while removing the current task-runner feel from the primary experience

## Route Contract

### Canonical route

- `/market`

### URL state

The page should preserve browser state in the query string where practical:

- `trade_date`
- `market`
- `quality_status`
- `snapshot_id`

The query state should support:

- loading the page with filters already applied
- restoring the selected snapshot on refresh
- sharing a snapshot view link

Do not introduce a separate mandatory detail route in the first pass. The browser should remain usable from a single canonical page.

## Page Structure

### 1. Header

Use the same light workbench header pattern as `UI-V2-002`.

The header should explain that this is a browser for understanding market snapshots, not a debug console.

Suggested content:

- title: `Market Snapshot Browser`
- subtitle: short Chinese explanation of the browser purpose

### 2. Filter Bar

Top-level filters:

- `trade_date`
- `market`
- `quality_status`

Optional browser-state support:

- `snapshot_id` selection from the list

The filter bar should be compact and easy to scan. It should not look like a multi-step form.

### 3. Snapshot List

Each row/card should show at least:

- `snapshot_id`
- `trade_date`
- `market`
- `data_version`
- `quality_status`
- `created_at`
- section counts / partial counts

The list should support:

- loading state
- empty state
- partial data indicator
- selection highlight
- keyboard-friendly row selection where practical

### 4. Detail Pane

The selected snapshot detail should show:

- snapshot identity summary
- quality report summary
- sections list
- section drill-down content
- regime features section if the API returns data
- links to source Job Detail
- links to Artifact Center

The detail pane should remain visible while the user changes the list filters if the selected snapshot is still valid.

### 5. Secondary Actions

Any existing market operations, if retained, should be visually secondary.

The browser must not feel like a task-runner page.

If any runtime actions remain on the page, they must be tucked behind a clearly secondary surface and must not compete with the snapshot browser hierarchy.

## Data Flow

The frontend should reuse the existing market UI API client and types.

Primary API usage:

- `GET /api/ui/v1/market/snapshots`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/sections`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/quality`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/regime-features`

Behavior rules:

- list data comes from the snapshot list endpoint
- selected snapshot detail comes from the detail endpoint
- quality report is displayed from the quality endpoint or the embedded detail payload
- regime features are optional and should render only when available
- the frontend must not synthesize snapshot data from local files

## State Model

The browser must handle the following states explicitly.

### List states

- loading
- empty
- invalid query
- API unavailable
- permission denied
- partial snapshot list

### Detail states

- loading
- empty selection
- snapshot missing
- partial snapshot
- data missing
- permission denied
- API unavailable

### Regime feature states

- loading
- available
- partial
- unavailable

The page should keep the list usable even if the detail pane fails.

## Error Handling

Use the shared `ErrorState` pattern from `UI-V2-008`.

Rules:

- keep technical details collapsed by default
- explain the next step clearly
- provide retry only when retry can help
- avoid showing a blank detail pane on fetch failure
- map `snapshot not found`, `partial data`, `permission denied`, and `API unavailable` to user-facing actions

The browser should avoid collapsing every failure into a generic empty state.

## Visual Direction

Match `UI-V2-002`:

- light background
- restrained borders and shadows
- compact cards
- Chinese copy
- strong typographic hierarchy
- no dark debug-console look
- no CLI-style dense wall of text

The final page should feel like a formal product browser, not a devtool panel.

## Acceptance Criteria

- users can query snapshots by `trade_date`, `market`, and `quality_status`
- users can inspect snapshot list and snapshot detail in the browser
- users can view quality report and section information
- users can view regime features when API data exists
- users can jump to Job Detail and Artifact Center from a snapshot
- the page clearly handles loading, empty, partial, invalid query, permission, and API unavailable states
- no server absolute paths are shown in the UI
- the canonical `/market` page remains the browser entry point
- the UI remains consistent with `UI-V2-002`

## Testing Plan

Test coverage should include:

- snapshot list filtering and selection
- detail pane rendering for a loaded snapshot
- quality report rendering
- regime feature rendering and fallback
- list failure while detail remains recoverable
- detail failure with a visible error state
- query-string state restoration
- route-level smoke coverage for `/market`

## Non-Goals

- replacing the entire market data stack
- introducing a second browser route for the first pass
- adding provider-side runtime actions to the browser as a primary interaction
- redesigning the dataset viewer in this task
- changing how market snapshots are generated
- building a new CLI surface

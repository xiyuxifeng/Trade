# UI-V2-008 Error Recovery Design

## Goal

Build a single, reusable error-recovery pattern for the V2 formal web workbench so users can tell:

1. what went wrong,
2. whether it is recoverable,
3. what they should do next.

This is a UI-only contract and must stay aligned with the existing Web-first, final-delivery direction of `UI-V2-002`. It must not introduce CLI-oriented language or behavior.

## Scope

In scope:

- V2 pages only
- `Job`
- `Profile`
- `Market`
- `Strategy`
- common loading, empty, error, retry, permission-denied states on those pages
- a shared error component and a small mapping layer from backend error categories to user-facing actions

Out of scope:

- V1 pages
- CLI surfaces
- new backend behaviors
- business logic changes
- workflow or pipeline changes

## Recommended Approach

Create a shared `ErrorState` component with a light, workbench-style appearance that matches `UI-V2-002`.

Why this approach:

- keeps the V2 experience consistent
- avoids duplicating error shells on each page
- gives `UI-V2-009` a reusable base component
- keeps the change local to presentation and page-level orchestration

## Error Model

Normalize backend failures into a compact set of user-facing categories:

- `validation error`
- `permission denied`
- `config missing`
- `provider unavailable`
- `data empty`
- `artifact missing`
- `job failed`
- `network error`

Each category should provide:

- a short title
- a one-sentence explanation
- a suggested next step
- optional deep technical detail in a collapsible section
- optional navigation actions

## UI Behavior

The shared error surface should follow these rules:

- keep the page in the normal workbench layout
- do not replace the whole app chrome with a blank error page
- keep technical details collapsed by default
- show a primary suggestion first
- expose retry only when retry can help
- surface navigation shortcuts when they are meaningful

Suggested action targets:

- Job detail
- Profile settings
- Market page
- Strategy workspace

## Page Integration

Each V2 page should use the shared error component through a thin adapter:

- `Job` pages map job fetch and artifact fetch failures
- `Profile` pages map config/profile lookup and permission failures
- `Market` pages map snapshot query and provider/data failures
- `Strategy` pages map job creation, config lookup, and artifact failures

Page adapters may customize the suggestion text, but they must not invent a separate error system.

## Visual Direction

Use the same visual language as `UI-V2-002`:

- light background
- restrained borders and shadows
- strong hierarchy with short headings
- no heavy warning-panel styling
- no CLI-like monospace wall of text

The error state should feel like part of the workbench, not a separate debug console.

## Acceptance Criteria

- V2 pages share one reusable error component family
- users can understand the next step from every supported error category
- technical details are available but not dominant
- retry behavior is explicit where applicable
- the UI remains consistent with `UI-V2-002`
- V1 pages are unchanged by this task

## Testing Plan

Test coverage should include:

- a standalone shared error component
- one page-level integration test per V2 area or adapter path
- category-to-action mapping for the supported backend failures
- loading, empty, error, retry, and permission-denied states

## Non-Goals

- redesigning the whole workbench
- introducing new backend error codes
- adding CLI-specific wording
- unifying V1 in this task
- building a brand new notification system


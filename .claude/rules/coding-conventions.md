# Coding Conventions

Self-contained, explicit, linearly readable code.

## File Structure
- One concern = one file. Co-locate types, constants, logic.
- Acceptable duplication over fragile shared abstraction.
- Export only what's consumed externally.
- Soft limit: 300 lines. Split by concern, not category.

## Naming
Names eliminate the need for comments:
- Booleans: `is/has/should/can`
- Transforms: `to/from/parse`
- Validation: `validate/assert`
- Events: `handle/on`
- Factories: `create/build/make`
- Fetching: `fetch/load/get`
- Constants: `UPPER_SNAKE_CASE`
- Avoid: single-letter vars, `data`/`info`/`temp`/`obj`, abbreviations

## Functions
- Pure by default: inputs → outputs, no side effects.
- Separate computation (pure) from coordination (I/O).
- Max 40 lines, max 3 params (options object beyond that).
- Early returns over nested if/else.
- No nested ternaries.

## Errors
- Fail fast: validate at boundary, not deep inside.
- Never empty catch. Include context: what failed, which inputs, why.

## Control Flow
- Linear top-to-bottom. No implicit event chain ordering.
- Explicit parallel vs sequential async.

## Config as Data
- Business rules as data structures, not procedural branches.
- New option = data change, not logic change.

## Module Boundaries
```
[External] → [Boundary: parse/validate] → [Pure Logic] → [Boundary: persist/send]
```
Business logic never imports I/O directly. Pass deps as params.

## Comments & Tests
- Comments: WHY only. Workarounds: link to issue. Delete commented-out code.
- Tests: co-locate. Behavior names. AAA pattern. Mock I/O only.

<!-- auto:programming-language-rules -->
## Python-Specific Rules

- Type hints on all function params and returns.
- Use `dataclass` (frozen when possible) or Pydantic `BaseModel` for structured data.
- Prefer `pathlib.Path` over `os.path`.
- Use `raise` with specific exception types, not bare `raise`.
- Docstrings: module-level required, function-level for public API only.
- Imports: standard lib → third-party → local, separated by blank lines.
- `from __future__ import annotations` at top of every module.
- All dicts returned from engine functions must be JSON-serializable (no custom classes).
- `dict[str, Any]` for tool return types (RLM compatibility).
- Module-level stores (`_STORE: dict`) for in-memory state + optional `engine_store` persistence.
- Lazy imports for cross-engine references to avoid circular imports.
<!-- /auto:programming-language-rules -->

## Do NOT
- Nested ternaries
- Empty catch blocks
- Mixed I/O and business logic
- Commented-out code
- Magic numbers
- Mutate function params

# UI Library Filter Sheets Design

**Date:** 2026-04-12  
**Status:** Approved (design-ready)  
**Scope:** New phase for UI/UX/FE library filtering with on-demand mirror sheets

## 1. Problem Statement

Current filtering supports category/priority/status/tags, but there is no dedicated workflow for UI/UX/FE library collections (animation, shadcn ecosystem, charts, forms, etc.).  
The new phase must let users filter by library group quickly in chat, and also create separate Google Sheets for each group when needed.

## 2. Goals and Non-Goals

### Goals
- Keep the current main sheet as the single source of truth.
- Add a normalized `Library Group` classification.
- Support `~group` manual override when saving links.
- Auto-detect group from URL/keywords when override is missing.
- Add `/lib`, `/lib <group>`, `/lib sheet <group>` commands.
- Create and keep `LIB_<group>` sheets in realtime sync.
- Backfill old records automatically on deploy.

### Non-Goals
- Replacing the main sheet with multiple independent sheets.
- Allowing arbitrary sheet names for filtered sheets.
- Moving rule management into Google Sheets in this phase.

## 3. Approved Product Decisions

1. Main sheet remains source-of-truth.
2. Filtered sheets are on-demand mirrors named `LIB_<group>`.
3. Sheet creation is user-accessible (not admin-only).
4. Mirror sheets include the same columns as main sheet.
5. If a record changes group, it must be removed from old mirror and upserted to new mirror.
6. Display labels follow user language, but stored group values are canonical keys.

## 4. Architecture Design

### 4.1 Data Model
- Add one new column in main sheet: `Library Group`.
- Canonical group keys:
  - `animation`
  - `shadcn`
  - `icons`
  - `charts`
  - `forms`
  - `table`
  - `state-management`
  - `utils`
- Existing rows get group value during deploy backfill.

### 4.2 Classification Pipeline
When saving a link:
1. Parse `~group` token from user message.
2. If valid override exists, use it.
3. Otherwise classify by rule map (domain + keyword matching).
4. If no rule matches, fallback to `utils`.

Rule map is stored in code/config file and versioned in git.

### 4.3 Command UX
- `/lib`  
  Return available library groups with counts.

- `/lib <group>`  
  Return filtered results for that group in chat.

- `/lib sheet <group>`  
  Ensure `LIB_<group>` exists and backfill all matching records from main sheet.

### 4.4 Realtime Sync Model (Event-Driven)
Main sheet write path stays primary. Mirror updates are secondary side effects.

Sync triggers:
- New link created
- Link edited (especially group changes)
- Link deleted

Sync actions:
- Upsert to target `LIB_<group>` by main `ID`.
- Remove from previous mirror sheet if group changed.
- Remove from mirror if main record deleted.

## 5. Error Handling and Recovery

- Main sheet write success is never rolled back because of mirror-sheet failure.
- Mirror failure is reported as warning and logged.
- Next `/lib sheet <group>` run performs full backfill, acting as reconciliation/self-heal.
- Group inputs are strictly validated; invalid values return valid-group suggestions.
- Mirror upsert uses main `ID` to avoid duplicate rows.

## 6. Testing Strategy

### Unit Tests
- `~group` parsing precedence.
- Classifier rule matching and fallback.
- Group validation and label localization behavior.

### Integration Tests
- `/lib`, `/lib <group>`, `/lib sheet <group>` behavior.
- Realtime mirror sync for create/update/delete.
- Group-change move between mirror sheets.

### Migration/Backfill Tests
- Existing rows without group are classified and populated.
- Creating mirror sheet after backfill includes full expected dataset.

## 7. Rollout Plan

1. Deploy code with new `Library Group` support and command set.
2. Run automatic backfill on startup/deploy for missing group values.
3. Users create needed mirror sheets via `/lib sheet <group>`.
4. Realtime sync keeps created mirror sheets up to date.

## 8. Success Criteria

- Users can filter library resources by group via `/lib <group>`.
- `/lib` shows group counts accurately from source data.
- `/lib sheet <group>` creates `LIB_<group>` and backfills correctly.
- Mirror sheets remain consistent after create/update/delete flows.
- Language display is localized while stored group keys remain canonical.

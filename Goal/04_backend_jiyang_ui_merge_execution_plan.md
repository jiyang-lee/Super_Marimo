# Super_Marimo Backend/Jiyang UI Merge Execution Plan

Date: 2026-05-20
Base branch: `backend/jiyang`
Working branch: `codex/backend-jiyang-ui-merge`
Reference plan: `Goal/03_Super_Marimo_Frontend_Merge_Plan.md`

## 1. What changed from Goal/03

`Goal/03` assumes a `develop` base branch. That is no longer the right base.

The real integration target is now `backend/jiyang`, because that branch already owns:

- the active API contract in `frontend/src/api.ts`
- the current route-based frontend shell
- the runtime mode toggle in `frontend/src/components/Layout.tsx`
- the operator pages for dashboard, events, test, sensor, and chat
- the Vite proxy setup for `/agent`, `/api`, `/voice`, `/llm`

So this is no longer a first merge. It is a consolidation pass:

- keep backend runtime behavior
- pull over the stronger `frontend/jeong` visual layer
- replace only the pages that are pure presentation
- create a new `LabPage` for operator-facing controls

## 2. Current comparison summary

### `backend/jiyang` already has

- `frontend/src/api.ts`
  - full API surface for sessions, sensor, runtime settings, events, chat, TTS
- `frontend/src/components/Layout.tsx`
  - route navigation plus runtime mode toggle
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/EventsPage.tsx`
- `frontend/src/pages/TestPage.tsx`
- `frontend/src/pages/SensorPage.tsx`
- `frontend/src/pages/ChatPage.tsx`
- `frontend/vite.config.ts`
  - proxy config and multi-entry HTML build inputs

### `frontend/jeong` is still the better source for

- `frontend/public/images/`
- `frontend/public/favicon.svg`
- `frontend/src/index.css`
- `frontend/src/components/PixelCard.tsx`
- `frontend/src/components/PixelButton.tsx`
- `frontend/src/components/MarimoSpeech.tsx`
- `frontend/src/PixelMarimo.tsx`
- `frontend/src/MarimoEntity.tsx`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/ReportPage.tsx`

### `frontend/jeong` files that should not be copied as-is

- `frontend/src/api.ts`
  - too small, drops most backend endpoints
- `frontend/src/App.tsx`
  - monolithic landing-page app, not aligned with backend route shell
- `frontend/src/main.tsx`
  - route shell from backend is the safer base
- `frontend/vite.config.ts`
  - backend branch already has the right proxy and HTML entry setup

## 3. Execution plan

### Phase 0. Freeze the base

- Work only in `codex/backend-jiyang-ui-merge`
- Keep the current `frontend/jeong` checkout untouched as a visual reference
- Do not merge branches directly; use selective file import and manual edits

### Phase 1. Import the visual layer from `frontend/jeong`

- Copy:
  - `frontend/public/images/`
  - `frontend/public/favicon.svg`
  - `frontend/src/index.css`
  - `frontend/src/components/PixelCard.tsx`
  - `frontend/src/components/PixelButton.tsx`
  - `frontend/src/components/MarimoSpeech.tsx`
  - `frontend/src/PixelMarimo.tsx`
  - `frontend/src/MarimoEntity.tsx`
  - `frontend/src/pages/HomePage.tsx`
  - `frontend/src/pages/SettingsPage.tsx`
  - `frontend/src/pages/ReportPage.tsx`

### Phase 2. Preserve backend contracts

- Keep backend versions of:
  - `frontend/src/api.ts`
  - `frontend/vite.config.ts`
  - `frontend/src/main.tsx`
- Update `frontend/package.json` only where needed
  - likely change `build` to `tsc -b && vite build`
  - keep `react-router-dom` and backend dependencies

### Phase 3. Rebuild the route shell

- Rewrite `frontend/src/App.tsx` to use this route map:

```tsx
<Routes>
  <Route path="/" element={<HomePage />} />
  <Route path="/chat" element={<ChatPage />} />
  <Route path="/sensor" element={<SensorPage />} />
  <Route path="/settings" element={<SettingsPage />} />
  <Route path="/lab" element={<LabPage />} />
  <Route path="/report" element={<ReportPage />} />
</Routes>
```

- Update `frontend/src/components/Layout.tsx`
  - replace nav labels with `Home`, `Chat`, `Sensor`, `Settings`, `Lab`, `Report`
  - preserve the runtime mode toggle and polling logic from backend

### Phase 4. Page-level integration policy

- `HomePage.tsx`
  - use the `jeong` version as the base
  - repair broken Korean text while importing

- `SettingsPage.tsx`
  - use `jeong` layout
  - wire it to backend `getRuntimeSettings` and `updateRuntimeSettings`
  - reflect actual runtime flags instead of static menu cards

- `ReportPage.tsx`
  - use `jeong` version first
  - keep it static unless backend data is actually needed

- `ChatPage.tsx`
  - keep backend functionality
  - retheme with `jeong` CSS tokens and pixel components

- `SensorPage.tsx`
  - keep backend sensor history, merged payload, and polling behavior
  - retheme cards and chart wrappers only

- `LabPage.tsx`
  - create a new page
  - merge:
    - dashboard health summary
    - recent events summary
    - test actions and TTS controls
  - this becomes the operator console

- `DashboardPage.tsx`, `EventsPage.tsx`, `TestPage.tsx`
  - use as source material for `LabPage`
  - once `LabPage` is stable, remove them from routing
  - file deletion can be deferred until after UI verification

## 4. CSS merge rules

- Start from `frontend/jeong` `index.css`
- Re-add only the backend utility classes still required by:
  - `ChatPage`
  - `SensorPage`
  - `LabPage`
  - `Layout`
- Normalize classes that still assume old green dashboard styling
- Preserve the stronger `jeong` atmosphere:
  - scene background
  - pixel cards
  - board-style surfaces
  - character art

## 5. Known risks

- `Goal/03` references `develop`; using it literally would regress backend behavior
- some `frontend/jeong` files contain broken Korean text and need manual rewriting
- copying `frontend/jeong/src/api.ts` would break most backend-linked pages
- deleting dashboard/events/test too early would remove working operator tools before `LabPage` is complete
- `frontend/jeong/src/App.tsx` contains useful visual sections but should be mined, not transplanted whole

## 6. Implementation order

1. Import visual assets and theme files
2. Lock backend runtime files in place
3. Rebuild `App.tsx` and `Layout.tsx`
4. Add `HomePage`, `SettingsPage`, `ReportPage`
5. Create `LabPage`
6. Retheme `ChatPage` and `SensorPage`
7. Build and fix TypeScript/UI errors
8. Run browser verification with backend services up

## 7. Exit criteria

- `npm run build` passes in `frontend/`
- `http://localhost:5173/` loads without route errors
- `/chat` still talks to `/agent`
- `/sensor` still renders backend sensor data
- `/settings` can read and update runtime settings
- `/lab` replaces the old operator split across dashboard/events/test
- the UI consistently uses the `jeong` visual language without breaking backend workflows

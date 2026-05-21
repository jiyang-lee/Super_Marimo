# Background-First UI Cleanup Report

- Order applied: background removal first, then `chat -> lab -> report`.
- Scope kept: shared API and router files were left untouched.
- Changed files: `frontend/src/index.css`, `frontend/src/pages/ChatPage.tsx`, `frontend/src/styles/lab.css`, `frontend/src/pages/LabPage.tsx`, `frontend/src/pages/ReportPage.tsx`.

## What changed

- Removed the dark translucent shell overlay so the app no longer sits under a black veil.
- Lightened the Lab surface and tab strip so the page reads on a pale background instead of a dark glass panel.
- Lightly tuned Chat cards and input chrome to read better after the shell background change, while preserving the current message/session/TTS flow.
- Added a real weekly/monthly toggle to Report and normalized the summary labels.

## What stayed frozen

- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/main.tsx`
- `frontend/src/index.css` shared layout structure beyond background styling

## Notes

- `lab` still maps to `frontend/src/pages/LabPage.tsx`.
- `report` still maps to the top-level `report/` docs plus `frontend/src/pages/ReportPage.tsx`.
- `chat` was the first page checked after the background change and only received a small visual tone-up, not a structural rewrite.

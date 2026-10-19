# Super Marimo demo design contract

## Reference and purpose
Reuse the repository's existing dashboard system (`site.css`) and React/Vite stack. This is a portfolio walkthrough of public test fixtures, for visitors who have no hardware or backend. Existing component system was inspected; this contract extracts its cream surfaces, forest green controls, rounded panels and Marimo character. No redesign research or generated imagery is needed for this scoped reuse.

## Tokens
Background #f4f1ea; surface #ffffff; secondary #faf7f0; ink #1f2937; muted #526071; border #ddd3c2; brand #006b5f; warning #995009. System Segoe UI/Malgun Gothic font; sizes 12/14/16/20/32/48px; spacing 4/8/12/16/24/32/48px; radius 14/24px. Borders 1px; shadow 0 16px 36px rgba(27,34,44,.09).

## Layout and primitives
Max width 1120px. Header: identity + sample badge. Intro: purpose + disclosure. Two-column workspace: numbered scenario selector and character, followed by replay panel with sensor metrics, ordered stages and saved reply. Footer: fixture provenance. Reuse bundled Marimo image, no third party fonts or assets. Buttons, badges, metric tiles, stage list and reply share tokens.

## States and interaction
Idle, replaying stages 1–4, completed. Explicit replay starts a deterministic local walkthrough; no artificial timings claimed as inference. Scenario changes and reset return to idle. Reset remains available during playback and cancels pending advancement. No mic, backend, persistence or paid service. Hover and focus communicate interaction; no decorative animation.

## Responsive behavior
At 760px collapse to one column. Metrics remain a two-column grid. All containers min-width 0 and text wraps. Page scrolls naturally at 375/768/1280px; no fixed-height panels.

## Accessibility and personas
Korean copy; semantic main/header/footer, ordered stages, button selected state, visible focus, 44px targets, text alongside every status. Screen reader live region announces replay updates politely. Reduced motion disables transitions. Keyboard-only visitor can select, play and reset. First-time visitor sees sample disclosure before controls; cautious visitor can inspect exact public test provenance.

## Content and constraints
Always show “샘플 데이터와 저장된 실행 결과를 사용하는 체험 모드”. Saved answers are exact strings from public automated test assertions, not recorded production inference. Sensor policy state is explicitly a mocked warning fixture, not a current evaluation. No free input implying live inference. Production API path remains intact and is excluded from demo entry graph.

## QA and debt
Build, strict demo typecheck, fixture and bundle isolation checks required. Browser visual/interaction evidence must be collected before release. No accessibility or visual pass claimed without actual browser evidence. Development tooling is kept out of this narrowly scoped published demo; existing app dependencies retained.

## Fixture provenance update
Primary temperature conversation uses the exact section 3 expected-response example from `report/demo_voice_script_guide.md`: 25 °C, “현재 온도는 25도입니다.” It is labeled a saved documentation example. The two settings scenarios remain exact public test expectations and retain their own mocked sensor snapshot. Source links are pinned to inspected repository revision a35976b75161ac92ebd3b99015a656bf68a28d9e.

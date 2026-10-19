# Static sample build

This is an isolated React entry inside the existing Vite project. It does not import production API clients, microphone code or live sensor providers. Demo builds disable public-directory copying and exclude legacy dashboard HTML, internal addresses and operational assets.

```powershell
npm ci
npm run build -- --mode demo
npm run preview -- --outDir dist-demo --host 127.0.0.1
```

Alternatively set `VITE_DEMO_MODE=true` and run the normal build. Publish only `dist-demo/` to any static host; never publish the repository root. No credentials, server or hardware are needed. Normal builds retain existing production entries and proxy/API behavior.

Fixtures: `src/demo/fixtures.ts`. The temperature question/answer is copied from `report/demo_voice_script_guide.md`, section 3. It is a documented expected response example, not a captured inference. Settings answers and input phrases are from `api_server/tests/test_interaction_service.py` (`test_handle_interaction_uses_llm_action_proposal`, `test_handle_interaction_falls_back_to_text_resolution`); sensor metrics and mocked warning state are from `_patch_common_flow`. UI step timing is illustrative. No real data is persisted; reset and scenario changes cancel playback.

Before publishing: build demo, run `node scripts/check-demo.mjs`, inspect at mobile/tablet/desktop widths and exercise all scenarios plus reset. npm install repaired the upstream lockfile's incomplete optional @emnapi dependency entries; no application dependency was added.

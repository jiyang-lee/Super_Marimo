import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
const demoApp = await readFile('src/demo/main.tsx', 'utf8');
const fixtures = await readFile('src/demo/fixtures.ts', 'utf8');
const testSource = await readFile('../api_server/tests/test_interaction_service.py', 'utf8');
const docSource = await readFile('../report/demo_voice_script_guide.md', 'utf8');
assert.equal((fixtures.match(/id: '/g) ?? []).length, 3, 'demo must expose exactly three fixed scenarios');
for (const expected of [
  'report/demo_voice_script_guide.md',
  'test_handle_interaction_uses_llm_action_proposal',
  'test_handle_interaction_falls_back_to_text_resolution',
]) assert.ok(fixtures.includes(expected), `missing fixture provenance: ${expected}`);
assert.match(demoApp, /srcSet=\{`\$\{marimoSmall\} 320w, \$\{marimo\} 480w`\}/);
assert.match(demoApp, /sizes="\(max-width: 760px\) 160px, 240px"/);
assert.match(demoApp, /width="240" height="240"/);
assert.match(demoApp, /https:\/\/jiyang-lee\.github\.io\/#\/projects\/super-marimo/);
for (const answer of ['깨우기 기능을 껐어요. 필요하면 다시 켜주세요!', '거리 감지 모드를 껐어요. 필요하면 다시 켜주세요!']) {
  assert.ok(fixtures.includes(answer) && testSource.includes(answer));
}
assert.ok(fixtures.includes('현재 온도는 25도입니다.') && docSource.includes('현재 온도는 25도입니다.'));
const names = await readdir('dist-demo');
assert.deepEqual(names.sort(), ['assets', 'index.html']);
const document = await readFile('dist-demo/index.html', 'utf8');
assert.match(document, /<title>Super Marimo · 샘플 체험<\/title>/);
assert.match(document, /<meta name="description" content="공개 문서와 테스트의 고정 예시로 살펴보는 Super Marimo 체험 모드"/);
assert.match(document, /<link rel="icon" href="data:image\/svg\+xml,/);
const assets = await readdir('dist-demo/assets');
const content = (await Promise.all(assets.filter(name => /\.(js|css)$/.test(name)).map(name => readFile(`dist-demo/assets/${name}`, 'utf8')))).join('\n');
for (const pattern of [/https?:\/\/(?:localhost|127\.0\.0\.1|192\.168\.|10\.)/, /getUserMedia|MediaRecorder|\/sensor\/latest|\/runtime-settings|\/agent\/ask/, /VITE_API_BASE_URL|super-marimo\.voice-name/]) assert.doesNotMatch(content, pattern);
console.log('PASS: three source-backed fixtures; responsive WebP image contract; demo-only metadata and favicon; isolated static output; no production endpoints, microphone code, storage, or API clients.');

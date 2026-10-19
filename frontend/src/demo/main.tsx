import { createRoot } from 'react-dom/client';
import { DemoProvider } from './DemoProvider';
import { useDemo } from './context';
import { replayStages, sampleScenarios } from './fixtures';
import marimo from './marimo-480.webp';
import marimoSmall from './marimo-320.webp';
import './demo.css';

function renderSensorState(state: string) {
  const phrase = '모의 상태입니다.';
  const index = state.indexOf(phrase);
  if (index < 0) return state;
  return <>{state.slice(0, index)}<span className="sensor-note-phrase">{phrase}</span>{state.slice(index + phrase.length)}</>;
}
export function DemoApp() {
  const { scenario, stage, playing, select, play, reset } = useDemo();
  const complete = stage === replayStages.length;
  return <div className="demo-shell">
    <header><a className="brand" href="./">SUPER MARIMO<span>작은 생명과 나누는 대화</span></a><span className="badge">SAMPLE EXPERIENCE</span></header>
    <main id="main">
      <section className="intro"><p className="eyebrow">SENSOR → CONTEXT → RESPONSE</p><h1>마리모의 하루를<br />대화로 살펴보세요.</h1><p>센서 문맥이 대화와 설정 변경으로 이어지는 과정을 따라가 보세요.</p><p className="disclosure">샘플 데이터와 저장된 실행 결과를 사용하는 체험 모드</p><p className="muted">공개 문서와 자동화 테스트의 고정 예시를 재생합니다. 실제 AI 추론·음성 인식·기기 제어는 실행하지 않습니다.</p></section>
      <div className="workspace">
        <section className="panel scenario-panel" aria-labelledby="scenario-heading"><p className="eyebrow">01 / CHOOSE A SCENARIO</p><h2 id="scenario-heading">어떤 말을 건넬까요?</h2><div className="choices">{sampleScenarios.map((item, index) => <button key={item.id} aria-pressed={scenario.id === item.id} onClick={() => select(item)}><span className="choice-number">0{index + 1}</span><span>{item.label}<small>{item.utterance}</small></span><span aria-hidden="true">↗</span></button>)}</div><img className="marimo" src={marimo} srcSet={`${marimoSmall} 320w, ${marimo} 480w`} sizes="(max-width: 760px) 160px, 240px" alt="초록색 마리모 캐릭터" width="240" height="240" /><p className="character-caption">마이크도, 센서 연결도 필요 없어요.</p></section>
        <section className="panel replay-panel" aria-labelledby="replay-heading"><div className="panel-top"><div><p className="eyebrow">02 / FOLLOW THE FLOW</p><h2 id="replay-heading">대화 흐름 살펴보기</h2></div><span className="badge">로컬 재생</span></div><div className="utterance"><span className="muted">선택한 샘플 발화</span><p>“{scenario.utterance}”</p></div><div className="metrics">{scenario.sensors.map((sensor) => <div key={sensor.label}><span>{sensor.label}</span><strong>{sensor.value}</strong></div>)}</div><p className="sensor-note">센서 문맥: {renderSensorState(scenario.state)}</p><ol className="stages">{replayStages.map((label, index) => <li key={label} data-complete={stage > index}><span aria-hidden="true">{stage > index ? '✓' : index + 1}</span>{label}</li>)}</ol><div className="result" role="status" aria-live="polite"><span className="eyebrow">{complete ? scenario.kind : 'REPLAY STATUS'}</span>{complete ? <><p className="answer">{scenario.answer}</p>{scenario.setting && <code>{scenario.setting}: true → false</code>}<p className="muted">이 화면의 로컬 체험에만 반영됩니다. 데이터베이스 저장과 실제 기기 변경은 없습니다.</p></> : <p>{playing ? `${stage + 1}단계 · ${replayStages[stage]}` : '샘플 재생을 누르면 저장된 결과가 여기에 표시됩니다.'}</p>}</div><div className="actions"><button className="primary" disabled={playing} onClick={play}>{playing ? '흐름 재생 중…' : complete ? '다시 재생' : '샘플 재생'}<span aria-hidden="true"> →</span></button><button className="secondary" onClick={reset}>초기화</button></div></section>
      </div>
      <details className="provenance"><summary>이 예시의 출처와 범위</summary><p>실제 운영 기록이 아닙니다. 온도 시나리오는 공개 시연 문서에 저장된 응답 형식 예시입니다. 설정 시나리오는 공개 자동화 테스트의 입력·센서 fixture·final_answer 기대 결과입니다. 재생 단계와 시간 간격은 이해를 돕기 위한 UI 연출입니다.</p><p><a href={`https://github.com/jiyang-lee/Super_Marimo/blob/a35976b75161ac92ebd3b99015a656bf68a28d9e/${scenario.source}`} target="_blank" rel="noreferrer">공개 원문 보기 ↗</a></p><code>{scenario.source}<br />{scenario.test}</code></details>
    </main><footer><span>SUPER MARIMO / INTERACTIVE SAMPLE</span><span>서버 연결 없이 브라우저 안에서만 실행 · <a href="https://jiyang-lee.github.io/#/projects/super-marimo">프로젝트 보기</a></span></footer>
  </div>;
}
const root = document.getElementById('root');
if (root) createRoot(root).render(<DemoProvider><DemoApp /></DemoProvider>);

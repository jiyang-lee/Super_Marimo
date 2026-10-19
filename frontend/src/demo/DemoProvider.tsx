import { useEffect, useState, type ReactNode } from 'react';
import { sampleScenarios, replayStages, type SampleScenario } from './fixtures';
import { DemoContext } from './context';
export function DemoProvider({ children }: { readonly children: ReactNode }) {
  const [scenario, setScenario] = useState<SampleScenario>(sampleScenarios[0]);
  const [stage, setStage] = useState(0);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(() => {
      setStage(stage + 1);
      if (stage + 1 === replayStages.length) setPlaying(false);
    }, 550);
    return () => window.clearTimeout(timer);
  }, [playing, stage]);
  const reset = () => { setPlaying(false); setStage(0); };
  return <DemoContext.Provider value={{ scenario, stage, playing, reset,
    select: (next) => { reset(); setScenario(next); },
    play: () => { setStage(0); setPlaying(true); },
  }}>{children}</DemoContext.Provider>;
}

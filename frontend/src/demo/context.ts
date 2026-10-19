import { createContext, useContext } from 'react';
import type { SampleScenario } from './fixtures';
type DemoState = {
  readonly scenario: SampleScenario;
  readonly stage: number;
  readonly playing: boolean;
  readonly select: (scenario: SampleScenario) => void;
  readonly play: () => void;
  readonly reset: () => void;
};
export const DemoContext = createContext<DemoState | null>(null);


export function useDemo() {
  const state = useContext(DemoContext);
  if (state === null) throw new Error('DemoProvider is required');
  return state;
}

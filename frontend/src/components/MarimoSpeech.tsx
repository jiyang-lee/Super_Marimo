import { PixelMarimo } from '../PixelMarimo';
import '../styles/speech.css';

export function MarimoSpeech({ text }: { text: string }) {
  return (
    <div className="flex items-end gap-3 justify-center mb-4">
      <PixelMarimo size={80} />
      <div className="speech-bubble max-w-[260px]">
        <p className="font-dot">{text}</p>
      </div>
    </div>
  );
}

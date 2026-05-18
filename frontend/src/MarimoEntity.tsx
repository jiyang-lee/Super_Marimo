import type { FC } from 'react';
import marimoImg from './assets/marimo.png';

interface MarimoEntityProps {
  size?: number;
  className?: string;
}

export const MarimoEntity: FC<MarimoEntityProps> = ({ size = 300, className = "" }) => {
  return (
    <div 
      className={`relative flex flex-col items-center select-none ${className}`} 
      style={{ width: size, height: size + 60 }}
    >
      {/* ─── Speech Bubble ─── */}
      <div className="absolute -top-16 left-1/2 -translate-x-1/2 z-40 animate-float pointer-events-none">
        <div className="maple-bubble whitespace-nowrap px-6 py-2">
          <span className="font-dot text-sm text-[#3e2723]">"오늘도 잘 부탁해!~"</span>
        </div>
      </div>

      {/* ─── The Character Sprite (Imported Asset) ─── */}
      <div className="w-full h-full origin-bottom animate-marimo-idle relative flex items-center justify-center">
        {/* Main Sprite (Using bundle-imported asset for stability) */}
        <div className="w-full h-full relative overflow-hidden flex items-center justify-center">
          <img 
            src={marimoImg} 
            alt="Marimo" 
            className="w-full h-full object-contain relative z-10 transition-transform active:scale-105"
            style={{ 
              imageRendering: 'pixelated'
            }}
          />
        </div>
      </div>
      
      {/* ─── Maple Name Tag ─── */}
      <div className="mt-[-10px] z-30">
        <div className="px-4 py-1 bg-black/70 border-2 border-white/10 rounded-sm">
          <span className="font-pixel text-[0.5rem] white-glow text-white tracking-widest" style={{ textShadow: '1px 1px 0 #000' }}>
            Lv.8 마리모
          </span>
        </div>
      </div>
    </div>
  );
};

import { useEffect, useRef } from 'react';

interface PixelMarimoProps {
  size?: number;
  mood?: 'happy' | 'idle' | 'blink';
}

export function PixelMarimo({ size = 180 }: PixelMarimoProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const RESOLUTION = 64; // 고해상도 픽셀
    canvas.width = RESOLUTION;
    canvas.height = RESOLUTION;

    let frame = 0;
    let animationId: number;

    const greens = ['#8bc34a', '#7cb342', '#689f38', '#558b2f', '#33691e'];
    const highlightColor = '#dcedc8';
    
    // Seeded random for consistent texture per frame
    let seed = 42;
    const rand = () => {
      seed = (seed * 9301 + 49297) % 233280;
      return seed / 233280;
    };

    const render = () => {
      frame++;
      seed = 42; // Reset seed each frame for texture consistency
      
      ctx.clearRect(0, 0, RESOLUTION, RESOLUTION);

      // 애니메이션 로직
      const breath = Math.sin(frame * 0.05) * 1.5;
      const isBlinking = Math.sin(frame * 0.03) > 0.96;
      const mouthOpen = Math.sin(frame * 0.1) > 0.6;

      const centerX = RESOLUTION / 2;
      const centerY = RESOLUTION / 2 + breath;
      const bodyRadius = 24;

      // ── 몸체 렌더링 ──
      for (let y = 0; y < RESOLUTION; y++) {
        for (let x = 0; x < RESOLUTION; x++) {
          const dx = x - centerX;
          const dy = y - centerY;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < bodyRadius) {
            // 가장자리 픽셀화 (털 느낌)
            if (dist > bodyRadius - 3 && rand() > 0.6) continue;

            const noise = (Math.sin(x * 0.7) * Math.cos(y * 0.7)) * 2;
            let colorIdx = Math.floor((dist / bodyRadius) * greens.length + noise);
            colorIdx = Math.max(0, Math.min(greens.length - 1, colorIdx));
            
            ctx.fillStyle = greens[colorIdx];
            
            // 상단 하이라이트 (입체감)
            if (y < centerY - 12 && dist < bodyRadius - 8 && rand() > 0.3) {
              ctx.fillStyle = highlightColor;
            }
            
            ctx.fillRect(x, y, 1, 1);
          }
        }
      }

      // ── 눈 ──
      const eyeY = centerY - 3;
      const leftEyeX = centerX - 9;
      const rightEyeX = centerX + 5;

      const drawEye = (ex: number, ey: number) => {
        ctx.fillStyle = '#1a1a1a';
        if (isBlinking) {
          ctx.fillRect(ex, ey + 2, 4, 1); // 감은 눈
        } else {
          ctx.fillRect(ex, ey, 4, 5); // 눈동자
          ctx.fillStyle = '#fff';
          ctx.fillRect(ex + 1, ey + 1, 2, 2); // 반짝임
          ctx.fillRect(ex, ey + 2, 1, 1);
        }
      };

      drawEye(leftEyeX, eyeY);
      drawEye(rightEyeX, eyeY);

      // ── 볼터치 ──
      ctx.fillStyle = 'rgba(244, 143, 177, 0.6)';
      ctx.fillRect(leftEyeX - 4, eyeY + 6, 3, 2);
      ctx.fillRect(rightEyeX + 5, eyeY + 6, 3, 2);

      // ── 입 ──
      ctx.fillStyle = '#3e2723';
      if (mouthOpen) {
        ctx.fillRect(centerX - 2, centerY + 6, 4, 3);
        ctx.fillStyle = '#f06292'; // 혀
        ctx.fillRect(centerX - 1, centerY + 8, 2, 1);
      } else {
        ctx.fillRect(centerX - 2, centerY + 7, 4, 1);
      }

      animationId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationId);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="marimo-pixel-art"
      style={{
        width: size,
        height: size,
        imageRendering: 'pixelated',
      }}
    />
  );
}

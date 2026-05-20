import type { ReactNode } from 'react';
import '../styles/ui.css';

interface Props {
  children: ReactNode;
  className?: string;
  title?: string;
}

export function PixelCard({ children, className = '', title }: Props) {
  return (
    <div className={`card-parchment p-3 ${className}`}>
      {title && (
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-dot font-bold text-bark">{title}</h3>
        </div>
      )}
      {children}
    </div>
  );
}

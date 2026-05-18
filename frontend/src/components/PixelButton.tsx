import type { ButtonHTMLAttributes, PropsWithChildren } from 'react';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'gold' | 'green' | 'red';
  size?: 'sm' | 'md' | 'lg';
}

export function PixelButton({ children, variant = 'gold', size = 'md', className = '', ...props }: PropsWithChildren<Props>) {
  const variantClass = variant === 'gold' ? 'btn-gold' : variant === 'green' ? 'btn-green' : 'bg-heart-red text-white btn-game';
  const sizeClass = size === 'sm' ? 'text-[0.65rem] px-2 py-0.5' : size === 'lg' ? 'px-6 py-3 text-lg' : 'px-4 py-2';
  
  return (
    <button className={`${variantClass} ${sizeClass} ${className}`} {...props}>
      {children}
    </button>
  );
}

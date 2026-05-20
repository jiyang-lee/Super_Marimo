type MarimoImageProps = {
  size?: 'large' | 'medium' | 'small';
  alt?: string;
  className?: string;
};

export function MarimoImage({ size = 'medium', alt = '마리모 캐릭터', className = '' }: MarimoImageProps) {
  const imageSourceBySize = {
    large: '/images/incoming/marimo-shadow-large.png',
    medium: '/images/incoming/marimo-main.png',
    small: '/images/incoming/marimo-small.png',
  };

  return (
    <img
      className={`marimo-image marimo-image--${size} ${className}`.trim()}
      src={imageSourceBySize[size]}
      alt={alt}
      onError={(event) => {
        event.currentTarget.onerror = null;
        event.currentTarget.src = '/images/common/marimo-placeholder.svg';
      }}
    />
  );
}

export function MarimoImage({ size = "medium", alt, className = "" }) {
  const imageSourceBySize = {
    large: "/images/character/marimo-large.png",
    medium: "/images/character/marimo-medium.png",
    small: "/images/character/marimo-small.png",
  };

  function handleFallback(event) {
    event.currentTarget.onerror = null;
    event.currentTarget.src = "/images/common/marimo-placeholder.svg";
  }

  return (
    <img
      className={`marimo-image marimo-image--${size} ${className}`.trim()}
      src={imageSourceBySize[size] || imageSourceBySize.medium}
      alt={alt || "마리모 캐릭터"}
      onError={handleFallback}
    />
  );
}

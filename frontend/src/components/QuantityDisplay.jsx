export default function QuantityDisplay({ display, secondary }) {
  if (!display) return "–";

  return (
    <span className="quantity-display">
      <strong>{display}</strong>
      {secondary && <small>{secondary}</small>}
    </span>
  );
}

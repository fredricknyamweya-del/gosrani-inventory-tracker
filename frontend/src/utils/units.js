function formatNumber(value) {
  const absolute = Math.abs(value);
  const scaled = absolute * 1000;
  const lower = Math.floor(scaled);
  const fraction = scaled - lower;
  const tolerance = Number.EPSILON * Math.max(1, scaled) * 2;
  let rounded = lower;

  if (fraction > 0.5 + tolerance) {
    rounded += 1;
  } else if (
    Math.abs(fraction - 0.5) <= tolerance &&
    lower % 2 !== 0
  ) {
    rounded += 1;
  }

  const formatted = (rounded / 1000).toLocaleString("en-US", {
    maximumFractionDigits: 3,
  });
  return value < 0 ? `-${formatted}` : formatted;
}

export function formatQuantityDisplay(quantity, unit, packSize) {
  const value = Number(quantity);
  if (!Number.isFinite(value)) {
    throw new TypeError("Quantity must be a finite number.");
  }
  if (packSize != null && (!Number.isInteger(packSize) || packSize <= 0)) {
    throw new RangeError("Pack size must be a positive whole number.");
  }
  if (value === 0) return ["0", null];
  if (unit === "KG") return [`${formatNumber(value)} kg`, null];

  const absolute = Math.abs(value);
  if (packSize == null) {
    return [
      `${formatNumber(value)} ${absolute === 1 ? "pc" : "pcs"}`,
      null,
    ];
  }

  const baleCount = Math.floor(absolute / packSize);
  const remainder = absolute - baleCount * packSize;
  const parts = [];
  if (baleCount > 0) {
    parts.push(
      `${baleCount.toLocaleString("en-US")} ${baleCount === 1 ? "bale" : "bales"}`,
    );
  }
  if (remainder > 0) {
    parts.push(
      `${formatNumber(remainder)} ${remainder === 1 ? "pc" : "pcs"}`,
    );
  }
  if (parts.length === 0) return ["0", null];

  const sign = value < 0 ? "-" : "";
  const display = `${sign}${parts.join(" + ")}`;
  const secondary =
    baleCount > 0
      ? `(${formatNumber(value)} ${absolute === 1 ? "pc" : "pcs"})`
      : null;
  return [display, secondary];
}

export function formatEntryQuantityPreview(
  quantity,
  enteredUnit,
  stockUnit,
  packSize,
) {
  if (quantity === "" || quantity == null || !stockUnit) return null;
  const value = Number(quantity);
  if (!Number.isFinite(value)) return null;
  if (enteredUnit === "BALE" && packSize == null) return null;
  const baseQuantity =
    enteredUnit === "BALE" ? value * packSize : value;
  const [display, secondary] = formatQuantityDisplay(
    baseQuantity,
    stockUnit,
    packSize,
  );
  return [display, secondary].filter(Boolean).join(" ");
}

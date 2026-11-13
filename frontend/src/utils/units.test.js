import assert from "node:assert/strict";
import test from "node:test";
import {
  formatEntryQuantityPreview,
  formatQuantityDisplay,
} from "./units.js";

const goldenCases = [
  [8300, "PCS", 20, ["415 bales", "(8,300 pcs)"]],
  [8307, "PCS", 20, ["415 bales + 7 pcs", "(8,307 pcs)"]],
  [20, "PCS", 20, ["1 bale", "(20 pcs)"]],
  [1, "PCS", 20, ["1 pc", null]],
  [7, "PCS", 20, ["7 pcs", null]],
  [0, "PCS", 20, ["0", null]],
  [-8307, "PCS", 20, ["-415 bales + 7 pcs", "(-8,307 pcs)"]],
  [2, "PCS", null, ["2 pcs", null]],
  [1, "PCS", null, ["1 pc", null]],
  [-2, "PCS", null, ["-2 pcs", null]],
  [22816, "KG", null, ["22,816 kg", null]],
  [22.8165, "KG", null, ["22.816 kg", null]],
  [0, "KG", null, ["0", null]],
];

for (const [quantity, unit, packSize, expected] of goldenCases) {
  test(`formats ${quantity} ${unit} with pack size ${packSize}`, () => {
    assert.deepEqual(
      formatQuantityDisplay(quantity, unit, packSize),
      expected,
    );
  });
}

test("previews bale entry in base pieces with the specification pack size", () => {
  assert.equal(
    formatEntryQuantityPreview(2, "BALE", "PCS", 20),
    "2 bales (40 pcs)",
  );
});

test("does not preview a bale entry without a specification pack size", () => {
  assert.equal(formatEntryQuantityPreview(2, "BALE", "PCS", null), null);
});

test("rejects invalid pack sizes", () => {
  assert.throws(() => formatQuantityDisplay(1, "PCS", 0), /positive whole/);
});

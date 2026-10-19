import { expect, it } from "vitest";
import { day, label, money } from "./format";

it("formats money in US dollars", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(money(0)).toBe("$0.00");
  expect(money(80.5)).toBe("$80.50");
});

it("turns codes into labels", () => {
  expect(label("trip_delay")).toBe("Trip delay");
  expect(label("baggage")).toBe("Baggage");
});

it("formats dates", () => {
  expect(day("2026-06-24")).toBe("Jun 24, 2026");
});

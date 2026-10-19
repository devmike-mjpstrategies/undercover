import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { parseRoute } from "./route";
import { stubApi, summary } from "./testing";

beforeEach(() => {
  vi.stubGlobal("scrollTo", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

describe("parseRoute", () => {
  it("reads the three views from the hash", () => {
    expect(parseRoute("")).toEqual({ page: "queue" });
    expect(parseRoute("#/")).toEqual({ page: "queue" });
    expect(parseRoute("#/claims/CLM-1001")).toEqual({
      page: "claim",
      claimId: "CLM-1001",
    });
    expect(parseRoute("#/instructions")).toEqual({ page: "instructions" });
    expect(parseRoute("#/nowhere")).toEqual({ page: "queue" });
  });
});

it("shows the queue first", async () => {
  stubApi({ "GET /api/claims": [summary({})] });
  render(<App />);
  expect(await screen.findByText("Claims queue")).toBeDefined();
  expect(screen.getByRole("link", { name: "Queue" }).ariaCurrent).toBe("page");
});

it("follows the hash", async () => {
  stubApi({ "GET /api/claims": [summary({})] });
  render(<App />);
  await screen.findByText("Claims queue");
  act(() => {
    window.location.hash = "#/instructions";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  expect(screen.getByRole("link", { name: "Queue" }).ariaCurrent).toBeNull();
});

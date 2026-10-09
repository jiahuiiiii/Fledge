import test from "node:test";
import assert from "node:assert/strict";
import { api } from "../api/client.js";

test("a stale account response is rejected and writes carry the expected account", async () => {
  const previousFetch = globalThis.fetch,
    previousWindow = globalThis.window;
  const events = [],
    calls = [];
  globalThis.window = { dispatchEvent: (event) => events.push(event.type) };
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith("/session"))
      return new Response(
        JSON.stringify({
          result: { authenticated: true, account_id: "account-a" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    return new Response(
      JSON.stringify({
        result: { errors: [{ error_message: "Account changed" }] },
      }),
      {
        status: 409,
        headers: {
          "Content-Type": "application/json",
          "X-Thesis-Account": "account-b",
        },
      },
    );
  };
  try {
    await api.session();
    await assert.rejects(api.savePeers("company", []), /account changed/);
    assert.equal(calls[1].options.headers["X-Thesis-Account"], "account-a");
    assert.deepEqual(events, ["thesis:account-changed"]);
  } finally {
    globalThis.fetch = previousFetch;
    globalThis.window = previousWindow;
  }
});

test("email retry headers reach the UI without triggering account logout", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        result: { errors: [{ error_message: "Please wait" }] },
      }),
      {
        status: 429,
        headers: { "Content-Type": "application/json", "Retry-After": "47" },
      },
    );
  try {
    await assert.rejects(
      api.login("test@example.test"),
      (error) => error.status === 429 && error.retryAfter === 47,
    );
  } finally {
    globalThis.fetch = previousFetch;
  }
});

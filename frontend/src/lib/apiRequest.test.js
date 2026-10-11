import test from "node:test";
import assert from "node:assert/strict";
import { api } from "../api/client.js";

test("an aborted response body cannot become a successful null workspace", async (t) => {
  const controller = new AbortController();
  t.mock.method(globalThis, "fetch", async (_url, options) => {
    assert.equal(options.signal, controller.signal);
    return {
      ok: true,
      headers: new Headers(),
      json: async () => {
        controller.abort();
        throw new DOMException("Aborted", "AbortError");
      },
    };
  });
  await assert.rejects(
    api.workspace("A", { signal: controller.signal, includeFinancials: false }),
    { name: "AbortError" },
  );
});

test("a non-JSON server error keeps its useful API failure", async (t) => {
  t.mock.method(globalThis, "fetch", async () => ({
    ok: false,
    status: 503,
    headers: new Headers(),
    json: async () => {
      throw new SyntaxError("HTML response");
    },
  }));
  await assert.rejects(api.workspace("A"), { name: "ApiError", status: 503 });
});

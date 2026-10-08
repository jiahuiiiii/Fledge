// Browser contract tests mock only the new channel API, never send to Telegram.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
    });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let data = {
      configured: false,
      linked: false,
      enabled: false,
      active: false,
      token_changed: false,
      pending: false,
      deliveries: [],
      watches: 0,
    };
    let sends = 0,
      connections = 0;
    await page.route("**/api/v1/telegram**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let result = data;
      if (path.endsWith("/connect")) {
        connections++;
        result = {
          url: "https://t.me/ThesisTestBot?start=" + "a".repeat(43),
          bot_username: "ThesisTestBot",
        };
      }
      if (path.endsWith("/check"))
        data = {
          ...data,
          linked: true,
          chat_label: "@test_owner",
          bot_username: "ThesisTestBot",
        };
      if (path.endsWith("/delivery")) {
        let on = route.request().postDataJSON().enabled;
        data = { ...data, enabled: on, active: on };
      }
      if (path.endsWith("/test")) {
        sends++;
        data = {
          ...data,
          deliveries: [
            {
              id: "a",
              kind: "test",
              status: "queued",
              created_at: new Date().toISOString(),
              attempts: 0,
            },
          ],
        };
      }
      if (path.endsWith("/disconnect"))
        data = {
          ...data,
          enabled: false,
          active: false,
          linked: false,
          chat_label: null,
        };
      if (!path.endsWith("/connect")) result = data;
      await route.fulfill({ json: { result } });
    });
    await page.goto(
      process.env.THESIS_TEST_URL +
        "/?company=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa&view=workspace",
    );
    await page.locator(".company-header").waitFor();
    await page
      .getByRole("button", { name: "Telegram alerts", exact: true })
      .click();
    const dialog = page.getByRole("dialog", { name: "Telegram alerts" });
    await dialog
      .getByRole("heading", { name: "Set up your bot once" })
      .waitFor();
    assert.equal(sends, 0);
    for (const width of [320, 390, 1440, 1920]) {
      await page.setViewportSize({ width, height: 1000 });
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      );
      assert(
        await dialog.evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
      );
      await page.screenshot({
        path: `/private/tmp/thesis-telegram-setup-${width}.png`,
      });
    }
    data.configured = true;
    await dialog.getByRole("button", { name: "Check setup" }).click();
    await dialog
      .getByRole("button", { name: "Connect Telegram", exact: true })
      .click();
    const link = dialog.getByRole("link", { name: "Open Telegram" });
    await link.waitFor();
    assert.match(
      await link.getAttribute("href"),
      /^https:\/\/t.me\/ThesisTestBot\?start=/,
    );
    assert.equal(connections, 1);
    await dialog
      .getByRole("button", { name: "Check connection", exact: true })
      .click();
    await dialog.getByRole("heading", { name: "@test_owner" }).waitFor();
    const checkbox = dialog.getByRole("checkbox", {
      name: /Send future alerts/,
    });
    assert.equal(await checkbox.isChecked(), false);
    await checkbox.check();
    await dialog.getByText("Delivery on", { exact: true }).waitFor();
    await dialog.getByRole("button", { name: "Send a test message" }).click();
    await dialog.getByText("Waiting to send", { exact: true }).waitFor();
    assert.equal(sends, 1);
    data.deliveries[0] = {
      ...data.deliveries[0],
      status: "uncertain",
      error:
        "Delivery could not be confirmed. Check Telegram; no automatic retry.",
    };
    await dialog
      .getByText("Delivery unconfirmed", { exact: true })
      .waitFor({ timeout: 8000 });
    assert.equal(sends, 1);
    for (const width of [320, 390, 1440, 1920]) {
      await page.setViewportSize({ width, height: 1000 });
      assert(
        await dialog.evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
      );
      await page.screenshot({
        path: `/private/tmp/thesis-telegram-linked-${width}.png`,
      });
    }
    await checkbox.uncheck();
    await dialog.getByText("Delivery off", { exact: true }).waitFor();
    await dialog
      .getByRole("button", { name: "Disconnect", exact: true })
      .click();
    await dialog
      .getByRole("button", { name: "Connect Telegram", exact: true })
      .waitFor();
    await dialog.getByRole("button", { name: "Close dialog" }).click();
    await page
      .getByRole("button", { name: "Telegram alerts", exact: true })
      .focus();
    await page.keyboard.press("Enter");
    await dialog.waitFor();
    await page.keyboard.press("Escape");
    await dialog.waitFor({ state: "hidden" });
    // The clean owner journey must also expose setup before a company exists.
    await page.route("**/api/v1/workspace**", (route) =>
      route.fulfill({
        json: {
          result: { empty: true, workspace_reset_at: "2026-10-05T00:00:00Z" },
        },
      }),
    );
    await page.reload();
    await page
      .getByRole("button", { name: /Add your first company/ })
      .waitFor();
    await page
      .getByRole("button", { name: "Telegram alerts", exact: true })
      .click();
    await dialog
      .getByRole("button", { name: "Connect Telegram", exact: true })
      .waitFor();
    assert.deepEqual(errors, []);
    console.log(
      "Telegram setup, pairing, explicit opt-in, delivery feedback, pause/disconnect, keyboard access and four viewport sizes passed; no external sends.",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});

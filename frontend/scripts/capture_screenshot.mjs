import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const baseUrl = process.env.ATLAS_SCREENSHOT_URL ?? "http://localhost:5173";
const output = resolve(
  process.env.ATLAS_SCREENSHOT_PATH ?? "../assets/screenshots/dashboard.png",
);

await mkdir(dirname(output), { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1440, height: 960 },
  deviceScaleFactor: 1,
});

await page.goto(baseUrl, { waitUntil: "networkidle" });
await page.getByRole("button", { name: "What is our enterprise refund policy?" }).click();
await page.locator(".source-card").first().waitFor({ state: "visible" });
await page.screenshot({ path: output, fullPage: true });
await browser.close();

console.log(`Saved dashboard screenshot to ${output}`);

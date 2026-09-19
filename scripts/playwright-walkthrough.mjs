import { chromium } from "playwright";
import path from "node:path";
import fs from "node:fs";

const out = "/opt/cursor/artifacts";
fs.mkdirSync(out, { recursive: true });

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.on("pageerror", (e) => console.log("PAGEERROR", e.message));

  await page.goto("http://localhost:5173/landing", { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(out, "walkthrough_landing.png"), fullPage: true });
  console.log("landing ok");

  await page.goto("http://localhost:5173/login");
  await page.fill("#email", "demo@interviewpilot.ai");
  await page.fill("#password", "demo12345");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/dashboard", { timeout: 15000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(out, "walkthrough_dashboard.png"), fullPage: true });
  console.log("dashboard ok");

  await page.goto("http://localhost:5173/session/new");
  await page.getByRole("button", { name: "Skip to end" }).click();
  await page.getByRole("button", { name: "Start Session" }).click();
  await page.waitForURL("**/session/**", { timeout: 15000 });
  await page.waitForTimeout(600);
  console.log("session", page.url());

  await page.getByLabel("Manual question input").fill("What is normalization in SQL?");
  await page.getByRole("button", { name: "Answer", exact: true }).click();
  await page.waitForTimeout(3500);
  await page.screenshot({ path: path.join(out, "walkthrough_session_answer.png"), fullPage: true });
  console.log("answer screenshot ok");

  const start = page.getByRole("button", { name: "Start", exact: true });
  if (await start.count()) {
    await start.click();
    await page.waitForTimeout(5000);
    await page.screenshot({ path: path.join(out, "walkthrough_session_live.png"), fullPage: true });
    console.log("live screenshot ok");
  }

  await page.goto("http://localhost:5173/mock-interview");
  await page.getByRole("button", { name: "Start mock interview" }).click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(out, "walkthrough_mock_interview.png"), fullPage: true });
  console.log("mock ok");

  console.log("DONE", fs.readdirSync(out).filter((f) => f.startsWith("walkthrough_")));
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

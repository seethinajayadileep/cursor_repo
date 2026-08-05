import { createApp } from "./app.js";
import { config } from "./config/index.js";
import { dailyDigestService } from "./services/alerts/dailyDigest.js";
import { cacheService } from "./services/cache/cacheService.js";
import { databaseService } from "./services/database/databaseService.js";

async function main() {
  await cacheService.init();
  await databaseService.init();

  const app = createApp();
  const host = process.env.HOST ?? "0.0.0.0";
  app.listen(config.port, host, () => {
    console.log(`Scout API listening on http://${host}:${config.port}`);
    console.log(
      `Mode — Apify: ${config.apifyToken ? "live" : "demo"}, AI: ${config.openaiApiKey ? "openai" : "heuristic"}, Cache: ${cacheService.mode()}, DB: ${databaseService.mode()}`
    );
    dailyDigestService.startCron();
  });
}

main().catch((error) => {
  console.error("Failed to start server:", error);
  process.exit(1);
});

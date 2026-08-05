import { createApp } from "./app.js";
import { config } from "./config/index.js";
import { cacheService } from "./services/cache/cacheService.js";
import { databaseService } from "./services/database/databaseService.js";

async function main() {
  await cacheService.init();
  await databaseService.init();

  const app = createApp();
  app.listen(config.port, () => {
    console.log(`Scout API listening on http://localhost:${config.port}`);
    console.log(
      `Mode — Apify: ${config.apifyToken ? "live" : "demo"}, AI: ${config.openaiApiKey ? "openai" : "heuristic"}, Cache: ${cacheService.mode()}, DB: ${databaseService.mode()}`
    );
  });
}

main().catch((error) => {
  console.error("Failed to start server:", error);
  process.exit(1);
});

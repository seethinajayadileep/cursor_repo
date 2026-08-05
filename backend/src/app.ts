import cors, { type CorsOptions } from "cors";
import express from "express";
import { ZodError } from "zod";
import { config } from "./config/index.js";
import { apiRouter } from "./routes/api.js";
import { portalRouter } from "./routes/portal.js";

function resolveCorsOrigin(): CorsOptions["origin"] {
  const configured = config.corsOrigin
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  return (origin, callback) => {
    if (!origin) {
      callback(null, true);
      return;
    }
    if (configured.includes("*") || configured.includes(origin)) {
      callback(null, true);
      return;
    }
    // Allow Vercel preview URLs when a production vercel.app origin is configured
    try {
      if (
        configured.some((o) => o.includes("vercel.app")) &&
        /\.vercel\.app$/.test(new URL(origin).hostname)
      ) {
        callback(null, true);
        return;
      }
    } catch {
      /* ignore invalid origin */
    }
    callback(new Error(`CORS blocked for origin: ${origin}`));
  };
}

export function createApp() {
  const app = express();
  app.set("trust proxy", 1);

  app.use(
    cors({
      origin: resolveCorsOrigin(),
      credentials: true,
    })
  );
  app.use(express.json({ limit: "2mb" }));
  app.use(express.urlencoded({ extended: true }));

  app.get("/", (_req, res) => {
    res.json({
      name: "Scout Job Discovery API",
      version: "1.0.0",
      docs: "/api/health",
    });
  });

  app.use("/api", apiRouter);
  app.use("/api/portal", portalRouter);

  app.use(
    (
      err: unknown,
      _req: express.Request,
      res: express.Response,
      _next: express.NextFunction
    ) => {
      if (err instanceof ZodError) {
        res.status(400).json({
          error: "Validation failed",
          details: err.flatten(),
        });
        return;
      }
      console.error(err);
      res.status(500).json({
        error: err instanceof Error ? err.message : "Internal server error",
      });
    }
  );

  return app;
}

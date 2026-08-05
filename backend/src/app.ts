import cors from "cors";
import express from "express";
import { ZodError } from "zod";
import { config } from "./config/index.js";
import { apiRouter } from "./routes/api.js";

export function createApp() {
  const app = express();

  app.use(
    cors({
      origin: config.corsOrigin.split(",").map((s) => s.trim()),
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

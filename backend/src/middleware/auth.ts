import type { NextFunction, Request, Response } from "express";
import { authService, type AuthTokenPayload } from "../services/auth/authService.js";

export interface AuthedRequest extends Request {
  user?: AuthTokenPayload;
}

export function requireAuth(req: AuthedRequest, res: Response, next: NextFunction) {
  try {
    const header = req.headers.authorization || "";
    const token = header.startsWith("Bearer ") ? header.slice(7) : "";
    if (!token) {
      res.status(401).json({ error: "Login required" });
      return;
    }
    req.user = authService.verify(token);
    next();
  } catch {
    res.status(401).json({ error: "Invalid or expired session" });
  }
}

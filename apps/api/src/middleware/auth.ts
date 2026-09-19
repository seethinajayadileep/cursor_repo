import type { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import type { AppContext } from "../context.js";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  plan: string;
}

declare global {
  namespace Express {
    interface Request {
      user?: AuthUser;
    }
  }
}

export function signToken(ctx: AppContext, user: AuthUser): string {
  return jwt.sign(user, ctx.config.authSecret, { expiresIn: "7d" });
}

export function requireAuth(ctx: AppContext) {
  return (req: Request, res: Response, next: NextFunction) => {
    const header = req.headers.authorization;
    if (!header?.startsWith("Bearer ")) {
      return res.status(401).json({ error: "Authentication required" });
    }
    try {
      const payload = jwt.verify(header.slice(7), ctx.config.authSecret) as AuthUser;
      req.user = payload;
      ctx.requestCount += 1;
      next();
    } catch {
      return res.status(401).json({ error: "Invalid or expired session" });
    }
  };
}

import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { config } from "../../config/index.js";
import type { PortalUser } from "../../types/portal.js";
import { createId } from "../../utils/helpers.js";
import { databaseService } from "../database/databaseService.js";

export interface AuthTokenPayload {
  sub: string;
  email: string;
  name: string;
}

export class AuthService {
  async register(input: {
    email: string;
    password: string;
    name: string;
  }): Promise<{ user: Omit<PortalUser, "passwordHash">; token: string }> {
    const email = input.email.trim().toLowerCase();
    if (!email || !input.password || input.password.length < 6) {
      throw new Error("Valid email and password (min 6 chars) required");
    }
    const existing = await databaseService.findUserByEmail(email);
    if (existing) throw new Error("Email already registered");

    const user: PortalUser = {
      id: createId("user"),
      email,
      name: input.name.trim() || email.split("@")[0],
      passwordHash: await bcrypt.hash(input.password, 10),
      createdAt: new Date().toISOString(),
    };
    await databaseService.createUser(user);
    await databaseService.ensureDefaultPrefs(user.id);

    return {
      user: this.publicUser(user),
      token: this.sign(user),
    };
  }

  async login(input: {
    email: string;
    password: string;
  }): Promise<{ user: Omit<PortalUser, "passwordHash">; token: string }> {
    const email = input.email.trim().toLowerCase();
    const user = await databaseService.findUserByEmail(email);
    if (!user) throw new Error("Invalid email or password");
    const ok = await bcrypt.compare(input.password, user.passwordHash);
    if (!ok) throw new Error("Invalid email or password");
    return { user: this.publicUser(user), token: this.sign(user) };
  }

  verify(token: string): AuthTokenPayload {
    return jwt.verify(token, config.jwtSecret) as AuthTokenPayload;
  }

  private sign(user: PortalUser): string {
    const payload: AuthTokenPayload = {
      sub: user.id,
      email: user.email,
      name: user.name,
    };
    return jwt.sign(payload, config.jwtSecret, { expiresIn: "30d" });
  }

  private publicUser(user: PortalUser): Omit<PortalUser, "passwordHash"> {
    const { passwordHash: _, ...rest } = user;
    return rest;
  }
}

export const authService = new AuthService();

import { Router } from "express";
import multer from "multer";
import { z } from "zod";
import { config, hasTelegram } from "../config/index.js";
import { requireAuth, type AuthedRequest } from "../middleware/auth.js";
import { dailyDigestService } from "../services/alerts/dailyDigest.js";
import { authService } from "../services/auth/authService.js";
import { databaseService } from "../services/database/databaseService.js";
import { extractSkillsFromText } from "../services/jobs/normalize.js";
import { extractResumeText } from "../services/resume/parseResume.js";
import { telegramService } from "../services/telegram/telegramService.js";
import type { PortalPrefs } from "../types/portal.js";

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 },
});

export const portalRouter = Router();

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6).max(100),
  name: z.string().min(1).max(80).optional(),
});

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

const prefsSchema = z.object({
  role: z.string().min(1).max(120).optional(),
  roles: z.array(z.string().min(1).max(120)).min(1).max(5).optional(),
  location: z.string().min(1).max(120),
  experienceLevel: z.string().default("any"),
  employmentType: z.string().default("any"),
  workMode: z.string().default("any"),
  companySize: z.string().default("any"),
  salaryMin: z.number().nonnegative().optional(),
  salaryMax: z.number().nonnegative().optional(),
  skillsMode: z.enum(["auto", "manual"]).default("auto"),
  manualSkills: z.array(z.string().min(1).max(80)).max(40).default([]),
  alertsEnabled: z.boolean().default(true),
  topN: z.number().int().min(1).max(10).default(5),
});

const chatIdSchema = z.object({
  chatId: z
    .string()
    .min(1)
    .max(40)
    .regex(/^-?\d+$/, "Chat ID must be numeric"),
  username: z.string().max(80).optional(),
});

portalRouter.post("/auth/register", async (req, res, next) => {
  try {
    const body = registerSchema.parse(req.body);
    const result = await authService.register({
      email: body.email,
      password: body.password,
      name: body.name || body.email.split("@")[0],
    });
    res.status(201).json(result);
  } catch (error) {
    if (error instanceof Error && /already registered|required/i.test(error.message)) {
      res.status(400).json({ error: error.message });
      return;
    }
    next(error);
  }
});

portalRouter.post("/auth/login", async (req, res, next) => {
  try {
    const body = loginSchema.parse(req.body);
    const result = await authService.login(body);
    res.json(result);
  } catch (error) {
    if (error instanceof Error && /invalid/i.test(error.message)) {
      res.status(401).json({ error: error.message });
      return;
    }
    next(error);
  }
});

portalRouter.get("/me", requireAuth, async (req: AuthedRequest, res, next) => {
  try {
    const userId = req.user!.sub;
    const user = await databaseService.findUserById(userId);
    if (!user) {
      res.status(404).json({ error: "User not found" });
      return;
    }
    const prefs = await databaseService.ensureDefaultPrefs(userId);
    const resume = await databaseService.getResume(userId);
    const telegram = await databaseService.getTelegram(userId);
    const runs = await databaseService.listAlertRuns(userId, 5);
    res.json({
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        createdAt: user.createdAt,
      },
      prefs,
      resume: resume
        ? {
            skills: resume.skills,
            updatedAt: resume.updatedAt,
            characters: resume.text.length,
          }
        : null,
      telegram: {
        linked: Boolean(telegram?.chatId),
        chatId: telegram?.chatId || null,
        username: telegram?.username || null,
        linkedAt: telegram?.linkedAt || null,
        botConfigured: hasTelegram,
        botUsername:
          telegramService.botUsername() || config.telegramBotUsername || null,
      },
      recentRuns: runs,
      schedule: {
        cron: config.digestCron,
        timezone: config.digestTimezone,
      },
    });
  } catch (error) {
    next(error);
  }
});

portalRouter.put("/prefs", requireAuth, async (req: AuthedRequest, res, next) => {
  try {
    const body = prefsSchema.parse(req.body);
    const roles =
      body.roles && body.roles.length > 0
        ? body.roles.map((r) => r.trim()).filter(Boolean)
        : body.role
          ? [body.role.trim()]
          : ["Software Engineer"];
    const prefs: PortalPrefs = {
      userId: req.user!.sub,
      role: roles[0],
      roles,
      location: body.location,
      experienceLevel: body.experienceLevel,
      employmentType: body.employmentType,
      workMode: body.workMode,
      companySize: body.companySize,
      salaryMin: body.salaryMin,
      salaryMax: body.salaryMax,
      skillsMode: body.skillsMode,
      manualSkills: body.manualSkills,
      alertsEnabled: body.alertsEnabled,
      topN: body.topN,
      updatedAt: new Date().toISOString(),
    };
    const saved = await databaseService.savePrefs(prefs);
    res.json({ prefs: saved });
  } catch (error) {
    next(error);
  }
});

portalRouter.post(
  "/resume",
  requireAuth,
  upload.single("resume"),
  async (req: AuthedRequest, res, next) => {
    try {
      const userId = req.user!.sub;
      const pasted = String(req.body.text ?? "");
      const { text, source } = await extractResumeText(req.file, pasted);
      if (!text.trim()) {
        res.status(400).json({ error: "Resume text or PDF required" });
        return;
      }
      const skills = extractSkillsFromText(text);
      await databaseService.saveResume(userId, text.slice(0, 50000), skills);
      res.json({
        skills,
        characters: text.length,
        source,
        message:
          source === "pdf"
            ? "PDF resume parsed and saved"
            : "Resume saved for personalized digests",
      });
    } catch (error) {
      next(error);
    }
  }
);

portalRouter.post("/telegram/link", requireAuth, async (req: AuthedRequest, res, next) => {
  try {
    const { token, deepLink, botUsername } = await telegramService.createLinkToken(
      req.user!.sub
    );
    res.json({
      token,
      deepLink,
      botUsername,
      instructions: deepLink
        ? "Open the Telegram link and press Start. The bot will link automatically."
        : `Bot username unknown. Message your bot with: /start ${token}`,
      botConfigured: hasTelegram,
      polling: hasTelegram,
    });
  } catch (error) {
    next(error);
  }
});

portalRouter.post("/telegram/chat-id", requireAuth, async (req: AuthedRequest, res, next) => {
  try {
    const body = chatIdSchema.parse(req.body);
    await databaseService.linkTelegramByChatId(
      req.user!.sub,
      body.chatId,
      body.username ?? null
    );
    if (hasTelegram) {
      await telegramService.sendMessage(
        body.chatId,
        "✅ Scout Portal connected via Chat ID. You’ll receive fresh job digests around 5:00 AM."
      );
    }
    res.json({ ok: true, chatId: body.chatId });
  } catch (error) {
    next(error);
  }
});

portalRouter.post("/telegram/unlink", requireAuth, async (req: AuthedRequest, res, next) => {
  try {
    await databaseService.unlinkTelegram(req.user!.sub);
    res.json({ ok: true });
  } catch (error) {
    next(error);
  }
});

// Public webhook for Telegram (optional — polling also works)
portalRouter.post("/telegram/webhook", async (req, res, next) => {
  try {
    await telegramService.handleUpdate(req.body);
    res.json({ ok: true });
  } catch (error) {
    next(error);
  }
});

portalRouter.post("/digest/run", requireAuth, async (req: AuthedRequest, res, next) => {
  try {
    const ok = await dailyDigestService.runForUser(req.user!.sub);
    const runs = await databaseService.listAlertRuns(req.user!.sub, 1);
    res.json({ ok, latest: runs[0] ?? null });
  } catch (error) {
    next(error);
  }
});

portalRouter.get("/digest/history", requireAuth, async (req: AuthedRequest, res, next) => {
  try {
    const runs = await databaseService.listAlertRuns(req.user!.sub, 20);
    res.json({ runs });
  } catch (error) {
    next(error);
  }
});

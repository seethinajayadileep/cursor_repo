import cron from "node-cron";
import { config } from "../../config/index.js";
import type { SearchCriteria } from "../../types/index.js";
import { createId } from "../../utils/helpers.js";
import { databaseService } from "../database/databaseService.js";
import { jobSearchService } from "../jobs/searchService.js";
import { telegramService } from "../telegram/telegramService.js";

export class DailyDigestService {
  private running = false;

  startCron(): void {
    if (!cron.validate(config.digestCron)) {
      console.warn("[digest] Invalid DIGEST_CRON:", config.digestCron);
      return;
    }
    cron.schedule(
      config.digestCron,
      () => {
        void this.runAll("cron");
      },
      { timezone: config.digestTimezone }
    );
    console.log(
      `[digest] Scheduled "${config.digestCron}" tz=${config.digestTimezone}`
    );
  }

  async runAll(trigger: "cron" | "manual" = "manual"): Promise<{
    processed: number;
    sent: number;
    errors: number;
  }> {
    if (this.running) {
      return { processed: 0, sent: 0, errors: 0 };
    }
    this.running = true;
    let processed = 0;
    let sent = 0;
    let errors = 0;
    try {
      const users = await databaseService.listDigestUsers();
      console.log(`[digest] ${trigger}: ${users.length} users`);
      for (const entry of users) {
        processed += 1;
        try {
          const ok = await this.runForUser(entry.user.id);
          if (ok) sent += 1;
        } catch (error) {
          errors += 1;
          console.warn(`[digest] user ${entry.user.id} failed:`, error);
          await databaseService.saveAlertRun({
            id: createId("ar"),
            userId: entry.user.id,
            ranAt: new Date().toISOString(),
            status: "error",
            jobsSent: 0,
            message: error instanceof Error ? error.message : "Digest failed",
          });
        }
      }
    } finally {
      this.running = false;
    }
    return { processed, sent, errors };
  }

  async runForUser(userId: string): Promise<boolean> {
    const prefs = await databaseService.getPrefs(userId);
    const telegram = await databaseService.getTelegram(userId);
    const resume = await databaseService.getResume(userId);

    if (!prefs?.alertsEnabled) {
      await databaseService.saveAlertRun({
        id: createId("ar"),
        userId,
        ranAt: new Date().toISOString(),
        status: "skipped",
        jobsSent: 0,
        message: "Alerts disabled",
      });
      return false;
    }
    if (!telegram?.chatId) {
      await databaseService.saveAlertRun({
        id: createId("ar"),
        userId,
        ranAt: new Date().toISOString(),
        status: "skipped",
        jobsSent: 0,
        message: "Telegram not linked",
      });
      return false;
    }

    const criteria: SearchCriteria = {
      role: prefs.role,
      location: prefs.location,
      experienceLevel: prefs.experienceLevel as SearchCriteria["experienceLevel"],
      employmentType: prefs.employmentType as SearchCriteria["employmentType"],
      workMode: prefs.workMode as SearchCriteria["workMode"],
      companySize: prefs.companySize as SearchCriteria["companySize"],
      salaryMin: prefs.salaryMin,
      salaryMax: prefs.salaryMax,
      skills: resume?.skills,
      userId,
    };

    const result = await jobSearchService.search(criteria, {
      userId,
      forceRefresh: true,
      resume: resume
        ? { text: resume.text, skills: resume.skills }
        : null,
    });

    const topN = Math.max(1, Math.min(10, prefs.topN || config.digestTopN));
    const top = result.jobs.slice(0, topN);

    if (top.length === 0) {
      await telegramService.sendMessage(
        telegram.chatId,
        `Scout morning digest\nNo matching roles today for ${prefs.role} · ${prefs.location}.`
      );
      await databaseService.saveAlertRun({
        id: createId("ar"),
        userId,
        ranAt: new Date().toISOString(),
        status: "success",
        jobsSent: 0,
        message: "No jobs matched",
      });
      return true;
    }

    const lines = [
      `☀️ Scout morning digest (${prefs.role} · ${prefs.location})`,
      `Top ${top.length} matches · mode ${result.mode}`,
      "",
      ...top.map(
        (j, i) =>
          `${i + 1}. AI ${j.score} · ${j.title} @ ${j.company}\n${j.location}${j.salary ? ` · ${j.salary}` : ""}\n${j.applyUrl || ""}`
      ),
      "",
      `Open portal: ${config.publicAppUrl}/portal`,
    ];

    const ok = await telegramService.sendMessage(
      telegram.chatId,
      lines.join("\n")
    );

    await databaseService.saveAlertRun({
      id: createId("ar"),
      userId,
      ranAt: new Date().toISOString(),
      status: ok ? "success" : "error",
      jobsSent: top.length,
      message: ok ? "Digest sent" : "Telegram send failed",
      preview: top.map((j) => ({
        title: j.title,
        company: j.company,
        score: j.score,
        applyUrl: j.applyUrl,
      })),
    });

    return ok;
  }
}

export const dailyDigestService = new DailyDigestService();

import { config, hasTelegram } from "../../config/index.js";
import { createId } from "../../utils/helpers.js";
import { databaseService } from "../database/databaseService.js";

type TelegramUpdate = {
  update_id?: number;
  message?: {
    text?: string;
    chat?: { id: number; username?: string; type?: string };
    from?: { username?: string };
  };
};

export class TelegramService {
  private resolvedUsername: string | null = null;
  private polling = false;
  private offset = 0;

  isConfigured(): boolean {
    return hasTelegram;
  }

  botUsername(): string | null {
    const fromEnv = config.telegramBotUsername?.replace(/^@/, "") || "";
    if (fromEnv) return fromEnv;
    return this.resolvedUsername;
  }

  botLink(token: string): string | null {
    const username = this.botUsername();
    if (!username) return null;
    return `https://t.me/${username}?start=${token}`;
  }

  async ensureBotUsername(): Promise<string | null> {
    const existing = this.botUsername();
    if (existing) return existing;
    if (!hasTelegram) return null;
    try {
      const res = await fetch(
        `https://api.telegram.org/bot${config.telegramBotToken}/getMe`
      );
      const data = (await res.json()) as {
        ok?: boolean;
        result?: { username?: string };
      };
      if (data.ok && data.result?.username) {
        this.resolvedUsername = data.result.username;
        console.log(`[telegram] Bot username resolved: @${this.resolvedUsername}`);
        return this.resolvedUsername;
      }
    } catch (error) {
      console.warn("[telegram] getMe failed:", error);
    }
    return null;
  }

  async createLinkToken(userId: string): Promise<{
    token: string;
    deepLink: string | null;
    botUsername: string | null;
  }> {
    await this.ensureBotUsername();
    const token = createId("tg");
    await databaseService.setTelegramLinkToken(userId, token);
    return {
      token,
      deepLink: this.botLink(token),
      botUsername: this.botUsername(),
    };
  }

  async handleUpdate(update: TelegramUpdate): Promise<void> {
    const text = update.message?.text?.trim() ?? "";
    const chatId = update.message?.chat?.id;
    if (!chatId || !text.startsWith("/start")) return;

    const parts = text.split(/\s+/);
    const token = parts[1];
    const username =
      update.message?.from?.username ??
      update.message?.chat?.username ??
      null;

    if (!token) {
      await this.sendMessage(
        String(chatId),
        "Welcome to Scout Digests.\n\nTo link your account:\n1. Open the Scout Portal\n2. Tap Connect Telegram\n3. Open the bot link (or send /start <token>)\n\nOr paste your Chat ID in the portal (get it from @userinfobot)."
      );
      return;
    }

    const linked = await databaseService.linkTelegramByToken(
      token,
      String(chatId),
      username
    );
    if (!linked) {
      await this.sendMessage(
        String(chatId),
        "That link expired or is invalid. Generate a new one from the Scout Portal."
      );
      return;
    }

    await this.sendMessage(
      String(chatId),
      "✅ Linked to Scout Portal. You’ll get fresh job digests around 5:00 AM (duplicates won’t be resent)."
    );
  }

  async sendMessage(chatId: string, text: string): Promise<boolean> {
    if (!hasTelegram) {
      console.log(`[telegram:demo] to=${chatId} ${text.slice(0, 120)}`);
      return true;
    }
    try {
      const res = await fetch(
        `https://api.telegram.org/bot${config.telegramBotToken}/sendMessage`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chat_id: chatId,
            text,
            disable_web_page_preview: true,
          }),
        }
      );
      if (!res.ok) {
        const body = await res.text();
        console.warn("[telegram] send failed:", res.status, body);
        return false;
      }
      return true;
    } catch (error) {
      console.warn("[telegram] send error:", error);
      return false;
    }
  }

  /** Long-poll Telegram so /start deep links work without a public webhook. */
  startPolling(): void {
    if (!hasTelegram || this.polling) return;
    this.polling = true;
    console.log("[telegram] Starting getUpdates polling for account linking");
    void this.pollLoop();
  }

  private async pollLoop(): Promise<void> {
    while (this.polling) {
      try {
        const url = new URL(
          `https://api.telegram.org/bot${config.telegramBotToken}/getUpdates`
        );
        url.searchParams.set("timeout", "25");
        url.searchParams.set("offset", String(this.offset));
        url.searchParams.set("allowed_updates", JSON.stringify(["message"]));

        const res = await fetch(url.toString());
        const data = (await res.json()) as {
          ok?: boolean;
          result?: TelegramUpdate[];
          description?: string;
        };

        if (!data.ok) {
          // Webhook may be set — delete it so polling works
          if (/webhook/i.test(data.description ?? "")) {
            console.warn("[telegram] Clearing conflicting webhook for polling");
            await fetch(
              `https://api.telegram.org/bot${config.telegramBotToken}/deleteWebhook?drop_pending_updates=false`
            );
          } else {
            console.warn("[telegram] getUpdates error:", data.description);
            await sleep(5000);
          }
          continue;
        }

        for (const update of data.result ?? []) {
          if (typeof update.update_id === "number") {
            this.offset = update.update_id + 1;
          }
          await this.handleUpdate(update);
        }
      } catch (error) {
        console.warn("[telegram] poll error:", error);
        await sleep(5000);
      }
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const telegramService = new TelegramService();

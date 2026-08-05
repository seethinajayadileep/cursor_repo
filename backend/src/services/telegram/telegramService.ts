import { config, hasTelegram } from "../../config/index.js";
import { createId } from "../../utils/helpers.js";
import { databaseService } from "../database/databaseService.js";

export class TelegramService {
  isConfigured(): boolean {
    return hasTelegram;
  }

  botLink(token: string): string | null {
    if (!config.telegramBotUsername) return null;
    return `https://t.me/${config.telegramBotUsername.replace(/^@/, "")}?start=${token}`;
  }

  async createLinkToken(userId: string): Promise<{ token: string; deepLink: string | null }> {
    const token = createId("tg");
    await databaseService.setTelegramLinkToken(userId, token);
    return { token, deepLink: this.botLink(token) };
  }

  async handleUpdate(update: {
    message?: {
      text?: string;
      chat?: { id: number; username?: string };
    };
  }): Promise<void> {
    const text = update.message?.text?.trim() ?? "";
    const chatId = update.message?.chat?.id;
    if (!chatId || !text.startsWith("/start")) return;

    const parts = text.split(/\s+/);
    const token = parts[1];
    if (!token) {
      await this.sendMessage(
        String(chatId),
        "Welcome to Scout Digests. Open the Portal and tap Connect Telegram to link your account."
      );
      return;
    }

    const linked = await databaseService.linkTelegramByToken(
      token,
      String(chatId),
      update.message?.chat?.username ?? null
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
      "✅ Linked to Scout Portal. You’ll get job digests around 5:00 AM."
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
}

export const telegramService = new TelegramService();

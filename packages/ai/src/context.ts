import type { ResumeProfile, TranscriptSegment } from "@interviewpilot/shared";

export interface AnswerContext {
  question: string;
  category: string;
  resume?: ResumeProfile;
  jobDescription?: string;
  instructions?: string;
  retrievedChunks: string[];
  recentTranscript: TranscriptSegment[];
  previousAnswers: string[];
  responseMode: "fast" | "balanced" | "detailed";
  aiMode: string;
  language: string;
}

export function buildContextPrompt(ctx: AnswerContext): string {
  const resumeFacts = ctx.resume
    ? JSON.stringify(
        {
          name: ctx.resume.name,
          skills: ctx.resume.skills.slice(0, 20),
          technologies: ctx.resume.technologies.slice(0, 20),
          experience: ctx.resume.experience.slice(0, 5),
          projects: ctx.resume.projects.slice(0, 5),
          education: ctx.resume.education.slice(0, 3),
          certifications: ctx.resume.certifications.slice(0, 5),
        },
        null,
        2
      )
    : "No resume provided.";

  const transcript = ctx.recentTranscript
    .slice(-12)
    .map((s) => `${s.speaker}: ${s.text}`)
    .join("\n");

  const chunks = ctx.retrievedChunks.slice(0, 5).map((c, i) => `[${i + 1}] ${c}`).join("\n\n");

  return [
    `Language: ${ctx.language}`,
    `AI mode: ${ctx.aiMode}`,
    `Response mode: ${ctx.responseMode}`,
    `Question category: ${ctx.category}`,
    `User instructions: ${ctx.instructions || "None"}`,
    `Job description:\n${(ctx.jobDescription || "None").slice(0, 2500)}`,
    `Resume facts (authoritative):\n${resumeFacts}`,
    `Retrieved documents:\n${chunks || "None"}`,
    `Recent transcript:\n${transcript || "None"}`,
    `Previous answers (do not repeat verbatim):\n${ctx.previousAnswers.slice(-3).join("\n---\n") || "None"}`,
    `Current question:\n${ctx.question}`,
  ].join("\n\n");
}

export function compressForTokens(text: string, maxChars = 6000): string {
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars) + "\n...[truncated for context budget]";
}

import { uid, nowIso, type GeneratedAnswer, type ResponseMode, type QuestionCategory } from "@interviewpilot/shared";
import { PROMPTS } from "./prompts.js";
import { buildContextPrompt, compressForTokens, type AnswerContext } from "./context.js";

export interface AIProvider {
  readonly name: string;
  generateAnswer(ctx: AnswerContext): Promise<GeneratedAnswer>;
  streamAnswer(ctx: AnswerContext, onToken: (t: string) => void): Promise<GeneratedAnswer>;
  summarizeMeeting(transcript: string): Promise<Record<string, unknown>>;
  mockQuestion(role: string, difficulty: string, asked: string[]): Promise<string>;
  evaluateAnswer(question: string, answer: string): Promise<Record<string, unknown>>;
}

function pickPrompt(category: string): string {
  switch (category) {
    case "behavioral":
      return PROMPTS.behavioral_answer_prompt;
    case "coding":
      return PROMPTS.coding_answer_prompt;
    case "system_design":
      return PROMPTS.system_design_prompt;
    case "technical":
      return PROMPTS.technical_answer_prompt;
    case "hr":
      return PROMPTS.resume_answer_prompt;
    default:
      return PROMPTS.resume_answer_prompt;
  }
}

function demoCode(language: string): string {
  const samples: Record<string, string> = {
    python: `def reverse_list(head):
    prev = None
    curr = head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev`,
    javascript: `function reverseList(head) {
  let prev = null;
  let curr = head;
  while (curr) {
    const next = curr.next;
    curr.next = prev;
    prev = curr;
    curr = next;
  }
  return prev;
}`,
    sql: `SELECT department, AVG(salary) AS avg_salary
FROM employees
GROUP BY department
HAVING AVG(salary) > 70000
ORDER BY avg_salary DESC;`,
  };
  return samples[language] || samples.python;
}

export class DemoAIProvider implements AIProvider {
  readonly name: string = "demo";

  async generateAnswer(ctx: AnswerContext): Promise<GeneratedAnswer> {
    return this.streamAnswer(ctx, () => undefined);
  }

  async streamAnswer(ctx: AnswerContext, onToken: (t: string) => void): Promise<GeneratedAnswer> {
    const skills = ctx.resume?.skills?.slice(0, 5).join(", ") || "the skills listed in your resume";
    const company = ctx.resume?.experience?.[0]?.company;
    const project = ctx.resume?.projects?.[0]?.name;
    const role = ctx.resume?.experience?.[0]?.title;

    let concise = "";
    if (ctx.category === "coding") {
      concise =
        "I'd clarify constraints first, then outline an approach, implement carefully, and walk through complexity and edge cases.";
    } else if (ctx.category === "behavioral") {
      concise = company
        ? `In a relevant situation at ${company}, I focused on clear communication, concrete actions, and measurable outcomes tied to the team's goal.`
        : "I would choose a real example from my experience, explain the situation and stakes, describe the actions I owned, and finish with the outcome and what I learned.";
    } else if (ctx.category === "hr") {
      concise = `I'm a candidate focused on ${skills}. I connect my background to this role's needs and keep answers specific rather than generic.`;
    } else if (ctx.category === "system_design") {
      concise =
        "I'd start from requirements and constraints, propose a simple architecture, call out bottlenecks, and discuss trade-offs around consistency, latency, and cost.";
    } else {
      concise = project
        ? `Based on my work on ${project}${role ? ` as a ${role}` : ""}, I'd answer with a clear definition, a short example, and how I've applied the concept in practice.`
        : `I'd give a direct definition, a short practical example, and relate it to ${skills} where relevant — without inventing experience I don't have.`;
    }

    if (ctx.responseMode === "fast") {
      concise = concise.split(". ").slice(0, 2).join(". ") + (concise.endsWith(".") ? "" : ".");
    }

    const detailed = [
      concise,
      ctx.jobDescription ? "I'd also mirror language from the job description where it matches my real background." : "",
      ctx.retrievedChunks[0] ? "I can anchor details to the uploaded documents rather than guessing." : "",
      "If a detail isn't in my resume or documents, I'll say so instead of inventing it.",
    ]
      .filter(Boolean)
      .join(" ");

    for (const word of (ctx.responseMode === "detailed" ? detailed : concise).split(/(\s+)/)) {
      onToken(word);
      await new Promise((r) => setTimeout(r, 8));
    }

    const answer: GeneratedAnswer = {
      id: uid("ans"),
      questionId: uid("q"),
      mode: ctx.responseMode,
      concise,
      detailed,
      talkingPoints: [
        "Lead with the direct answer",
        "Tie to real resume evidence",
        "Offer one concrete example",
        "Invite a follow-up",
      ],
      followUps: ["Would you like a shorter spoken version?", "Want a STAR version of this?"],
      createdAt: nowIso(),
    };

    if (ctx.category === "behavioral") {
      answer.star = {
        situation: company ? `While working at ${company}` : "In a prior team setting from my experience",
        task: "I needed to resolve a clear goal under time pressure",
        action: "I clarified requirements, coordinated with stakeholders, and executed a practical plan",
        result: "We reached a positive outcome and I documented what to reuse next time",
      };
    }

    if (ctx.category === "coding") {
      const language = /sql/i.test(ctx.question) ? "sql" : /javascript|typescript/i.test(ctx.question) ? "javascript" : "python";
      answer.code = {
        language,
        approach: "Clarify inputs/outputs, choose a simple correct approach, then optimize if needed.",
        algorithm: "Iterate with clear state; prefer readable interview code over clever tricks.",
        code: demoCode(language),
        complexity: language === "sql" ? "Depends on indexes and table size" : "Time O(n), Space O(1)",
        edgeCases: ["Empty input", "Single element", "Invalid or null references"],
        explanation: "This solution is easy to explain aloud and verify with a quick dry run.",
      };
    }

    return answer;
  }

  async summarizeMeeting(transcript: string): Promise<Record<string, unknown>> {
    const lines = transcript.split(/\n/).filter(Boolean);
    return {
      summary: `Conversation covered ${lines.length} turns. Key themes were interview preparation, role fit, and next steps.`,
      keyPoints: lines.slice(0, 5).map((l) => l.slice(0, 120)),
      decisions: ["Continue preparation with mock practice"],
      questions: lines.filter((l) => l.includes("?")).slice(0, 8),
      actionItems: [
        { id: uid("act"), task: "Review resume bullet points", owner: "Candidate", deadline: "", status: "open" },
        { id: uid("act"), task: "Practice one coding question aloud", owner: "Candidate", deadline: "", status: "open" },
      ],
      importantDates: [],
      peopleMentioned: [],
      followUpTasks: ["Export notes", "Schedule another mock interview"],
      insights: ["Answers were clearer when tied to concrete resume evidence."],
    };
  }

  async mockQuestion(role: string, difficulty: string, asked: string[]): Promise<string> {
    const bank = [
      `Tell me about yourself and why you're interested in the ${role} role.`,
      `What relevant skills make you a strong ${role}?`,
      `Describe a challenging project and your contribution.`,
      `How do you prioritize tasks when deadlines conflict?`,
      `Explain a technical concept you use often as a ${role}.`,
      `Write a function that finds duplicates in a list.`,
      `How would you design a URL shortener at a high level?`,
      `Tell me about a time you received critical feedback.`,
    ];
    const next = bank.find((q) => !asked.includes(q)) || bank[Math.floor(Math.random() * bank.length)];
    return difficulty === "hard" ? `${next} Please go deep on trade-offs.` : next;
  }

  async evaluateAnswer(question: string, answer: string): Promise<Record<string, unknown>> {
    const words = answer.trim().split(/\s+/).length;
    const score = Math.max(4, Math.min(9, Math.round(words / 25) + 5));
    return {
      overall: score,
      relevance: score,
      clarity: score - 1,
      structure: score - 1,
      technicalCorrectness: /code|algorithm|complexity|design/i.test(question) ? score : null,
      communication: score,
      completeness: words > 40 ? score : score - 2,
      useOfExamples: /for example|e\.g\.|project|when i/i.test(answer) ? score : score - 2,
      filler: /um+|uh+|like,/i.test(answer) ? "Some filler detected" : "Little filler",
      missingDetails: words < 30 ? ["Add a concrete example", "Quantify impact if available"] : [],
      suggestedImprovement: "Lead with the answer, then one proof point from your resume.",
      betterExample: "Start with a one-sentence answer, then a short STAR or technical walkthrough.",
      topicsToStudy: ["Resume storytelling", "Concise technical explanations"],
      disclaimer: "Practice feedback only — not a prediction of real interview outcomes.",
    };
  }
}

async function openAiCompatibleChat(
  apiKey: string,
  baseUrl: string,
  model: string,
  system: string,
  user: string
): Promise<string> {
  const res = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
      temperature: 0.4,
    }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`AI provider error: ${res.status} ${err}`);
  }
  const data = (await res.json()) as { choices?: Array<{ message?: { content?: string } }> };
  return data.choices?.[0]?.message?.content || "";
}

export class OpenAICompatibleProvider implements AIProvider {
  readonly name = "openai";
  constructor(
    private apiKey: string,
    private baseUrl = "https://api.openai.com/v1",
    private model = "gpt-4o-mini"
  ) {}

  async generateAnswer(ctx: AnswerContext): Promise<GeneratedAnswer> {
    return this.streamAnswer(ctx, () => undefined);
  }

  async streamAnswer(ctx: AnswerContext, onToken: (t: string) => void): Promise<GeneratedAnswer> {
    const system = pickPrompt(ctx.category);
    const user = compressForTokens(buildContextPrompt(ctx));
    const content = await openAiCompatibleChat(this.apiKey, this.baseUrl, this.model, system, user);
    for (const ch of content.match(/.{1,12}/g) || []) {
      onToken(ch);
    }
    return {
      id: uid("ans"),
      questionId: uid("q"),
      mode: ctx.responseMode as ResponseMode,
      concise: content.slice(0, 600),
      detailed: content,
      talkingPoints: content
        .split(/\n/)
        .map((l) => l.replace(/^[-*\d.\s]+/, "").trim())
        .filter(Boolean)
        .slice(0, 5),
      createdAt: nowIso(),
    };
  }

  async summarizeMeeting(transcript: string) {
    const content = await openAiCompatibleChat(
      this.apiKey,
      this.baseUrl,
      this.model,
      PROMPTS.meeting_summary_prompt,
      transcript.slice(0, 12000)
    );
    return { summary: content, keyPoints: [], decisions: [], questions: [], actionItems: [], importantDates: [], peopleMentioned: [], followUpTasks: [] };
  }

  async mockQuestion(role: string, difficulty: string, asked: string[]) {
    return openAiCompatibleChat(
      this.apiKey,
      this.baseUrl,
      this.model,
      PROMPTS.mock_interviewer_prompt,
      `Role: ${role}\nDifficulty: ${difficulty}\nAlready asked: ${asked.join(" | ")}\nAsk the next question only.`
    );
  }

  async evaluateAnswer(question: string, answer: string) {
    const content = await openAiCompatibleChat(
      this.apiKey,
      this.baseUrl,
      this.model,
      "Evaluate the interview answer. Return concise JSON-like feedback fields in plain text.",
      `Question: ${question}\nAnswer: ${answer}`
    );
    return { overall: 7, summary: content, disclaimer: "Practice feedback only." };
  }
}

export class AnthropicCompatibleProvider extends DemoAIProvider {
  readonly name: string = "anthropic";
  constructor(private apiKey: string) {
    super();
  }
  // Falls back to demo-quality local synthesis if Anthropic SDK is not configured in this environment.
  async streamAnswer(ctx: AnswerContext, onToken: (t: string) => void): Promise<GeneratedAnswer> {
    if (!this.apiKey) return super.streamAnswer(ctx, onToken);
    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": this.apiKey,
          "anthropic-version": "2023-06-01",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "claude-3-5-haiku-latest",
          max_tokens: 1024,
          system: pickPrompt(ctx.category),
          messages: [{ role: "user", content: compressForTokens(buildContextPrompt(ctx)) }],
        }),
      });
      if (!res.ok) return super.streamAnswer(ctx, onToken);
      const data = (await res.json()) as { content?: Array<{ text?: string }> };
      const text = data.content?.map((c) => c.text || "").join("\n") || "";
      onToken(text);
      return {
        id: uid("ans"),
        questionId: uid("q"),
        mode: ctx.responseMode,
        concise: text.slice(0, 600),
        detailed: text,
        createdAt: nowIso(),
      };
    } catch {
      return super.streamAnswer(ctx, onToken);
    }
  }
}

export class GoogleCompatibleProvider extends DemoAIProvider {
  readonly name: string = "google";
  constructor(private apiKey: string) {
    super();
  }
}

export class LocalModelProvider extends DemoAIProvider {
  readonly name: string = "local";
}

export function createAIProvider(opts: {
  provider: string;
  openaiApiKey?: string;
  anthropicApiKey?: string;
  googleApiKey?: string;
  demoMode?: boolean;
}): AIProvider {
  if (opts.demoMode || opts.provider === "demo") return new DemoAIProvider();
  if (opts.provider === "openai" && opts.openaiApiKey) {
    return new OpenAICompatibleProvider(opts.openaiApiKey);
  }
  if (opts.provider === "anthropic" && opts.anthropicApiKey) {
    return new AnthropicCompatibleProvider(opts.anthropicApiKey);
  }
  if (opts.provider === "google" && opts.googleApiKey) {
    return new GoogleCompatibleProvider(opts.googleApiKey);
  }
  if (opts.provider === "local") return new LocalModelProvider();
  return new DemoAIProvider();
}

export type { AnswerContext, QuestionCategory };

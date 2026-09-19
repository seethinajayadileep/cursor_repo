import type { QuestionCategory } from "@interviewpilot/shared";

const PATTERNS: Array<{ category: QuestionCategory; re: RegExp }> = [
  { category: "coding", re: /\b(write|implement|code|function|algorithm|leetcode|linked list|binary tree|sql query)\b/i },
  { category: "system_design", re: /\b(design|architect|scale|system design|how would you build|design youtube|design twitter)\b/i },
  { category: "behavioral", re: /\b(tell me about a time|conflict|challenging situation|leadership|failure|mistake)\b/i },
  { category: "hr", re: /\b(tell me about yourself|why (do )?you want|strengths|weaknesses|salary|notice period|relocat)\b/i },
  { category: "situational", re: /\b(what would you do if|how would you handle|suppose|imagine you)\b/i },
  { category: "technical", re: /\b(what is|explain|difference between|how does|normalize|index|complexity|api|database)\b/i },
  { category: "clarification", re: /\b(can you clarify|what do you mean|could you repeat)\b/i },
  { category: "follow_up", re: /\b(follow[- ]?up|and then|can you elaborate|go deeper)\b/i },
];

export function looksLikeQuestion(text: string): boolean {
  const t = text.trim();
  if (!t) return false;
  if (t.endsWith("?")) return true;
  if (/^(tell me|describe|explain|walk me|how |what |why |when |where |who |write |implement |design )/i.test(t)) {
    return true;
  }
  return false;
}

export function classifyQuestion(text: string): { category: QuestionCategory; confidence: number } {
  for (const p of PATTERNS) {
    if (p.re.test(text)) return { category: p.category, confidence: 0.82 };
  }
  if (looksLikeQuestion(text)) return { category: "general", confidence: 0.55 };
  return { category: "general", confidence: 0.2 };
}

export function shouldTriggerDetection(text: string, lastTriggerAt: number, debounceMs = 1200): boolean {
  if (Date.now() - lastTriggerAt < debounceMs) return false;
  return looksLikeQuestion(text) && text.trim().split(/\s+/).length >= 3;
}

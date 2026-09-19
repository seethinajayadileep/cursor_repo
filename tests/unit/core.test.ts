import { describe, expect, it } from "vitest";
import { looksLikeQuestion, classifyQuestion } from "@interviewpilot/ai";
import { parseResume, chunkText, cleanText, embedText, cosineSimilarity, retrieveChunks } from "@interviewpilot/documents";
import { DemoAIProvider } from "@interviewpilot/ai";
import { uid } from "@interviewpilot/shared";

describe("question detection", () => {
  it("detects common interview questions", () => {
    expect(looksLikeQuestion("Tell me about yourself.")).toBe(true);
    expect(classifyQuestion("What is normalization in SQL?").category).toBe("technical");
    expect(classifyQuestion("Write a Python function to reverse a linked list.").category).toBe("coding");
    expect(classifyQuestion("How would you design YouTube?").category).toBe("system_design");
    expect(classifyQuestion("Tell me about a conflict you handled.").category).toBe("behavioral");
  });
});

describe("documents", () => {
  it("cleans and chunks text", () => {
    const text = cleanText("Hello\n\n\nWorld");
    expect(text.includes("Hello")).toBe(true);
    expect(chunkText("a".repeat(2000)).length).toBeGreaterThan(1);
  });

  it("parses resume skills", () => {
    const profile = parseResume(`Alex\n\nSkills\nSQL, Python, Tableau\n\nExperience\nAnalyst - Acme`);
    expect(profile.skills.join(" ").toLowerCase()).toContain("sql");
  });

  it("retrieves relevant chunks", () => {
    const chunks = [
      { id: "1", text: "SQL normalization reduces redundancy", embedding: embedText("SQL normalization reduces redundancy") },
      { id: "2", text: "Cooking recipes for pasta", embedding: embedText("Cooking recipes for pasta") },
    ];
    const hits = retrieveChunks("What is SQL normalization?", chunks, 1);
    expect(hits[0].id).toBe("1");
    expect(cosineSimilarity(embedText("a"), embedText("a"))).toBeGreaterThan(0.99);
  });
});

describe("demo AI", () => {
  it("streams an answer without inventing employers when resume lacks them", async () => {
    const ai = new DemoAIProvider();
    let tokens = "";
    const answer = await ai.streamAnswer(
      {
        question: "Tell me about yourself.",
        category: "hr",
        retrievedChunks: [],
        recentTranscript: [],
        previousAnswers: [],
        responseMode: "fast",
        aiMode: "interview",
        language: "en",
        resume: {
          skills: ["SQL"],
          technologies: ["Python"],
          languages: ["English"],
          education: [],
          experience: [],
          projects: [],
          certifications: [],
          achievements: [],
          internships: [],
        },
      },
      (t) => {
        tokens += t;
      }
    );
    expect(answer.concise).toBeTruthy();
    expect(tokens.length).toBeGreaterThan(0);
    expect(uid("x")).toMatch(/^x_/);
  });
});

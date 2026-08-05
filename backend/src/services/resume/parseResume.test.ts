import assert from "node:assert/strict";
import fs from "node:fs";
import { describe, it } from "node:test";
import { extractResumeText } from "./parseResume.js";

describe("extractResumeText", () => {
  it("parses text from a PDF buffer", async () => {
    const buffer = fs.readFileSync("/tmp/real_resume.pdf");
    const result = await extractResumeText(
      {
        buffer,
        mimetype: "application/pdf",
        originalname: "resume.pdf",
      },
      ""
    );
    assert.equal(result.source, "pdf");
    assert.match(result.text, /TypeScript/i);
    assert.match(result.text, /React/i);
  });

  it("reads plain text files", async () => {
    const result = await extractResumeText(
      {
        buffer: Buffer.from("Expert in Go and Kubernetes"),
        mimetype: "text/plain",
        originalname: "resume.txt",
      },
      ""
    );
    assert.equal(result.source, "file-text");
    assert.match(result.text, /Kubernetes/);
  });
});

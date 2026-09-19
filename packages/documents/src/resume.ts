import type { ResumeProfile } from "@interviewpilot/shared";

const EMPTY: ResumeProfile = {
  skills: [],
  technologies: [],
  languages: [],
  education: [],
  experience: [],
  projects: [],
  certifications: [],
  achievements: [],
  internships: [],
};

function lines(text: string): string[] {
  return text.split(/\n+/).map((l) => l.trim()).filter(Boolean);
}

function section(text: string, names: string[]): string {
  const lower = text.toLowerCase();
  for (const name of names) {
    const idx = lower.indexOf(name.toLowerCase());
    if (idx >= 0) {
      const rest = text.slice(idx + name.length);
      const next = rest.search(/\n\s*(experience|education|skills|projects|certifications|achievements|languages|summary|work history)\b/i);
      return (next >= 0 ? rest.slice(0, next) : rest).trim();
    }
  }
  return "";
}

export function parseResume(text: string): ResumeProfile {
  const profile: ResumeProfile = structuredClone(EMPTY);
  const ls = lines(text);
  if (ls[0] && ls[0].length < 80) profile.name = ls[0].replace(/^#\s*/, "");

  const email = text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  if (email) profile.email = email[0];

  const skillsBlock = section(text, ["Skills", "Technical Skills", "Core Competencies"]);
  if (skillsBlock) {
    profile.skills = skillsBlock
      .split(/[,|•\n]/)
      .map((s) => s.trim())
      .filter((s) => s.length > 1 && s.length < 40)
      .slice(0, 40);
  }

  const techHints = [
    "Python", "JavaScript", "TypeScript", "SQL", "React", "Node", "Java", "C++", "AWS",
    "Docker", "Kubernetes", "Pandas", "NumPy", "Tableau", "Power BI", "Excel", "Git",
  ];
  profile.technologies = techHints.filter((t) => {
    const escaped = t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`\\b${escaped}\\b`, "i").test(text);
  });

  const edu = section(text, ["Education"]);
  for (const line of lines(edu).slice(0, 8)) {
    profile.education.push({ institution: line });
  }

  const exp = section(text, ["Experience", "Work Experience", "Work History"]);
  for (const line of lines(exp).slice(0, 12)) {
    if (/at | — |- |@ /.test(line) || line.length > 20) {
      const parts = line.split(/\s[-—|]\s|\sat\s/i);
      profile.experience.push({
        company: parts[1]?.trim() || "Unknown",
        title: parts[0]?.trim() || line,
        highlights: [],
      });
    }
  }

  const projects = section(text, ["Projects"]);
  for (const line of lines(projects).slice(0, 10)) {
    profile.projects.push({ name: line.slice(0, 80), description: line, technologies: [] });
  }

  const certs = section(text, ["Certifications", "Certificates"]);
  profile.certifications = lines(certs).slice(0, 10);

  const ach = section(text, ["Achievements", "Accomplishments"]);
  profile.achievements = lines(ach).slice(0, 10);

  return profile;
}

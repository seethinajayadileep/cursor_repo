import type { ExperienceLevel, WorkMode } from "../../types/index.js";

export const DEMO_JOBS = [
  {
    title: "Senior Software Engineer",
    company: "Stripe",
    location: "Remote — Americas",
    salary: "$180,000 – $240,000",
    salaryMin: 180000,
    salaryMax: 240000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "remote" as const,
    description:
      "Build and scale payment infrastructure used by millions of businesses. Work with TypeScript, Go, and distributed systems. Collaborate across product and infrastructure teams to deliver reliable APIs.",
    postedAt: daysAgo(1),
    applyUrl: "https://stripe.com/jobs",
    companySize: "large",
    skills: ["TypeScript", "Go", "Distributed Systems", "PostgreSQL", "AWS"],
    experienceLevel: "senior",
  },
  {
    title: "Software Engineer — Platform",
    company: "Notion",
    location: "San Francisco, CA (Hybrid)",
    salary: "$160,000 – $210,000",
    salaryMin: 160000,
    salaryMax: 210000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Own core product surfaces that millions of knowledge workers rely on daily. Ship features in React and Node, improve performance, and partner with design on polished UX.",
    postedAt: daysAgo(2),
    applyUrl: "https://www.notion.so/careers",
    companySize: "medium",
    skills: ["React", "TypeScript", "Node.js", "PostgreSQL", "GraphQL"],
    experienceLevel: "mid",
  },
  {
    title: "Product Manager, Growth",
    company: "Figma",
    location: "New York, NY",
    salary: "$150,000 – $195,000",
    salaryMin: 150000,
    salaryMax: 195000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Drive activation and retention experiments across the Figma product suite. Define roadmaps, run A/B tests, and partner with engineering and design to ship measurable impact.",
    postedAt: daysAgo(3),
    applyUrl: "https://www.figma.com/careers",
    companySize: "large",
    skills: ["Product Strategy", "A/B Testing", "SQL", "Analytics", "Roadmapping"],
    experienceLevel: "mid",
  },
  {
    title: "Backend Engineer",
    company: "Razorpay",
    location: "Bangalore, India",
    salary: "₹25L – ₹45L",
    salaryMin: 2500000,
    salaryMax: 4500000,
    currency: "INR",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Design resilient payment APIs and settlement systems. Work with Java/Kotlin, Kafka, and PostgreSQL at scale serving millions of merchants across India.",
    postedAt: daysAgo(1),
    applyUrl: "https://razorpay.com/jobs",
    companySize: "large",
    skills: ["Java", "Kotlin", "Kafka", "PostgreSQL", "Microservices"],
    experienceLevel: "mid",
  },
  {
    title: "Full Stack Engineer",
    company: "Vercel",
    location: "Remote",
    salary: "$145,000 – $200,000",
    salaryMin: 145000,
    salaryMax: 200000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "remote" as const,
    description:
      "Build developer experience products that power the modern web. Work deeply with Next.js, React Server Components, and edge runtimes.",
    postedAt: daysAgo(4),
    applyUrl: "https://vercel.com/careers",
    companySize: "medium",
    skills: ["Next.js", "React", "TypeScript", "Edge Computing", "Node.js"],
    experienceLevel: "mid",
  },
  {
    title: "Machine Learning Engineer",
    company: "DeepMind",
    location: "London, UK",
    salary: "£90,000 – £140,000",
    salaryMin: 90000,
    salaryMax: 140000,
    currency: "GBP",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Train and deploy large-scale models for scientific discovery. Collaborate with research scientists on production ML systems using Python, JAX, and GCP.",
    postedAt: daysAgo(5),
    applyUrl: "https://deepmind.google/careers",
    companySize: "enterprise",
    skills: ["Python", "JAX", "PyTorch", "MLOps", "GCP"],
    experienceLevel: "senior",
  },
  {
    title: "Frontend Engineer",
    company: "Linear",
    location: "Remote — Europe",
    salary: "€70,000 – €110,000",
    salaryMin: 70000,
    salaryMax: 110000,
    currency: "EUR",
    employmentType: "full-time",
    workMode: "remote" as const,
    description:
      "Craft delightful, high-performance interfaces for the issue tracker loved by product teams. Deep React expertise and an eye for interaction design required.",
    postedAt: daysAgo(2),
    applyUrl: "https://linear.app/careers",
    companySize: "startup",
    skills: ["React", "TypeScript", "CSS", "Performance", "Design Systems"],
    experienceLevel: "mid",
  },
  {
    title: "DevOps / Platform Engineer",
    company: "Datadog",
    location: "Remote",
    salary: "$155,000 – $215,000",
    salaryMin: 155000,
    salaryMax: 215000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "remote" as const,
    description:
      "Own Kubernetes platforms, CI/CD, and observability tooling that keeps Datadog reliable for customers worldwide.",
    postedAt: daysAgo(6),
    applyUrl: "https://careers.datadoghq.com",
    companySize: "enterprise",
    skills: ["Kubernetes", "Terraform", "AWS", "CI/CD", "Go"],
    experienceLevel: "senior",
  },
  {
    title: "Data Analyst",
    company: "Spotify",
    location: "Stockholm, Sweden",
    salary: "SEK 550,000 – 750,000",
    salaryMin: 550000,
    salaryMax: 750000,
    currency: "SEK",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Turn listener insights into actionable product recommendations. Strong SQL, experimentation, and storytelling skills needed.",
    postedAt: daysAgo(7),
    applyUrl: "https://www.lifeatspotify.com",
    companySize: "enterprise",
    skills: ["SQL", "Python", "Looker", "Experimentation", "Statistics"],
    experienceLevel: "mid",
  },
  {
    title: "Staff Software Engineer",
    company: "Airbnb",
    location: "Remote — US",
    salary: "$220,000 – $300,000",
    salaryMin: 220000,
    salaryMax: 300000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "remote" as const,
    description:
      "Lead technical strategy for marketplace reliability systems. Mentor engineers and drive multi-quarter architectural initiatives.",
    postedAt: daysAgo(3),
    applyUrl: "https://careers.airbnb.com",
    companySize: "enterprise",
    skills: ["Java", "Distributed Systems", "Leadership", "Kafka", "MySQL"],
    experienceLevel: "lead",
  },
  {
    title: "Python Backend Developer",
    company: "Revolut",
    location: "Remote — Europe",
    salary: "€80,000 – €120,000",
    salaryMin: 80000,
    salaryMax: 120000,
    currency: "EUR",
    employmentType: "full-time",
    workMode: "remote" as const,
    description:
      "Build fintech services powering banking products across Europe. Python, FastAPI, and event-driven architecture experience preferred.",
    postedAt: daysAgo(1),
    applyUrl: "https://www.revolut.com/careers",
    companySize: "large",
    skills: ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
    experienceLevel: "mid",
  },
  {
    title: "UX Designer",
    company: "Canva",
    location: "Sydney, Australia",
    salary: "AUD $120,000 – $160,000",
    salaryMin: 120000,
    salaryMax: 160000,
    currency: "AUD",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Design intuitive creative tools used by over 100 million people. Partner with research and engineering to ship accessible, delightful experiences.",
    postedAt: daysAgo(8),
    applyUrl: "https://www.canva.com/careers",
    companySize: "large",
    skills: ["Figma", "User Research", "Prototyping", "Accessibility", "Design Systems"],
    experienceLevel: "mid",
  },
  {
    title: "Site Reliability Engineer",
    company: "Cloudflare",
    location: "Remote",
    salary: "$160,000 – $230,000",
    salaryMin: 160000,
    salaryMax: 230000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "remote" as const,
    description:
      "Keep the edge network healthy at planetary scale. Automate toil, respond to incidents, and improve SLOs across global PoPs.",
    postedAt: daysAgo(2),
    applyUrl: "https://www.cloudflare.com/careers",
    companySize: "enterprise",
    skills: ["Linux", "Go", "Networking", "Prometheus", "Incident Response"],
    experienceLevel: "senior",
  },
  {
    title: "Junior Software Engineer",
    company: "Freshworks",
    location: "Chennai, India",
    salary: "₹8L – ₹14L",
    salaryMin: 800000,
    salaryMax: 1400000,
    currency: "INR",
    employmentType: "full-time",
    workMode: "onsite" as const,
    description:
      "Join a product engineering team building SaaS tools for customer experience. Mentorship-heavy environment with modern JavaScript stack.",
    postedAt: daysAgo(4),
    applyUrl: "https://www.freshworks.com/company/careers",
    companySize: "large",
    skills: ["JavaScript", "React", "Node.js", "REST APIs", "Git"],
    experienceLevel: "entry",
  },
  {
    title: "Contract React Developer",
    company: "Shopify",
    location: "Remote — Canada",
    salary: "CAD $90 – $130 /hr",
    salaryMin: 90000,
    salaryMax: 130000,
    currency: "CAD",
    employmentType: "contract",
    workMode: "remote" as const,
    description:
      "6-month contract to help ship merchant-facing dashboards. Strong React, GraphQL, and e-commerce domain experience preferred.",
    postedAt: daysAgo(1),
    applyUrl: "https://www.shopify.com/careers",
    companySize: "enterprise",
    skills: ["React", "GraphQL", "TypeScript", "Polaris", "E-commerce"],
    experienceLevel: "senior",
  },
  {
    title: "AI Product Manager",
    company: "Anthropic",
    location: "San Francisco, CA",
    salary: "$180,000 – $250,000",
    salaryMin: 180000,
    salaryMax: 250000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Shape how Claude is experienced by developers and enterprises. Bridge research breakthroughs with product packaging and go-to-market.",
    postedAt: daysAgo(2),
    applyUrl: "https://www.anthropic.com/careers",
    companySize: "medium",
    skills: ["AI/ML Product", "Developer Tools", "Strategy", "User Research", "Technical Writing"],
    experienceLevel: "senior",
  },
  {
    title: "Mobile Engineer (iOS)",
    company: "Duolingo",
    location: "Pittsburgh, PA",
    salary: "$140,000 – $185,000",
    salaryMin: 140000,
    salaryMax: 185000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Build delightful learning experiences on iOS using Swift and SwiftUI. Obsess over performance, accessibility, and playful interactions.",
    postedAt: daysAgo(9),
    applyUrl: "https://careers.duolingo.com",
    companySize: "medium",
    skills: ["Swift", "SwiftUI", "iOS", "UIKit", "Animation"],
    experienceLevel: "mid",
  },
  {
    title: "Security Engineer",
    company: "Okta",
    location: "Remote — US",
    salary: "$170,000 – $230,000",
    salaryMin: 170000,
    salaryMax: 230000,
    currency: "USD",
    employmentType: "full-time",
    workMode: "remote" as const,
    description:
      "Harden identity platforms against emerging threats. Threat modeling, secure SDLC, and incident response experience required.",
    postedAt: daysAgo(5),
    applyUrl: "https://www.okta.com/company/careers",
    companySize: "enterprise",
    skills: ["AppSec", "Threat Modeling", "Python", "Cloud Security", "Identity"],
    experienceLevel: "senior",
  },
  {
    title: "Software Engineer",
    company: "Microsoft",
    location: "Hyderabad, India",
    salary: "₹18L – ₹35L",
    salaryMin: 1800000,
    salaryMax: 3500000,
    currency: "INR",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Build cloud and productivity experiences for Microsoft 365 and Azure customers. Work with TypeScript, C#, and large-scale distributed systems from the Hyderabad campus.",
    postedAt: daysAgo(1),
    applyUrl: "https://careers.microsoft.com",
    companySize: "enterprise",
    skills: ["TypeScript", "C#", "Azure", "Distributed Systems", "React"],
    experienceLevel: "mid",
  },
  {
    title: "Senior Software Engineer",
    company: "Google",
    location: "Hyderabad, India",
    salary: "₹35L – ₹65L",
    salaryMin: 3500000,
    salaryMax: 6500000,
    currency: "INR",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Design and ship backend services powering Google products used by millions in India and globally. Strong DSA, Java/Go, and system design skills required.",
    postedAt: daysAgo(2),
    applyUrl: "https://careers.google.com",
    companySize: "enterprise",
    skills: ["Java", "Go", "System Design", "Distributed Systems", "Kubernetes"],
    experienceLevel: "senior",
  },
  {
    title: "Full Stack Developer",
    company: "PhonePe",
    location: "Hyderabad, India",
    salary: "₹20L – ₹40L",
    salaryMin: 2000000,
    salaryMax: 4000000,
    currency: "INR",
    employmentType: "full-time",
    workMode: "onsite" as const,
    description:
      "Build consumer fintech experiences at scale. React, Node.js, and Java microservices across payments and merchant products.",
    postedAt: daysAgo(3),
    applyUrl: "https://www.phonepe.com/careers",
    companySize: "large",
    skills: ["React", "Node.js", "Java", "Kafka", "PostgreSQL"],
    experienceLevel: "mid",
  },
  {
    title: "Backend Engineer",
    company: "Amazon",
    location: "Hyderabad, India",
    salary: "₹25L – ₹50L",
    salaryMin: 2500000,
    salaryMax: 5000000,
    currency: "INR",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Own services within Amazon's retail and AWS-adjacent teams. Java, distributed systems, and operational excellence.",
    postedAt: daysAgo(4),
    applyUrl: "https://www.amazon.jobs",
    companySize: "enterprise",
    skills: ["Java", "AWS", "Distributed Systems", "DynamoDB", "Kotlin"],
    experienceLevel: "mid",
  },
  {
    title: "Software Development Engineer",
    company: "ServiceNow",
    location: "Hyderabad, India",
    salary: "₹15L – ₹28L",
    salaryMin: 1500000,
    salaryMax: 2800000,
    currency: "INR",
    employmentType: "full-time",
    workMode: "hybrid" as const,
    description:
      "Develop platform features for enterprise workflow automation. JavaScript, Java, and cloud-native services.",
    postedAt: daysAgo(2),
    applyUrl: "https://www.servicenow.com/careers.html",
    companySize: "enterprise",
    skills: ["JavaScript", "Java", "REST APIs", "Cloud", "SQL"],
    experienceLevel: "entry",
  },
];

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

const ROLE_KEYWORDS: Record<string, string[]> = {
  engineer: ["engineer", "developer", "sre", "devops", "backend", "frontend", "full stack", "software"],
  product: ["product manager", "product", "pm"],
  design: ["designer", "ux", "ui"],
  data: ["data", "analyst", "ml", "machine learning", "ai"],
  security: ["security", "appsec"],
  mobile: ["mobile", "ios", "android"],
};

const INDIA_CITIES = [
  "hyderabad",
  "hyd",
  "bangalore",
  "bengaluru",
  "chennai",
  "mumbai",
  "pune",
  "delhi",
  "gurgaon",
  "gurugram",
  "noida",
  "kolkata",
  "india",
];

export function locationMatches(
  jobLocation: string,
  jobWorkMode: string,
  query: string
): boolean {
  if (!query || query === "anywhere") return true;
  const loc = query.toLowerCase().trim();
  const hay = jobLocation.toLowerCase();

  if (hay.includes(loc) || loc.includes(hay.split(",")[0]?.trim() ?? "")) return true;
  if (loc === "remote" || loc.includes("remote")) return jobWorkMode === "remote";

  if (loc.includes("europe")) {
    return /europe|london|stockholm|berlin|amsterdam|paris|€/i.test(`${jobLocation}`);
  }

  // Treat Indian city searches as India-local
  if (INDIA_CITIES.some((c) => loc.includes(c) || loc === c)) {
    return (
      INDIA_CITIES.some((c) => hay.includes(c)) ||
      /₹|india/i.test(`${jobLocation}`)
    );
  }

  return false;
}

export function filterDemoJobs(opts: {
  role: string;
  location: string;
  experienceLevel?: ExperienceLevel;
  employmentType?: string;
  workMode?: WorkMode | "any";
  salaryMin?: number;
  salaryMax?: number;
  companySize?: string;
}) {
  const role = opts.role.toLowerCase();
  const location = opts.location.toLowerCase();

  return DEMO_JOBS.filter((job) => {
    const hay = `${job.title} ${job.description} ${job.skills.join(" ")}`.toLowerCase();
    const roleTokens = role.split(/\s+/).filter(Boolean);
    const roleMatch =
      roleTokens.length === 0 ||
      roleTokens.some((t) => hay.includes(t)) ||
      Object.values(ROLE_KEYWORDS).some(
        (group) =>
          group.some((g) => role.includes(g)) &&
          group.some((g) => hay.includes(g))
      );

    const locMatch = locationMatches(job.location, job.workMode, location);

    const expMatch =
      !opts.experienceLevel ||
      opts.experienceLevel === "any" ||
      job.experienceLevel === opts.experienceLevel;

    const empMatch =
      !opts.employmentType ||
      opts.employmentType === "any" ||
      job.employmentType === opts.employmentType;

    const modeMatch =
      !opts.workMode ||
      opts.workMode === "any" ||
      job.workMode === opts.workMode;

    const sizeMatch =
      !opts.companySize ||
      opts.companySize === "any" ||
      job.companySize === opts.companySize;

    const salaryOk =
      (!opts.salaryMin || (job.salaryMax ?? job.salaryMin ?? 0) >= opts.salaryMin) &&
      (!opts.salaryMax || (job.salaryMin ?? job.salaryMax ?? Infinity) <= opts.salaryMax);

    return roleMatch && locMatch && expMatch && empMatch && modeMatch && sizeMatch && salaryOk;
  });
}

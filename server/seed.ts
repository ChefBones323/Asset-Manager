import { db } from "./db";
import { jobs } from "@shared/schema";
import { randomUUID } from "crypto";
import { log } from "./index";

export async function seedDatabase() {
  const existing = await db.select().from(jobs).limit(1);
  if (existing.length > 0) {
    return;
  }

  log("Seeding database with sample jobs...", "seed");

  const now = new Date();
  const hourAgo = new Date(now.getTime() - 60 * 60 * 1000);
  const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);
  const threeHoursAgo = new Date(now.getTime() - 3 * 60 * 60 * 1000);

  await db.insert(jobs).values([
    {
      id: randomUUID(),
      intent: "Generate a 60-second product launch script for TechVault Pro",
      status: "completed",
      reasoningSummary:
        "Strategist: Identified script generation task. Designer: Applied 60s pacing structure with hook, value prop, and CTA. Systems: Non-destructive file creation.",
      proposedPlan: [
        "Create /Drafts directory if not exists",
        "Generate structured 60s script in Markdown format",
        "Save file as /Drafts/generated_script.md",
      ],
      impactAnalysis: {
        filesCreated: ["/Drafts/generated_script.md"],
        filesModified: [],
        destructiveChanges: false,
        estimatedTimeSeconds: 20,
      },
      logs: "[00:01] Creating /Drafts directory...\n[00:03] Directory created successfully\n[00:05] Generating script structure...\n[00:12] Writing hook section (0-10s)\n[00:15] Writing value proposition (10-40s)\n[00:18] Writing call-to-action (40-60s)\n[00:20] Script saved to /Drafts/generated_script.md\n[00:20] Task completed successfully",
      createdAt: threeHoursAgo,
      approvedAt: new Date(threeHoursAgo.getTime() + 5 * 60 * 1000),
      completedAt: new Date(threeHoursAgo.getTime() + 6 * 60 * 1000),
    },
    {
      id: randomUUID(),
      intent: "Analyze Q4 sales performance across all regions",
      status: "completed",
      reasoningSummary:
        "Strategist: Data analysis task detected. Analyst: Structured report format with key findings. Systems: Read-only data access, non-destructive output.",
      proposedPlan: [
        "Connect to data source and validate access",
        "Extract relevant data points",
        "Generate structured analysis report",
        "Save report as /Reports/analysis_output.md",
      ],
      impactAnalysis: {
        filesCreated: ["/Reports/analysis_output.md"],
        filesModified: [],
        destructiveChanges: false,
        estimatedTimeSeconds: 30,
      },
      logs: "[00:01] Connecting to data source...\n[00:04] Connection established\n[00:06] Querying Q4 data across regions...\n[00:15] Data extraction complete (4 regions, 2847 records)\n[00:20] Generating analysis...\n[00:28] Report saved to /Reports/analysis_output.md\n[00:30] Task completed successfully",
      createdAt: twoHoursAgo,
      approvedAt: new Date(twoHoursAgo.getTime() + 3 * 60 * 1000),
      completedAt: new Date(twoHoursAgo.getTime() + 4 * 60 * 1000),
    },
    {
      id: randomUUID(),
      intent: "Deploy frontend build to staging environment",
      status: "failed",
      reasoningSummary:
        "Strategist: Deployment workflow identified. Systems: Build artifacts, run tests, push to staging. Risk: Medium - staging-facing operation.",
      proposedPlan: [
        "Run test suite to verify integrity",
        "Build production artifacts",
        "Deploy to staging environment",
        "Verify health checks pass",
      ],
      impactAnalysis: {
        filesCreated: ["/dist/bundle.js", "/dist/index.html"],
        filesModified: ["/config/deploy.json"],
        destructiveChanges: false,
        estimatedTimeSeconds: 45,
      },
      logs: "[00:01] Running test suite...\n[00:12] Tests passed (47/47)\n[00:14] Building production artifacts...\n[00:30] Build complete\n[00:32] Deploying to staging...\n[00:38] ERROR: Connection to staging server refused\n[00:38] Retrying (attempt 2/3)...\n[00:42] ERROR: Connection timeout\n[00:42] Task failed: Unable to reach staging server",
      createdAt: hourAgo,
      approvedAt: new Date(hourAgo.getTime() + 2 * 60 * 1000),
      completedAt: new Date(hourAgo.getTime() + 3 * 60 * 1000),
    },
    {
      id: randomUUID(),
      intent: "Create a comprehensive API documentation for the user endpoints",
      status: "awaiting_approval",
      reasoningSummary:
        "General structured workflow generation. Documentation task identified with structured output format. No destructive operations proposed.",
      proposedPlan: [
        "Create /Workspace/output.txt",
        "Write structured result based on intent",
      ],
      impactAnalysis: {
        filesCreated: ["/Workspace/output.txt"],
        filesModified: [],
        destructiveChanges: false,
        estimatedTimeSeconds: 10,
      },
      logs: "",
      createdAt: new Date(now.getTime() - 10 * 60 * 1000),
    },
    {
      id: randomUUID(),
      intent: "Clean up deprecated test fixtures from /tests/legacy folder",
      status: "awaiting_approval",
      reasoningSummary:
        "Strategist: Cleanup operation identified. Systems: CAUTION - potentially destructive changes detected. Requires careful review before approval.",
      proposedPlan: [
        "Scan target paths for matching files",
        "Generate list of files to be affected",
        "Execute cleanup with logging",
        "Verify results and report changes",
      ],
      impactAnalysis: {
        filesCreated: ["/Logs/cleanup_report.txt"],
        filesModified: [],
        destructiveChanges: true,
        estimatedTimeSeconds: 15,
      },
      logs: "",
      createdAt: new Date(now.getTime() - 5 * 60 * 1000),
    },
  ]);

  log("Database seeded with 5 sample jobs", "seed");
}

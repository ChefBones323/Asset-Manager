export function buildProposal(intent: string) {
  const intentLower = intent.toLowerCase();

  if (intentLower.includes("script")) {
    return {
      reasoningSummary:
        "Strategist: Identified script generation task. " +
        "Designer: Applied 60s pacing structure. " +
        "Systems: Non-destructive file creation.",
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
    };
  }

  if (intentLower.includes("deploy") || intentLower.includes("publish")) {
    return {
      reasoningSummary:
        "Strategist: Deployment workflow identified. " +
        "Systems: Build artifacts, run tests, push to production. " +
        "Risk: Medium - production-facing operation.",
      proposedPlan: [
        "Run test suite to verify integrity",
        "Build production artifacts",
        "Deploy to target environment",
        "Verify health checks pass",
      ],
      impactAnalysis: {
        filesCreated: ["/dist/bundle.js", "/dist/index.html"],
        filesModified: ["/config/deploy.json"],
        destructiveChanges: false,
        estimatedTimeSeconds: 45,
      },
    };
  }

  if (intentLower.includes("report") || intentLower.includes("analyze") || intentLower.includes("analysis")) {
    return {
      reasoningSummary:
        "Strategist: Data analysis task detected. " +
        "Analyst: Structured report format with key findings. " +
        "Systems: Read-only data access, non-destructive output.",
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
    };
  }

  if (intentLower.includes("clean") || intentLower.includes("delete") || intentLower.includes("remove")) {
    return {
      reasoningSummary:
        "Strategist: Cleanup operation identified. " +
        "Systems: CAUTION - potentially destructive changes detected. " +
        "Requires careful review before approval.",
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
    };
  }

  return {
    reasoningSummary:
      "General structured workflow generation. " +
      "No destructive operations proposed.",
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
  };
}

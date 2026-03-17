import type { Express, Request, Response, NextFunction } from "express";
import { createServer, type Server } from "http";
import session from "express-session";
import { storage } from "./storage";

import { insertJobSchema } from "@shared/schema";

declare module "express-session" {
  interface SessionData {
    admin?: boolean;
  }
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  const sessionSecret = process.env.SESSION_SECRET;
  const adminPassword = process.env.ADMIN_PASSWORD;
  const workerToken = process.env.WORKER_TOKEN;

  if (!adminPassword) {
    throw new Error("ADMIN_PASSWORD environment variable is required");
  }
  if (!workerToken) {
    throw new Error("WORKER_TOKEN environment variable is required");
  }
  if (!sessionSecret) {
    throw new Error("SESSION_SECRET environment variable is required");
  }

  app.use(
    session({
      secret: sessionSecret,
      resave: false,
      saveUninitialized: false,
      cookie: {
        secure: process.env.NODE_ENV === "production",
        httpOnly: true,
        sameSite: "lax",
        maxAge: 24 * 60 * 60 * 1000,
      },
    })
  );

  function requireAdmin(req: any, res: any, next: any) {
    if (!req.session?.admin) {
      return res.status(401).json({ error: "Unauthorized" });
    }
    next();
  }

  function requireWorker(req: any, res: any, next: any) {
    const token = req.headers.authorization;
    if (token !== `Bearer ${workerToken}`) {
      return res.status(401).json({ error: "Unauthorized" });
    }
    next();
  }

  app.post("/api/auth/login", (req, res) => {
    const { password } = req.body;
    if (password === adminPassword) {
      req.session.admin = true;
      return res.json({ admin: true });
    }
    return res.status(401).json({ error: "Invalid password" });
  });

  app.post("/api/auth/logout", (req, res) => {
    req.session.destroy(() => {
      res.json({ ok: true });
    });
  });

  app.get("/api/auth/me", (req, res) => {
    if (req.session?.admin) {
      return res.json({ admin: true });
    }
    return res.status(401).json({ error: "Not authenticated" });
  });

  app.get("/api/jobs", requireAdmin, async (_req, res) => {
    const jobs = await storage.getJobs();
    res.json(jobs);
  });

  app.post("/api/jobs", requireAdmin, async (req, res) => {
    const parsed = insertJobSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: "Invalid input", details: parsed.error.flatten() });
    }

    const intent = parsed.data.intent;

    const destructiveChanges =
      intent.includes("rm ") ||
      intent.includes("sudo") ||
      intent.includes("chmod") ||
      intent.includes("chown");

    const impactAnalysis = {
      filesCreated: [] as string[],
      filesModified: [] as string[],
      destructiveChanges,
      estimatedTimeSeconds: 10,
    };

    const executableManifest = {
      version: 1,
      requiresRollback: destructiveChanges,
      steps: [
        {
          id: "step-1",
          type: "shell",
          command: intent,
        },
      ],
    };

    const job = await storage.createJob({
      intent,
      reasoningSummary: "Direct manifest-driven execution from user intent.",
      proposedPlan: ["Execute shell command via executable manifest"],
      impactAnalysis,
      executableManifest,
    });

    res.json(job);
  });

  app.post("/api/jobs/:id/approve", requireAdmin, async (req, res) => {
    const job = await storage.getJob(req.params.id);
    if (!job) return res.status(404).json({ error: "Not found" });
    if (job.status !== "awaiting_approval") {
      return res.status(400).json({ error: "Can only approve jobs awaiting approval" });
    }

    const updated = await storage.approveJob(req.params.id);
    res.json(updated);
  });

  app.post("/api/jobs/:id/reject", requireAdmin, async (req, res) => {
    const job = await storage.getJob(req.params.id);
    if (!job) return res.status(404).json({ error: "Not found" });
    if (job.status !== "awaiting_approval") {
      return res.status(400).json({ error: "Can only reject jobs awaiting approval" });
    }

    const updated = await storage.rejectJob(req.params.id);
    res.json(updated);
  });

  app.post("/api/jobs/:id/pause", requireAdmin, async (req, res) => {
    try {
      const job = await storage.getJob(req.params.id);
      if (!job) return res.status(404).json({ error: "Not found" });
      if (job.status !== "running") {
        return res.status(400).json({ error: "Can only pause running jobs" });
      }
      const updated = await storage.pauseJob(req.params.id);
      res.json(updated);
    } catch (error) {
      console.error("Pause job error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/jobs/:id/resume", requireAdmin, async (req, res) => {
    try {
      const job = await storage.getJob(req.params.id);
      if (!job) return res.status(404).json({ error: "Not found" });
      if (job.status !== "paused" && job.status !== "escalated") {
        return res.status(400).json({ error: "Can only resume paused or escalated jobs" });
      }
      const updated = await storage.resumeJob(req.params.id);
      res.json(updated);
    } catch (error) {
      console.error("Resume job error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/jobs/:id/escalate", requireAdmin, async (req, res) => {
    try {
      const job = await storage.getJob(req.params.id);
      if (!job) return res.status(404).json({ error: "Not found" });
      if (job.status !== "running") {
        return res.status(400).json({ error: "Can only escalate running jobs" });
      }
      const updated = await storage.escalateJob(req.params.id);
      res.json(updated);
    } catch (error) {
      console.error("Escalate job error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/jobs/:id/cancel", requireAdmin, async (req, res) => {
    try {
      const job = await storage.getJob(req.params.id);
      if (!job) return res.status(404).json({ error: "Not found" });

      if (job.status === "completed" || job.status === "failed" || job.status === "cancelled") {
        return res.json(job);
      }

      if (job.status !== "running" && job.status !== "approved" && job.status !== "paused" && job.status !== "escalated") {
        return res.status(400).json({ error: "Can only cancel active jobs" });
      }

      const updated = await storage.cancelJob(req.params.id);
      res.json(updated);
    } catch (error) {
      console.error("Cancel job error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/jobs/:id/delete", requireAdmin, async (req, res) => {
    try {
      const job = await storage.getJob(req.params.id);
      if (!job) return res.status(404).json({ error: "Not found" });

      if (job.status !== "completed" && job.status !== "failed" && job.status !== "cancelled") {
        return res.status(400).json({ error: "Can only delete completed, failed, or cancelled jobs" });
      }

      await storage.deleteJob(req.params.id);
      return res.json({ success: true, id: req.params.id });
    } catch (error) {
      console.error("Delete job error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/jobs/:id/approve-destructive", requireAdmin, async (req, res) => {
    try {
      const job = await storage.getJob(req.params.id);
      if (!job) return res.status(404).json({ error: "Not found" });
      const updated = await storage.approveDestructive(req.params.id);
      res.json(updated);
    } catch (error) {
      console.error("Approve destructive error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.get("/api/jobs/:id/status", requireWorker, async (req, res) => {
    try {
      const job = await storage.getJob(req.params.id);
      if (!job) return res.status(404).json({ error: "Not found" });
      return res.json({ id: job.id, status: job.status });
    } catch (error) {
      console.error("Job status check error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.get("/api/worker/next", requireWorker, async (req, res) => {
    try {
      const workerId = req.headers["x-worker-id"] as string || "default-worker";

      const currentlyRunning = await storage.getRunningJob();
      if (currentlyRunning) {
        if (currentlyRunning.leaseExpiresAt && new Date(currentlyRunning.leaseExpiresAt) <= new Date()) {
          const escalationLog = (currentlyRunning.logs || "") + "\n[WATCHDOG] Lease expired. Worker presumed dead.";
          await storage.updateRunningJob(currentlyRunning.id, escalationLog, "escalated");
        } else {
          return res.json({ job: null, reason: "A job is already running" });
        }
      }

      const job = await storage.getNextApprovedJob();
      if (!job) return res.json({ job: null });

      const impact = job.impactAnalysis as { destructiveChanges?: boolean } | null;
      if (impact?.destructiveChanges && !job.destructiveApprovedAt) {
        const escalationLog = (job.logs || "") + "\nDestructive execution requires explicit destructive approval.";
        await storage.updateRunningJob(job.id, escalationLog, "escalated");
        return res.json({ job: null, reason: "Job requires destructive approval" });
      }

      const started = await storage.startJob(job.id, workerId);
      const manifest = (started?.executableManifest ?? {}) as Record<string, unknown>;
      return res.json({
        ...started,
        status: "running",
        type: started?.intent ?? (manifest.jobType as string) ?? null,
        payload: (manifest.payload ?? {}) as Record<string, unknown>,
      });
    } catch (error) {
      console.error("Worker next error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/worker/heartbeat", requireWorker, async (req, res) => {
    try {
      const { jobId, workerId } = req.body;
      if (!jobId || !workerId) {
        return res.status(400).json({ error: "jobId and workerId required" });
      }

      const job = await storage.getJob(jobId);
      if (!job) return res.status(404).json({ error: "Not found" });

      if (job.workerId !== workerId) {
        return res.status(403).json({ error: "Worker ID mismatch" });
      }

      if (job.status !== "running") {
        return res.status(400).json({ error: "Job is not running" });
      }

      await storage.renewLease(jobId);
      return res.json({ ok: true });
    } catch (error) {
      console.error("Heartbeat error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/worker/update", requireWorker, async (req, res) => {
    try {
      const { id, logs, status, workerId } = req.body;
      if (!id) return res.status(400).json({ error: "Job ID required" });

      const job = await storage.getJob(id);
      if (!job) return res.status(404).json({ error: "Not found" });

      if (workerId && job.workerId && job.workerId !== workerId) {
        return res.status(403).json({ error: "Worker ID mismatch" });
      }

      if (job.leaseExpiresAt && new Date(job.leaseExpiresAt) < new Date() && job.status === "running") {
        return res.status(400).json({ error: "Lease expired" });
      }

      if (job.status !== "running" && job.status !== "cancelled" && job.status !== "paused" && job.status !== "escalated") {
        return res.status(400).json({ error: "Invalid state transition" });
      }

      let newStatus: "completed" | "failed" | "cancelled" | "escalated" | undefined;
      if (status === "Completed") newStatus = "completed";
      else if (status === "Failed") newStatus = "failed";
      else if (status === "Cancelled") newStatus = "cancelled";
      else if (status === "Escalated") newStatus = "escalated";

      const appendedLogs = logs
        ? (job.logs ? job.logs + "\n" + logs : logs)
        : job.logs || "";

      if (!newStatus && job.status === "running" && job.approvedAt) {
        const impact = job.impactAnalysis as { estimatedTimeSeconds?: number } | null;
        if (impact?.estimatedTimeSeconds) {
          const elapsedMs = Date.now() - new Date(job.approvedAt).getTime();
          const thresholdMs = impact.estimatedTimeSeconds * 2 * 1000;
          if (elapsedMs > thresholdMs) {
            newStatus = "escalated";
            const escalationLog = appendedLogs + "\n[WATCHDOG] Execution exceeded safety threshold. Escalated.";
            const updated = await storage.updateRunningJob(id, escalationLog, newStatus);
            return res.json({ status: "updated", job: updated, autoEscalated: true });
          }
        }
      }

      if (job.status === "running" && !newStatus) {
        await storage.renewLease(id);
      }

      const updated = await storage.updateRunningJob(id, appendedLogs, newStatus);
      return res.json({ status: "updated", job: updated });
    } catch (error) {
      console.error("Worker update error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/worker/:id/complete", requireWorker, async (req, res) => {
    try {
      const { logs = "", workerId } = req.body ?? {};
      const job = await storage.getJob(req.params.id);
      if (!job) return res.status(404).json({ error: "Not found" });

      if (workerId && job.workerId && job.workerId !== workerId) {
        return res.status(403).json({ error: "Worker ID mismatch" });
      }

      if (job.status !== "running" && job.status !== "paused" && job.status !== "escalated") {
        return res.status(400).json({ error: `Cannot complete job in state: ${job.status}` });
      }

      const appendedLogs = job.logs ? `${job.logs}\n${logs}` : logs;
      const updated = await storage.updateRunningJob(req.params.id, appendedLogs, "completed");
      console.log(`[ROUTES] Job ${req.params.id} completed by worker ${workerId ?? "unknown"}`);
      return res.json({ status: "completed", job: updated });
    } catch (error) {
      console.error("Worker complete error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/worker/:id/fail", requireWorker, async (req, res) => {
    try {
      const { logs = "", error: failReason = "", workerId } = req.body ?? {};
      const job = await storage.getJob(req.params.id);
      if (!job) return res.status(404).json({ error: "Not found" });

      if (workerId && job.workerId && job.workerId !== workerId) {
        return res.status(403).json({ error: "Worker ID mismatch" });
      }

      if (job.status !== "running" && job.status !== "paused" && job.status !== "escalated") {
        return res.status(400).json({ error: `Cannot fail job in state: ${job.status}` });
      }

      const failLog = failReason ? `[FAILURE] ${failReason}\n${logs}` : logs;
      const appendedLogs = job.logs ? `${job.logs}\n${failLog}` : failLog;
      const updated = await storage.updateRunningJob(req.params.id, appendedLogs, "failed");
      console.log(`[ROUTES] Job ${req.params.id} failed — ${failReason}`);
      return res.json({ status: "failed", job: updated });
    } catch (error) {
      console.error("Worker fail error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.get("/metrics", async (_req, res) => {
    try {
      const stats = await storage.getJobStats();
      return res.json(stats);
    } catch (error) {
      console.error("Metrics error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  app.post("/api/worker/enqueue", requireWorker, async (req, res) => {
    try {
      const { type = "test_job", payload = {} } = req.body ?? {};

      const executableManifest = {
        version: 1,
        jobType: type,
        payload,
        requiresRollback: false,
        steps: [
          {
            id: "step-1",
            type: "shell",
            command: `echo type=${type}`,
          },
        ],
      };

      const job = await storage.createJob({
        intent: type,
        reasoningSummary: `Enqueued ${type} job via worker API`,
        proposedPlan: [`Execute ${type} job with provided payload`],
        impactAnalysis: {
          filesCreated: [],
          filesModified: [],
          destructiveChanges: false,
          estimatedTimeSeconds: 5,
        },
        executableManifest,
      });

      const approved = await storage.approveJob(job.id);
      return res.json({ status: "queued", job: approved });
    } catch (error) {
      console.error("Enqueue error:", error);
      return res.status(500).json({ error: "Internal server error" });
    }
  });

  return httpServer;
}

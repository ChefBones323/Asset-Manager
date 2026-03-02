import type { Express, Request, Response, NextFunction } from "express";
import { createServer, type Server } from "http";
import session from "express-session";
import { storage } from "./storage";
import { buildProposal } from "./proposal-builder";
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

    const proposal = buildProposal(parsed.data.intent);
    const job = await storage.createJob({
      intent: parsed.data.intent,
      ...proposal,
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

  app.get("/api/worker/next", requireWorker, async (_req, res) => {
    const currentlyRunning = await storage.getRunningJob();
    if (currentlyRunning) {
      return res.json({ job: null, reason: "A job is already running" });
    }

    const job = await storage.getNextApprovedJob();
    if (!job) return res.json({ job: null });

    const started = await storage.startJob(job.id);
    res.json(started);
  });

  app.post("/api/worker/update", requireWorker, async (req, res) => {
    const { id, logs, status } = req.body;
    if (!id) return res.status(400).json({ error: "Job ID required" });

    const job = await storage.getJob(id);
    if (!job) return res.status(404).json({ error: "Not found" });
    if (job.status !== "running") {
      return res.status(400).json({ error: "Invalid state transition" });
    }

    let newStatus: "completed" | "failed" | undefined;
    if (status === "Completed") newStatus = "completed";
    else if (status === "Failed") newStatus = "failed";

    const updated = await storage.updateRunningJob(id, logs || job.logs, newStatus);
    res.json({ status: "updated", job: updated });
  });

  return httpServer;
}

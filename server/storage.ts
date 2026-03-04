import { db } from "./db";
import { jobs, type Job, type InsertJob } from "@shared/schema";
import { eq, desc, asc, and, lt, isNotNull } from "drizzle-orm";
import { randomUUID } from "crypto";

export interface IStorage {
  getJobs(): Promise<Job[]>;
  getJob(id: string): Promise<Job | undefined>;
  createJob(job: InsertJob & {
    reasoningSummary: string;
    proposedPlan: string[];
    impactAnalysis: {
      filesCreated: string[];
      filesModified: string[];
      destructiveChanges: boolean;
      estimatedTimeSeconds: number;
    };
    executableManifest?: unknown;
  }): Promise<Job>;
  approveJob(id: string): Promise<Job | undefined>;
  rejectJob(id: string): Promise<Job | undefined>;
  getNextApprovedJob(): Promise<Job | undefined>;
  startJob(id: string, workerId: string): Promise<Job | undefined>;
  updateRunningJob(id: string, logs: string, status?: "completed" | "failed" | "cancelled" | "escalated"): Promise<Job | undefined>;
  getRunningJob(): Promise<Job | undefined>;
  cancelJob(id: string): Promise<Job | undefined>;
  pauseJob(id: string): Promise<Job | undefined>;
  resumeJob(id: string): Promise<Job | undefined>;
  escalateJob(id: string): Promise<Job | undefined>;
  deleteJob(id: string): Promise<boolean>;
  renewLease(id: string): Promise<Job | undefined>;
  getExpiredLeaseJobs(): Promise<Job[]>;
  getRunawayJobs(): Promise<Job[]>;
  approveDestructive(id: string): Promise<Job | undefined>;
}

export class DatabaseStorage implements IStorage {
  async getJobs(): Promise<Job[]> {
    return db.select().from(jobs).orderBy(desc(jobs.createdAt));
  }

  async getJob(id: string): Promise<Job | undefined> {
    const [job] = await db.select().from(jobs).where(eq(jobs.id, id));
    return job;
  }

  async createJob(input: InsertJob & {
    reasoningSummary: string;
    proposedPlan: string[];
    impactAnalysis: {
      filesCreated: string[];
      filesModified: string[];
      destructiveChanges: boolean;
      estimatedTimeSeconds: number;
    };
    executableManifest?: unknown;
  }): Promise<Job> {
    const [job] = await db.insert(jobs).values({
      id: randomUUID(),
      intent: input.intent,
      status: "awaiting_approval",
      reasoningSummary: input.reasoningSummary,
      proposedPlan: input.proposedPlan,
      impactAnalysis: input.impactAnalysis,
      executableManifest: input.executableManifest ?? null,
      logs: "",
    }).returning();
    return job;
  }

  async approveJob(id: string): Promise<Job | undefined> {
    const [job] = await db.update(jobs)
      .set({ status: "approved", approvedAt: new Date() })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async rejectJob(id: string): Promise<Job | undefined> {
    const [job] = await db.update(jobs)
      .set({ status: "failed" })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async getNextApprovedJob(): Promise<Job | undefined> {
    const [job] = await db.select().from(jobs)
      .where(eq(jobs.status, "approved"))
      .orderBy(asc(jobs.createdAt))
      .limit(1);
    return job;
  }

  async startJob(id: string, workerId: string): Promise<Job | undefined> {
    const now = new Date();
    const leaseExpiry = new Date(now.getTime() + 30000);
    const [job] = await db.update(jobs)
      .set({
        status: "running",
        workerId,
        lastHeartbeatAt: now,
        leaseExpiresAt: leaseExpiry,
      })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async updateRunningJob(id: string, logs: string, status?: "completed" | "failed" | "cancelled" | "escalated"): Promise<Job | undefined> {
    const updates: Record<string, any> = { logs };
    if (status) {
      updates.status = status;
      updates.completedAt = new Date();
    }
    const [job] = await db.update(jobs)
      .set(updates)
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async getRunningJob(): Promise<Job | undefined> {
    const [job] = await db.select().from(jobs)
      .where(eq(jobs.status, "running"))
      .limit(1);
    return job;
  }

  async cancelJob(id: string): Promise<Job | undefined> {
    const [job] = await db.update(jobs)
      .set({ status: "cancelled", completedAt: new Date() })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async pauseJob(id: string): Promise<Job | undefined> {
    const [job] = await db.update(jobs)
      .set({ status: "paused" })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async resumeJob(id: string): Promise<Job | undefined> {
    const now = new Date();
    const leaseExpiry = new Date(now.getTime() + 30000);
    const [job] = await db.update(jobs)
      .set({ status: "running", lastHeartbeatAt: now, leaseExpiresAt: leaseExpiry })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async escalateJob(id: string): Promise<Job | undefined> {
    const [job] = await db.update(jobs)
      .set({ status: "escalated" })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async deleteJob(id: string): Promise<boolean> {
    await db.delete(jobs).where(eq(jobs.id, id));
    return true;
  }

  async renewLease(id: string): Promise<Job | undefined> {
    const now = new Date();
    const leaseExpiry = new Date(now.getTime() + 30000);
    const [job] = await db.update(jobs)
      .set({ lastHeartbeatAt: now, leaseExpiresAt: leaseExpiry })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async getExpiredLeaseJobs(): Promise<Job[]> {
    return db.select().from(jobs)
      .where(
        and(
          eq(jobs.status, "running"),
          isNotNull(jobs.leaseExpiresAt),
          lt(jobs.leaseExpiresAt, new Date())
        )
      );
  }

  async getRunawayJobs(): Promise<Job[]> {
    return db.select().from(jobs)
      .where(
        and(
          eq(jobs.status, "running"),
          isNotNull(jobs.approvedAt)
        )
      );
  }

  async approveDestructive(id: string): Promise<Job | undefined> {
    const [job] = await db.update(jobs)
      .set({ destructiveApprovedAt: new Date() })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }
}

export const storage = new DatabaseStorage();

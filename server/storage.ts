import { db } from "./db";
import { jobs, type Job, type InsertJob } from "@shared/schema";
import { eq, desc, asc } from "drizzle-orm";
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
  }): Promise<Job>;
  approveJob(id: string): Promise<Job | undefined>;
  rejectJob(id: string): Promise<Job | undefined>;
  getNextApprovedJob(): Promise<Job | undefined>;
  startJob(id: string): Promise<Job | undefined>;
  updateRunningJob(id: string, logs: string, status?: "completed" | "failed" | "cancelled"): Promise<Job | undefined>;
  getRunningJob(): Promise<Job | undefined>;
  cancelJob(id: string): Promise<Job | undefined>;
  deleteJob(id: string): Promise<boolean>;
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
  }): Promise<Job> {
    const [job] = await db.insert(jobs).values({
      id: randomUUID(),
      intent: input.intent,
      status: "awaiting_approval",
      reasoningSummary: input.reasoningSummary,
      proposedPlan: input.proposedPlan,
      impactAnalysis: input.impactAnalysis,
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

  async startJob(id: string): Promise<Job | undefined> {
    const [job] = await db.update(jobs)
      .set({ status: "running" })
      .where(eq(jobs.id, id))
      .returning();
    return job;
  }

  async updateRunningJob(id: string, logs: string, status?: "completed" | "failed" | "cancelled"): Promise<Job | undefined> {
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

  async deleteJob(id: string): Promise<boolean> {
    const result = await db.delete(jobs).where(eq(jobs.id, id));
    return true;
  }
}

export const storage = new DatabaseStorage();

import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, jsonb, pgEnum } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const jobStatusEnum = pgEnum("job_status", [
  "draft",
  "awaiting_approval",
  "approved",
  "running",
  "completed",
  "failed",
]);

export const jobs = pgTable("jobs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  intent: text("intent").notNull(),
  status: jobStatusEnum("status").notNull().default("awaiting_approval"),
  reasoningSummary: text("reasoning_summary"),
  proposedPlan: jsonb("proposed_plan").$type<string[]>(),
  impactAnalysis: jsonb("impact_analysis").$type<{
    filesCreated: string[];
    filesModified: string[];
    destructiveChanges: boolean;
    estimatedTimeSeconds: number;
  }>(),
  logs: text("logs").default(""),
  createdAt: timestamp("created_at").defaultNow(),
  approvedAt: timestamp("approved_at"),
  completedAt: timestamp("completed_at"),
});

export const insertJobSchema = createInsertSchema(jobs).pick({
  intent: true,
});

export type InsertJob = z.infer<typeof insertJobSchema>;
export type Job = typeof jobs.$inferSelect;
export type JobStatus = Job["status"];

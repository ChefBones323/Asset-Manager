import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { serveStatic } from "./static";
import { createServer } from "http";
import { storage } from "./storage";

const app = express();
app.set('trust proxy', 1);
const httpServer = createServer(app);

declare module "http" {
  interface IncomingMessage {
    rawBody: unknown;
  }
}

app.use(
  express.json({
    verify: (req, _res, buf) => {
      req.rawBody = buf;
    },
  }),
);

app.use(express.urlencoded({ extended: false }));

export function log(message: string, source = "express") {
  const formattedTime = new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });

  console.log(`${formattedTime} [${source}] ${message}`);
}

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      log(logLine);
    }
  });

  next();
});

(async () => {
  const { seedDatabase } = await import("./seed");
  await seedDatabase();
  await registerRoutes(httpServer, app);

  app.use((err: any, _req: Request, res: Response, next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";

    console.error("Internal Server Error:", err);

    if (res.headersSent) {
      return next(err);
    }

    return res.status(status).json({ message });
  });

  // importantly only setup vite in development and after
  // setting up all the other routes so the catch-all route
  // doesn't interfere with the other routes
  if (process.env.NODE_ENV === "production") {
    serveStatic(app);
  } else {
    const { setupVite } = await import("./vite");
    await setupVite(httpServer, app);
  }

  // ALWAYS serve the app on the port specified in the environment variable PORT
  // Other ports are firewalled. Default to 5000 if not specified.
  // this serves both the API and the client.
  // It is the only port that is not firewalled.
  const port = parseInt(process.env.PORT || "5000", 10);
  httpServer.listen(
    {
      port,
      host: "0.0.0.0",
      reusePort: true,
    },
    () => {
      log(`serving on port ${port}`);

      setInterval(async () => {
        try {
          const expiredJobs = await storage.getExpiredLeaseJobs();
          for (const job of expiredJobs) {
            const escalationLog = (job.logs || "") + "\n[WATCHDOG] Lease expired. Execution halted automatically.";
            await storage.updateRunningJob(job.id, escalationLog, "escalated");
            log(`[WATCHDOG] Escalated job ${job.id} — lease expired`);
          }

          const runawayJobs = await storage.getRunawayJobs();
          for (const job of runawayJobs) {
            const impact = job.impactAnalysis as { estimatedTimeSeconds?: number } | null;
            if (impact?.estimatedTimeSeconds && job.approvedAt) {
              const elapsedMs = Date.now() - new Date(job.approvedAt).getTime();
              const thresholdMs = impact.estimatedTimeSeconds * 2 * 1000;
              if (elapsedMs > thresholdMs) {
                const escalationLog = (job.logs || "") + "\n[WATCHDOG] Execution exceeded safety threshold. Escalated.";
                await storage.updateRunningJob(job.id, escalationLog, "escalated");
                log(`[WATCHDOG] Escalated job ${job.id} — exceeded time threshold`);
              }
            }
          }
        } catch (err) {
          console.error("[WATCHDOG] Error:", err);
        }
      }, 5000);
    },
  );
})();

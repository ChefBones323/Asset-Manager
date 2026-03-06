import { InfrastructurePanel } from "@/components/workers/InfrastructurePanel";
import { EventPulsePanel } from "@/components/events/EventPulsePanel";
import { VerifiedPostCard, type PostData } from "@/components/feed/VerifiedPostCard";
import { Rss } from "lucide-react";

const MOCK_FEED: PostData[] = [
  {
    content_id: "demo-001",
    author_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    author_name: "CivicReporter",
    trust_score: 82,
    content: "New governance proposal submitted: Increase trust weight in feed ranking from 0.20 to 0.30 for community-sourced content.",
    reaction_count: 14,
    comment_count: 3,
    timestamp: new Date(Date.now() - 120000).toISOString(),
    event_id: "evt-f7a3b2c1-demo",
    manifest_id: "mfst-98765-demo",
    policy_version: "CivicBalanced_v3",
  },
  {
    content_id: "demo-002",
    author_id: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    author_name: "InfraOps",
    trust_score: 65,
    content: "Worker pool scaled to 12 nodes. Queue depth nominal. All projections current.",
    reaction_count: 8,
    timestamp: new Date(Date.now() - 300000).toISOString(),
    event_id: "evt-d4e5f6a7-demo",
    manifest_id: "mfst-54321-demo",
    policy_version: "CivicBalanced_v3",
  },
  {
    content_id: "demo-003",
    author_id: "c3d4e5f6-a7b8-9012-cdef-123456789012",
    author_name: "TrustAnalyst",
    trust_score: 28,
    content: "Trust delegation chain detected between 4 accounts. Loop prevention engaged at depth 3. Manual review recommended.",
    reaction_count: 2,
    comment_count: 7,
    timestamp: new Date(Date.now() - 900000).toISOString(),
  },
];

export default function MissionControl() {
  return (
    <div className="h-full flex flex-col" data-testid="mission-control">
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[260px_1fr_280px] gap-0 min-h-0 overflow-hidden">
        <div className="glass-panel border-r border-white/[0.06] p-3 overflow-y-auto hidden lg:block">
          <InfrastructurePanel />
        </div>

        <div className="p-4 overflow-y-auto">
          <div className="flex items-center gap-2 mb-4">
            <Rss className="w-4 h-4 text-signal-blue" />
            <span className="mono-label">Verified Civic Feed</span>
          </div>
          <div className="space-y-3 max-w-2xl" data-testid="civic-feed">
            {MOCK_FEED.map((post) => (
              <VerifiedPostCard key={post.content_id} post={post} />
            ))}
          </div>
        </div>

        <div className="glass-panel border-l border-white/[0.06] hidden lg:flex flex-col min-h-0">
          <EventPulsePanel />
        </div>
      </div>
    </div>
  );
}

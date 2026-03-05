import { memo, useState, useCallback } from "react";
import { GlassModal } from "@/components/common/Modal";
import { cn } from "@/lib/utils";
import { ShieldCheck, Heart, MessageCircle, Share2, Clock } from "lucide-react";

export interface PostData {
  content_id: string;
  author_id: string;
  author_name?: string;
  trust_score: number;
  content: string;
  reaction_count: number;
  comment_count?: number;
  share_count?: number;
  timestamp: string;
  event_id?: string;
  manifest_id?: string;
  proposal_creator?: string;
  proposal_approver?: string;
  policy_version?: string;
}

function trustGlowClass(score: number): string {
  if (score >= 50) return "border-signal-green/20 shadow-[0_0_12px_-4px_hsl(var(--signal-green)/0.1)]";
  if (score >= 0) return "border-white/[0.06]";
  return "border-white/[0.04]";
}

function trustLabel(score: number): { text: string; color: string } {
  if (score >= 70) return { text: "High Trust", color: "text-signal-green" };
  if (score >= 30) return { text: "Medium Trust", color: "text-signal-amber" };
  return { text: "Low Trust", color: "text-muted-foreground" };
}

export const VerifiedPostCard = memo(function VerifiedPostCard({ post }: { post: PostData }) {
  const [provOpen, setProvOpen] = useState(false);
  const openProv = useCallback(() => setProvOpen(true), []);
  const closeProv = useCallback(() => setProvOpen(false), []);

  const trust = trustLabel(post.trust_score);
  const ts = new Date(post.timestamp);
  const timeStr = ts.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + " " +
    ts.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" });

  return (
    <>
      <div
        className={cn("glass-panel rounded-lg border transition-colors", trustGlowClass(post.trust_score))}
        data-testid={`post-card-${post.content_id}`}
      >
        <div className="px-4 py-3 flex items-center gap-3 border-b border-white/[0.06]">
          <div className="w-8 h-8 rounded-full bg-white/[0.06] flex items-center justify-center text-xs font-mono text-foreground">
            {(post.author_name || post.author_id).slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-foreground truncate">{post.author_name || post.author_id.slice(0, 12)}</div>
            <div className="flex items-center gap-2 text-[10px]">
              <span className={cn("font-mono", trust.color)}>{trust.text} ({post.trust_score})</span>
            </div>
          </div>
          <button
            onClick={openProv}
            className="p-1.5 rounded-md hover:bg-white/[0.06] transition-colors"
            title="View provenance"
            data-testid={`post-verify-${post.content_id}`}
          >
            <ShieldCheck className="w-4 h-4 text-signal-blue" />
          </button>
        </div>

        <div className="px-4 py-3">
          <p className="text-sm text-foreground leading-relaxed">{post.content}</p>
        </div>

        <div className="px-4 py-2 flex items-center gap-4 border-t border-white/[0.06] text-xs text-muted-foreground">
          <span className="flex items-center gap-1"><Heart className="w-3 h-3" />{post.reaction_count}</span>
          {post.comment_count !== undefined && (
            <span className="flex items-center gap-1"><MessageCircle className="w-3 h-3" />{post.comment_count}</span>
          )}
          {post.share_count !== undefined && (
            <span className="flex items-center gap-1"><Share2 className="w-3 h-3" />{post.share_count}</span>
          )}
          <span className="ml-auto flex items-center gap-1"><Clock className="w-3 h-3" />{timeStr}</span>
        </div>
      </div>

      <GlassModal open={provOpen} onClose={closeProv} title="Provenance" size="md" data-testid="provenance-modal">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-signal-blue" />
            <span className="text-sm font-semibold text-foreground">Verified Content</span>
          </div>
          <div className="grid grid-cols-1 gap-2 text-xs">
            <div className="glass-inset rounded-md px-3 py-2">
              <span className="mono-label">Event ID</span>
              <p className="font-mono text-foreground mt-0.5 break-all" data-testid="prov-event-id">{post.event_id || "N/A"}</p>
            </div>
            <div className="glass-inset rounded-md px-3 py-2">
              <span className="mono-label">Manifest ID</span>
              <p className="font-mono text-foreground mt-0.5 break-all" data-testid="prov-manifest-id">{post.manifest_id || "N/A"}</p>
            </div>
            <div className="glass-inset rounded-md px-3 py-2">
              <span className="mono-label">Proposal Creator</span>
              <p className="font-mono text-foreground mt-0.5 break-all">{post.proposal_creator || "N/A"}</p>
            </div>
            <div className="glass-inset rounded-md px-3 py-2">
              <span className="mono-label">Policy Version</span>
              <p className="font-mono text-foreground mt-0.5">{post.policy_version || "N/A"}</p>
            </div>
          </div>
        </div>
      </GlassModal>
    </>
  );
});

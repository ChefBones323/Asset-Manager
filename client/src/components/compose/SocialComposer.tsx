import { useState, useCallback } from "react";
import { useUIState } from "@/store/uiState";
import { useEventStore, type PlatformEvent } from "@/store/eventStore";
import { GlassModal } from "@/components/common/Modal";
import { SUPPORTED_PLATFORMS, type PlatformId } from "@/interfaces/socialPost";
import { cn } from "@/lib/utils";
import { Send, Shield, MessageSquare, Check } from "lucide-react";
import {
  SiFacebook, SiX, SiLinkedin, SiInstagram, SiYoutube, SiReddit, SiDiscord,
} from "react-icons/si";

type ComposeMode = "post" | "proposal";

const platformIcons: Record<string, typeof SiFacebook> = {
  facebook: SiFacebook,
  twitter: SiX,
  linkedin: SiLinkedin,
  instagram: SiInstagram,
  youtube: SiYoutube,
  reddit: SiReddit,
  discord: SiDiscord,
};

export function SocialComposer() {
  const { composerOpen, closeComposer } = useUIState();
  const pushEvent = useEventStore((s) => s.pushEvent);
  const [mode, setMode] = useState<ComposeMode>("post");
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [domain, setDomain] = useState("content");
  const [submitting, setSubmitting] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<PlatformId>>(
    () => new Set(SUPPORTED_PLATFORMS.filter((p) => p.default).map((p) => p.id))
  );

  const togglePlatform = useCallback((id: PlatformId) => {
    setSelectedPlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        if (id === "civic" && next.size === 1) return prev;
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleClose = () => {
    closeComposer();
    setContent("");
    setTitle("");
    setMode("post");
    setSelectedPlatforms(new Set(SUPPORTED_PLATFORMS.filter((p) => p.default).map((p) => p.id)));
  };

  const handleSubmit = async () => {
    if (mode === "post" && !content.trim()) return;
    if (mode === "proposal" && (!title.trim() || !content.trim())) return;

    setSubmitting(true);

    const platforms = Array.from(selectedPlatforms);
    const eventId = `evt-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

    if (mode === "post") {
      const event: PlatformEvent = {
        event_id: eventId,
        domain: "content",
        event_type: "content_created",
        actor_id: "operator",
        payload: {
          content: content.trim(),
          platforms,
          publish_type: "social_post",
        },
        timestamp: new Date().toISOString(),
      };
      pushEvent(event);
    } else {
      const event: PlatformEvent = {
        event_id: eventId,
        domain: "governance",
        event_type: "proposal_submitted",
        actor_id: "operator",
        payload: {
          title: title.trim(),
          description: content.trim(),
          domain,
          proposal_type: "policy_change",
          platforms,
        },
        timestamp: new Date().toISOString(),
      };
      pushEvent(event);
    }

    await new Promise((resolve) => setTimeout(resolve, 400));
    setSubmitting(false);
    handleClose();
  };

  const canSubmit = mode === "post"
    ? content.trim().length > 0
    : title.trim().length > 0 && content.trim().length > 0;

  return (
    <GlassModal
      open={composerOpen}
      onClose={handleClose}
      title={mode === "post" ? "Create Civic Post" : "Create Governance Proposal"}
      size="md"
      data-testid="social-composer-modal"
    >
      <div className="space-y-4">
        <div className="flex gap-1 p-0.5 rounded-lg bg-white/[0.04]" data-testid="composer-mode-tabs">
          <button
            onClick={() => setMode("post")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex-1 justify-center",
              mode === "post"
                ? "bg-white/[0.08] text-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
            data-testid="tab-post"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Post
          </button>
          <button
            onClick={() => setMode("proposal")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex-1 justify-center",
              mode === "proposal"
                ? "bg-white/[0.08] text-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
            data-testid="tab-proposal"
          >
            <Shield className="w-3.5 h-3.5" />
            Proposal
          </button>
        </div>

        {mode === "proposal" && (
          <>
            <div className="space-y-1.5">
              <label className="mono-label text-[10px]">Title</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Proposal title..."
                className="w-full bg-background border border-white/[0.1] rounded-md px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground outline-none focus:border-signal-blue/50"
                data-testid="input-proposal-title"
              />
            </div>
            <div className="space-y-1.5">
              <label className="mono-label text-[10px]">Domain</label>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="bg-background border border-white/[0.1] rounded-md px-2 py-1.5 text-xs font-mono text-foreground"
                data-testid="select-proposal-domain"
              >
                <option value="content">Content</option>
                <option value="trust">Trust</option>
                <option value="governance">Governance</option>
                <option value="platform">Platform</option>
                <option value="feed_policy">Feed Policy</option>
              </select>
            </div>
          </>
        )}

        <div className="space-y-1.5">
          <label className="mono-label text-[10px]">
            {mode === "post" ? "Content" : "Description"}
          </label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={mode === "post" ? "Share a civic update..." : "Describe the proposal..."}
            rows={4}
            className="w-full bg-background border border-white/[0.1] rounded-md px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground outline-none focus:border-signal-blue/50 resize-none"
            data-testid="input-content"
          />
        </div>

        <div className="space-y-2">
          <label className="mono-label text-[10px]">Platforms</label>
          <div className="grid grid-cols-2 gap-1.5" data-testid="platform-selector">
            {SUPPORTED_PLATFORMS.map((platform) => {
              const selected = selectedPlatforms.has(platform.id);
              const PlatformIcon = platformIcons[platform.id];
              return (
                <button
                  key={platform.id}
                  onClick={() => togglePlatform(platform.id)}
                  className={cn(
                    "flex items-center gap-2 px-2.5 py-2 rounded-md text-xs transition-colors text-left",
                    selected
                      ? "bg-white/[0.08] text-foreground border border-signal-blue/30"
                      : "bg-white/[0.02] text-muted-foreground border border-white/[0.06] hover:bg-white/[0.04]"
                  )}
                  data-testid={`platform-toggle-${platform.id}`}
                >
                  <div className={cn(
                    "w-4 h-4 rounded border flex items-center justify-center shrink-0",
                    selected
                      ? "bg-signal-blue border-signal-blue"
                      : "border-white/[0.2]"
                  )}>
                    {selected && <Check className="w-3 h-3 text-white" />}
                  </div>
                  {PlatformIcon && <PlatformIcon className="w-3.5 h-3.5 shrink-0" />}
                  <span className="font-medium">{platform.label}</span>
                </button>
              );
            })}
          </div>
          <p className="text-[10px] font-mono text-muted-foreground">
            {selectedPlatforms.size} platform{selectedPlatforms.size !== 1 ? "s" : ""} selected
          </p>
        </div>

        <div className="flex items-center justify-between pt-1">
          <span className="text-[10px] font-mono text-muted-foreground">
            {content.length} chars
          </span>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-medium transition-colors",
              canSubmit && !submitting
                ? "bg-signal-blue text-white hover:bg-signal-blue/90"
                : "bg-white/[0.04] text-muted-foreground cursor-not-allowed"
            )}
            data-testid="btn-submit-compose"
          >
            {submitting ? (
              <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send className="w-3.5 h-3.5" />
            )}
            {mode === "post" ? "Publish" : "Submit Proposal"}
          </button>
        </div>
      </div>
    </GlassModal>
  );
}

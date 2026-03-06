import { useState } from "react";
import { useUIState } from "@/store/uiState";
import { GlassModal } from "@/components/common/Modal";
import { cn } from "@/lib/utils";
import { Send, FileText, Shield, MessageSquare } from "lucide-react";

type ComposeMode = "post" | "proposal";

export function SocialComposer() {
  const { composerOpen, closeComposer } = useUIState();
  const [mode, setMode] = useState<ComposeMode>("post");
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [domain, setDomain] = useState("content");
  const [submitting, setSubmitting] = useState(false);

  const handleClose = () => {
    closeComposer();
    setContent("");
    setTitle("");
    setMode("post");
  };

  const handleSubmit = async () => {
    if (mode === "post" && !content.trim()) return;
    if (mode === "proposal" && (!title.trim() || !content.trim())) return;

    setSubmitting(true);
    setTimeout(() => {
      setSubmitting(false);
      handleClose();
    }, 600);
  };

  const canSubmit = mode === "post" ? content.trim().length > 0 : title.trim().length > 0 && content.trim().length > 0;

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

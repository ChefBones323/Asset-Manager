import { memo, useCallback, useState } from "react";
import { useEventStore, type PlatformEvent } from "@/store/eventStore";
import { GlassModal } from "@/components/common/Modal";
import { cn } from "@/lib/utils";

const domainColors: Record<string, string> = {
  content: "signal-dot-blue",
  trust: "signal-dot-green",
  governance: "signal-dot-purple",
  platform: "signal-dot-amber",
  feed_policy: "signal-dot-purple",
  workers: "signal-dot-amber",
  error: "signal-dot-red",
};

function getDotClass(event: PlatformEvent): string {
  if (event.event_type.includes("failed") || event.event_type.includes("error")) {
    return "signal-dot-red";
  }
  return domainColors[event.domain] || "signal-dot-blue";
}

const EventPulseItem = memo(function EventPulseItem({
  event,
  onSelect,
}: {
  event: PlatformEvent;
  onSelect: (e: PlatformEvent) => void;
}) {
  const handleClick = useCallback(() => onSelect(event), [event, onSelect]);
  const ts = new Date(event.timestamp);
  const timeStr = ts.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });

  return (
    <button
      onClick={handleClick}
      className="w-full flex items-center gap-2.5 px-3 py-1.5 hover:bg-white/[0.04] transition-colors text-left group"
      data-testid={`event-pulse-${event.event_id}`}
    >
      <div className={cn("signal-dot shrink-0", getDotClass(event))} />
      <span className="font-mono text-[11px] text-muted-foreground w-[60px] shrink-0">{timeStr}</span>
      <span className="font-mono text-[11px] text-foreground truncate flex-1">{event.event_type}</span>
      <span className="mono-label text-[9px] opacity-0 group-hover:opacity-100 transition-opacity">{event.domain}</span>
    </button>
  );
});

interface EventPulsePanelProps {
  maxVisible?: number;
  className?: string;
}

export const EventPulsePanel = memo(function EventPulsePanel({ maxVisible = 50, className }: EventPulsePanelProps) {
  const events = useEventStore((s) => s.events);
  const [inspecting, setInspecting] = useState<PlatformEvent | null>(null);

  const handleSelect = useCallback((e: PlatformEvent) => setInspecting(e), []);
  const handleClose = useCallback(() => setInspecting(null), []);

  const visible = events.slice(-maxVisible).reverse();

  return (
    <>
      <div className={cn("flex flex-col h-full", className)} data-testid="event-pulse-panel">
        <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.06]">
          <span className="mono-label">Event Pulse</span>
          <span className="font-mono text-[10px] text-muted-foreground">{events.length} events</span>
        </div>
        <div className="flex-1 overflow-y-auto min-h-0">
          {visible.length === 0 ? (
            <div className="px-3 py-8 text-center text-xs text-muted-foreground" data-testid="event-pulse-empty">
              Waiting for events...
            </div>
          ) : (
            visible.map((ev) => (
              <EventPulseItem key={ev.event_id} event={ev} onSelect={handleSelect} />
            ))
          )}
        </div>
      </div>

      <GlassModal
        open={!!inspecting}
        onClose={handleClose}
        title="Event Inspector"
        size="lg"
        data-testid="event-inspector-modal"
      >
        {inspecting && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className={cn("signal-dot", getDotClass(inspecting))} />
              <span className="font-mono text-sm font-semibold">{inspecting.event_type}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div><span className="mono-label">Event ID</span><p className="font-mono text-foreground mt-0.5 break-all" data-testid="inspector-event-id">{inspecting.event_id}</p></div>
              <div><span className="mono-label">Domain</span><p className="font-mono text-foreground mt-0.5">{inspecting.domain}</p></div>
              <div><span className="mono-label">Actor</span><p className="font-mono text-foreground mt-0.5 break-all">{inspecting.actor_id}</p></div>
              <div><span className="mono-label">Timestamp</span><p className="font-mono text-foreground mt-0.5">{inspecting.timestamp}</p></div>
              {inspecting.manifest_id && (
                <div><span className="mono-label">Manifest ID</span><p className="font-mono text-foreground mt-0.5 break-all">{inspecting.manifest_id}</p></div>
              )}
              {inspecting.event_sequence !== undefined && (
                <div><span className="mono-label">Sequence</span><p className="font-mono text-foreground mt-0.5">{inspecting.event_sequence}</p></div>
              )}
            </div>
            <div>
              <span className="mono-label">Payload</span>
              <pre className="mt-1 glass-inset rounded-md p-3 text-[11px] font-mono text-foreground overflow-auto max-h-[300px]" data-testid="inspector-payload">
                {JSON.stringify(inspecting.payload, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </GlassModal>
    </>
  );
});

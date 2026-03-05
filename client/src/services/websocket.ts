import { pushEventFromStream } from "@/store/eventStore";

let eventSource: EventSource | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

export function connectEventStream(): void {
  if (eventSource) return;

  try {
    eventSource = new EventSource("/admin/events?stream=true");

    eventSource.addEventListener("event", (e) => {
      try {
        const data = JSON.parse(e.data);
        pushEventFromStream(data);
      } catch {
      }
    });

    eventSource.onerror = () => {
      disconnectEventStream();
      reconnectTimer = setTimeout(connectEventStream, 5000);
    };
  } catch {
    reconnectTimer = setTimeout(connectEventStream, 5000);
  }
}

export function disconnectEventStream(): void {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

export function isConnected(): boolean {
  return eventSource !== null && eventSource.readyState === EventSource.OPEN;
}

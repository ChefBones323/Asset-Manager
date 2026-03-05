import { create } from "zustand";

export interface PlatformEvent {
  event_id: string;
  event_sequence?: number;
  domain: string;
  event_type: string;
  actor_id: string;
  payload: Record<string, unknown>;
  timestamp: string;
  manifest_id?: string;
  execution_id?: string;
}

const MAX_BUFFER_SIZE = 200;

class CircularBuffer<T> {
  private buffer: T[] = [];
  private head = 0;
  private count = 0;
  private capacity: number;

  constructor(capacity: number) {
    this.capacity = capacity;
    this.buffer = new Array(capacity);
  }

  push(item: T): void {
    const index = (this.head + this.count) % this.capacity;
    if (this.count < this.capacity) {
      this.buffer[index] = item;
      this.count++;
    } else {
      this.buffer[this.head] = item;
      this.head = (this.head + 1) % this.capacity;
    }
  }

  toArray(): T[] {
    const result: T[] = [];
    for (let i = 0; i < this.count; i++) {
      result.push(this.buffer[(this.head + i) % this.capacity]);
    }
    return result;
  }

  get length(): number {
    return this.count;
  }

  clear(): void {
    this.buffer = new Array(this.capacity);
    this.head = 0;
    this.count = 0;
  }
}

interface EventStoreState {
  events: PlatformEvent[];
  _buffer: CircularBuffer<PlatformEvent>;
  pushEvent: (event: PlatformEvent) => void;
  clearEvents: () => void;
}

export const useEventStore = create<EventStoreState>((set, get) => {
  const buffer = new CircularBuffer<PlatformEvent>(MAX_BUFFER_SIZE);
  return {
    events: [],
    _buffer: buffer,
    pushEvent: (event: PlatformEvent) => {
      const buf = get()._buffer;
      buf.push(deepFreeze(event) as PlatformEvent);
      set({ events: buf.toArray() });
    },
    clearEvents: () => {
      get()._buffer.clear();
      set({ events: [] });
    },
  };
});

function deepFreeze<T extends object>(obj: T): T {
  Object.freeze(obj);
  for (const val of Object.values(obj)) {
    if (val && typeof val === "object" && !Object.isFrozen(val)) {
      deepFreeze(val as object);
    }
  }
  return obj;
}

export function pushEventFromStream(raw: unknown): void {
  if (!raw || typeof raw !== "object") return;
  const obj = raw as Record<string, unknown>;
  if (typeof obj.event_id !== "string" || !obj.event_id) return;
  if (typeof obj.domain !== "string" || !obj.domain) return;
  if (typeof obj.event_type !== "string" || !obj.event_type) return;
  if (obj.timestamp !== undefined && typeof obj.timestamp !== "string") return;
  if (obj.actor_id !== undefined && typeof obj.actor_id !== "string") return;

  const payloadSource = obj.payload && typeof obj.payload === "object" ? obj.payload : {};
  const frozenPayload = deepFreeze(JSON.parse(JSON.stringify(payloadSource))) as Record<string, unknown>;

  const event: PlatformEvent = {
    event_id: obj.event_id,
    event_sequence: typeof obj.event_sequence === "number" ? obj.event_sequence : undefined,
    domain: obj.domain,
    event_type: obj.event_type,
    actor_id: typeof obj.actor_id === "string" ? obj.actor_id : "",
    payload: frozenPayload,
    timestamp: typeof obj.timestamp === "string" ? obj.timestamp : new Date().toISOString(),
    manifest_id: typeof obj.manifest_id === "string" ? obj.manifest_id : undefined,
    execution_id: typeof obj.execution_id === "string" ? obj.execution_id : undefined,
  };
  useEventStore.getState().pushEvent(event);
}

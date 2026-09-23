import type { RunEvent } from "../api/types";
import type { EventSourceFactory, EventSourceLike } from "../dashboard/useRun";

type Listener = (event: MessageEvent | Event) => void;

export class FakeEventSource implements EventSourceLike {
  static instances: FakeEventSource[] = [];
  readonly listeners = new Map<string, Set<Listener>>();
  closed = false;

  constructor(public readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener): void {
    const set = this.listeners.get(type) ?? new Set<Listener>();
    set.add(listener);
    this.listeners.set(type, set);
  }

  close(): void {
    this.closed = true;
  }

  emit(event: RunEvent): void {
    const message = new MessageEvent(event.type, { data: JSON.stringify(event), lastEventId: String(event.id) });
    this.listeners.get(event.type)?.forEach((listener) => listener(message));
  }

  emitAll(events: RunEvent[]): void {
    events.forEach((event) => this.emit(event));
  }

  emitRaw(type: string, data: string): void {
    const message = new MessageEvent(type, { data });
    this.listeners.get(type)?.forEach((listener) => listener(message));
  }

  emitError(): void {
    const event = new Event("error");
    this.listeners.get("error")?.forEach((listener) => listener(event));
  }

  static reset(): void {
    FakeEventSource.instances = [];
  }

  static last(): FakeEventSource {
    const last = FakeEventSource.instances.at(-1);
    if (!last) throw new Error("no FakeEventSource opened");
    return last;
  }
}

export const fakeEventSourceFactory: EventSourceFactory = (url) => new FakeEventSource(url);

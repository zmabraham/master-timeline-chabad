import type { EventRecord } from './types';

let cachedEvents: EventRecord[] | null = null;
const storyCache = new Map<string, string>();

export async function loadEvents(): Promise<EventRecord[]> {
  if (cachedEvents) return cachedEvents;
  const resp = await fetch(import.meta.env.BASE_URL + 'events.json');
  if (!resp.ok) {
    throw new Error(`failed to load events.json: ${resp.status} ${resp.statusText}`);
  }
  cachedEvents = (await resp.json()) as EventRecord[];
  return cachedEvents;
}

export async function loadStory(id: string, storyPath: string): Promise<string> {
  if (storyCache.has(id)) return storyCache.get(id)!;
  const resp = await fetch(import.meta.env.BASE_URL + storyPath);
  if (!resp.ok) {
    throw new Error(`failed to load story ${id}: ${resp.status}`);
  }
  const text = await resp.text();
  storyCache.set(id, text);
  return text;
}

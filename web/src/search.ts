import lunr from 'lunr';
import type { EventRecord } from './types';

export interface SearchHandle {
  query(q: string): Set<string>;  // returns matching event ids
}

export function buildSearch(events: EventRecord[]): SearchHandle {
  const idx = lunr(function () {
    this.ref('id');
    this.field('title', { boost: 3 });
    this.field('summary');
    this.field('tags');
    this.metadataWhitelist = ['position'];
    for (const e of events) {
      this.add({
        id: e.id,
        title: e.title_en,
        summary: e.summary_en,
        tags: e.tags.join(' '),
      });
    }
  });
  return {
    query(q) {
      if (!q.trim()) return new Set(events.map((e) => e.id));
      try {
        const results = idx.search(q + '*');  // prefix match
        return new Set(results.map((r) => r.ref));
      } catch {
        return new Set();
      }
    },
  };
}

import { marked } from 'marked';
import type { EventRecord } from './types';
import { loadStory } from './data';

export interface PanelHandle {
  open(event: EventRecord, allEvents: EventRecord[]): Promise<void>;
  close(): void;
}

export function buildPanel(host: HTMLElement): PanelHandle {
  host.classList.add('panel');
  host.innerHTML = `
    <button class="panel-close" aria-label="Close">&times;</button>
    <div class="panel-body"></div>
  `;
  const body = host.querySelector('.panel-body') as HTMLElement;
  const closeBtn = host.querySelector('.panel-close') as HTMLButtonElement;

  function close() { host.classList.remove('open'); }
  closeBtn.addEventListener('click', close);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });

  async function open(e: EventRecord, allEvents: EventRecord[]) {
    host.classList.add('open');
    body.innerHTML = `<p class="panel-loading">Loading…</p>`;

    let storyHtml = '';
    try {
      const md = await loadStory(e.id, e.story_path);
      storyHtml = await marked.parse(md);
    } catch (_err) {
      storyHtml = `<p><em>Story unavailable.</em></p>`;
    }

    const dateStr = e.date.m && e.date.d
      ? `${e.date.y}-${String(e.date.m).padStart(2, '0')}-${String(e.date.d).padStart(2, '0')}`
      : e.date.m
      ? `${e.date.y}-${String(e.date.m).padStart(2, '0')}`
      : String(e.date.y);

    const related = e.related
      .map((id) => allEvents.find((x) => x.id === id))
      .filter((x): x is EventRecord => !!x)
      .slice(0, 5);

    body.innerHTML = `
      <div class="panel-meta">${dateStr}</div>
      <h2>${escape(e.title_en)}</h2>
      <p class="panel-summary">${escape(e.summary_en)}</p>
      <div class="panel-story">${storyHtml}</div>
      ${e.tags.length ? `<div class="panel-tags">${e.tags.map((t) => `<span class="tag">${escape(t)}</span>`).join('')}</div>` : ''}
      ${related.length ? `
        <h3>Related</h3>
        <ul class="panel-related">${related.map((r) => `<li data-related-id="${r.id}">${escape(r.title_en)} <em>(${r.date.y})</em></li>`).join('')}</ul>
      ` : ''}
      ${e.sources.length ? `
        <h3>Sources</h3>
        <ul class="panel-sources">${e.sources.map((s) => `<li>${escape(s.name)}${s.page ? ` p.${s.page}` : ''}</li>`).join('')}</ul>
      ` : ''}
    `;

    body.querySelectorAll<HTMLElement>('[data-related-id]').forEach((li) => {
      li.addEventListener('click', () => {
        const rid = li.dataset.relatedId!;
        const rev = allEvents.find((x) => x.id === rid);
        if (rev) open(rev, allEvents);
      });
    });
  }

  return { open, close };
}

function escape(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

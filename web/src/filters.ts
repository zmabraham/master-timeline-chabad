import type { EventRecord, EventCategory, RebbeId, SignificanceBin } from './types';
import { bin } from './types';

export interface FilterState {
  rebbes: Set<RebbeId | 'none'>;     // 'none' = events with no rebbe set
  categories: Set<EventCategory>;
  bins: Set<SignificanceBin>;
}

export function initialFilters(): FilterState {
  return {
    rebbes: new Set(),
    categories: new Set(),
    bins: new Set(),
  };
}

export function applyFilters(events: EventRecord[], f: FilterState): EventRecord[] {
  return events.filter((e) => {
    if (f.rebbes.size > 0) {
      const rk = e.rebbe ?? 'none';
      if (!f.rebbes.has(rk)) return false;
    }
    if (f.categories.size > 0) {
      if (!e.categories.some((c) => f.categories.has(c))) return false;
    }
    if (f.bins.size > 0) {
      if (!f.bins.has(bin(e.significance))) return false;
    }
    return true;
  });
}

const REBBE_OPTIONS: { id: RebbeId | 'none'; label: string }[] = [
  { id: 'besht', label: 'Baal Shem Tov' },
  { id: 'magid', label: 'Maggid' },
  { id: 'alter', label: 'Alter Rebbe' },
  { id: 'mitteler', label: 'Mitteler' },
  { id: 'tzemach-tzedek', label: 'Tzemach Tzedek' },
  { id: 'maharash', label: 'Maharash' },
  { id: 'rashab', label: 'Rashab' },
  { id: 'rayatz', label: 'Rayatz' },
  { id: 'rebbe', label: 'The Rebbe' },
  { id: 'none', label: '(none)' },
];

const CATEGORY_OPTIONS: EventCategory[] = [
  'rebbe', 'publication', 'conflict', 'education',
  'organization', 'location', 'calendar', 'general',
];

const BIN_OPTIONS: SignificanceBin[] = ['macro', 'meso', 'micro'];

export function buildFilterBar(host: HTMLElement, state: FilterState, onChange: () => void) {
  host.classList.add('filters');
  const renderGroup = <T extends string>(
    label: string,
    options: T[] | { id: T; label: string }[],
    set: Set<T>,
  ) => {
    const isString = (o: unknown): o is string => typeof o === 'string';
    const chips = options.map((opt) => {
      const id = isString(opt) ? opt : opt.id;
      const text = isString(opt) ? opt : opt.label;
      const active = set.has(id);
      return `<button class="chip${active ? ' active' : ''}" data-value="${id}">${text}</button>`;
    }).join('');
    return `<div class="filter-group"><span class="filter-label">${label}</span><div class="filter-chips">${chips}</div></div>`;
  };

  host.innerHTML = `
    ${renderGroup('Rebbe', REBBE_OPTIONS, state.rebbes)}
    ${renderGroup('Category', CATEGORY_OPTIONS, state.categories)}
    ${renderGroup('Level', BIN_OPTIONS, state.bins)}
  `;

  host.querySelectorAll<HTMLButtonElement>('.chip').forEach((btn) => {
    btn.addEventListener('click', () => {
      const group = btn.closest('.filter-group')!;
      const label = group.querySelector('.filter-label')!.textContent;
      const value = btn.dataset.value!;
      const set = label === 'Rebbe' ? state.rebbes
                : label === 'Category' ? state.categories
                : state.bins;
      // @ts-ignore narrowing via the Set type
      if (set.has(value)) set.delete(value); else set.add(value);
      btn.classList.toggle('active');
      onChange();
    });
  });
}

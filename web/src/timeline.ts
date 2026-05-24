import { Timeline, type TimelineOptions } from 'vis-timeline/standalone';
import { DataSet } from 'vis-data';
import type { EventRecord, RebbeId } from './types';
import { bin } from './types';

export type GroupBy = 'rebbe' | 'category' | 'era' | 'flat';

const REBBE_LABELS: Record<RebbeId, string> = {
  besht: 'Baal Shem Tov',
  magid: 'Maggid of Mezeritch',
  alter: 'Alter Rebbe',
  mitteler: 'Mitteler Rebbe',
  'tzemach-tzedek': 'Tzemach Tzedek',
  maharash: 'Maharash',
  rashab: 'Rashab',
  rayatz: 'Rayatz',
  rebbe: 'The Rebbe',
};
const REBBE_ORDER: (RebbeId | 'general')[] = [
  'besht', 'magid', 'alter', 'mitteler', 'tzemach-tzedek',
  'maharash', 'rashab', 'rayatz', 'rebbe', 'general',
];

const CATEGORY_LABELS: Record<string, string> = {
  rebbe: 'Rebbe', publication: 'Publication', conflict: 'Conflict',
  education: 'Education', organization: 'Organization', location: 'Location',
  calendar: 'Calendar', general: 'General',
};

function eventDate(e: EventRecord): Date {
  const { y, m, d } = e.date;
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

export function groupForEvent(e: EventRecord, mode: GroupBy): string {
  switch (mode) {
    case 'rebbe': return e.rebbe ?? 'general';
    case 'category': return e.categories[0] ?? 'general';
    case 'era': return e.era ?? 'unsorted';
    case 'flat': return 'all';
  }
}

function buildGroupsForMode(events: EventRecord[], mode: GroupBy) {
  if (mode === 'rebbe') {
    return REBBE_ORDER.map((id, idx) => ({
      id,
      content: id === 'general' ? 'General' : REBBE_LABELS[id as RebbeId],
      order: idx,
    }));
  }
  if (mode === 'category') {
    const seen = new Set(events.flatMap((e) => e.categories[0] ?? 'general'));
    return [...seen].sort().map((id, idx) => ({
      id, content: CATEGORY_LABELS[id] ?? id, order: idx,
    }));
  }
  if (mode === 'era') {
    const seen = new Set(events.map((e) => e.era ?? 'unsorted'));
    return [...seen].sort().map((id, idx) => ({ id, content: id, order: idx }));
  }
  // flat
  return [{ id: 'all', content: 'All events', order: 0 }];
}

function itemFor(e: EventRecord, mode: GroupBy) {
  return {
    id: e.id,
    group: groupForEvent(e, mode),
    start: eventDate(e),
    content: e.title_en,
    title: e.summary_en,
    className: `level-${bin(e.significance)}`,
  };
}

export interface TimelineHandle {
  timeline: Timeline;
  refresh(events: EventRecord[]): void;
  setGroupBy(mode: GroupBy): void;
}

export function buildTimeline(
  container: HTMLElement,
  events: EventRecord[],
  onSelect: (id: string) => void,
): TimelineHandle {
  let currentMode: GroupBy = 'rebbe';
  let currentEvents = events;

  const groups = new DataSet(buildGroupsForMode(events, currentMode));
  const items = new DataSet(events.map((e) => itemFor(e, currentMode)));

  const options: TimelineOptions = {
    cluster: { titleTemplate: '{count} events', maxItems: 1 },
    stack: true,
    orientation: { axis: 'bottom' },
    zoomMin: 1000 * 60 * 60 * 24 * 7,
    zoomMax: 1000 * 60 * 60 * 24 * 365 * 500,
    horizontalScroll: true,
    zoomKey: 'ctrlKey',
    margin: { item: 4 },
  };

  const tl = new Timeline(container, items, groups, options);
  tl.on('select', (props) => {
    const id = props.items[0];
    if (typeof id === 'string') onSelect(id);
  });

  function rebuild() {
    groups.clear();
    groups.add(buildGroupsForMode(currentEvents, currentMode));
    items.clear();
    items.add(currentEvents.map((e) => itemFor(e, currentMode)));
  }

  return {
    timeline: tl,
    refresh(es) {
      currentEvents = es;
      rebuild();
    },
    setGroupBy(mode) {
      currentMode = mode;
      rebuild();
    },
  };
}

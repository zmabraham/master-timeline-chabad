import { Timeline, type TimelineOptions } from 'vis-timeline/standalone';
import { DataSet } from 'vis-data';
import type { EventRecord, RebbeId } from './types';
import { bin } from './types';

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

function eventDate(e: EventRecord): Date {
  const { y, m, d } = e.date;
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

export interface TimelineHandle {
  timeline: Timeline;
  refresh(events: EventRecord[]): void;
}

export function buildTimeline(
  container: HTMLElement,
  events: EventRecord[],
  onSelect: (id: string) => void,
): TimelineHandle {
  const groups = new DataSet(
    REBBE_ORDER.map((id, idx) => ({
      id,
      content: id === 'general' ? 'General' : REBBE_LABELS[id as RebbeId],
      order: idx,
    })),
  );

  const items = new DataSet(
    events.map((e) => ({
      id: e.id,
      group: e.rebbe ?? 'general',
      start: eventDate(e),
      content: e.title_en,
      title: e.summary_en,
      className: `level-${bin(e.significance)}`,
    })),
  );

  const options: TimelineOptions = {
    cluster: { titleTemplate: '{count} events', maxItems: 1 },
    stack: true,
    orientation: { axis: 'bottom' },
    zoomMin: 1000 * 60 * 60 * 24 * 7,        // 1 week
    zoomMax: 1000 * 60 * 60 * 24 * 365 * 500, // 500 years
    horizontalScroll: true,
    zoomKey: 'ctrlKey',
    margin: { item: 4 },
  };

  const tl = new Timeline(container, items, groups, options);
  tl.on('select', (props) => {
    const id = props.items[0];
    if (typeof id === 'string') onSelect(id);
  });

  return {
    timeline: tl,
    refresh(es) {
      items.clear();
      items.add(
        es.map((e) => ({
          id: e.id,
          group: e.rebbe ?? 'general',
          start: eventDate(e),
          content: e.title_en,
          title: e.summary_en,
          className: `level-${bin(e.significance)}`,
        })),
      );
    },
  };
}

export type EventCategory =
  | 'rebbe' | 'publication' | 'conflict' | 'education'
  | 'organization' | 'location' | 'calendar' | 'general';

export type RebbeId =
  | 'besht' | 'magid' | 'alter' | 'mitteler' | 'tzemach-tzedek'
  | 'maharash' | 'rashab' | 'rayatz' | 'rebbe';

export type DatePrecision = 'year' | 'month' | 'day';

export interface EventDate {
  y: number;
  m?: number;
  d?: number;
  precision: DatePrecision;
}

export interface EventPhoto {
  url: string;
  credit: string;
  caption?: string;
}

export interface EventSource {
  name: string;
  url?: string;
  page?: number;
}

export interface EventRecord {
  id: string;
  significance: number;            // 0-100
  date: EventDate;
  hebrew_date?: { y: number; m?: string; d?: number };
  title_en: string;
  summary_en: string;
  story_body?: string | null;
  story_path: string;
  categories: EventCategory[];
  tags: string[];
  rebbe?: RebbeId;
  era?: string;
  photo?: EventPhoto | null;
  sources: EventSource[];
  related: string[];
}

export type SignificanceBin = 'macro' | 'meso' | 'micro';

export function bin(sig: number): SignificanceBin {
  if (sig >= 80) return 'macro';
  if (sig >= 40) return 'meso';
  return 'micro';
}

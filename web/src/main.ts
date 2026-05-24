import { loadEvents } from './data';
import { buildTimeline } from './timeline';
import { buildPanel } from './panel';
import { buildSearch } from './search';
import { initialFilters, applyFilters, buildFilterBar } from './filters';
import './styles.css';
import 'vis-timeline/styles/vis-timeline-graph2d.min.css';

const app = document.getElementById('app')!;
app.innerHTML = `
  <header>
    <h1>Master Timeline Chabad</h1>
    <input id="search" type="search" placeholder="Search events…" />
  </header>
  <main id="timeline"></main>
  <aside id="panel"></aside>
`;

(async () => {
  const events = await loadEvents();
  const search = buildSearch(events);
  const panel = buildPanel(document.getElementById('panel')!);
  const tl = buildTimeline(
    document.getElementById('timeline')!,
    events,
    (id) => {
      const ev = events.find((e) => e.id === id);
      if (ev) panel.open(ev, events);
    },
  );

  const filters = initialFilters();
  const filtersHost = document.createElement('div');
  filtersHost.id = 'filters';
  document.querySelector('header')!.appendChild(filtersHost);

  const searchEl = document.getElementById('search') as HTMLInputElement;
  let debounce: number | undefined;

  function refresh() {
    const searchMatches = search.query(searchEl.value);
    const filtered = applyFilters(events, filters).filter((e) => searchMatches.has(e.id));
    tl.refresh(filtered);
  }

  buildFilterBar(filtersHost, filters, refresh);

  searchEl.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = window.setTimeout(refresh, 200);
  });
})();

import { loadEvents } from './data';
import { buildTimeline } from './timeline';
import { buildPanel } from './panel';
import { buildSearch } from './search';
import { initialFilters, applyFilters, buildFilterBar } from './filters';
import { buildGroupByToggle } from './groupby';
import './styles.css';
import 'vis-timeline/styles/vis-timeline-graph2d.min.css';

const app = document.getElementById('app')!;
app.innerHTML = `
  <header>
    <div class="header-row">
      <h1>Master Timeline Chabad</h1>
      <div class="header-spacer"></div>
      <div id="toolbar" class="toolbar" role="toolbar" aria-label="Timeline controls">
        <input id="year-jump" type="number" min="1500" max="2100" placeholder="Year" aria-label="Jump to year" />
        <button id="zoom-out" type="button" title="Zoom out" aria-label="Zoom out">−</button>
        <button id="zoom-in" type="button" title="Zoom in" aria-label="Zoom in">+</button>
        <button id="zoom-fit" type="button" title="Fit all events" aria-label="Fit all events">⤓</button>
      </div>
      <input id="search" type="search" placeholder="Search events…" aria-label="Search events" />
    </div>
  </header>
  <main id="timeline"></main>
  <p id="hint">Scroll to zoom · drag to pan · click a cluster to dive in</p>
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
  // Expose vis-timeline instance for E2E testability
  (window as any).__timeline = tl.timeline;

  const filters = initialFilters();
  const header = document.querySelector('header')!;

  const filtersHost = document.createElement('div');
  filtersHost.id = 'filters';
  header.appendChild(filtersHost);

  const groupByHost = document.createElement('div');
  groupByHost.id = 'groupby';
  header.appendChild(groupByHost);

  const searchEl = document.getElementById('search') as HTMLInputElement;
  let debounce: number | undefined;

  function refresh() {
    const searchMatches = search.query(searchEl.value);
    const filtered = applyFilters(events, filters).filter((e) => searchMatches.has(e.id));
    tl.refresh(filtered);
  }

  buildFilterBar(filtersHost, filters, refresh);
  buildGroupByToggle(groupByHost, 'rebbe', (g) => tl.setGroupBy(g));

  searchEl.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = window.setTimeout(refresh, 200);
  });

  document.getElementById('zoom-in')!.addEventListener('click', () => tl.zoomIn());
  document.getElementById('zoom-out')!.addEventListener('click', () => tl.zoomOut());
  document.getElementById('zoom-fit')!.addEventListener('click', () => tl.fit());

  const yearJump = document.getElementById('year-jump') as HTMLInputElement;
  function applyYearJump() {
    const y = parseInt(yearJump.value, 10);
    if (Number.isFinite(y) && y >= 1500 && y <= 2100) tl.goToYear(y);
  }
  yearJump.addEventListener('change', applyYearJump);
  yearJump.addEventListener('keydown', (e) => { if (e.key === 'Enter') applyYearJump(); });
})();

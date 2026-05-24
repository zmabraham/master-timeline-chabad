import { loadEvents } from './data';
import { buildTimeline } from './timeline';
import { buildPanel } from './panel';
import './styles.css';
import 'vis-timeline/styles/vis-timeline-graph2d.min.css';

const app = document.getElementById('app')!;
app.innerHTML = `
  <header><h1>Master Timeline Chabad</h1></header>
  <main id="timeline"></main>
  <aside id="panel"></aside>
`;

(async () => {
  const events = await loadEvents();
  const panel = buildPanel(document.getElementById('panel')!);
  buildTimeline(
    document.getElementById('timeline')!,
    events,
    (id) => {
      const ev = events.find((e) => e.id === id);
      if (ev) panel.open(ev, events);
    },
  );
})();

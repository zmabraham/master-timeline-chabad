import { loadEvents } from './data';
import { buildTimeline } from './timeline';
import './styles.css';
import 'vis-timeline/styles/vis-timeline-graph2d.min.css';

const app = document.getElementById('app')!;
app.innerHTML = `
  <header><h1>Master Timeline Chabad</h1></header>
  <main id="timeline"></main>
`;

(async () => {
  const events = await loadEvents();
  buildTimeline(
    document.getElementById('timeline')!,
    events,
    (id) => console.log('selected', id),
  );
  console.log(`rendered ${events.length} events into timeline`);
})();

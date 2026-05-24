import { loadEvents } from './data';

loadEvents().then(events => {
  console.log(`loaded ${events.length} events`);
  document.body.textContent = `loaded ${events.length} events`;
});

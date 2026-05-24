import type { GroupBy } from './timeline';

export function buildGroupByToggle(host: HTMLElement, current: GroupBy, onChange: (g: GroupBy) => void) {
  const options: { id: GroupBy; label: string }[] = [
    { id: 'rebbe', label: 'By Rebbe' },
    { id: 'category', label: 'By Category' },
    { id: 'era', label: 'By Era' },
    { id: 'flat', label: 'Flat' },
  ];
  host.innerHTML = `<label class="groupby-label">Group by:</label>` + options
    .map((o) => `<button class="chip${o.id === current ? ' active' : ''}" data-g="${o.id}">${o.label}</button>`)
    .join('');
  host.querySelectorAll<HTMLButtonElement>('[data-g]').forEach((btn) => {
    btn.addEventListener('click', () => {
      host.querySelectorAll('.chip').forEach((c) => c.classList.remove('active'));
      btn.classList.add('active');
      onChange(btn.dataset.g as GroupBy);
    });
  });
}

'use strict';
const urlap = document.getElementById('belepes');
const hiba = document.getElementById('belepes-hiba');
urlap.addEventListener('submit', async (e) => {
  e.preventDefault();
  const elso = urlap.dataset.elso === '1';
  const jelszo = urlap.jelszo.value;
  if (elso && jelszo !== urlap.jelszo2.value) {
    hiba.textContent = 'A két jelszó nem egyezik.';
    return;
  }
  hiba.textContent = '';
  const v = await fetch(elso ? '/api/v1/elso-jelszo' : '/api/v1/belepes', {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Kozgaz-FM': '1' }, body: JSON.stringify({ jelszo }),
  }).catch(() => null);
  if (!v) { hiba.textContent = 'A szerver nem érhető el.'; return; }
  const j = await v.json().catch(() => ({}));
  if (!v.ok) { hiba.textContent = j.error?.message || 'Hiba történt.'; urlap.jelszo.select(); return; }
  location.href = '/';
});

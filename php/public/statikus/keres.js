'use strict';
const $ = (s) => document.querySelector(s);
const ALLAPOT_OSZTALY = { kereses: '', varakozik: 'sarga', elfogadva: 'kek', szol: 'zold', elutasitva: 'piros', levett: '' };
let utolso = null;
async function keres(metodus, torzs) {
  const v = await fetch('/api/v1/zenekeres', { method: metodus, headers: { 'Content-Type': 'application/json', 'X-Kozgaz-FM': '1' }, body: torzs ? JSON.stringify(torzs) : undefined });
  const j = await v.json().catch(() => ({}));
  if (!v.ok) throw new Error(j.error?.message || 'Hiba történt, próbáld újra.');
  return j.data;
}
function rajzol(a) {
  utolso = a;
  $('#cim').textContent = a.cim || 'Közgáz FM';
  document.title = `Zenekérés – ${a.cim || 'Közgáz FM'}`;
  $('#urlap-kartya').hidden = !a.aktiv;
  $('#kikapcsolva').hidden = a.aktiv;
  $('#most-szol').hidden = !a.most;
  $('#most').textContent = a.most ? `♪ ${a.most}` : '';
  const info = a.tiltva ? 'Erről a telefonról most nem lehet számot kérni.' : `Ma még ${a.maradek} számot kérhetsz (napi ${a.napi}). Legfeljebb ${a.max_perc} perces lehet – hosszabbnál a rádiós változat szól, ha van.`;
  $('#info').textContent = info;
  $('#kuld').disabled = a.tiltva || a.maradek <= 0;
  const lista = $('#keresek');
  lista.replaceChildren();
  if (!a.keresek.length) {
    const u = document.createElement('div');
    u.className = 'lista-ures';
    u.textContent = 'Ma még nem kértél számot.';
    lista.append(u);
  }
  for (const k of a.keresek) {
    const sor = document.createElement('div');
    sor.className = 'lista-elem';
    const szoveg = document.createElement('div');
    szoveg.className = 'noveszt';
    const c = document.createElement('div');
    c.className = 'cimke-sor';
    c.textContent = k.cim || k.szoveg;
    const al = document.createElement('div');
    al.className = 'al-sor';
    al.textContent = `${k.ido}${k.ok ? ' · ' + k.ok : ''}`;
    szoveg.append(c, al);
    const jel = document.createElement('span');
    jel.className = `jel ${ALLAPOT_OSZTALY[k.allapot] || ''}`;
    jel.textContent = k.allapot_nev;
    sor.append(szoveg, jel);
    lista.append(sor);
  }
}
async function frissit() {
  try { rajzol(await keres('GET')); } catch (_) { }
}
$('#urlap').addEventListener('submit', async (e) => {
  e.preventDefault();
  $('#hiba').textContent = '';
  $('#kuld').disabled = true;
  try {
    rajzol(await keres('POST', { szoveg: $('#szoveg').value, nev: $('#nev').value }));
    $('#szoveg').value = '';
    localStorage.setItem('kfm-nev', $('#nev').value);
  } catch (h) {
    $('#hiba').textContent = h.message;
  } finally {
    if (utolso) $('#kuld').disabled = utolso.tiltva || utolso.maradek <= 0;
  }
});
const param = new URLSearchParams(location.search).get('szam');
if (param) $('#szoveg').value = param;
$('#nev').value = localStorage.getItem('kfm-nev') || '';
frissit();
setInterval(frissit, 5000);

'use strict';
const $ = (s) => document.querySelector(s);
const HONAPOK = ['január', 'február', 'március', 'április', 'május', 'június', 'július', 'augusztus', 'szeptember', 'október', 'november', 'december'];
const NAPOK = ['vasárnap', 'hétfő', 'kedd', 'szerda', 'csütörtök', 'péntek', 'szombat'];
const k = (n) => String(n).padStart(2, '0');
let a = null;
let kapott = 0;
let elteres = 0;
let qr = '';
function idotartam(mp) {
  const o = Math.floor(mp / 3600), p = Math.floor((mp % 3600) / 60), s = mp % 60;
  return o ? `${o}:${k(p)}:${k(s)}` : `${p}:${k(s)}`;
}
function rajzol() {
  const m = new Date(Date.now() + elteres);
  $('#ora').textContent = `${k(m.getHours())}:${k(m.getMinutes())}`;
  $('#datum').textContent = `${HONAPOK[m.getMonth()]} ${m.getDate()}., ${NAPOK[m.getDay()]}`;
  if (!a) return;
  $('#cim').textContent = a.cim;
  $('#szakasz').textContent = a.szakasz;
  const hatra = a.hatra_mp !== null ? Math.max(0, a.hatra_mp - Math.floor((Date.now() - kapott) / 1000)) : null;
  $('#hatra').textContent = hatra !== null ? `${a.hatra_mire === 'kicsengetésig' ? 'Kicsengetésig' : 'Becsengetésig'} ${idotartam(hatra)}` : '';
  $('#halado').style.width = a.hossz_mp && hatra !== null ? `${Math.min(100, 100 * (1 - hatra / a.hossz_mp))}%` : '0';
  $('#kovetkezo').textContent = a.kovetkezo ? `Következő: ${a.kovetkezo.nap_szoveg} ${a.kovetkezo.ido} – ${a.kovetkezo.leiras}` : '';
  $('#zene').textContent = a.zene.szol && a.zene.cim ? `♪ ${a.zene.cim}` : '';
}
async function frissit() {
  try {
    const v = await fetch('/api/v1/kijelzo');
    const j = await v.json();
    a = j.data;
    kapott = Date.now();
    elteres = new Date(a.ido).getTime() - Date.now();
    if (Math.abs(elteres) < 2000) elteres = 0;
    if (a.keres_cim !== qr) {
      qr = a.keres_cim;
      $('#qr').hidden = !qr;
      if (qr) $('#qr-kep').src = `/api/v1/qr?szoveg=${encodeURIComponent(qr)}`;
    }
    rajzol();
  } catch (_) { }
}
document.addEventListener('dblclick', () => (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen()));
document.addEventListener('keydown', (e) => { if (e.key === 'F11') { e.preventDefault(); document.documentElement.requestFullscreen(); } });
frissit();
setInterval(rajzol, 1000);
setInterval(frissit, 3000);

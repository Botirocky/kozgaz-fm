'use strict';

const $ = (s, r = document) => r.querySelector(s);
const OLDAL = JSON.parse($('#oldal-adat').textContent);
const NAPOK = ['Hétfő', 'Kedd', 'Szerda', 'Csütörtök', 'Péntek', 'Szombat', 'Vasárnap'];
const NAP_ROVID = ['H', 'K', 'Sze', 'Cs', 'P', 'Szo', 'V'];
let ALLAPOT = null;
let B = null;
let idoElteres = 0;
let oldal = null;

const ures = (g) => g === null || g === undefined || g === false;
for (const nev of ['replaceChildren', 'append', 'prepend']) {
  const eredeti = Element.prototype[nev];
  Element.prototype[nev] = function (...gyerekek) { return eredeti.apply(this, gyerekek.filter((g) => !ures(g))); };
}

function el(tag, props = {}, ...gyerekek) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k === 'text') e.textContent = v;
    else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'value') e.value = v;
    else if (k === 'style') e.style.cssText = v;
    else if (k === 'checked') e.checked = !!v;
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const g of gyerekek.flat()) {
    if (g === null || g === undefined || g === false) continue;
    e.append(g instanceof Node ? g : document.createTextNode(String(g)));
  }
  return e;
}

function uzenet(szoveg, szint = 'info') {
  const u = el('div', { class: `uzenet ${szint}`, text: szoveg });
  $('#uzenetek').append(u);
  setTimeout(() => u.remove(), szint === 'hiba' ? 9000 : 4500);
}

async function api(metodus, url, torzs, { csendes = false, pinUtan = true } = {}) {
  const opciok = { method: metodus, headers: { 'X-Kozgaz-FM': '1', Accept: 'application/json' } };
  if (torzs instanceof FormData) opciok.body = torzs;
  else if (torzs !== undefined) {
    opciok.headers['Content-Type'] = 'application/json';
    opciok.body = JSON.stringify(torzs);
  }
  let valasz;
  try {
    valasz = await fetch(url, opciok);
  } catch (e) {
    const h = new Error('A szerver nem érhető el.');
    if (!csendes) uzenet(h.message, 'hiba');
    throw h;
  }
  if (valasz.status === 401 && !url.includes('/feloldas')) {
    location.href = '/belepes';
    throw new Error('Jelentkezz be.');
  }
  if (valasz.status === 423 && pinUtan) {
    await pinKeres();
    return api(metodus, url, torzs, { csendes, pinUtan: false });
  }
  const j = await valasz.json().catch(() => ({}));
  if (!valasz.ok) {
    const h = new Error(j.error?.message || `Hiba (${valasz.status})`);
    h.kod = j.error?.code;
    if (!csendes) uzenet(h.message, 'hiba');
    throw h;
  }
  return j.data;
}

function modal(cim, tartalom, gombok = [], { szeles = false } = {}) {
  return new Promise((kesz) => {
    const hatter = el('div', { class: 'modal-hatter' });
    const bezar = (ertek) => { hatter.remove(); kesz(ertek); };
    const doboz = el('div', { class: `modal${szeles ? ' szeles' : ''}`, role: 'dialog', 'aria-modal': 'true' }, el('h2', { text: cim }), tartalom,
      el('div', { class: 'gombsor' }, gombok.map(([felirat, ertek, osztaly]) =>
        el('button', { class: `gomb ${osztaly || ''}`, text: felirat, onclick: async () => {
          if (typeof ertek === 'function') {
            try { const e = await ertek(); if (e !== false) bezar(e); } catch (_) { }
          } else bezar(ertek);
        } }))));
    hatter.append(doboz);
    hatter.addEventListener('keydown', (e) => { if (e.key === 'Escape') bezar(null); });
    document.body.append(hatter);
    (doboz.querySelector('input, textarea, select') || doboz.querySelector('button'))?.focus();
  });
}

function pinKeres() {
  const mezo = el('input', { type: 'password', inputmode: 'numeric', autocomplete: 'off', maxlength: '8', placeholder: 'PIN' });
  const hiba = el('p', { class: 'hiba-szoveg' });
  const kuld = async () => {
    try {
      await api('POST', '/api/v1/feloldas', { pin: mezo.value }, { csendes: true, pinUtan: false });
      OLDAL.feloldva = true;
      return true;
    } catch (e) {
      hiba.textContent = e.message;
      mezo.select();
      return false;
    }
  };
  mezo.addEventListener('keydown', async (e) => { if (e.key === 'Enter') { e.preventDefault(); doboz.querySelector('.gomb.fo').click(); } });
  const doboz = el('div', {}, el('p', { class: 'halvany', text: 'Ez a beállító oldal PIN-kóddal védett.' }), mezo, hiba);
  return modal('PIN-kód', doboz, [['Mégse', null], ['Feloldás', kuld, 'fo']]).then((e) => {
    if (!e) throw new Error('Mégse');
  });
}

function megerosit(cim, szoveg, igen = 'Igen', osztaly = 'fo') {
  return modal(cim, el('p', { text: szoveg }), [['Mégse', false], [igen, true, osztaly]]);
}

const ido2 = (n) => String(n).padStart(2, '0');
function idotartam(mp) {
  if (mp === null || mp === undefined) return '';
  const o = Math.floor(mp / 3600), p = Math.floor((mp % 3600) / 60), s = mp % 60;
  return o ? `${o}:${ido2(p)}:${ido2(s)}` : `${p}:${ido2(s)}`;
}
const HONAPOK = ['január', 'február', 'március', 'április', 'május', 'június', 'július', 'augusztus', 'szeptember', 'október', 'november', 'december'];
function datumSzoveg(d) {
  return `${d.getFullYear()}. ${HONAPOK[d.getMonth()]} ${d.getDate()}., ${NAPOK[(d.getDay() + 6) % 7].toLowerCase()}`;
}
const most = () => new Date(Date.now() + idoElteres);

let utolsoUzenet = Number(sessionStorage.getItem('kfm-uzenet') || 0);
function fejlecFrissit() {
  const m = most();
  $('#ora').textContent = `${ido2(m.getHours())}:${ido2(m.getMinutes())}:${ido2(m.getSeconds())}`;
  if (!ALLAPOT) return;
  const a = ALLAPOT;
  $('#fej-szakasz').textContent = a.szakasz + (a.csend ? ` · ${a.csend.nev} (${a.csend.ig}-ig)` : '');
  const eltelt = Math.floor((Date.now() - a._kapott) / 1000);
  $('#fej-hatra').textContent = a.hatra_mp !== null ? `${a.hatra_mire.replace('ig', 'ig hátra')}: ${idotartam(Math.max(0, a.hatra_mp - eltelt))}`
    : (a.kovetkezo ? `Következő: ${a.kovetkezo.nap_szoveg} ${a.kovetkezo.ido}` : '');
  const elo = $('#elo');
  elo.classList.toggle('riaszt', a.riasztas);
  const szoveg = a.riasztas ? 'RIASZTÁS SZÓL' : a.bemondas_szol ? 'Bemondás szól' : a.csengo_szol ? 'Csengő szól' : a.zene.szol ? `♪ ${a.zene.cim || 'Szünetzene'}` : '';
  elo.hidden = !szoveg;
  elo.textContent = szoveg;
}

function allapotsorFrissit(a) {
  const auto = $('#as-automatika');
  auto.replaceChildren();
  if (!a.demon.el) auto.append(el('span', { class: 'pont hiba' }), 'A lejátszó démon nem fut');
  else if (a.riasztas) auto.append(el('span', { class: 'pont hiba' }), 'Riasztás');
  else if (a.rendszer?.tartalek?.passziv) auto.append(el('span', { class: 'pont kek' }), 'Tartalék gép: készenlétben');
  else auto.append(el('span', { class: 'pont' }), 'Automatika fut');
  if (a.rendszer) {
    $('#as-kimenet').textContent = `Hangkimenet: ${a.rendszer.kimenet_nev || 'NEM ÉRHETŐ EL'}`;
    $('#as-tartalek').textContent = a.rendszer.tartalek?.szoveg || '';
  }
}

async function allapotFrissit() {
  try {
    const a = await api('GET', '/api/v1/allapot', undefined, { csendes: true });
    a._kapott = Date.now();
    idoElteres = new Date(a.ido).getTime() - Date.now();
    if (Math.abs(idoElteres) < 2000) idoElteres = 0;
    ALLAPOT = a;
    for (const u of a.demon.uzenetek || []) {
      if (u.id > utolsoUzenet && Date.now() / 1000 - u.ido < 30) uzenet(u.szoveg, u.szint === 'hiba' ? 'hiba' : 'info');
      utolsoUzenet = Math.max(utolsoUzenet, u.id);
    }
    sessionStorage.setItem('kfm-uzenet', String(utolsoUzenet));
    allapotsorFrissit(a);
    fejlecFrissit();
    if (oldal?.frissit) oldal.frissit(a);
  } catch (_) { }
}

async function muvelet(metodus, url, torzs, siker) {
  const a = await api(metodus, url, torzs);
  if (a && a.szakasz) {
    a._kapott = Date.now();
    ALLAPOT = a;
    if (oldal?.frissit) oldal.frissit(a);
    fejlecFrissit();
  }
  if (siker) uzenet(siker, 'siker');
  return a;
}

function kartya(cim, ...tartalom) {
  return el('section', { class: 'kartya' }, cim ? el('h2', { text: cim }) : null, ...tartalom);
}

function mezoSugo(szoveg) {
  return szoveg ? el('div', { class: 'mezo-sugo', text: szoveg }) : null;
}

function kapcsolo(obj, kulcs, felirat, sugo, valt) {
  const doboz = el('input', { type: 'checkbox', checked: obj[kulcs] });
  doboz.addEventListener('change', () => { obj[kulcs] = doboz.checked; valt?.(); });
  return el('div', { class: 'mezo' }, el('label', { class: 'sor' }, doboz, felirat), mezoSugo(sugo));
}

function szam(obj, kulcs, felirat, min, max, lepes = 1, utotag = '', valt, sugo) {
  const m = el('input', { type: 'number', min, max, step: lepes, value: obj[kulcs] });
  m.addEventListener('input', () => {
    const v = lepes < 1 ? parseFloat(m.value) : parseInt(m.value, 10);
    if (!Number.isNaN(v)) { obj[kulcs] = v; valt?.(); }
  });
  return el('div', { class: 'mezo' }, el('label', { text: felirat + (utotag ? ` (${utotag})` : '') }), m, mezoSugo(sugo));
}

function szoveg(obj, kulcs, felirat, { tipus = 'text', hely = '', sugo, sorok = 0, valt, datalist } = {}) {
  const m = sorok ? el('textarea', { rows: sorok, placeholder: hely }) : el('input', { type: tipus, placeholder: hely, autocomplete: tipus === 'password' ? 'new-password' : 'off', list: datalist });
  m.value = obj[kulcs] ?? '';
  m.addEventListener('input', () => { obj[kulcs] = m.value; valt?.(); });
  return el('div', { class: 'mezo' }, felirat ? el('label', { text: felirat }) : null, m, mezoSugo(sugo));
}

function idoMezo(obj, kulcs, felirat, valt, tipus = 'time') {
  const m = el('input', { type: tipus, value: obj[kulcs] || '' });
  m.addEventListener('input', () => { obj[kulcs] = m.value; valt?.(); });
  return el('div', { class: 'mezo' }, felirat ? el('label', { text: felirat }) : null, m);
}

function valaszto(obj, kulcs, felirat, opciok, valt, sugo) {
  const s = el('select', {}, opciok.map(([e, n]) => el('option', { value: e, text: n })));
  s.value = String(obj[kulcs] ?? '');
  s.addEventListener('change', () => {
    const eredeti = opciok.find(([e]) => String(e) === s.value);
    obj[kulcs] = eredeti ? eredeti[0] : s.value;
    valt?.();
  });
  return el('div', { class: 'mezo' }, felirat ? el('label', { text: felirat }) : null, s, mezoSugo(sugo));
}

function hangOpciok() {
  return (B?.hangok || []).map((h) => [h.ertek, h.beepitett ? h.nev : `${h.nev} (saját)`]);
}

function hangValaszto(obj, kulcs, felirat, valt) {
  const v = valaszto(obj, kulcs, felirat, hangOpciok(), valt);
  const s = v.querySelector('select');
  const proba = el('button', { class: 'gomb ikonos', title: 'Meghallgatás', text: '▶', onclick: () => api('POST', '/api/v1/hang-proba', { ertek: s.value }) });
  v.replaceChild(el('div', { class: 'gombsor' }, s, proba), s);
  s.style.flex = '1';
  return v;
}

function napValaszto(obj, kulcs, felirat, valt) {
  const doboz = el('div', { class: 'gombsor' });
  NAP_ROVID.forEach((nev, i) => {
    const c = el('input', { type: 'checkbox', checked: (obj[kulcs] || []).includes(i) });
    c.addEventListener('change', () => {
      const lista = new Set(obj[kulcs] || []);
      c.checked ? lista.add(i) : lista.delete(i);
      obj[kulcs] = [...lista].sort((a, b) => a - b);
      valt?.();
    });
    doboz.append(el('label', { class: 'sor' }, c, nev));
  });
  return el('div', { class: 'mezo' }, felirat ? el('label', { text: felirat }) : null, doboz);
}

function beallitasKartya(cim, kulcsok, epit, { leiras, utana } = {}) {
  const k = el('section', { class: 'kartya' });
  const rajzol = () => {
    const piszkozat = structuredClone(B.beallitasok);
    const allapot = el('span', { class: 'allapot', text: 'Mentve' });
    const mentes = el('button', { class: 'gomb fo', text: 'Mentés', disabled: true });
    const sav = el('div', { class: 'mentes-sav' }, mentes, allapot);
    const valt = () => {
      const piszkos = kulcsok.some((kulcs) => JSON.stringify(piszkozat[kulcs]) !== JSON.stringify(B.beallitasok[kulcs]));
      mentes.disabled = !piszkos;
      sav.classList.toggle('piszkos', piszkos);
      allapot.textContent = piszkos ? 'Nincs mentve' : 'Mentve';
    };
    mentes.addEventListener('click', async () => {
      const valtozasok = {};
      for (const kulcs of kulcsok) {
        if (JSON.stringify(piszkozat[kulcs]) !== JSON.stringify(B.beallitasok[kulcs])) valtozasok[kulcs] = piszkozat[kulcs];
      }
      mentes.disabled = true;
      try {
        B = await api('PATCH', '/api/v1/beallitasok', { valtozasok });
        uzenet('Mentve.', 'siker');
        rajzol();
        utana?.();
      } catch (_) {
        mentes.disabled = false;
      }
    });
    k.replaceChildren(el('h2', { text: cim }), leiras ? el('p', { class: 'halvany', text: leiras }) : null, epit(piszkozat, valt, rajzol), sav);
  };
  rajzol();
  return k;
}

function listaSzerkeszto(lista, { felirat, uj, mezok, valt, ujFelirat = 'Hozzáadás', ures = 'Még nincs egy sem.', nyitva = false, rendezheto = true }) {
  const doboz = el('div');
  const rajzol = (nyitottIndex = -1) => {
    doboz.replaceChildren();
    if (!lista.length) doboz.append(el('div', { class: 'lista-ures', text: ures }));
    lista.forEach((elem, i) => {
      const test = el('div', { class: 'szerkeszto-test', hidden: !(nyitva || i === nyitottIndex) });
      const fejSzoveg = el('span', { class: 'cimke-sor', text: felirat(elem, i) });
      const frissit = () => { fejSzoveg.textContent = felirat(elem, i); valt?.(); };
      test.append(mezok(elem, frissit, i));
      const fej = el('div', { class: 'szerkeszto-fej' },
        el('button', { class: 'gomb ikonos kicsi', text: test.hidden ? '▸' : '▾', title: 'Megnyitás', onclick: (e) => { test.hidden = !test.hidden; e.currentTarget.textContent = test.hidden ? '▸' : '▾'; } }),
        fejSzoveg,
        rendezheto ? el('button', { class: 'gomb ikonos kicsi', text: '↑', title: 'Feljebb', disabled: i === 0, onclick: () => { [lista[i - 1], lista[i]] = [lista[i], lista[i - 1]]; valt?.(); rajzol(); } }) : null,
        rendezheto ? el('button', { class: 'gomb ikonos kicsi', text: '↓', title: 'Lejjebb', disabled: i === lista.length - 1, onclick: () => { [lista[i + 1], lista[i]] = [lista[i], lista[i + 1]]; valt?.(); rajzol(); } }) : null,
        el('button', { class: 'gomb ikonos kicsi veszely', text: '✕', title: 'Törlés', onclick: () => { lista.splice(i, 1); valt?.(); rajzol(); } }));
      doboz.append(el('div', { class: `szerkeszto-elem${elem.aktiv === false ? ' kikapcsolt' : ''}` }, fej, test));
    });
    doboz.append(el('button', { class: 'gomb', text: `+ ${ujFelirat}`, onclick: () => { lista.push(uj()); valt?.(); rajzol(lista.length - 1); } }));
  };
  rajzol();
  return doboz;
}

async function beallitasBetolt() {
  B = await api('GET', '/api/v1/beallitasok');
  return B;
}

function feltoltes(url, fajl, extra = {}) {
  const fd = new FormData();
  fd.append('fajl', fajl);
  for (const [k, v] of Object.entries(extra)) fd.append(k, v);
  return api('POST', url, fd);
}

const Pult = {
  async init(main) {
    this.main = main;
    const a = ALLAPOT;
    this.most = el('div');
    this.idovonal = el('div', { class: 'idovonal' });
    this.menetrend = el('div', { class: 'lista' });
    this.zeneDoboz = el('div');
    this.keresek = el('div');
    this.maDoboz = el('div');
    this.csendDoboz = el('div');
    this.moKartya = el('section', { class: 'kartya' }, this.most, el('div', { class: 'halado' }, el('div', { id: 'halado' })), this.idovonal);
    const masHang = el('select', {}, (a.hangok || []).map((h) => el('option', { value: h.azonosito, text: h.nev })));
    const szoveg = el('textarea', { rows: 3, placeholder: 'Bemondás szövege…', maxlength: 500 });
    const gong = el('input', { type: 'checkbox', checked: true });
    const sablon = el('select', {}, el('option', { value: '', text: 'Sablonból…' }), (a.sablonok || []).map((s) => el('option', { value: s, text: s.slice(0, 80) })));
    sablon.addEventListener('change', () => { if (sablon.value) szoveg.value = sablon.value; sablon.value = ''; });
    const gyors = kartya('Gyors műveletek',
      el('div', { class: 'gombsor nyujt' },
        el('button', { class: 'gomb adas nagy', text: '🔔 Csengetés most', onclick: () => muvelet('POST', '/api/v1/csengetes', { hang: 'becsengo' }, 'Csengetés elindítva') })),
      el('div', { class: 'gombsor', style: 'margin-top:8px' }, masHang,
        el('button', { class: 'gomb', text: 'Más hanggal', onclick: () => muvelet('POST', '/api/v1/csengetes', { hang: masHang.value }, 'Csengetés elindítva') })),
      el('h2', { text: 'Bemondás', style: 'margin-top:16px' }), sablon, szoveg,
      el('div', { class: 'gombsor', style: 'margin-top:6px' }, el('label', { class: 'sor' }, gong, 'Gonggal'),
        el('button', { class: 'gomb fo', text: 'Felolvasás', onclick: async () => {
          if (!szoveg.value.trim()) return uzenet('Írd be a bemondás szövegét.', 'hiba');
          await muvelet('POST', '/api/v1/bemondas', { szoveg: szoveg.value, gong: gong.checked }, 'Bemondás elindítva');
        } }),
        el('button', { class: 'gomb', text: 'Leállítás', onclick: () => muvelet('DELETE', '/api/v1/bemondas') })),
      this.maDoboz, this.csendDoboz);
    main.replaceChildren(
      this.moKartya,
      el('div', { class: 'racs' }, gyors, kartya('Szünetzene', this.zeneDoboz)),
      el('div', { class: 'racs', style: 'margin-top:16px' }, kartya('Mai menetrend', this.menetrend), kartya('Zenekérések', this.keresek)));
    this.frissit(a, true);
  },
  frissit(a, elso = false) {
    const m = most();
    this.moKartya.className = `kartya ${a.szakasz_tipus === 'óra' ? 'szakasz-ora' : a.szakasz_tipus === 'szünet' ? 'szakasz-szunet' : ''}`;
    const eltelt = Math.floor((Date.now() - a._kapott) / 1000);
    const hatra = a.hatra_mp !== null ? Math.max(0, a.hatra_mp - eltelt) : null;
    this.most.replaceChildren(el('div', { class: 'halvany', text: datumSzoveg(m) }),
      el('div', { class: 'most' }, el('div', {}, el('div', { class: 'szakasz-nagy', text: a.szakasz }),
        a.csend ? el('div', { class: 'jel kek', text: `${a.csend.nev} – ${a.csend.ig}-ig` }) : null),
        hatra !== null ? el('div', { class: 'visszaszamlalo', text: `${a.hatra_mire}: ${idotartam(hatra)}` }) : null,
        el('div', { class: 'halvany', style: 'margin-left:auto', text: a.kovetkezo ? `Következő: ${a.kovetkezo.nap_szoveg} ${a.kovetkezo.ido}, ${a.kovetkezo.leiras}` : 'A következő két hétben nincs csengetés' })));
    const halado = $('#halado');
    if (halado) halado.style.width = a.hossz_mp && hatra !== null ? `${Math.min(100, 100 * (1 - hatra / a.hossz_mp))}%` : '0%';
    this.idovonalRajzol(a, m);
    this.menetrend.replaceChildren(...(a.menetrend.length ? a.menetrend.map((e, i) => {
      const kovetkezo = !e.mult && (i === 0 || a.menetrend[i - 1].mult);
      return el('div', { class: `lista-elem${e.mult ? ' mult' : ''}${kovetkezo ? ' kovetkezo-sor' : ''}` }, el('span', { class: 'ido-oszlop', text: e.ido }),
        el('span', { class: 'noveszt', text: e.leiras }), e.tipus !== 'csengo' ? el('span', { class: 'jel', text: { zene_indul: 'zene', bemondas: 'bemondás', riado: 'riadó', csend: 'csend', rendkivuli: 'rendkívüli' }[e.tipus] || e.tipus }) : null);
    }) : [el('div', { class: 'lista-ures', text: 'Ma nincs csengetés.' })]));
    if (elso || !this.maDoboz.contains(document.activeElement)) this.maRajzol(a);
    if (elso || !this.csendDoboz.contains(document.activeElement)) this.csendRajzol(a);
    if (elso || !this.zeneDoboz.contains(document.activeElement)) this.zeneRajzol(a);
    this.keresekRajzol(a);
  },
  idovonalRajzol(a, m) {
    const orak = a.idovonal || [];
    if (!orak.length) { this.idovonal.replaceChildren(); this.idovonal.hidden = true; return; }
    this.idovonal.hidden = false;
    const perc = (s) => { const [o, p] = s.split(':').map(Number); return o * 60 + p; };
    const tol = perc(orak[0][0]) - 10, ig = perc(orak[orak.length - 1][1]) + 10;
    const hely = (p) => `${Math.max(0, Math.min(100, (100 * (p - tol)) / (ig - tol)))}%`;
    const mostPerc = m.getHours() * 60 + m.getMinutes() + m.getSeconds() / 60;
    const elemek = orak.map(([k, v], i) => el('div', { class: `ora-blokk${mostPerc >= perc(k) && mostPerc < perc(v) ? ' aktiv' : ''}`,
      style: `left:${hely(perc(k))};width:calc(${hely(perc(v))} - ${hely(perc(k))})`, text: `${i + 1}.` }));
    const skala = orak.map(([k]) => el('div', { class: 'skala', style: `left:${hely(perc(k))}`, text: k }));
    this.idovonal.replaceChildren(...elemek, ...skala, mostPerc >= tol && mostPerc <= ig ? el('div', { class: 'most-jel', style: `left:${hely(mostPerc)}` }) : '');
  },
  maRajzol(a) {
    const cs = el('input', { type: 'checkbox', checked: a.ma.csengetes });
    cs.addEventListener('change', () => muvelet('PATCH', '/api/v1/ma', { csengetes: cs.checked }));
    const z = el('input', { type: 'checkbox', checked: a.ma.zene });
    z.addEventListener('change', () => muvelet('PATCH', '/api/v1/ma', { zene: z.checked }));
    const rend = el('select', {}, el('option', { value: '', text: 'Szokásos (heti beosztás)' }), a.ma.rendek.map((r) => el('option', { value: r, text: r })));
    rend.value = a.ma.rend;
    rend.addEventListener('change', () => muvelet('PATCH', '/api/v1/ma', { rend: rend.value }));
    this.maDoboz.replaceChildren(el('h2', { text: 'Ma', style: 'margin-top:16px' }),
      el('label', { class: 'sor' }, cs, 'Ma legyen csengetés'), el('div', { class: 'mezo-sugo', text: 'Kikapcsolva ma egyáltalán nem csenget (pl. kirándulás, rendezvény).' }),
      el('label', { class: 'sor' }, z, 'Ma legyen szünetzene'),
      el('label', { text: 'Mai csengetési rend (éjfélkor visszaáll)' }), rend);
  },
  csendRajzol(a) {
    if (a.csend) {
      this.csendDoboz.replaceChildren(el('h2', { text: 'Csendes időszak', style: 'margin-top:16px' }),
        el('p', { text: `${a.csend.nev}, ${a.csend.ig}-ig${a.csend.halk ? ' (halk csengő)' : ' (néma csengő)'}` }),
        el('button', { class: 'gomb', text: 'Csendes időszak vége', onclick: () => muvelet('DELETE', '/api/v1/csend', undefined, 'A csendes időszak véget ért') }));
      return;
    }
    const perc = el('select', {}, [15, 30, 45, 60, 90, 120, 180, 240].map((p) => el('option', { value: p, text: `${p} perc` })));
    perc.value = '45';
    const halk = el('select', {}, el('option', { value: '0', text: 'néma csengő' }), [10, 20, 30, 40].map((h) => el('option', { value: h, text: `halk csengő (${h}%)` })));
    this.csendDoboz.replaceChildren(el('h2', { text: 'Csendes időszak most', style: 'margin-top:16px' }),
      el('p', { class: 'halvany kicsi-szoveg', text: 'Nincs zene és ütemezett bemondás (pl. érettségi, mérés).' }),
      el('div', { class: 'gombsor' }, perc, halk, el('button', { class: 'gomb', text: 'Indítás', onclick: () => muvelet('POST', '/api/v1/csend', { perc: Number(perc.value), hangero: Number(halk.value) }, 'Csendes időszak elindítva') })));
  },
  zeneRajzol(a) {
    const z = a.zene;
    const forras = el('select', {}, z.forrasok.length ? z.forrasok.map((f) => el('option', { value: f.index, text: `${f.nev} (${f.tipus})` })) : el('option', { value: '', text: 'Nincs zeneforrás – add hozzá a Zene oldalon' }));
    if (z.forras !== null) forras.value = String(z.forras);
    forras.addEventListener('change', () => muvelet('PATCH', '/api/v1/zene', { forras: Number(forras.value) }));
    const hangero = el('input', { type: 'range', min: 0, max: 100, value: z.hangero });
    const hangeroSzoveg = el('span', { text: `${z.hangero}%` });
    hangero.addEventListener('input', () => { hangeroSzoveg.textContent = `${hangero.value}%`; });
    hangero.addEventListener('change', () => muvelet('PATCH', '/api/v1/zene', { hangero: Number(hangero.value) }));
    const sor = z.szol && z.sor.length ? el('div', { class: 'lista', style: 'margin-top:10px' }, el('div', { class: 'lista-elem halvany kicsi-szoveg', text: 'Következik (kattints az ugráshoz):' }),
      z.sor.map((s) => el('div', { class: 'lista-elem' }, s.kert ? el('span', { class: 'jel kek', text: 'Kért' }) : null, el('span', { class: 'noveszt', text: s.cim }),
        el('button', { class: 'gomb kicsi', text: 'Ugrás', onclick: () => muvelet('POST', '/api/v1/zene/ugras', { index: s.index, cim: s.cim }) })))) : null;
    this.zeneDoboz.replaceChildren(forras,
      z.blokk ? el('div', { class: 'jel sarga', style: 'margin-top:6px', text: `Műsorblokk: ${z.blokk}` }) : null,
      el('div', { class: 'zene-cim', style: 'margin-top:10px', text: z.szol ? `♪ ${z.cim || '…'}` : 'Nem szól zene' }),
      el('div', { class: 'vezerlo-gombok' },
        el('button', { class: 'gomb ikonos nagy', text: '⏮', title: 'Előző', onclick: () => muvelet('POST', '/api/v1/zene/elozo') }),
        el('button', { class: 'gomb fo nagy', text: z.szol ? '⏸ Szünet' : '▶ Lejátszás', onclick: () => muvelet('POST', z.szol ? '/api/v1/zene/leallitas' : '/api/v1/zene/inditas') }),
        el('button', { class: 'gomb ikonos nagy', text: '⏭', title: 'Következő', onclick: () => muvelet('POST', '/api/v1/zene/kovetkezo') }),
        el('button', { class: 'gomb ikonos nagy', text: '🔀', title: 'Keverés most: a hátralévő alap számok új sorrendben (a kért zenék maradnak elöl)', disabled: !z.szol || z.sor.length < 2,
          onclick: () => muvelet('POST', '/api/v1/zene/keveres', undefined, 'Lejátszási sor újrakeverve') })),
      helySzoveg(z) ? el('div', { class: 'halvany kicsi-szoveg', text: helySzoveg(z) }) : null,
      el('label', { class: 'sor' }, el('input', { type: 'checkbox', checked: z.keveres, onchange: (e) => muvelet('PATCH', '/api/v1/zene', { keveres: e.target.checked }) }), 'Véletlen sorrend (keverés)'),
      el('div', { class: 'gombsor' }, '🔊', hangero, hangeroSzoveg),
      z.szol ? el('button', { class: 'gomb kicsi veszely', style: 'margin-top:8px', text: 'A most szóló szám letiltása', onclick: async () => {
        if (await megerosit('Szám letiltása', `Letiltod ezt a számot? „${z.cim}”`, 'Letiltás', 'veszely')) muvelet('POST', '/api/v1/zene/tiltas', undefined, 'A szám letiltva');
      } }) : null, sor);
  },
  keresekRajzol(a) {
    const zk = a.zenekeres;
    if (!zk) return;
    if (!zk.aktiv) { this.keresek.replaceChildren(el('p', { class: 'halvany', text: 'A zenekérés ki van kapcsolva (Zene oldal).' })); return; }
    const fuggo = zk.keresek.filter((k) => k.allapot === 'varakozik' || k.allapot === 'kereses');
    this.keresek.replaceChildren(fuggo.length ? el('div', { class: 'lista' }, fuggo.map((k) => el('div', { class: 'lista-elem' },
      el('div', { class: 'noveszt' }, el('div', { class: 'cimke-sor', text: k.cim || k.szoveg }), el('div', { class: 'al-sor', text: `${k.ido} · ${k.nev || 'névtelen'} · ${k.allapot_nev}${k.megjegyzes ? ' · ' + k.megjegyzes : ''}` })),
      k.link ? el('a', { class: 'gomb kicsi', href: k.link, target: '_blank', rel: 'noopener', text: 'YouTube' }) : null,
      k.allapot === 'varakozik' ? el('button', { class: 'gomb kicsi fo', text: 'Elfogad', onclick: () => muvelet('POST', '/api/v1/zenekeres/dontes', { azon: k.azon, elfogad: true }) }) : null,
      el('button', { class: 'gomb kicsi', text: 'Elutasít', onclick: () => muvelet('POST', '/api/v1/zenekeres/dontes', { azon: k.azon, elfogad: false }) })))) :
      el('p', { class: 'halvany', text: zk.auto ? 'Nincs jóváhagyásra váró kérés (az ellenőrzött kérések maguktól a sorba kerülnek).' : 'Nincs jóváhagyásra váró kérés.' }),
      el('a', { href: '/zene#moderalas', text: 'Mai kérések és moderálás →' }));
  },
};

const Riasztas = {
  init(main) {
    this.gomb = el('button', { class: 'gomb veszely orias', onclick: () => this.kattint() });
    this.allapot = el('p');
    this.kartya = kartya('Riasztás', el('p', { class: 'halvany', text: 'Folyamatos riasztó hang minden hangszóróban, teljes hangerővel, amíg valaki le nem állítja. A szünetzene azonnal elhallgat, és a riasztás alatt nincs csengetés és bemondás.' }), this.allapot, this.gomb);
    main.replaceChildren(this.kartya, kartya('Tudnivalók',
      el('p', { text: 'Előre beállított tűzriadó-gyakorlat: Naptár → Rendkívüli események, típusa „Tűzriadó-gyakorlat”. A megadott időpontban magától indul, és a beállított idő után leáll.' }),
      el('p', { text: 'A riasztó hangja a Csengetési rend oldalon cserélhető. Ez az oldal PIN-kód nélkül is elérhető, és telefonról is használható.' })));
    this.frissit(ALLAPOT);
  },
  async kattint() {
    if (ALLAPOT.riasztas) return muvelet('DELETE', '/api/v1/riasztas', undefined, 'Riasztás leállítva');
    if (await megerosit('Riasztás', 'Biztosan elindítod a riasztó hangot? A zene leáll, a riasztás a leállításig szól.', 'Riasztás indítása', 'veszely')) {
      muvelet('POST', '/api/v1/riasztas', undefined, 'Riasztás elindítva');
    }
  },
  frissit(a) {
    this.gomb.textContent = a.riasztas ? '■ Riasztás leállítása' : '⚠ Riasztás indítása';
    this.gomb.classList.toggle('aktiv', a.riasztas);
    this.kartya.classList.toggle('riaszt-aktiv', a.riasztas);
    this.allapot.textContent = a.riasztas ? 'A riasztás most szól.' : 'Most nincs riasztás.';
    this.allapot.className = a.riasztas ? 'hiba-szoveg' : 'halvany';
  },
};

function rendSzerkeszto(rendek, valt) {
  return listaSzerkeszto(rendek, {
    felirat: (r) => `${r.nev || 'Névtelen rend'} – ${r.orak.length} óra${r.orak.length ? `, ${r.orak[0].kezdet}–${r.orak[r.orak.length - 1].vege}` : ''}`,
    uj: () => ({ nev: 'Új rend', orak: [{ kezdet: '08:00', vege: '08:45' }] }),
    ujFelirat: 'Új csengetési rend',
    valt,
    mezok: (r, frissit) => {
      const tabla = el('tbody');
      const sorok = () => {
        tabla.replaceChildren(...r.orak.map((o, i) => {
          const k = el('input', { type: 'time', value: o.kezdet });
          const v = el('input', { type: 'time', value: o.vege });
          k.addEventListener('input', () => { o.kezdet = k.value; frissit(); });
          v.addEventListener('input', () => { o.vege = v.value; frissit(); });
          return el('tr', {}, el('td', { text: `${i + 1}.` }), el('td', {}, k), el('td', {}, v),
            el('td', {}, el('button', { class: 'gomb ikonos kicsi veszely', text: '✕', onclick: () => { r.orak.splice(i, 1); sorok(); frissit(); } })));
        }));
      };
      sorok();
      const ujOra = () => {
        const utolso = r.orak[r.orak.length - 1];
        const plusz = (s, p) => { const [o, m] = s.split(':').map(Number); const t = o * 60 + m + p; return `${ido2(Math.floor(t / 60) % 24)}:${ido2(t % 60)}`; };
        r.orak.push(utolso ? { kezdet: plusz(utolso.vege, 10), vege: plusz(utolso.vege, 55) } : { kezdet: '08:00', vege: '08:45' });
        sorok();
        frissit();
      };
      const generalo = async () => {
        const p = { elso: '07:30', darab: 8, ora_hossz: 45, szunet: 10, nagyszunet_utan: 3, nagyszunet: 15 };
        const doboz = el('div', { class: 'mezok ket' }, idoMezo(p, 'elso', 'Első óra kezdete'), szam(p, 'darab', 'Órák száma', 1, 15),
          szam(p, 'ora_hossz', 'Óra hossza', 10, 120, 1, 'perc'), szam(p, 'szunet', 'Szünet', 0, 60, 1, 'perc'),
          szam(p, 'nagyszunet_utan', 'Nagyszünet hányadik óra után', 0, 15), szam(p, 'nagyszunet', 'Nagyszünet hossza', 0, 90, 1, 'perc'));
        if (await modal('Rend generálása', doboz, [['Mégse', false], ['Generálás', true, 'fo']])) {
          r.orak = await api('POST', '/api/v1/rend-generalas', p);
          sorok();
          frissit();
        }
      };
      return el('div', {}, szoveg(r, 'nev', 'Név', { valt: frissit }),
        el('table', { class: 'ora-tabla' }, el('thead', {}, el('tr', {}, el('th', { text: '' }), el('th', { text: 'Kezdete' }), el('th', { text: 'Vége' }), el('th'))), tabla),
        el('div', { class: 'gombsor', style: 'margin-top:6px' }, el('button', { class: 'gomb kicsi', text: '+ Óra', onclick: ujOra }),
          el('button', { class: 'gomb kicsi', text: 'Generálás…', onclick: generalo })));
    },
  });
}

const Csengetes = {
  async init(main) {
    await beallitasBetolt();
    this.main = main;
    this.rajzol();
  },
  rajzol() {
    const main = this.main;
    const rendOpciok = () => [['', '— nincs csengetés —'], ...B.beallitasok.rendek.map((r) => [r.nev, r.nev])];
    main.replaceChildren(
      beallitasKartya('Csengetési rendek', ['rendek'], (p, valt) => rendSzerkeszto(p.rendek, valt),
        { leiras: 'Az órák kezdete és vége. A jelzőcsengő a becsengetés előtt szól, a kicsengő az óra végén.', utana: () => this.rajzol() }),
      el('div', { class: 'racs' },
        beallitasKartya('Heti beosztás', ['het'], (p, valt) => el('div', {}, NAPOK.map((nap, i) => {
          const s = el('select', {}, rendOpciok().map(([e, n]) => el('option', { value: e, text: n })));
          s.value = p.het[i] || '';
          s.addEventListener('change', () => { p.het[i] = s.value; valt(); });
          return el('div', { class: 'mezo' }, el('label', { text: nap }), s);
        })), { leiras: 'Melyik napon melyik rend szerint csengessen. Szünnapon és kivételnapon a Naptár dönt.' }),
        beallitasKartya('Csengetés', ['jelzo', 'jelzo_perc', 'kicsengo', 'csengo_hangero'], (p, valt) => el('div', {},
          kapcsolo(p, 'jelzo', 'Jelzőcsengő a becsengetés előtt', '', valt), szam(p, 'jelzo_perc', 'Jelzőcsengő ideje', 0, 15, 1, 'perc a becsengetés előtt', valt),
          kapcsolo(p, 'kicsengo', 'Kicsengetés az óra végén', '', valt), szam(p, 'csengo_hangero', 'Csengő és bemondás hangereje', 0, 100, 1, '%', valt)))),
      el('div', { class: 'racs', style: 'margin-top:16px' },
        beallitasKartya('Hangok', Object.keys({ hang_becsengo: 1, hang_kicsengo: 1, hang_jelzo: 1, hang_gong: 1, hang_riasztas: 1 }), (p, valt) => el('div', {},
          hangValaszto(p, 'hang_becsengo', 'Becsengő', valt), hangValaszto(p, 'hang_kicsengo', 'Kicsengő', valt), hangValaszto(p, 'hang_jelzo', 'Jelzőcsengő', valt),
          hangValaszto(p, 'hang_gong', 'Bemondás előtti gong', valt), hangValaszto(p, 'hang_riasztas', 'Riasztás', valt))),
        this.sajatHangok()));
  },
  sajatHangok() {
    const lista = el('div', { class: 'lista' });
    const rajzol = () => {
      const sajat = B.hangok.filter((h) => !h.beepitett);
      lista.replaceChildren(...(sajat.length ? sajat.map((h) => el('div', { class: 'lista-elem' }, el('span', { class: 'noveszt', text: h.nev }),
        el('button', { class: 'gomb ikonos kicsi', text: '▶', title: 'Meghallgatás', onclick: () => api('POST', '/api/v1/hang-proba', { ertek: h.ertek }) }),
        el('button', { class: 'gomb kicsi', text: 'Átnevezés', onclick: async () => {
          const p = { nev: h.nev };
          if (await modal('Átnevezés', szoveg(p, 'nev', 'Új név'), [['Mégse', false], ['Mentés', true, 'fo']])) {
            B.hangok = await api('PATCH', '/api/v1/hangok', { ertek: h.ertek, nev: p.nev });
            await beallitasBetolt();
            this.rajzol();
          }
        } }),
        el('button', { class: 'gomb kicsi veszely', text: 'Törlés', onclick: async () => {
          if (await megerosit('Törlés', `Törlöd: „${h.nev}”? Ahol használtad, a beépített hang lép a helyére.`, 'Törlés', 'veszely')) {
            await api('DELETE', '/api/v1/hangok', { ertek: h.ertek });
            await beallitasBetolt();
            this.rajzol();
          }
        } }))) : [el('div', { class: 'lista-ures', text: 'Még nincs saját hang.' })]));
    };
    rajzol();
    const fajl = el('input', { type: 'file', accept: 'audio/*,.mp3,.wav,.ogg,.m4a,.flac,.opus' });
    const nev = el('input', { type: 'text', placeholder: 'Név (nem kötelező)' });
    return kartya('Saját hangok', el('p', { class: 'halvany', text: 'Saját csengőhang, gong vagy hangfájlos bemondás (MP3, WAV, OGG, M4A, FLAC; legfeljebb 30 MB).' }), lista,
      el('div', { class: 'gombsor', style: 'margin-top:10px' }, fajl, nev, el('button', { class: 'gomb fo', text: 'Feltöltés', onclick: async () => {
        if (!fajl.files[0]) return uzenet('Válassz egy hangfájlt.', 'hiba');
        await feltoltes('/api/v1/hangok', fajl.files[0], { nev: nev.value });
        await beallitasBetolt();
        uzenet('Hang hozzáadva.', 'siker');
        this.rajzol();
      } })));
  },
};

function forrasCimMezo(f, frissit) {
  if (f.tipus === 'fajlok') return szoveg(f, 'cim', 'Fájlok (soronként egy útvonal, .m3u is)', { sorok: 4, valt: frissit, sugo: 'A konténerben látható útvonalak, pl. /zene/Lista/szam.mp3' });
  const sugo = { mappa: 'A konténerben látható mappa, pl. /zene/Szunetzene (az almappák is számítanak).', youtube: 'YouTube-lejátszási lista vagy videó linkje.', spotify: 'Spotify-lejátszási lista, album vagy szám linkje (Premium kell).' }[f.tipus];
  return szoveg(f, 'cim', f.tipus === 'mappa' ? 'Mappa' : 'Link', { valt: frissit, sugo, datalist: f.tipus === 'mappa' ? 'zene-mappak' : undefined });
}

function helySzoveg(z) {
  const reszek = [];
  if (z.szol && z.most_kert) reszek.push('kért zene szól');
  if (z.kert_db) reszek.push(`${z.kert_db} kért zene várakozik`);
  if (z.alap && z.alap.hely) reszek.push(`alap lista: ${z.alap.hely}/${z.alap.osszes}`);
  return reszek.join(' · ');
}

function lejatszasiSor(doboz, a) {
  const z = a.zene;
  const kulcs = JSON.stringify([z.szol, z.cim, z.most_kert, z.kertek, z.alap, z.alap_lista]);
  if (doboz.dataset.kulcs === kulcs) return;
  doboz.dataset.kulcs = kulcs;
  const ugras = (s) => muvelet('POST', '/api/v1/zene/ugras', { index: s.index, cim: s.cim });
  const most = !z.alap_lista.length && !z.kertek.length ? 'A sor a zene indításakor töltődik be.'
    : !z.szol ? `Áll a zene. Az alap listában itt tart: ${z.alap?.hely ?? '–'}/${z.alap?.osszes ?? 0}.`
      : z.most_kert ? `Most szól (kért zene): ${z.cim}. Utána az alap lista folytatódik, eddig: ${z.alap?.hely ?? '–'}/${z.alap?.osszes ?? 0}.`
        : `Most szól: ${z.cim}. Az alap listában: ${z.alap?.hely ?? '–'}/${z.alap?.osszes ?? 0}.`;
  const alapLista = el('div', { class: 'lista lejatszasi-lista' }, z.alap_lista.map((s, n) => el('div', { class: `lista-elem${n + 1 === z.alap?.hely ? ' aktiv' : ''}` },
    el('span', { class: 'noveszt', text: `${n + 1}. ${s.cim}` }), el('button', { class: 'gomb kicsi', text: 'Lejátszás', onclick: () => ugras(s) }))));
  doboz.replaceChildren(el('p', { text: most }),
    el('h3', { text: z.kertek.length ? `Kért zenék: ${z.kertek.length} várakozik – ezek szólnak először` : 'Kért zenék: nincs várakozó kérés' }),
    z.kertek.length ? el('div', { class: 'lista' }, z.kertek.map((s, n) => el('div', { class: 'lista-elem' },
      el('span', { class: 'noveszt', text: `${n + 1}. ${s.cim}` }), el('button', { class: 'gomb kicsi', text: 'Lejátszás', onclick: () => ugras(s) })))) : null,
    el('h3', { text: `Alap lejátszási lista: ${z.alap_lista.length} szám` }), alapLista);
  const aktiv = alapLista.querySelector('.aktiv');
  if (aktiv) alapLista.scrollTop = aktiv.offsetTop - alapLista.clientHeight / 2;
}

const Zene = {
  async init(main) {
    await beallitasBetolt();
    this.main = main;
    this.rendszer = await api('GET', '/api/v1/rendszer');
    this.sorDoboz = el('div');
    this.rajzol();
    if (ALLAPOT) lejatszasiSor(this.sorDoboz, ALLAPOT);
    if (location.hash) setTimeout(() => document.getElementById(location.hash.slice(1))?.scrollIntoView(), 100);
  },
  rajzol() {
    const r = this.rendszer;
    const forrasOpciok = () => B.beallitasok.forrasok.map((f, i) => [i, `${f.nev} (${f.tipus})`]);
    const datalist = el('datalist', { id: 'zene-mappak' }, (r.zene_mappak || []).map((m) => el('option', { value: m })));
    this.moderalas = el('section', { class: 'kartya', id: 'moderalas' });
    this.main.replaceChildren(datalist,
      kartya('Lejátszási sor', this.sorDoboz),
      beallitasKartya('Zeneforrások', ['forrasok', 'aktiv_forras'], (p, valt) => el('div', {},
        listaSzerkeszto(p.forrasok, {
          felirat: (f) => `${f.nev || 'Névtelen'} · ${({ mappa: 'Mappa', fajlok: 'Fájlok', youtube: 'YouTube', spotify: 'Spotify' })[f.tipus]}${f.aktiv ? '' : ' (kikapcsolva)'}`,
          uj: () => ({ tipus: 'mappa', nev: 'Új forrás', cim: r.zene_gyoker || '/zene', aktiv: true }), ujFelirat: 'Új zeneforrás', valt,
          mezok: (f, frissit) => {
            const cim = el('div', {}, forrasCimMezo(f, frissit));
            return el('div', {}, el('div', { class: 'mezok ket' }, szoveg(f, 'nev', 'Név', { valt: frissit }),
              valaszto(f, 'tipus', 'Típus', [['mappa', 'Mappa'], ['fajlok', 'Fájlok'], ['youtube', 'YouTube'], ['spotify', 'Spotify']], () => { cim.replaceChildren(forrasCimMezo(f, frissit)); frissit(); })),
              cim, kapcsolo(f, 'aktiv', 'Használható', '', frissit));
          },
        }),
        p.forrasok.length ? valaszto(p, 'aktiv_forras', 'Alapértelmezett forrás', forrasOpciok(), valt) : null,
        el('button', { class: 'gomb kicsi', text: 'Lista újratöltése (új fájlok, YouTube-lista)', onclick: () => api('POST', '/api/v1/forras-ujratoltes').then(() => uzenet('Újratöltés elindítva.', 'siker')) })),
        { leiras: `Helyi zene a konténer ${r.zene_gyoker || '/zene'} mappájában (a gépen: KFM_ZENE_MAPPA, alapból ~/Zenék).`, utana: () => this.rajzol() }),
      el('div', { class: 'racs' },
        beallitasKartya('Szünetzene', ['zene_szunetben', 'zene_min_szunet', 'zene_kesleltetes', 'zene_leall_elotte', 'reggeli_zene', 'reggeli_zene_tol', 'keveres', 'elhalkitas', 'atusztatas', 'zene_hangero', 'zene_kihagyott_szunetek'], (p, valt) => el('div', {},
          kapcsolo(p, 'zene_szunetben', 'Szünetzene automatikusan a szünetekben', '', valt),
          el('div', { class: 'mezok ket' }, szam(p, 'zene_min_szunet', 'Legrövidebb zenés szünet', 0, 60, 1, 'perc', valt),
            szam(p, 'zene_kesleltetes', 'Indulás a kicsengetés után', 0, 600, 1, 'mp', valt),
            szam(p, 'zene_leall_elotte', 'Leállás a jelző/becsengő előtt', 0, 600, 1, 'mp', valt),
            szam(p, 'zene_hangero', 'Hangerő', 0, 100, 1, '%', valt),
            szam(p, 'elhalkitas', 'Elhalkítás leállításkor', 0, 15, 0.5, 'mp', valt),
            szam(p, 'atusztatas', 'Átúsztatás a számok között', 0, 15, 0.5, 'mp', valt)),
          el('label', { text: 'Ezekben a szünetekben ne legyen zene' }),
          el('div', { class: 'gombsor' }, Array.from({ length: 10 }, (_, sz) => {
            const c = el('input', { type: 'checkbox', checked: p.zene_kihagyott_szunetek.includes(sz) });
            c.addEventListener('change', () => {
              const h = new Set(p.zene_kihagyott_szunetek);
              c.checked ? h.add(sz) : h.delete(sz);
              p.zene_kihagyott_szunetek = [...h].sort((a, b) => a - b);
              valt();
            });
            return el('label', { class: 'sor', title: sz === 0 ? 'Tanítás előtt' : `A ${sz}. óra utáni szünet` }, c, sz === 0 ? 'Reggel' : `${sz}.`);
          })),
          kapcsolo(p, 'reggeli_zene', 'Reggeli zene tanítás előtt', '', valt), idoMezo(p, 'reggeli_zene_tol', 'Reggeli zene kezdete', valt),
          kapcsolo(p, 'keveres', 'Keverés (véletlen sorrend)', '', valt))),
        el('div', {},
          beallitasKartya('YouTube és hangerő', ['youtube_gyorsitotar', 'hangero_kiegyenlites'], (p, valt) => el('div', {},
            kapcsolo(p, 'youtube_gyorsitotar', 'YouTube-számok előre letöltése (gyorsítótár)', `Most ${r.gyorsitotar_mb} MB.`, valt),
            el('button', { class: 'gomb kicsi', text: 'Gyorsítótár ürítése', onclick: async () => { await api('POST', '/api/v1/gyorsitotar-urites'); uzenet('Gyorsítótár ürítve.', 'siker'); } }),
            kapcsolo(p, 'hangero_kiegyenlites', 'Hangerő-kiegyenlítés (minden szám egyformán hangos)', `${ALLAPOT.rendszer?.kiegyenlito?.ismert ?? 0} szám hangossága ismert. A csengő- és riasztóhangokat nem változtatja.`, valt))),
          this.spotifyKartya())),
      beallitasKartya('Műsorblokkok', ['musorblokkok'], (p, valt) => listaSzerkeszto(p.musorblokkok, {
        felirat: (m) => `${m.nev || 'Névtelen'} · ${m.forras || '?'} · ${m.napok.map((n) => NAP_ROVID[n]).join(', ')}${m.szunetek.length ? ` · ${m.szunetek.map((s) => (s === 0 ? 'reggel' : `${s}.`)).join(', ')} szünet` : ' · minden szünet'}`,
        uj: () => ({ nev: 'Új műsorblokk', forras: B.beallitasok.forrasok[0]?.nev || '', napok: [0, 1, 2, 3, 4], szunetek: [], aktiv: true }), valt, ujFelirat: 'Új műsorblokk',
        mezok: (m, frissit) => {
          const sz = { szoveg: m.szunetek.join(', ') };
          return el('div', {}, el('div', { class: 'mezok ket' }, szoveg(m, 'nev', 'Név', { valt: frissit }),
            valaszto(m, 'forras', 'Zeneforrás', B.beallitasok.forrasok.map((f) => [f.nev, f.nev]), frissit)),
            napValaszto(m, 'napok', 'Napok', frissit),
            szoveg(sz, 'szoveg', 'Szünetek', { hely: 'üres = mind; 0 = tanítás előtt; pl. 2, 3', valt: () => { m.szunetek = sz.szoveg.split(/[,\s]+/).filter((x) => x !== '').map(Number).filter((x) => Number.isInteger(x) && x >= 0); frissit(); } }),
            kapcsolo(m, 'aktiv', 'Bekapcsolva', '', frissit));
        },
      }), { leiras: 'Szünetenként és naponként más zeneforrás (pl. hétfő reggel nyugis lista, nagyszünetben a diákok kedvencei).' }),
      el('div', { class: 'racs' },
        beallitasKartya('Szűrő', ['szuro_alap', 'szuro_korhataros', 'szuro_dalszoveg', 'szuro_erzekenyseg', 'szuro_szavak'], (p, valt) => {
          const szavak = { szoveg: p.szuro_szavak.join('\n') };
          return el('div', {}, kapcsolo(p, 'szuro_alap', 'Beépített trágárszó-lista és „Explicit” jelölés', '', valt),
            kapcsolo(p, 'szuro_korhataros', 'Korhatáros YouTube-videók kihagyása', '', valt),
            kapcsolo(p, 'szuro_dalszoveg', 'Dalszöveg-ellenőrzés (LRCLIB)', 'A túl trágár szövegű számok kimaradnak.', valt),
            valaszto(p, 'szuro_erzekenyseg', 'Érzékenység', [['szigoru', 'Szigorú'], ['normal', 'Normál'], ['laza', 'Laza']], valt),
            szoveg(szavak, 'szoveg', 'Saját tiltott szavak (soronként; a „szó*” szókezdet)', { sorok: 4, valt: () => { p.szuro_szavak = szavak.szoveg.split('\n').map((s) => s.trim()).filter(Boolean); valt(); } }));
        }),
        this.zenekeresKartya()),
      this.szinkronKartya(),
      this.moderalas);
    this.moderalasRajzol(ALLAPOT);
  },
  szinkronKartya() {
    this.szinkronAllapot = el('div', { class: 'gombsor' });
    const k = beallitasKartya('Zenék a szerverről', ['zene_szinkron', 'zene_szinkron_mappa', 'zene_szinkron_kbps'], (p, valt) => el('div', {},
      kapcsolo(p, 'zene_szinkron', 'Zenék letöltése a szerverről', '', valt),
      szoveg(p, 'zene_szinkron_mappa', 'Letöltési mappa ezen a gépen', { hely: ALLAPOT.rendszer?.zene_szinkron?.mappa || 'alapból az adatmappa szerver-zenek almappája', valt }),
      szam(p, 'zene_szinkron_kbps', 'Sebességkorlát (hogy ne fogja meg a hálózatot)', 0, 100000, 256, 'KB/s', valt, '0 = korlátlan')),
      { leiras: 'A szerver zenemappáját a program letölti erre a gépre, és innen játssza le, így szünetben nem streamel a hálózaton. Csak az új vagy megváltozott fájlokat tölti le, félbeszakadt letöltésnél onnan folytatja, ahol abbamaradt, és amit a szerveren törölsz, itt is törli. A zenekérő szerver címét és kulcsát használja; félóránként néz rá.' });
    k.append(this.szinkronAllapot);
    this.szinkronRajzol(ALLAPOT);
    return k;
  },
  szinkronRajzol(a) {
    if (!this.szinkronAllapot) return;
    const sz = a?.rendszer?.zene_szinkron;
    const kulcs = JSON.stringify(sz);
    if (this.szinkronAllapot.dataset.kulcs === kulcs) return;
    this.szinkronAllapot.dataset.kulcs = kulcs;
    let szoveg;
    let osztaly = 'halvany';
    if (!sz) szoveg = 'A lejátszó démon nem fut.';
    else if (!sz.szerver) szoveg = 'Előbb add meg lent a zenekérő szerver címét és kulcsát.';
    else if (!sz.be) szoveg = 'Kikapcsolva.';
    else if (sz.fut) szoveg = sz.allapot || 'Letöltés…';
    else if (sz.hiba) { szoveg = sz.hiba; osztaly = 'hiba-szoveg'; }
    else if (sz.utolso && sz.eredmeny) {
      const e = sz.eredmeny;
      szoveg = `Naprakész · ${e.osszes} szám · utoljára ${new Date(sz.utolso * 1000).toLocaleTimeString('hu-HU', { hour: '2-digit', minute: '2-digit' })}`
        + (e.uj ? ` · ${e.uj} új` : '') + (e.torolt ? ` · ${e.torolt} törölve` : '') + (e.hibas ? ` · ${e.hibas} hibás, újrapróbálja` : '');
    } else szoveg = 'Hamarosan ellenőrzi a szervert…';
    this.szinkronAllapot.replaceChildren(el('span', { class: `noveszt ${osztaly}`, text: szoveg }),
      sz?.fut ? el('button', { class: 'gomb kicsi', text: 'Leállítás', onclick: () => muvelet('DELETE', '/api/v1/zene-szinkron') })
        : el('button', { class: 'gomb kicsi', text: 'Letöltés most', disabled: !sz?.beallitva, onclick: () => muvelet('POST', '/api/v1/zene-szinkron', undefined, 'Letöltés elindítva') }));
  },
  zenekeresKartya() {
    const r = this.rendszer;
    return beallitasKartya('Zenekérés diákoktól', ['zenekeres', 'zenekeres_auto', 'zenekeres_napi', 'zenekeres_max_perc', 'zenekeres_tiltott', 'zenekeres_szerver', 'zenekeres_szerver_kulcs', 'kijelzo_cim', 'zenekeres_oldal', 'zenekeres_mp3', 'zenekeres_mp3_mappa'], (p, valt) => {
      const tiltott = { szoveg: p.zenekeres_tiltott.join('\n') };
      const oldal = (p.zenekeres_oldal || '').trim() || r.keres_szerver?.oldal || (ALLAPOT.rendszer?.keres_szerver?.oldal) || `${location.origin}/keres`;
      const qr = el('div', { class: 'qr-kep' }, el('img', { src: `/api/v1/qr?szoveg=${encodeURIComponent(oldal)}`, alt: 'QR-kód' }));
      const ks = ALLAPOT.rendszer?.keres_szerver;
      return el('div', {}, kapcsolo(p, 'zenekeres', 'Zenekérés bekapcsolása', '', valt),
        kapcsolo(p, 'zenekeres_auto', 'Automatikus hozzáadás (az ellenőrzött kérés magától a sorba kerül)', '', valt),
        el('div', { class: 'mezok ket' }, szam(p, 'zenekeres_napi', 'Napi kérés telefononként', 1, 50, 1, '', valt),
          szam(p, 'zenekeres_max_perc', 'Leghosszabb szám', 1, 60, 1, 'perc', valt, 'Hosszabbnál a rádiós változat (radio edit) szól, ha van.')),
        szoveg(tiltott, 'szoveg', 'Tiltott szavak a kérésekben (soronként)', { sorok: 3, valt: () => { p.zenekeres_tiltott = tiltott.szoveg.split('\n').map((s) => s.trim()).filter(Boolean); valt(); } }),
        szoveg(p, 'kijelzo_cim', 'Iskolarádió neve (a kérő oldalon és a kijelzőn)', { valt }),
        kapcsolo(p, 'zenekeres_mp3', 'Elfogadott kért számok mentése MP3-ként', 'A cím lesz a fájlnév.', valt),
        szoveg(p, 'zenekeres_mp3_mappa', 'MP3-mappa (a konténerben)', { hely: '/adat/kert-szamok', valt }),
        szoveg(p, 'zenekeres_oldal', 'Kérő oldal címe (QR-kód, plakát, kijelző)', { hely: 'https://botirocky.github.io/kozgaz-fm/', valt }),
        el('h2', { text: 'Zenekérő szerver (mobilnetről is)', style: 'margin-top:14px' }),
        szoveg(p, 'zenekeres_szerver', 'Szerver címe', { hely: 'https://…', valt }), szoveg(p, 'zenekeres_szerver_kulcs', 'Szerver kulcsa', { tipus: 'password', valt }),
        ks?.beallitva ? el('p', { class: ks.hiba ? 'hiba-szoveg' : 'siker-szoveg', text: ks.hiba || (ks.utolso ? `Kapcsolat rendben (${new Date(ks.utolso * 1000).toLocaleTimeString('hu-HU')})` : 'Kapcsolódás…') }) : null,
        el('h2', { text: 'Kérő oldal', style: 'margin-top:14px' }), el('p', {}, el('a', { href: oldal, target: '_blank', rel: 'noopener', text: oldal })),
        el('div', { class: 'gombsor' }, qr, el('div', { class: 'gombsor', style: 'flex-direction:column;align-items:flex-start' },
          el('a', { class: 'gomb', href: `/api/v1/qr?letoltes=1&szoveg=${encodeURIComponent(oldal)}`, text: 'QR-kód mentése (SVG)' }),
          el('a', { class: 'gomb', href: `/plakat?cim=${encodeURIComponent(oldal)}&nev=${encodeURIComponent(p.kijelzo_cim || 'Közgáz FM')}`, target: '_blank', text: 'Nyomtatható plakát (A4)' }))));
    });
  },
  spotifyKartya() {
    const r = this.rendszer;
    return beallitasKartya('Spotify', ['spotify_client_id', 'spotify_eszkoz'], (p, valt) => {
      const eszkozDoboz = el('div');
      const eszkozok = async () => {
        try {
          const lista = await api('GET', '/api/v1/spotify/eszkozok');
          eszkozDoboz.replaceChildren(valaszto(p, 'spotify_eszkoz', 'Lejátszó eszköz', [['', 'Az éppen aktív'], ...lista.map((e) => [e.name, `${e.name} (${e.type})`])], valt));
        } catch (_) { }
      };
      return el('div', { id: 'spotify' }, el('p', { class: 'halvany', text: 'A Spotify-forrás egy Spotify-alkalmazást vezérel (pl. a hangosító gépen fut). Premium-előfizetés kell.' }),
        szoveg(p, 'spotify_client_id', 'Client ID', { valt, sugo: 'Átirányítási cím (Redirect URI) a Spotify-alkalmazásnál: http://127.0.0.1:8898/callback' }),
        el('p', { text: r.spotify ? 'Bejelentkezve.' : 'Nincs bejelentkezve.', class: r.spotify ? 'siker-szoveg' : 'halvany' }),
        el('div', { class: 'gombsor' }, el('a', { class: 'gomb', href: 'http://127.0.0.1:8898/spotify/belepes', text: 'Bejelentkezés (ezen a gépen)' }),
          r.spotify ? el('button', { class: 'gomb', text: 'Kijelentkezés', onclick: async () => { await api('POST', '/api/v1/spotify/kijelentkezes'); this.rendszer.spotify = false; this.rajzol(); } }) : null,
          r.spotify ? el('button', { class: 'gomb', text: 'Eszközök betöltése', onclick: eszkozok }) : null),
        eszkozDoboz, p.spotify_eszkoz ? el('p', { class: 'halvany', text: `Kiválasztott eszköz: ${p.spotify_eszkoz}` }) : null);
    });
  },
  frissit(a) {
    if (this.sorDoboz) lejatszasiSor(this.sorDoboz, a);
    this.szinkronRajzol(a);
    if (this.moderalas && !this.moderalas.contains(document.activeElement)) this.moderalasRajzol(a);
  },
  moderalasRajzol(a) {
    const zk = a.zenekeres;
    if (!zk || !this.moderalas) return;
    const jel = (k) => ({ varakozik: 'sarga', elfogadva: 'kek', szol: 'zold', elutasitva: 'piros', levett: '' }[k.allapot] || '');
    const sorok = zk.mai.map((k) => el('tr', {}, el('td', { text: k.ido }),
      el('td', {}, el('div', { class: 'cimke-sor', text: k.cim || k.szoveg }), el('div', { class: 'al-sor', text: `${k.nev || 'névtelen'} · ${k.ip}${k.megjegyzes ? ' · ' + k.megjegyzes : ''}${k.ok ? ' · ' + k.ok : ''}` })),
      el('td', {}, el('span', { class: `jel ${jel(k)}`, text: k.allapot_nev })),
      el('td', {}, el('div', { class: 'gombsor' },
        k.link ? el('a', { class: 'gomb kicsi', href: k.link, target: '_blank', rel: 'noopener', text: '▶' }) : null,
        k.allapot === 'varakozik' ? el('button', { class: 'gomb kicsi fo', text: 'Elfogad', onclick: () => muvelet('POST', '/api/v1/zenekeres/dontes', { azon: k.azon, elfogad: true }) }) : null,
        ['varakozik', 'kereses'].includes(k.allapot) ? el('button', { class: 'gomb kicsi', text: 'Elutasít', onclick: () => muvelet('POST', '/api/v1/zenekeres/dontes', { azon: k.azon, elfogad: false }) }) : null,
        ['elfogadva', 'szol'].includes(k.allapot) ? el('button', { class: 'gomb kicsi', text: 'Levesz', onclick: () => muvelet('POST', '/api/v1/zenekeres/levetel', { azon: k.azon }) }) : null,
        k.yt_van ? el('button', { class: 'gomb kicsi', text: 'Szám tiltása', onclick: () => muvelet('POST', '/api/v1/zenekeres/szam-tiltas', { azon: k.azon }, 'Szám letiltva') }) : null,
        !k.telefon_tiltva ? el('button', { class: 'gomb kicsi veszely', text: 'Telefon tiltása (7 nap)', onclick: async () => {
          if (await megerosit('Telefon tiltása', 'Erről a telefonról 7 napig nem lehet számot kérni, és a sorban lévő kérései is kikerülnek.', 'Tiltás', 'veszely')) muvelet('POST', '/api/v1/zenekeres/telefon-tiltas', { azon: k.azon }, 'Telefon letiltva');
        } }) : el('span', { class: 'jel piros', text: 'telefon tiltva' })))));
    this.moderalas.replaceChildren(el('h2', { text: 'Moderálás' }),
      el('h3', { text: 'Mai kérések' }), zk.mai.length ? el('table', { class: 'tabla' }, el('thead', {}, el('tr', {}, ['Idő', 'Kérés', 'Állapot', ''].map((t) => el('th', { text: t })))), el('tbody', {}, sorok)) : el('p', { class: 'halvany', text: 'Ma még nem jött kérés.' }),
      el('h3', { text: 'Letiltott számok', style: 'margin-top:14px' }), zk.tiltott_szamok.length ? el('div', { class: 'lista' }, zk.tiltott_szamok.map((t) => el('div', { class: 'lista-elem' },
        el('span', { class: 'noveszt', text: t.cim }), el('span', { class: 'halvany', text: t.ido }), el('button', { class: 'gomb kicsi', text: 'Feloldás', onclick: () => muvelet('DELETE', '/api/v1/zene/tiltas', { azon: t.azon }, 'Tiltás feloldva') })))) : el('p', { class: 'halvany', text: 'Nincs letiltott szám.' }),
      el('h3', { text: 'Letiltott telefonok', style: 'margin-top:14px' }), zk.tiltott_telefonok.length ? el('div', { class: 'lista' }, zk.tiltott_telefonok.map((t) => el('div', { class: 'lista-elem' },
        el('span', { class: 'noveszt', text: t.nev || 'névtelen' }), el('span', { class: 'halvany', text: `${t.ig}-ig` }), el('button', { class: 'gomb kicsi', text: 'Feloldás', onclick: () => muvelet('DELETE', '/api/v1/zenekeres/telefon-tiltas', { kulcs: t.kulcs }, 'Tiltás feloldva') })))) : el('p', { class: 'halvany', text: 'Nincs letiltott telefon.' }));
  },
};

const RENDKIVULI_TIPUSOK = [['csengetes', 'Rendkívüli csengetés'], ['riado', 'Tűzriadó-gyakorlat'], ['csend', 'Csendes időszak']];

const Naptar = {
  async init(main) {
    await beallitasBetolt();
    this.main = main;
    this.rajzol();
  },
  rajzol() {
    const rendek = B.beallitasok.rendek.map((r) => [r.nev, r.nev]);
    this.main.replaceChildren(
      el('div', { class: 'racs' },
        beallitasKartya('Szünnapok', ['szunnapok'], (p, valt) => el('div', {}, listaSzerkeszto(p.szunnapok, {
          felirat: (s) => `${s.tol}${s.ig && s.ig !== s.tol ? ' – ' + s.ig : ''} · ${s.nev || 'Szünnap'}`,
          uj: () => { const d = new Date().toISOString().slice(0, 10); return { tol: d, ig: d, nev: '' }; }, valt, ujFelirat: 'Új szünnap', rendezheto: false,
          mezok: (s, frissit) => el('div', { class: 'mezok' }, idoMezo(s, 'tol', 'Kezdete', frissit, 'date'), idoMezo(s, 'ig', 'Vége', frissit, 'date'), szoveg(s, 'nev', 'Név', { valt: frissit })),
        }), el('div', { class: 'gombsor', style: 'margin-top:8px' }, el('button', { class: 'gomb', text: 'Ünnepnapok betöltése…', onclick: async () => {
          const p = { ev: new Date().getFullYear() + (new Date().getMonth() >= 7 ? 1 : 0) };
          if (await modal('Ünnepnapok', szam(p, 'ev', 'Év', 2000, 2100), [['Mégse', false], ['Betöltés', true, 'fo']])) {
            const e = await api('POST', '/api/v1/unnepek', p);
            uzenet(`${e.uj} új ünnepnap.`, 'siker');
            await beallitasBetolt();
            this.rajzol();
          }
        } }))), { leiras: 'Ezeken a napokon nincs csengetés és szünetzene.' }),
        beallitasKartya('Kivételnapok', ['kivetelek'], (p, valt) => {
          const lista = Object.entries(p.kivetelek).sort().map(([datum, rend]) => ({ datum, rend }));
          const vissza = () => { p.kivetelek = Object.fromEntries(lista.filter((x) => x.datum).map((x) => [x.datum, x.rend])); valt(); };
          return listaSzerkeszto(lista, {
            felirat: (x) => `${x.datum} · ${x.rend}`, uj: () => ({ datum: new Date().toISOString().slice(0, 10), rend: rendek[0]?.[0] || '' }),
            valt: vissza, ujFelirat: 'Új kivételnap', rendezheto: false,
            mezok: (x, frissit) => el('div', { class: 'mezok ket' }, idoMezo(x, 'datum', 'Dátum', frissit, 'date'), valaszto(x, 'rend', 'Csengetési rend', rendek, frissit)),
          });
        }, { leiras: 'Egy adott napon más rend (pl. rövidített órák, szombati tanítási nap). Szünnapnál is erősebb.' })),
      beallitasKartya('Rendkívüli események', ['rendkivuli'], (p, valt) => listaSzerkeszto(p.rendkivuli, {
        felirat: (r) => `${r.datum} ${r.tol}${r.tipus === 'csend' ? '–' + r.ig : ''} · ${r.nev || 'névtelen'} · ${RENDKIVULI_TIPUSOK.find(([t]) => t === r.tipus)?.[1]}${r.aktiv ? '' : ' (kikapcsolva)'}`,
        uj: () => ({ nev: '', datum: new Date().toISOString().slice(0, 10), tol: '10:00', tipus: 'csengetes', ig: '', hang: 'beepitett:csengo', riado_perc: 3, csengo_hangero: 0, aktiv: true }),
        valt, ujFelirat: 'Új esemény', rendezheto: false,
        mezok: (r, frissit) => {
          const reszlet = el('div');
          const rajzolR = () => {
            reszlet.replaceChildren(
              r.tipus === 'csend' ? el('div', { class: 'mezok ket' }, idoMezo(r, 'ig', 'Vége', frissit), szam(r, 'csengo_hangero', 'Csengő hangereje (0 = néma)', 0, 100, 1, '%', frissit)) : null,
              r.tipus === 'csengetes' ? hangValaszto(r, 'hang', 'Hang', frissit) : null,
              r.tipus === 'riado' ? szam(r, 'riado_perc', 'Riasztás hossza (0 = kézi leállításig)', 0, 60, 1, 'perc', frissit) : null,
              el('p', { class: 'halvany kicsi-szoveg', text: { csengetes: 'A megadott időpontban egyszer megszólal a hang (pl. ünnepség kezdete). Szünnapon is szól.', riado: 'Magától indul és leáll. A folyosói kijelző előre nem mutatja.', csend: 'Nincs szünetzene és ütemezett bemondás; a csengő néma vagy halk.' }[r.tipus] }));
          };
          rajzolR();
          return el('div', {}, el('div', { class: 'mezok' }, szoveg(r, 'nev', 'Név', { valt: frissit, hely: 'pl. Érettségi' }),
            valaszto(r, 'tipus', 'Típus', RENDKIVULI_TIPUSOK, () => { if (r.tipus === 'csend' && !r.ig) r.ig = r.tol; rajzolR(); frissit(); }),
            idoMezo(r, 'datum', 'Dátum', frissit, 'date'), idoMezo(r, 'tol', 'Időpont / kezdete', frissit)), reszlet, kapcsolo(r, 'aktiv', 'Bekapcsolva', '', frissit));
        },
      })),
      this.importKartya());
  },
  importKartya() {
    const fajl = el('input', { type: 'file', accept: '.ics,text/calendar' });
    const url = el('input', { type: 'url', placeholder: 'https://… vagy webcal://…' });
    const elonezet = async (adat) => {
      const lista = adat.javaslatok.map((j) => ({ ...j, valasztva: j.muvelet !== 'kihagy' }));
      const rend = { atvesz: adat.valtozott?.length > 0 };
      const tabla = el('table', { class: 'tabla' }, el('thead', {}, el('tr', {}, ['', 'Esemény', 'Időszak', 'Teendő'].map((t) => el('th', { text: t })))),
        el('tbody', {}, lista.map((j) => {
          const c = el('input', { type: 'checkbox', checked: j.valasztva, disabled: j.muvelet === 'kihagy' });
          c.addEventListener('change', () => { j.valasztva = c.checked; });
          return el('tr', {}, el('td', {}, c), el('td', { text: j.esemeny.nev }), el('td', { text: j.esemeny.tol === j.esemeny.ig ? j.esemeny.tol : `${j.esemeny.tol} – ${j.esemeny.ig}` }),
            el('td', { text: adat.muveletek[j.muvelet] + (j.megjegyzes ? ` (${j.megjegyzes})` : '') }));
        })));
      const rendDoboz = adat.normal ? el('div', { class: 'kartya' }, el('h3', { text: 'Csengetési rend a honlapról' }),
        el('p', { text: `Normál: ${adat.normal_szoveg}${adat.rovid_szoveg ? `; Rövidített: ${adat.rovid_szoveg}` : ''}` }),
        adat.valtozott.length ? kapcsolo(rend, 'atvesz', `A(z) ${adat.valtozott.join(', ')} rend átvétele (eltér a mostanitól)`) : el('p', { class: 'halvany', text: 'Megegyezik a mostanival.' })) : null;
      const ok = await modal('Tanév rendje – előnézet', el('div', {}, rendDoboz, lista.length ? tabla : el('p', { text: 'Nincs új esemény.' }),
        el('p', { class: 'halvany kicsi-szoveg', text: 'Kézzel beállított kivételnapot nem ír felül.' })), [['Mégse', false], ['Alkalmazás', true, 'fo']], { szeles: true });
      if (!ok) return;
      const e = await api('POST', '/api/v1/import/alkalmaz', { javaslatok: lista.filter((j) => j.valasztva), rend: rend.atvesz ? { normal: adat.normal, rovid: adat.rovid } : null });
      uzenet(`Kész: ${e.szunnapok} szünnap, ${e.kivetelek} kivételnap${e.rendek.length ? ', rend: ' + e.rendek.join(', ') : ''}.`, 'siker');
      await beallitasBetolt();
      this.rajzol();
    };
    return kartya('Tanév rendje importálása',
      el('p', { class: 'halvany', text: 'Szünetek szünnapként, rövidített és szombati munkanapok kivételnapként – előnézettel, pipálással.' }),
      el('div', { class: 'gombsor' }, el('button', { class: 'gomb fo', text: 'Az iskola honlapjáról (kghsz.hu)', onclick: async (e) => {
        e.currentTarget.disabled = true;
        try { await elonezet(await api('POST', '/api/v1/import/kghsz')); } finally { e.currentTarget.disabled = false; }
      } })),
      el('label', { text: '.ics fájlból' }), el('div', { class: 'gombsor' }, fajl, el('button', { class: 'gomb', text: 'Beolvasás', onclick: async () => {
        if (!fajl.files[0]) return uzenet('Válassz egy .ics fájlt.', 'hiba');
        await elonezet(await feltoltes('/api/v1/import/ics', fajl.files[0]));
      } })),
      el('label', { text: 'Naptárlinkről (Google Naptár, webcal)' }), el('div', { class: 'gombsor' }, url, el('button', { class: 'gomb', text: 'Letöltés', onclick: async () => {
        if (!url.value.trim()) return uzenet('Add meg a naptár linkjét.', 'hiba');
        await elonezet(await api('POST', '/api/v1/import/ics', { url: url.value.trim() }));
      } })));
  },
};

const Bemondasok = {
  async init(main) {
    await beallitasBetolt();
    this.main = main;
    this.rendszer = await api('GET', '/api/v1/rendszer');
    this.rajzol();
  },
  rajzol() {
    const hangok = B.hangok.filter((h) => !h.beepitett).map((h) => [h.ertek, h.nev]);
    this.main.replaceChildren(
      beallitasKartya('Ütemezett bemondások', ['bemondasok'], (p, valt) => listaSzerkeszto(p.bemondasok, {
        felirat: (b) => `${b.ido} · ${b.nev || 'névtelen'} · ${b.datum ? b.datum : b.napok.map((n) => NAP_ROVID[n]).join(', ')}${b.aktiv ? '' : ' (kikapcsolva)'}`,
        uj: () => ({ nev: 'Új bemondás', ido: '08:00', napok: [0, 1, 2, 3, 4], datum: '', tipus: 'szoveg', tartalom: '', gong: true, aktiv: true }), valt, ujFelirat: 'Új bemondás',
        mezok: (b, frissit) => {
          const tartalom = el('div');
          const rajzolT = () => tartalom.replaceChildren(b.tipus === 'szoveg' ? szoveg(b, 'tartalom', 'Szöveg (felolvasás)', { sorok: 3, valt: frissit })
            : valaszto(b, 'tartalom', 'Hangfájl (Csengetési rend → Saját hangok)', hangok.length ? hangok : [['', 'Előbb tölts fel egy saját hangot']], frissit));
          rajzolT();
          return el('div', {}, el('div', { class: 'mezok' }, szoveg(b, 'nev', 'Név', { valt: frissit }), idoMezo(b, 'ido', 'Időpont', frissit),
            idoMezo(b, 'datum', 'Egyszeri dátum (üres = ismétlődő)', frissit, 'date'),
            valaszto(b, 'tipus', 'Típus', [['szoveg', 'Felolvasott szöveg'], ['fajl', 'Hangfájl']], () => { b.tartalom = ''; rajzolT(); frissit(); })),
            b.datum ? null : napValaszto(b, 'napok', 'Napok (szünnapon nem szól)', frissit), tartalom,
            kapcsolo(b, 'gong', 'Gong előtte', '', frissit), kapcsolo(b, 'aktiv', 'Bekapcsolva', '', frissit));
        },
      })),
      el('div', { class: 'racs' },
        beallitasKartya('Sablonok', ['bemondas_sablonok'], (p, valt) => {
          const lista = p.bemondas_sablonok.map((s) => ({ s }));
          const vissza = () => { p.bemondas_sablonok = lista.map((x) => x.s.trim()).filter(Boolean); valt(); };
          return listaSzerkeszto(lista, {
            felirat: (x) => x.s || '(üres)', uj: () => ({ s: '' }), ujFelirat: 'Új sablon',
            valt: vissza, mezok: (x, frissit) => szoveg(x, 's', '', { sorok: 3, valt: frissit }),
          });
        }, { leiras: 'Gyakori bemondások a Vezérlőpulton és a telefonos panelen.' }),
        beallitasKartya('Felolvasó hang', ['tts_hang'], (p, valt) => el('div', {},
          valaszto(p, 'tts_hang', 'eSpeak NG hang', [['', 'Magyar (alap)'], ...this.rendszer.tts_hangok.filter((h) => h !== 'hu').map((h) => [h, h])], valt),
          el('p', { class: this.rendszer.tts ? 'halvany' : 'hiba-szoveg', text: this.rendszer.tts ? 'Az eSpeak NG elérhető.' : 'Az eSpeak NG nem érhető el a démonban!' }),
          el('button', { class: 'gomb', text: 'Próba-bemondás', onclick: () => muvelet('POST', '/api/v1/bemondas', { szoveg: 'Ez egy próba bemondás a Közgáz FM-ről.', gong: false }, 'Próba elindítva') })))));
  },
};

const Naplo = {
  init(main) {
    this.szuro = el('input', { type: 'search', placeholder: 'Szűrés…' });
    this.hibak = el('input', { type: 'checkbox' });
    this.sorok = el('div', { class: 'naplo-sorok' });
    this.szuro.addEventListener('input', () => this.rajzol());
    this.hibak.addEventListener('change', () => this.rajzol());
    main.replaceChildren(kartya('Napló', el('div', { class: 'gombsor', style: 'margin-bottom:10px' }, this.szuro, el('label', { class: 'sor' }, this.hibak, 'Csak hibák'),
      el('button', { class: 'gomb', text: 'Frissítés', onclick: () => this.betolt() })), this.sorok));
    this.betolt();
    this.idozito = setInterval(() => this.betolt(), 5000);
  },
  async betolt() {
    this.lista = await api('GET', '/api/v1/naplo?n=1500', undefined, { csendes: true });
    this.rajzol();
  },
  rajzol() {
    const q = this.szuro.value.toLowerCase();
    const lent = this.sorok.scrollTop + this.sorok.clientHeight >= this.sorok.scrollHeight - 20;
    const lista = (this.lista || []).filter((s) => (!q || s.toLowerCase().includes(q)) && (!this.hibak.checked || s.includes('HIBA')));
    this.sorok.replaceChildren(...lista.map((s) => el('div', { class: s.includes('HIBA') ? 'hiba-sor' : '', text: s })));
    if (lent) this.sorok.scrollTop = this.sorok.scrollHeight;
  },
};

const Statisztika = {
  init(main) {
    this.nap = el('select', {}, [[7, 'Elmúlt 7 nap'], [30, 'Elmúlt 30 nap'], [90, 'Elmúlt 90 nap'], [365, 'Elmúlt év']].map(([e, n]) => el('option', { value: e, text: n })));
    this.nap.addEventListener('change', () => this.betolt());
    this.tartalom = el('div');
    this.csv = el('a', { class: 'gomb', text: 'CSV-export (jogdíj-elszámoláshoz)' });
    main.replaceChildren(el('div', { class: 'gombsor', style: 'margin-bottom:14px' }, this.nap, this.csv), this.tartalom);
    this.betolt();
  },
  async betolt() {
    const s = await api('GET', `/api/v1/statisztika?nap=${this.nap.value}&top=15`);
    this.csv.href = `/api/v1/statisztika?nap=${this.nap.value}&csv=1`;
    const max = Math.max(1, ...s.napok.map((n) => n.zene_perc));
    const lepes = Math.ceil(s.napok.length / 15);
    const csempe = (cim, ertek, al) => el('div', { class: 'csempe' }, el('div', { class: 'halvany kicsi-szoveg', text: cim }), el('div', { class: 'ertek', text: ertek }), al ? el('div', { class: 'halvany kicsi-szoveg', text: al }) : null);
    this.tartalom.replaceChildren(
      el('div', { class: 'szam-csempe' }, csempe('Lejátszott szám', s.zene.szamok, `${s.zene.kert} kért`), csempe('Zene', `${s.zene.perc} perc`),
        csempe('Csengetés', s.csengetes.darab, `${s.csengetes.kezi} kézi`), csempe('Átlagos eltérés', s.csengetes.atlag_keses_ms === null ? '–' : `${(s.csengetes.atlag_keses_ms / 1000).toFixed(1).replace('.', ',')} mp`, s.csengetes.kesett ? `${s.csengetes.kesett} késett (>2 mp)` : 'pontos'),
        csempe('Zenekérés', s.keresek.erkezett, `${s.keresek.elfogadva} elfogadva, ${s.keresek.elutasitva} elutasítva`)),
      el('div', { class: 'racs', style: 'margin-top:16px' },
        kartya('Napi zeneidő (perc)', el('div', { class: 'oszlopdiagram', style: 'margin-bottom:22px' }, s.napok.map((n, i) => el('div', { class: 'oszlop', title: `${n.nap}: ${n.zene_perc} perc, ${n.csengetes} csengetés`, style: `height:${(100 * n.zene_perc) / max}%` },
          i % lepes === 0 ? el('span', { text: n.nap.slice(5).replace('-', '.') }) : null)))),
        kartya('Legtöbbet játszott', s.legtobbet.length ? el('div', { class: 'lista' }, s.legtobbet.map((t, i) => el('div', { class: 'lista-elem' }, el('span', { class: 'ido-oszlop', text: `${i + 1}.` }),
          el('span', { class: 'noveszt', text: t.cim }), t.kert ? el('span', { class: 'jel kek', text: 'kért' }) : null, el('span', { class: 'halvany', text: `${t.darab}×` })))) : el('p', { class: 'halvany', text: 'Még nincs adat.' }))));
  },
};

const Beallitasok = {
  async init(main) {
    await beallitasBetolt();
    this.main = main;
    this.rendszer = await api('GET', '/api/v1/rendszer');
    this.rajzol();
  },
  rajzol() {
    const r = this.rendszer;
    const kimenetek = [['', 'Alapértelmezett'], ...(r.kimenetek || []).map((k) => [k.azon, k.nev])];
    const ESEMENYEK = { kimaradt: 'Kimaradt csengetés', hiba: 'Hibák', hangkimenet: 'Eltűnt hangkimenet', riasztas: 'Riasztás indult', tartalek: 'Tartalékgép átvette / visszaadta', indulas: 'A program elindult', reggel: 'Reggeli önteszt' };
    this.main.replaceChildren(
      el('div', { class: 'racs' },
        beallitasKartya('Hangkimenet', ['kimenet'], (p, valt) => el('div', {}, valaszto(p, 'kimenet', 'Kimenet (ha nincsenek zónák)', kimenetek, valt),
          el('p', { class: 'halvany kicsi-szoveg', text: `Most: ${r.kimenet_nev || 'nem érhető el'}${r.demon ? '' : ' – a démon nem fut!'}` }))),
        this.hozzaferesKartya()),
      beallitasKartya('Hangzónák', ['zonak'], (p, valt) => listaSzerkeszto(p.zonak, {
        felirat: (z) => `${z.nev || 'zóna'} · ${(r.kimenetek || []).find((k) => k.azon === z.kimenet)?.nev || 'alapértelmezett'} · ${[z.csengo && 'csengő', z.zene && 'zene', z.bemondas && 'bemondás'].filter(Boolean).join(', ')} · ${z.hangero}%`,
        uj: () => ({ nev: `${p.zonak.length + 1}. zóna`, kimenet: '', csengo: true, zene: true, bemondas: true, hangero: 100 }), valt, ujFelirat: 'Új zóna',
        mezok: (z, frissit, i) => el('div', {}, el('div', { class: 'mezok ket' }, szoveg(z, 'nev', 'Név', { valt: frissit }), valaszto(z, 'kimenet', 'Hangkimenet', kimenetek, frissit)),
          el('div', { class: 'gombsor' }, kapcsolo(z, 'csengo', 'Csengő', '', frissit), kapcsolo(z, 'zene', 'Zene', '', frissit), kapcsolo(z, 'bemondas', 'Bemondás', '', frissit)),
          szam(z, 'hangero', 'Halkítás ebben a zónában', 0, 100, 1, '%', frissit, 'A riasztás mindig mindenhol teljes hangerővel szól.'),
          el('button', { class: 'gomb kicsi', text: '▶ Próbahang ebben a zónában (mentés után)', onclick: () => api('POST', '/api/v1/zona-proba', { index: i }) })),
      }), { leiras: 'Több hangkimenet (pl. folyosó, udvar, tanári): zónánként kapcsolható csengő, zene és bemondás. Üres lista esetén minden a fenti kimenetre megy.' }),
      el('div', { class: 'racs' },
        beallitasKartya('Tartalékgép', ['tartalek_mod', 'tartalek_cim', 'tartalek_kulcs'], (p, valt, rajzol) => el('div', {},
          valaszto(p, 'tartalek_mod', 'Szerep', [['', 'Kikapcsolva'], ['fo', 'Ez a fő gép'], ['tartalek', 'Ez a tartalék gép']], valt),
          szoveg(p, 'tartalek_cim', 'A másik gép címe', { hely: '192.168.1.20:8080', valt }),
          (() => {
            const kulcsMezo = szoveg(p, 'tartalek_kulcs', 'Közös kulcs (mindkét gépen ugyanaz)', { valt });
            return el('div', { class: 'gombsor' }, el('div', { style: 'flex:1' }, kulcsMezo),
              el('button', { class: 'gomb kicsi', text: 'Új kulcs', onclick: async () => {
                p.tartalek_kulcs = (await api('POST', '/api/v1/tartalek-kulcs')).kulcs;
                kulcsMezo.querySelector('input').value = p.tartalek_kulcs;
                valt();
              } }));
          })(),
          ALLAPOT.rendszer?.tartalek?.szoveg ? el('p', { text: ALLAPOT.rendszer.tartalek.szoveg }) : null),
          { leiras: 'Két gép figyeli egymást; ha a fő gép kiesik, a tartalék kb. 15 mp-en belül átveszi a csengetést. A rendet és a naptárt a tartalék magától átveszi.' }),
        beallitasKartya('Folyosói kijelző', ['kijelzo_cim'], (p, valt) => el('div', {}, szoveg(p, 'kijelzo_cim', 'Felirat', { valt }),
          el('a', { class: 'gomb', href: '/kijelzo', target: '_blank', text: 'Kijelző megnyitása (F11 = teljes képernyő)' })))),
      beallitasKartya('Értesítések a rendszergazdának', ['ertesites_ntfy', 'ertesites_ntfy_token', 'ertesites_email', 'smtp_szerver', 'smtp_port', 'smtp_mod', 'smtp_felhasznalo', 'smtp_jelszo', 'smtp_felado', 'ertesites_esemenyek', 'ertesites_reggel_ido'], (p, valt) => el('div', {},
        el('div', { class: 'mezok ket' }, szoveg(p, 'ertesites_ntfy', 'ntfy-cím', { hely: 'https://ntfy.sh/kozgaz-fm-titkos-nev', valt }), szoveg(p, 'ertesites_ntfy_token', 'ntfy-token (nem kötelező)', { tipus: 'password', valt }),
          szoveg(p, 'ertesites_email', 'E-mail címzett(ek)', { valt }), szoveg(p, 'smtp_szerver', 'SMTP-szerver', { valt }),
          szam(p, 'smtp_port', 'SMTP-port', 1, 65535, 1, '', valt), valaszto(p, 'smtp_mod', 'Titkosítás', [['starttls', 'STARTTLS (587)'], ['ssl', 'SSL/TLS (465)'], ['nincs', 'Nincs (csak belső háló)']], valt),
          szoveg(p, 'smtp_felhasznalo', 'SMTP-felhasználó', { valt }), szoveg(p, 'smtp_jelszo', 'SMTP-jelszó', { tipus: 'password', valt }), szoveg(p, 'smtp_felado', 'Feladó (nem kötelező)', { valt })),
        el('label', { text: 'Mikor küldjön' }), el('div', {}, Object.entries(ESEMENYEK).map(([k, n]) => {
          const c = el('input', { type: 'checkbox', checked: p.ertesites_esemenyek.includes(k) });
          c.addEventListener('change', () => { const s = new Set(p.ertesites_esemenyek); c.checked ? s.add(k) : s.delete(k); p.ertesites_esemenyek = [...s]; valt(); });
          return el('label', { class: 'sor' }, c, n);
        })), idoMezo(p, 'ertesites_reggel_ido', 'Reggeli önteszt ideje', valt),
        el('button', { class: 'gomb', text: 'Próbaértesítés (mentés után)', onclick: () => api('POST', '/api/v1/ertesites-proba').then(() => uzenet('Próbaértesítés elküldve, nézd a telefont / postafiókot.', 'siker')) }))),
      el('div', { class: 'racs' },
        kartya('Mentés és visszaállítás', el('p', { class: 'halvany', text: 'Minden beállítás egy fájlban (a gépfüggő adatok – jelszavak, hangkimenet, zónák, tartalékgép – nélkül). A Python-változat fájlja is betölthető.' }),
          el('div', { class: 'gombsor' }, el('a', { class: 'gomb', href: '/api/v1/export', text: 'Exportálás' })),
          (() => {
            const f = el('input', { type: 'file', accept: '.json,application/json' });
            return el('div', { class: 'gombsor', style: 'margin-top:8px' }, f, el('button', { class: 'gomb', text: 'Importálás', onclick: async () => {
              if (!f.files[0]) return uzenet('Válassz egy fájlt.', 'hiba');
              if (!(await megerosit('Importálás', 'A fájlban lévő beállítások felülírják a mostaniakat. Folytatod?'))) return;
              B = await feltoltes('/api/v1/import/beallitasok', f.files[0]);
              uzenet('Beállítások importálva.', 'siker');
              this.rajzol();
            } }));
          })()),
        kartya('Rendszer', el('table', { class: 'tabla' }, el('tbody', {}, [['Verzió', r.verzio], ['Gép', r.gep], ['Lejátszó démon', r.demon ? 'fut' : 'NEM FUT'], ['Felolvasó (eSpeak NG)', r.tts ? 'elérhető' : 'nincs'],
          ['Szabad hely', `${r.szabad_gb} GB`], ['YouTube-gyorsítótár', `${r.gyorsitotar_mb} MB`], ['Zene mappa', r.zene_gyoker]].map(([k, v]) => el('tr', {}, el('th', { text: k }), el('td', { text: v }))))))));
  },
  hozzaferesKartya() {
    const regi = el('input', { type: 'password', autocomplete: 'current-password', placeholder: 'Jelenlegi jelszó' });
    const uj = el('input', { type: 'password', autocomplete: 'new-password', placeholder: 'Új jelszó (min. 8 karakter)' });
    const pin = el('input', { type: 'password', inputmode: 'numeric', maxlength: 8, placeholder: '4–8 számjegy' });
    return beallitasKartya('Hozzáférés', ['admin_zar_perc'], (p, valt) => el('div', {},
      el('label', { text: 'Webes jelszó' }), el('div', { class: 'gombsor' }, regi, uj, el('button', { class: 'gomb', text: 'Csere', onclick: async () => {
        await api('POST', '/api/v1/jelszo', { regi: regi.value, uj: uj.value });
        regi.value = uj.value = '';
        uzenet('A jelszó megváltozott.', 'siker');
      } })),
      el('label', { text: `PIN-kód a beállító oldalakhoz (${B.beallitasok.admin_pin ? 'be van állítva' : 'nincs'})` }),
      el('div', { class: 'gombsor' }, pin, el('button', { class: 'gomb', text: 'Beállítás', onclick: async () => {
        await api('POST', '/api/v1/pin', { pin: pin.value });
        location.reload();
      } }), B.beallitasok.admin_pin ? el('button', { class: 'gomb veszely', text: 'PIN törlése', onclick: async () => {
        if (await megerosit('PIN törlése', 'A beállító oldalak ezután PIN nélkül is megnyílnak.', 'Törlés', 'veszely')) {
          await api('POST', '/api/v1/pin', { pin: '' });
          location.reload();
        }
      } }) : null),
      el('p', { class: 'halvany kicsi-szoveg', text: 'A Vezérlőpult, a Riasztás, a Napló, a Statisztika és a Súgó PIN nélkül is használható.' }),
      szam(p, 'admin_zar_perc', 'Automatikus zárolás tétlenség után', 1, 240, 1, 'perc', valt)));
  },
};

const Sugo = {
  init(main) {
    main.replaceChildren(el('article', { class: 'kartya sugo', html: OLDAL.sugo || '' }));
  },
};

const OLDALAK = { '/': Pult, '/riasztas': Riasztas, '/csengetes': Csengetes, '/zene': Zene, '/naptar': Naptar, '/bemondasok': Bemondasok,
  '/naplo': Naplo, '/statisztika': Statisztika, '/beallitasok': Beallitasok, '/sugo': Sugo };

document.addEventListener('click', async (e) => {
  const gomb = e.target.closest('[data-muvelet]');
  if (!gomb) return;
  const m = gomb.dataset.muvelet;
  if (m === 'menu') document.body.classList.toggle('menu-nyitva');
  if (m === 'kilepes') { await api('POST', '/api/v1/kilepes'); location.href = '/belepes'; }
  if (m === 'zarolas') { await api('POST', '/api/v1/zarolas'); location.href = '/'; }
});

async function indul() {
  await allapotFrissit();
  setInterval(fejlecFrissit, 1000);
  setInterval(allapotFrissit, 1500);
  const main = $('#tartalom');
  oldal = OLDALAK[OLDAL.oldal];
  if (!oldal) return;
  if (OLDAL.vedett && OLDAL.pin && !OLDAL.feloldva) {
    try {
      await pinKeres();
    } catch (_) {
      main.replaceChildren(kartya('Zárolva', el('p', { text: 'Ez az oldal PIN-kóddal védett.' }), el('button', { class: 'gomb fo', text: 'Feloldás', onclick: () => location.reload() })));
      oldal = null;
      return;
    }
  }
  try {
    await oldal.init(main);
  } catch (e) {
    main.replaceChildren(kartya('Hiba', el('p', { text: e.message })));
  }
}

indul();

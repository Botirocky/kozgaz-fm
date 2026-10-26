"use strict";

const API = "/api/v1";
const FRISSITES_MS = 2000;
const $ = (id) => document.getElementById(id);

let allapot = null;
let allapotIdeje = 0;
let idozito = null;
let hangeroKuldes = null;
let uzenetIdozito = null;
let sablonTorles = false;
let statIdeje = 0;
const STAT_MS = 60000;
const HALK_CSENGO = 30;

class BelepesKell extends Error {}

async function keres(metodus, ut, adat) {
  const opciok = { method: metodus, headers: { "X-Kozgaz-FM": "1" }, credentials: "same-origin", cache: "no-store" };
  if (adat !== undefined) {
    opciok.headers["Content-Type"] = "application/json";
    opciok.body = JSON.stringify(adat);
  }
  const valasz = await fetch(API + ut, opciok);
  if (valasz.status === 204) return null;
  let tartalom = null;
  try {
    tartalom = await valasz.json();
  } catch {
    tartalom = null;
  }
  if (valasz.ok) return tartalom ? tartalom.data : null;
  const uzenet = tartalom && tartalom.error ? tartalom.error.message : `Hiba (${valasz.status})`;
  if (valasz.status === 401 && ut !== "/munkamenet") throw new BelepesKell(uzenet);
  throw new Error(uzenet);
}

function uzenet(szoveg, hibas = false) {
  const doboz = $("uzenet");
  doboz.textContent = szoveg;
  doboz.classList.toggle("hibas", hibas);
  doboz.classList.add("latszik");
  clearTimeout(uzenetIdozito);
  uzenetIdozito = setTimeout(() => doboz.classList.remove("latszik"), hibas ? 5000 : 2600);
}

function belepesMutat() {
  clearInterval(idozito);
  idozito = null;
  $("panel").hidden = true;
  $("belepes").hidden = false;
  $("jelszo").focus();
}

function panelMutat() {
  $("belepes").hidden = true;
  $("panel").hidden = false;
  frissit();
  if (!idozito) idozito = setInterval(frissit, FRISSITES_MS);
}

async function frissit() {
  try {
    megjelenit(await keres("GET", "/allapot"));
    if (Date.now() - statIdeje > STAT_MS) {
      statIdeje = Date.now();
      keres("GET", "/statisztika").then(statisztika).catch(() => { statIdeje = 0; });
    }
    $("kapcsolat").classList.remove("nincs");
    $("kapcsolat").title = "Kapcsolódva a hangosító géphez";
  } catch (e) {
    if (e instanceof BelepesKell) {
      belepesMutat();
      return;
    }
    $("kapcsolat").classList.add("nincs");
    $("kapcsolat").title = "Nincs kapcsolat a hangosító géppel";
  }
}

async function muvelet(metodus, ut, adat, siker) {
  try {
    const uj = await keres(metodus, ut, adat);
    if (uj) megjelenit(uj);
    if (siker) uzenet(siker);
    return true;
  } catch (e) {
    if (e instanceof BelepesKell) belepesMutat();
    else uzenet(e.message, true);
    return false;
  }
}

function idoszoveg(mp) {
  mp = Math.max(0, Math.round(mp));
  const ora = Math.floor(mp / 3600);
  const perc = Math.floor((mp % 3600) / 60);
  const masodperc = String(mp % 60).padStart(2, "0");
  return ora ? `${ora}:${String(perc).padStart(2, "0")}:${masodperc}` : `${perc}:${masodperc}`;
}

function ketjegyu(n) {
  return String(n).padStart(2, "0");
}

function orat() {
  const most = new Date();
  $("ora").textContent = `${ketjegyu(most.getHours())}:${ketjegyu(most.getMinutes())}`;
  if (!allapot) return;
  if (allapot.hatra_mp === null) {
    $("hatra").textContent = "–";
    $("halad").style.width = "0";
    return;
  }
  const hatra = allapot.hatra_mp - (Date.now() - allapotIdeje) / 1000;
  $("hatra").textContent = idoszoveg(hatra);
  if (allapot.hossz_mp) {
    const arany = 1 - Math.max(0, hatra) / allapot.hossz_mp;
    $("halad").style.width = `${Math.min(100, Math.max(0, arany * 100)).toFixed(1)}%`;
  }
}

function opciok(select, elemek, kivalasztott) {
  const kulcs = JSON.stringify(elemek);
  if (select.dataset.kulcs !== kulcs) {
    select.replaceChildren(...elemek.map(([ertek, szoveg]) => new Option(szoveg, ertek)));
    select.dataset.kulcs = kulcs;
  }
  if (document.activeElement !== select) select.value = kivalasztott;
}

function megjelenit(a) {
  allapot = a;
  allapotIdeje = Date.now();
  document.title = a.riasztas ? "RIASZTÁS – Közgáz FM" : `${a.szakasz} – Közgáz FM`;
  $("cim").textContent = a.cim || "Közgáz FM";
  $("verzio").textContent = `Közgáz FM ${a.verzio}`;
  $("szakasz").textContent = a.szakasz;
  $("mire").textContent = a.hatra_mire;
  $("kovetkezo").textContent = a.kovetkezo
    ? `Következő: ${a.kovetkezo.nap} ${a.kovetkezo.ido}, ${a.kovetkezo.leiras}`
    : "A következő két hétben nincs csengetés";
  $("riasztas-sav").hidden = !a.riasztas;
  const riasztoGomb = $("riasztas-gomb");
  riasztoGomb.dataset.muvelet = a.riasztas ? "riasztas-le" : "riasztas";
  riasztoGomb.textContent = a.riasztas ? "Riasztás leállítása" : "Riasztás indítása";

  const elo = $("elo");
  const eloSzoveg = a.riasztas ? "" : a.bemondas_szol ? "Bemondás szól" : a.csengo_szol ? "Csengő szól" : "";
  elo.hidden = !eloSzoveg;
  elo.textContent = eloSzoveg;

  const hangok = $("hangok");
  const hangKulcs = JSON.stringify(a.hangok);
  if (hangok.dataset.kulcs !== hangKulcs) {
    hangok.dataset.kulcs = hangKulcs;
    hangok.replaceChildren(...a.hangok.filter((h) => h.azonosito !== "becsengo").map((h) => {
      const g = document.createElement("button");
      g.type = "button";
      g.className = "gomb";
      g.dataset.muvelet = "csengetes";
      g.dataset.hang = h.azonosito;
      g.textContent = h.nev;
      return g;
    }));
  }

  const z = a.zene;
  const szam = $("zene-szam");
  szam.textContent = z.szol ? z.cim || "Szünetzene szól" : "Nem szól zene";
  szam.title = z.szol && z.blokk ? `Műsorblokk: ${z.blokk}` : "";
  szam.classList.toggle("csend", !z.szol);
  $("zene-gomb").textContent = z.szol ? "Zene leállítása" : "Zene indítása";
  $("kovetkezo-gomb").disabled = !z.szol;
  const forrasok = z.forrasok.map((f) => [String(f.index), f.nev]);
  if (!forrasok.length) forrasok.push(["", "Nincs zeneforrás beállítva"]);
  opciok($("forras"), forrasok, z.forras === null ? "" : String(z.forras));
  if (document.activeElement !== $("hangero") && hangeroKuldes === null) {
    $("hangero").value = z.hangero;
    $("hangero-ertek").textContent = `${z.hangero}%`;
  }

  zenesor(z.sor);
  keresek(a.zenekeres);
  sablonok(a.sablonok);
  $("csend-sav").hidden = !a.csend;
  $("csend-indito").hidden = !!a.csend;
  if (a.csend) {
    $("csend-szoveg").textContent = `Csendes időszak ${a.csend.ig}-ig, ${a.csend.halk ? "halk" : "néma"} csengővel`;
  }

  $("bemondas-stop").hidden = !a.bemondas_szol;
  $("ma-csengetes").checked = a.ma.csengetes;
  $("ma-zene").checked = a.ma.zene;
  opciok($("ma-rend"), [["", "Szokásos (heti beosztás)"], ...a.ma.rendek.map((r) => [r, r])], a.ma.rend);

  menetrend(a.menetrend);
  orat();
}

function percSzoveg(perc) {
  if (perc < 60) return `${perc} perc`;
  return perc % 60 ? `${Math.floor(perc / 60)} óra ${perc % 60} perc` : `${perc / 60} óra`;
}

function statisztika(s) {
  const dl = $("stat-szamok");
  dl.replaceChildren();
  const c = s.csengetes;
  const sorok = [
    ["Zene", `${percSzoveg(s.zene.perc)}, ${s.zene.szamok} szám`],
    ["Kért számok", `${s.zene.kert} (érkezett: ${s.keresek.erkezett})`],
    ["Csengetések", `${c.darab}${c.kezi ? `, ebből ${c.kezi} kézi` : ""}`],
    ["Pontosság", c.atlag_keses_ms === null ? "–" : `átlag ${(c.atlag_keses_ms / 1000).toFixed(1).replace(".", ",")} mp`
      + (c.kesett ? `, ${c.kesett} késett` : "")],
  ];
  for (const [cim, ertek] of sorok) {
    const dt = document.createElement("dt");
    dt.textContent = cim;
    const dd = document.createElement("dd");
    dd.textContent = ertek;
    dl.append(dt, dd);
  }
  const ol = $("stat-top");
  ol.replaceChildren();
  for (const t of s.legtobbet) {
    const li = document.createElement("li");
    li.textContent = `${t.cim} – ${t.darab}×`;
    ol.append(li);
  }
  if (!s.legtobbet.length) {
    const li = document.createElement("li");
    li.textContent = "A héten még nem szólt zene.";
    li.className = "ures";
    ol.append(li);
  }
}

function menetrend(esemenyek) {
  const lista = $("menetrend");
  const kulcs = JSON.stringify(esemenyek);
  if (lista.dataset.kulcs === kulcs) return;
  lista.dataset.kulcs = kulcs;
  if (!esemenyek.length) {
    const li = document.createElement("li");
    li.className = "ures";
    li.textContent = "Ma nincs csengetés.";
    lista.replaceChildren(li);
    return;
  }
  let kovetkezoVolt = false;
  let kovetkezoElem = null;
  lista.replaceChildren(...esemenyek.map((e) => {
    const li = document.createElement("li");
    li.classList.add(e.tipus);
    if (e.mult) li.classList.add("mult");
    else if (!kovetkezoVolt) {
      kovetkezoVolt = true;
      li.classList.add("kovetkezo-sor");
      kovetkezoElem = li;
    }
    const ido = document.createElement("time");
    ido.textContent = e.ido;
    const leiras = document.createElement("span");
    leiras.textContent = e.leiras;
    li.append(ido, leiras);
    return li;
  }));
  if (kovetkezoElem) {
    const elotte = kovetkezoElem.previousElementSibling?.previousElementSibling || lista.firstElementChild;
    lista.scrollTop = elotte.offsetTop;
  }
  lista.classList.toggle("gorgetett", lista.scrollTop > 2);
}

function zenesor(sor) {
  const lista = $("zenesor");
  const kulcs = JSON.stringify(sor);
  $("zenesor-blokk").hidden = !sor.length;
  if (lista.dataset.kulcs === kulcs) return;
  lista.dataset.kulcs = kulcs;
  lista.replaceChildren(...sor.map((s) => {
    const li = document.createElement("li");
    const g = document.createElement("button");
    g.type = "button";
    g.className = "zenesor-elem";
    g.dataset.muvelet = "ugras";
    g.dataset.index = s.index;
    g.dataset.cim = s.cim;
    g.title = "Lejátszás most";
    g.textContent = s.cim;
    li.append(g);
    return li;
  }));
}

function keresek(zk) {
  $("keresek-blokk").hidden = !zk.aktiv && !zk.keresek.length;
  $("keresek-ures").hidden = zk.keresek.length > 0;
  const lista = $("keresek");
  const kulcs = JSON.stringify(zk.keresek);
  if (lista.dataset.kulcs === kulcs) return;
  lista.dataset.kulcs = kulcs;
  lista.replaceChildren(...zk.keresek.map((k) => {
    const li = document.createElement("li");
    const cim = document.createElement(k.link ? "a" : "strong");
    cim.textContent = k.cim || k.szoveg;
    if (k.link) {
      cim.href = k.link;
      cim.target = "_blank";
      cim.rel = "noopener noreferrer";
    }
    const meta = document.createElement("p");
    meta.className = "keres-meta";
    const hossz = k.hossz ? `${Math.floor(k.hossz / 60)}:${String(k.hossz % 60).padStart(2, "0")}` : "";
    meta.textContent = [k.ido, k.nev, hossz, k.cim && k.cim !== k.szoveg ? `kérés: „${k.szoveg}”` : ""]
      .filter(Boolean).join(" · ");
    li.append(cim, meta);
    if (k.allapot === "kereses") {
      const var_ = document.createElement("p");
      var_.className = "keres-meta";
      var_.textContent = "Keresés a YouTube-on…";
      li.append(var_);
    } else {
      const sor = document.createElement("div");
      sor.className = "sor";
      for (const [szoveg, elfogad, osztaly] of [["Elfogadás", true, "gomb fo"], ["Elutasítás", false, "gomb"]]) {
        const g = document.createElement("button");
        g.type = "button";
        g.className = osztaly;
        g.dataset.muvelet = "dontes";
        g.dataset.azon = k.azon;
        g.dataset.elfogad = String(elfogad);
        g.textContent = szoveg;
        sor.append(g);
      }
      li.append(sor);
    }
    return li;
  }));
}

function sablonok(lista) {
  const doboz = $("sablonok");
  const kulcs = JSON.stringify([lista, sablonTorles]);
  if (doboz.dataset.kulcs === kulcs) return;
  doboz.dataset.kulcs = kulcs;
  doboz.classList.toggle("torles", sablonTorles);
  $("sablon-szerkesztes").textContent = sablonTorles ? "Kész" : "Sablonok törlése";
  $("sablon-szerkesztes").setAttribute("aria-pressed", String(sablonTorles));
  $("sablon-szerkesztes").hidden = !lista.length;
  doboz.replaceChildren(...lista.map((szoveg, i) => {
    const g = document.createElement("button");
    g.type = "button";
    g.className = "sablon";
    g.dataset.muvelet = sablonTorles ? "sablon-torles" : "sablon";
    g.dataset.index = i;
    g.title = sablonTorles ? "Sablon törlése" : szoveg;
    g.textContent = szoveg;
    return g;
  }));
}

function riasztasKerdes() {
  const ablak = $("megerosites");
  ablak.returnValue = "";
  ablak.showModal();
  ablak.addEventListener("close", () => {
    if (ablak.returnValue === "igen") muvelet("POST", "/riasztas", undefined, "Riasztás elindítva");
  }, { once: true });
}

document.addEventListener("click", (esemeny) => {
  const gomb = esemeny.target.closest("[data-muvelet]");
  if (!gomb) return;
  switch (gomb.dataset.muvelet) {
    case "csengetes":
      muvelet("POST", "/csengetes", { hang: gomb.dataset.hang }, `${gomb.textContent === "Csengetés most" ? "Csengetés" : gomb.textContent} elküldve`);
      break;
    case "zene":
      if (allapot && allapot.zene.szol) muvelet("POST", "/zene/leallitas", undefined, "Zene leállítva");
      else muvelet("POST", "/zene/inditas", undefined, "Zene indul");
      break;
    case "kovetkezo":
      muvelet("POST", "/zene/kovetkezo", undefined, "Következő szám");
      break;
    case "bemondas-le":
      muvelet("DELETE", "/bemondas", undefined, "Bemondás leállítva");
      break;
    case "riasztas":
      riasztasKerdes();
      break;
    case "riasztas-le":
      muvelet("DELETE", "/riasztas", undefined, "Riasztás leállítva");
      break;
    case "dontes": {
      const elfogad = gomb.dataset.elfogad === "true";
      muvelet("POST", "/zenekeres/dontes", { azon: gomb.dataset.azon, elfogad }, elfogad ? "Kérés elfogadva" : "Kérés elutasítva");
      break;
    }
    case "ugras":
      muvelet("POST", "/zene/ugras", { index: Number(gomb.dataset.index), cim: gomb.dataset.cim }, "Szám indul");
      break;
    case "sablon":
      $("bemondas-szoveg").value = allapot.sablonok[Number(gomb.dataset.index)] || "";
      $("bemondas-szoveg").focus();
      break;
    case "sablon-mentes": {
      const szoveg = $("bemondas-szoveg").value.trim();
      if (!szoveg) {
        uzenet("Előbb írd be a szöveget.", true);
        break;
      }
      if (allapot.sablonok.includes(szoveg)) {
        uzenet("Ez már szerepel a sablonok között.");
        break;
      }
      muvelet("PUT", "/bemondas/sablonok", { sablonok: [...allapot.sablonok, szoveg] }, "Sablon elmentve");
      break;
    }
    case "sablon-szerkesztes":
      sablonTorles = !sablonTorles;
      sablonok(allapot.sablonok);
      break;
    case "sablon-torles": {
      const szoveg = allapot.sablonok[Number(gomb.dataset.index)];
      if (szoveg === undefined || !confirm(`Törlöd ezt a sablont?\n\n${szoveg}`)) break;
      muvelet("PUT", "/bemondas/sablonok", { sablonok: allapot.sablonok.filter((s) => s !== szoveg) }, "Sablon törölve");
      break;
    }
    case "csend":
      muvelet("POST", "/csend", { perc: Number($("csend-perc").value), hangero: $("csend-halk").checked ? HALK_CSENGO : 0 },
        "Csendes időszak elindítva");
      break;
    case "csend-le":
      muvelet("DELETE", "/csend", undefined, "Csendes időszak befejezve");
      break;
    case "kilepes":
      keres("DELETE", "/munkamenet").catch(() => {}).finally(belepesMutat);
      break;
  }
});

$("belepes-urlap").addEventListener("submit", async (esemeny) => {
  esemeny.preventDefault();
  const hiba = $("belepes-hiba");
  hiba.textContent = "";
  const gomb = esemeny.submitter || esemeny.target.querySelector("button");
  gomb.disabled = true;
  try {
    await keres("POST", "/munkamenet", { jelszo: $("jelszo").value });
    $("jelszo").value = "";
    panelMutat();
  } catch (e) {
    hiba.textContent = e.message;
    $("jelszo").select();
  } finally {
    gomb.disabled = false;
  }
});

$("bemondas-urlap").addEventListener("submit", async (esemeny) => {
  esemeny.preventDefault();
  const mezo = $("bemondas-szoveg");
  const szoveg = mezo.value.trim();
  if (!szoveg) {
    uzenet("Írd be, mit olvasson fel a rendszer.", true);
    mezo.focus();
    return;
  }
  if (await muvelet("POST", "/bemondas", { szoveg, gong: $("gong").checked }, "Bemondás elküldve")) mezo.value = "";
});

$("menetrend").addEventListener("scroll", (e) => {
  e.target.classList.toggle("gorgetett", e.target.scrollTop > 2);
}, { passive: true });

$("forras").addEventListener("change", (e) => {
  if (e.target.value !== "") muvelet("PATCH", "/zene", { forras: Number(e.target.value) }, "Zeneforrás átállítva");
});

$("hangero").addEventListener("input", (e) => {
  $("hangero-ertek").textContent = `${e.target.value}%`;
  clearTimeout(hangeroKuldes);
  hangeroKuldes = setTimeout(() => {
    hangeroKuldes = null;
    muvelet("PATCH", "/zene", { hangero: Number(e.target.value) });
  }, 250);
});

$("ma-csengetes").addEventListener("change", (e) => {
  muvelet("PATCH", "/ma", { csengetes: e.target.checked }, e.target.checked ? "Ma lesz csengetés" : "Ma nincs csengetés");
});

$("ma-zene").addEventListener("change", (e) => {
  muvelet("PATCH", "/ma", { zene: e.target.checked }, e.target.checked ? "Ma lesz szünetzene" : "Ma nincs szünetzene");
});

$("ma-rend").addEventListener("change", (e) => {
  muvelet("PATCH", "/ma", { rend: e.target.value }, "Mai csengetési rend átállítva");
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && !$("panel").hidden) frissit();
});

setInterval(orat, 1000);

keres("GET", "/munkamenet")
  .then((adat) => (adat && adat.belepve ? panelMutat() : belepesMutat()))
  .catch(belepesMutat);

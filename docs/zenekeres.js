"use strict";

const SZERVER = "https://kozgazfm-zenekeres.kozgazfm-zenekeres-worker.workers.dev";
const API = `${SZERVER}/api/zenekeres`;
const FOLYAMATBAN = ["kereses", "varakozik", "elfogadva"];
const MAX_POTTY = 8;

function eszkozAzon() {
  let azon = "";
  try { azon = localStorage.getItem("kfm-eszkoz") || ""; } catch { azon = ""; }
  if (!/^[0-9a-f]{64}$/.test(azon)) {
    const bajtok = new Uint8Array(32);
    crypto.getRandomValues(bajtok);
    azon = Array.from(bajtok, (b) => b.toString(16).padStart(2, "0")).join("");
    try { localStorage.setItem("kfm-eszkoz", azon); } catch { }
  }
  return azon;
}
const $ = (id) => document.getElementById(id);
let uzenetIdozito = null;
let idozito = null;
let autoMod = false;
let betoltve = false;
let sajatKulcs = "";
let sorKulcs = "";

function elem(nev, osztaly, szoveg) {
  const e = document.createElement(nev);
  if (osztaly) e.className = osztaly;
  if (szoveg !== undefined) e.textContent = szoveg;
  return e;
}

async function keres(metodus, adat) {
  const opciok = { method: metodus, headers: { "X-Kozgaz-FM": "1", "X-Kozgaz-FM-Eszkoz": eszkozAzon() }, credentials: "omit", cache: "no-store" };
  if (adat !== undefined) {
    opciok.headers["Content-Type"] = "application/json";
    opciok.body = JSON.stringify(adat);
  }
  let valasz;
  try {
    valasz = await fetch(API, opciok);
  } catch {
    throw new Error("Az iskolarádió szervere most nem érhető el. Próbáld újra később.");
  }
  let tartalom = null;
  try {
    tartalom = await valasz.json();
  } catch {
    tartalom = null;
  }
  if (valasz.ok) return tartalom ? tartalom.data : null;
  throw new Error(tartalom && tartalom.error ? tartalom.error.message : `Hiba (${valasz.status})`);
}

function uzenet(szoveg, hibas = false) {
  const doboz = $("uzenet");
  doboz.textContent = szoveg;
  doboz.classList.toggle("hibas", hibas);
  doboz.classList.add("latszik");
  clearTimeout(uzenetIdozito);
  uzenetIdozito = setTimeout(() => doboz.classList.remove("latszik"), hibas ? 6000 : 3500);
}

function allapotSzoveg(k) {
  if (k.ok) return `${k.allapot_nev}: ${k.ok}`;
  if (k.hely === 1) return "Következő szám";
  if (k.hely > 1) return `${k.hely}. a sorban`;
  return k.allapot_nev;
}

function sajatElem(k) {
  const li = elem("li", `keres ${k.allapot}`);
  const fej = elem("div", "keres-fej");
  fej.append(elem("strong", "", k.cim || k.szoveg), elem("time", "", k.ido));
  const allapot = elem("p", "keres-allapot");
  const jel = elem("span", k.allapot === "szol" ? "hangsav" : "jel");
  jel.setAttribute("aria-hidden", "true");
  if (k.allapot === "szol") jel.append(elem("i"), elem("i"), elem("i"));
  allapot.append(jel, elem("span", "", allapotSzoveg(k)));
  li.append(fej, allapot);
  return li;
}

async function szavaz(gomb, azon) {
  if (gomb.getAttribute("aria-busy") === "true") return;
  gomb.setAttribute("aria-busy", "true");
  try {
    megjelenit(await keres("POST", { szavaz: azon }));
  } catch (e) {
    uzenet(e.message, true);
    gomb.removeAttribute("aria-busy");
  }
}

function sorElem(k, maradek) {
  const li = elem("li", "sor-elem");
  const hely = elem("span", "hely", k.hely ? `${k.hely}.` : "–");
  if (!k.hely) hely.setAttribute("aria-hidden", "true");
  const cim = elem("strong", "", k.cim);
  li.append(hely, cim);
  if (k.sajat) {
    const sajat = elem("span", "sajat-jelzo");
    sajat.append(elem("span", "sajat-szam", String(k.szavazat)), elem("span", "", "a tiéd"));
    sajat.setAttribute("role", "img");
    sajat.setAttribute("aria-label", `A te kérésed, ${k.szavazat} szavazat`);
    li.append(sajat);
    return li;
  }
  const gomb = elem("button", `szavaz${k.szavaztam ? " aktiv" : ""}`);
  gomb.type = "button";
  gomb.dataset.azon = k.azon;
  const nyil = elem("span", "nyil");
  nyil.setAttribute("aria-hidden", "true");
  gomb.append(nyil, elem("span", "", String(k.szavazat)));
  gomb.disabled = !k.szavaztam && !maradek;
  gomb.setAttribute("aria-pressed", String(k.szavaztam));
  gomb.setAttribute("aria-label", `${k.szavaztam ? "Szavazat visszavonása" : "Szavazok rá"}: ${k.cim}, ${k.szavazat} szavazat`);
  gomb.addEventListener("click", () => szavaz(gomb, k.azon));
  li.append(gomb);
  return li;
}

function megjelenit(a) {
  betoltve = true;
  $("betolt").hidden = true;
  $("hiba").hidden = true;
  $("kapcsolat").hidden = true;
  $("cim").textContent = a.cim || "Közgáz FM";
  autoMod = a.auto;
  $("leiras").textContent = a.auto
    ? "Ha a szám rendben van, magától bekerül a szünetzenébe."
    : "Jóváhagyás után a következő szünetek egyikében szól.";
  $("szabaly-napi").textContent = `Naponta ${a.napi} számot kérhetsz, legfeljebb ${a.max_perc} perceset.`;
  $("kikapcsolva").hidden = a.aktiv;
  $("kikapcsolva-szoveg").textContent = a.elerheto
    ? "A zenekérés most nincs bekapcsolva. Nézz vissza később!"
    : "Az iskolarádió most nem elérhető (például tanítási időn kívül). Nézz vissza később!";
  $("urlap").hidden = !a.aktiv;
  const maradek = $("maradek");
  maradek.textContent = a.maradek
    ? `Ma még ${a.maradek} számot kérhetsz.`
    : "Mára elfogytak a kéréseid, holnap újra kérhetsz.";
  if (a.tiltva) maradek.textContent = "Erről a telefonról most nem kérhetsz számot.";
  const pottyok = $("pottyok");
  pottyok.hidden = a.tiltva || a.napi > MAX_POTTY;
  pottyok.replaceChildren(...Array.from({ length: Math.min(a.napi, MAX_POTTY) }, (_, i) => elem("i", i < a.maradek ? "van" : "")));
  $("kuld").disabled = !a.maradek || a.tiltva;

  const ujSajat = JSON.stringify(a.sajat);
  $("sajat-blokk").hidden = !a.sajat.length;
  if (ujSajat !== sajatKulcs) {
    sajatKulcs = ujSajat;
    $("sajat").replaceChildren(...a.sajat.map(sajatElem));
  }

  const sor = a.sor || [];
  const szavazatMaradek = a.szavazat_maradek ?? 0;
  $("sor-blokk").hidden = !sor.length && !a.aktiv;
  $("sor-ures").hidden = sor.length > 0;
  $("szavazat-maradek").hidden = !sor.length;
  $("szavazat-maradek").textContent = szavazatMaradek
    ? `Koppints a nyílra, ha te is hallanád. Ma még ${szavazatMaradek} szavazatod van, újra koppintva visszavonhatod.`
    : "Mára elfogytak a szavazataid. A leadottakat újra koppintva visszavonhatod.";
  const ujSor = JSON.stringify([sor, szavazatMaradek]);
  if (ujSor !== sorKulcs) {
    sorKulcs = ujSor;
    const fokusz = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.azon : "";
    $("sor").replaceChildren(...sor.map((k) => sorElem(k, szavazatMaradek)));
    if (fokusz) {
      const gomb = Array.from($("sor").querySelectorAll("button")).find((g) => g.dataset.azon === fokusz);
      if (gomb && !gomb.disabled) gomb.focus();
    }
  }

  const folyamatban = sor.length > 0 || a.sajat.some((k) => FOLYAMATBAN.includes(k.allapot));
  clearInterval(idozito);
  idozito = setInterval(frissit, folyamatban ? 4000 : 30000);
}

async function frissit() {
  if (document.hidden) return;
  try {
    megjelenit(await keres("GET"));
  } catch (e) {
    if (betoltve) {
      $("kapcsolat").hidden = false;
      return;
    }
    $("betolt").hidden = true;
    $("hiba-szoveg").textContent = e.message;
    $("hiba").hidden = false;
    clearInterval(idozito);
    idozito = setInterval(frissit, 10000);
  }
}

$("ujra").addEventListener("click", async () => {
  $("hiba").hidden = true;
  $("betolt").hidden = false;
  await frissit();
  if (!$("hiba").hidden) $("ujra").focus();
});

$("urlap").addEventListener("submit", async (esemeny) => {
  esemeny.preventDefault();
  const gomb = $("kuld");
  const szoveg = $("szoveg").value.trim();
  if (!szoveg) {
    $("szoveg").focus();
    return;
  }
  gomb.disabled = true;
  gomb.textContent = "Küldés…";
  try {
    megjelenit(await keres("POST", { szoveg, nev: $("nev").value.trim() }));
    $("szoveg").value = "";
    uzenet(autoMod ? "Kérés elküldve, ellenőrizzük a számot." : "Kérés elküldve, jóváhagyásra vár.");
  } catch (e) {
    uzenet(e.message, true);
    gomb.disabled = false;
  }
  gomb.textContent = "Kérés küldése";
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) frissit();
});

async function indul() {
  const parameterek = new URLSearchParams(location.search);
  const szam = parameterek.get("szam");
  await frissit();
  if (!szam) return;
  history.replaceState(null, "", location.pathname);
  $("szoveg").value = szam.slice(0, 150);
  if (!$("urlap").hidden && !$("kuld").disabled) $("urlap").requestSubmit();
}

indul();

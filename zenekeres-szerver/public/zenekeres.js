"use strict";

const API = "/api/zenekeres";
const $ = (id) => document.getElementById(id);
let uzenetIdozito = null;
let idozito = null;
let autoMod = false;

async function keres(metodus, adat) {
  const opciok = { method: metodus, headers: { "X-Kozgaz-FM": "1" }, credentials: "same-origin", cache: "no-store" };
  if (adat !== undefined) {
    opciok.headers["Content-Type"] = "application/json";
    opciok.body = JSON.stringify(adat);
  }
  let valasz;
  try {
    valasz = await fetch(API, opciok);
  } catch {
    throw new Error("Nincs internetkapcsolat, próbáld újra.");
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
  uzenetIdozito = setTimeout(() => doboz.classList.remove("latszik"), hibas ? 5000 : 3000);
}

function megjelenit(a) {
  $("betolt").hidden = true;
  $("cim").textContent = a.cim || "Közgáz FM";
  autoMod = a.auto;
  $("leiras").textContent = a.auto
    ? "Írd be a szám előadóját és címét, vagy másold be a YouTube-linkjét. Ha a szám rendben van, magától bekerül a szünetzenébe."
    : "Írd be a szám előadóját és címét, vagy másold be a YouTube-linkjét. Jóváhagyás után a következő szünetek egyikében szól.";
  $("szabaly-napi").textContent = `Naponta ${a.napi} számot kérhetsz, legfeljebb ${a.max_perc} perceset.`;
  const kikapcsolva = $("kikapcsolva");
  kikapcsolva.hidden = a.aktiv;
  kikapcsolva.textContent = a.elerheto
    ? "A zenekérés most nincs bekapcsolva. Nézz vissza később!"
    : "Az iskolarádió most nem elérhető (például tanítási időn kívül). Nézz vissza később!";
  $("urlap").hidden = !a.aktiv;
  const maradek = $("maradek");
  maradek.textContent = a.maradek
    ? `Ma még ${a.maradek} számot kérhetsz.`
    : "Mára elfogytak a kéréseid, holnap újra kérhetsz.";
  if (a.tiltva) maradek.textContent = "Erről a telefonról most nem kérhetsz számot.";
  $("urlap").querySelector("button").disabled = !a.maradek || a.tiltva;
  $("sajat-blokk").hidden = !a.sajat.length;
  $("sajat").replaceChildren(...a.sajat.map((k) => {
    const li = document.createElement("li");
    li.className = `elem ${k.allapot}`;
    const cim = document.createElement("strong");
    cim.textContent = k.cim || k.szoveg;
    const allapot = document.createElement("span");
    allapot.className = "allapot";
    allapot.textContent = k.ok ? `${k.allapot_nev}: ${k.ok}` : k.allapot_nev;
    const ido = document.createElement("time");
    ido.textContent = k.ido;
    li.append(cim, ido, allapot);
    return li;
  }));
  const folyamatban = a.sajat.some((k) => ["kereses", "varakozik", "elfogadva"].includes(k.allapot));
  clearInterval(idozito);
  idozito = setInterval(frissit, folyamatban ? 4000 : 30000);
}

async function frissit() {
  if (document.hidden) return;
  try {
    megjelenit(await keres("GET"));
  } catch (e) {
    $("betolt").textContent = e.message;
  }
}

$("urlap").addEventListener("submit", async (esemeny) => {
  esemeny.preventDefault();
  const gomb = esemeny.submitter || esemeny.target.querySelector("button");
  const szoveg = $("szoveg").value.trim();
  if (!szoveg) {
    $("szoveg").focus();
    return;
  }
  gomb.disabled = true;
  try {
    megjelenit(await keres("POST", { szoveg, nev: $("nev").value.trim() }));
    $("szoveg").value = "";
    uzenet(autoMod ? "Kérés elküldve, ellenőrizzük a számot." : "Kérés elküldve, jóváhagyásra vár.");
  } catch (e) {
    uzenet(e.message, true);
    gomb.disabled = false;
  }
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
  if (!$("urlap").hidden && !$("urlap").querySelector("button").disabled) $("urlap").requestSubmit();
}

indul();

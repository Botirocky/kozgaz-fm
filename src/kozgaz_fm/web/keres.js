"use strict";

const API = "/api/v1/zenekeres";
const $ = (id) => document.getElementById(id);
let uzenetIdozito = null;
let idozito = null;

async function keres(metodus, adat) {
  const opciok = { method: metodus, headers: { "X-Kozgaz-FM": "1" }, credentials: "same-origin", cache: "no-store" };
  if (adat !== undefined) {
    opciok.headers["Content-Type"] = "application/json";
    opciok.body = JSON.stringify(adat);
  }
  const valasz = await fetch(API, opciok);
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
  $("cim").textContent = a.cim || "Közgáz FM";
  $("kikapcsolva").hidden = a.aktiv;
  $("urlap").hidden = !a.aktiv;
  $("maradek").textContent = a.maradek
    ? `Ma még ${a.maradek} számot kérhetsz. Legfeljebb ${a.max_perc} perces szám kérhető.`
    : "Mára elfogytak a kéréseid, holnap újra kérhetsz.";
  $("urlap").querySelector("button").disabled = !a.maradek;
  $("sajat-blokk").hidden = !a.sajat.length;
  $("sajat").replaceChildren(...a.sajat.map((k) => {
    const li = document.createElement("li");
    li.className = `keres-elem ${k.allapot}`;
    const cim = document.createElement("strong");
    cim.textContent = k.cim || k.szoveg;
    const allapot = document.createElement("span");
    allapot.className = "keres-allapot";
    allapot.textContent = k.ok ? `${k.allapot_nev}: ${k.ok}` : k.allapot_nev;
    const ido = document.createElement("time");
    ido.textContent = k.ido;
    li.append(cim, allapot, ido);
    return li;
  }));
  const folyamatban = a.sajat.some((k) => ["kereses", "varakozik", "elfogadva"].includes(k.allapot));
  clearInterval(idozito);
  idozito = folyamatban ? setInterval(frissit, 5000) : null;
}

async function frissit() {
  try {
    megjelenit(await keres("GET"));
  } catch (e) {
    uzenet(e.message, true);
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
    uzenet("Kérés elküldve, jóváhagyásra vár.");
  } catch (e) {
    uzenet(e.message, true);
    gomb.disabled = false;
  }
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) frissit();
});

frissit();

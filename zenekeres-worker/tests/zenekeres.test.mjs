import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";

const CIM = process.env.KFM_WORKER_URL || "http://127.0.0.1:8787";
const KULCS = process.env.KFM_GEP_KULCS || "helyi-proba-kulcs-0123456789abcdef";
const ORIGIN = "https://botirocky.github.io";

const ujEszkoz = () => randomBytes(32).toString("hex");

async function diak(eszkoz, metodus = "GET", adat, extra = {}) {
  const r = await fetch(`${CIM}/api/zenekeres`, {
    method: metodus,
    headers: { Origin: ORIGIN, "X-Kozgaz-FM": "1", "X-Kozgaz-FM-Eszkoz": eszkoz, "Content-Type": "application/json", ...extra },
    body: adat === undefined ? undefined : JSON.stringify(adat),
  });
  return { statusz: r.status, fejlec: r.headers, test: await r.json() };
}

async function gepKor(beallitasok = {}, allapotok = [], kulcs = KULCS) {
  const r = await fetch(`${CIM}/api/gep`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Kozgaz-FM-Kulcs": kulcs },
    body: JSON.stringify({ beallitasok: { aktiv: true, auto: true, cim: "Közgáz FM", napi: 3, max_perc: 7, tiltott_telefonok: [], ...beallitasok }, allapotok, verzio: "teszt" }),
  });
  return { statusz: r.status, test: await r.json() };
}

test("rossz kulcs 401", async () => {
  const r = await gepKor({}, [], "rossz");
  assert.equal(r.statusz, 401);
  assert.equal(r.test.error.code, "unauthorized");
});

test("CORS előzetes kérés", async () => {
  const r = await fetch(`${CIM}/api/zenekeres`, { method: "OPTIONS", headers: { Origin: ORIGIN } });
  assert.equal(r.status, 204);
  assert.equal(r.headers.get("access-control-allow-origin"), ORIGIN);
});

test("idegen origin tiltva", async () => {
  const r = await fetch(`${CIM}/api/zenekeres`, { headers: { Origin: "https://gonosz.example", "X-Kozgaz-FM-Eszkoz": ujEszkoz() } });
  assert.equal(r.status, 403);
});

test("kikapcsolt zenekérés 409", async () => {
  await gepKor({ aktiv: false });
  const r = await diak(ujEszkoz(), "POST", { szoveg: "Valami", nev: "" });
  assert.equal(r.statusz, 409);
  assert.equal(r.test.error.code, "disabled");
});

test("teljes kör: kérés → gép → állapot vissza", async () => {
  await gepKor({ napi: 2 });
  const e = ujEszkoz();
  const elotte = await diak(e);
  assert.equal(elotte.test.data.aktiv, true);
  assert.equal(elotte.test.data.maradek, 2);
  const kuld = await diak(e, "POST", { szoveg: "  Wellhello   Apuveded ", nev: "Teszt" });
  assert.equal(kuld.statusz, 200);
  assert.equal(kuld.test.data.maradek, 1);
  const sajat = kuld.test.data.sajat[0];
  assert.equal(sajat.szoveg, "Wellhello Apuveded");
  assert.equal(sajat.allapot_nev, "Továbbítás a rádiónak…");
  assert.match(sajat.ido, /^\d\d:\d\d$/);

  const kor = await gepKor({ napi: 2 });
  const uj = kor.test.data.uj.find((k) => k.azon === sajat.azon);
  assert.ok(uj);
  assert.equal(uj.nev, "Teszt");
  assert.match(uj.ido, /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$/);

  const nyugta = await gepKor({ napi: 2 }, [{ azon: sajat.azon, allapot: "elfogadva", allapot_nev: "Elfogadva", cim: "Wellhello – Apuveded", ok: "", hely: 3 }]);
  assert.ok(!nyugta.test.data.uj.some((k) => k.azon === sajat.azon));
  const utana = await diak(e);
  assert.equal(utana.test.data.sajat[0].allapot_nev, "Elfogadva, hamarosan szól");
  assert.equal(utana.test.data.sajat[0].cim, "Wellhello – Apuveded");
  assert.equal(utana.test.data.sajat[0].hely, 3);
  await gepKor({ napi: 2 }, [{ azon: sajat.azon, allapot: "szol", allapot_nev: "Most szól", cim: "Wellhello – Apuveded", ok: "", hely: 1 }]);
  assert.equal((await diak(e)).test.data.sajat[0].hely, 0);
});

test("napi korlát", async () => {
  await gepKor({ napi: 1 });
  const e = ujEszkoz();
  assert.equal((await diak(e, "POST", { szoveg: "Első", nev: "" })).statusz, 200);
  const masodik = await diak(e, "POST", { szoveg: "Második", nev: "" });
  assert.equal(masodik.statusz, 429);
  assert.equal(masodik.test.error.code, "daily_limit");
});

test("csak YouTube-link", async () => {
  await gepKor();
  const r = await diak(ujEszkoz(), "POST", { szoveg: "https://example.com/zene", nev: "" });
  assert.equal(r.statusz, 422);
  assert.equal(r.test.error.code, "bad_link");
  const jo = await diak(ujEszkoz(), "POST", { szoveg: "youtu.be/dQw4w9WgXcQ", nev: "" });
  assert.equal(jo.statusz, 200);
});

test("X-Kozgaz-FM fejléc nélkül tiltva", async () => {
  await gepKor();
  const r = await diak(ujEszkoz(), "POST", { szoveg: "Valami", nev: "" }, { "X-Kozgaz-FM": "0" });
  assert.equal(r.statusz, 403);
});

test("zenék végpont 503", async () => {
  const r = await fetch(`${CIM}/api/zenek`, { headers: { "X-Kozgaz-FM-Kulcs": KULCS } });
  assert.equal(r.status, 503);
});

test("rádió elérhető", async () => {
  await gepKor();
  const r = await (await fetch(`${CIM}/egeszseg`)).json();
  assert.equal(r.data.radio, true);
  assert.equal(r.data.verzio, "teszt");
});

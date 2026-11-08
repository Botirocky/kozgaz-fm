const MAX_SZOVEG = 150;
const MAX_NEV = 30;
const MAX_VARAKOZO = 40;
const IP_ORANKENT = 20;
const GEP_ELAVULT_MP = 90;
const GEP_IRAS_MP = 30;
const ATADATLAN_LEJAR_MP = 7200;
const MEGORZES_NAP = 2;
const IDOZONA = "Europe/Budapest";
const YOUTUBE_GAZDAK = ["youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"];
const ERVENYES_ALLAPOTOK = ["kereses", "varakozik", "elfogadva", "szol", "elutasitva", "levett"];
const GEP_ALAP = { aktiv: false, auto: true, cim: "Közgáz FM", napi: 3, max_perc: 7, tiltott_telefonok: [], utolso: 0, verzio: "" };

class KeresHiba extends Error {
  constructor(statusz, kod, uzenet) {
    super(uzenet);
    this.statusz = statusz;
    this.kod = kod;
  }
}

const most = () => Math.floor(Date.now() / 1000);

const reszek = (ts) => {
  const r = {};
  for (const p of new Intl.DateTimeFormat("en-GB", {
    timeZone: IDOZONA, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(new Date(ts * 1000))) {
    r[p.type] = p.value;
  }
  return r;
};

const ma = () => {
  const r = reszek(most());
  return `${r.year}-${r.month}-${r.day}`;
};

const oraPerc = (ts) => {
  const r = reszek(ts);
  return `${r.hour}:${r.minute}`;
};

const isoIdo = (ts) => {
  const r = reszek(ts);
  const helyi = Date.UTC(+r.year, +r.month - 1, +r.day, +r.hour, +r.minute, +r.second) / 1000;
  const elteres = Math.round((helyi - ts) / 60);
  const elojel = elteres < 0 ? "-" : "+";
  const a = Math.abs(elteres);
  const ketto = (n) => String(n).padStart(2, "0");
  return `${r.year}-${r.month}-${r.day}T${r.hour}:${r.minute}:${r.second}${elojel}${ketto(Math.floor(a / 60))}:${ketto(a % 60)}`;
};

const szokoz = (s) => s.replace(/\s+/gu, " ").trim();
const hossz = (s) => Array.from(s).length;
const vag = (s, n) => Array.from(String(s)).slice(0, n).join("");

const hex = (puffer) => Array.from(new Uint8Array(puffer), (b) => b.toString(16).padStart(2, "0")).join("");
const sha256 = async (s) => hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)));

const telefonKulcs = async (eszkoz) => (await sha256(eszkoz)).slice(0, 32);

const veletlenAzon = () => {
  const b = new Uint8Array(9);
  crypto.getRandomValues(b);
  return btoa(String.fromCharCode(...b)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

function youtubeEllenoriz(szoveg) {
  const kis = szoveg.toLowerCase();
  const gazdaEleje = YOUTUBE_GAZDAK.some((g) => kis.startsWith(g));
  if (!szoveg.includes("://") && !gazdaEleje) {
    return;
  }
  const hibas = new KeresHiba(422, "bad_link", "Csak YouTube-link vagy a szám címe adható meg.");
  let url;
  try {
    url = new URL(szoveg.includes("://") ? szoveg : `https://${szoveg}`);
  } catch {
    throw hibas;
  }
  if (!["http:", "https:"].includes(url.protocol) || !YOUTUBE_GAZDAK.includes(url.hostname.toLowerCase())) {
    throw hibas;
  }
}

async function ertek(db, kulcs, alap) {
  const sor = await db.prepare("SELECT ertek FROM ertekek WHERE kulcs = ?").bind(kulcs).first();
  return sor ? JSON.parse(sor.ertek) : alap;
}

async function gep(db) {
  const g = await ertek(db, "gep", {});
  return { ...GEP_ALAP, ...(g && typeof g === "object" ? g : {}) };
}

const gepElerheto = (g) => most() - Number(g.utolso) <= GEP_ELAVULT_MP;

const MAI_SZAM_SQL = "SELECT COUNT(*) AS n FROM keresek WHERE eszkoz = ? AND nap = ? AND NOT (allapot = 'elutasitva' AND ok <> '')";
const IP_SQL = "SELECT COUNT(*) AS n FROM keresek WHERE ip = ? AND ido >= ?";
const SOR_SQL = "SELECT COUNT(*) AS n FROM keresek WHERE allapot IN ('kereses', 'varakozik')";

const szam = async (db, sql, ...p) => Number((await db.prepare(sql).bind(...p).first()).n);

function nyilvanos(k) {
  const nevek = {
    kereses: k.atadva ? "Keresés és ellenőrzés…" : "Továbbítás a rádiónak…",
    varakozik: "Jóváhagyásra vár",
    elfogadva: "Elfogadva, hamarosan szól",
    szol: "Most szól",
    elutasitva: "Elutasítva",
    levett: "Levették a sorból",
  };
  return {
    azon: k.azon,
    szoveg: k.szoveg,
    cim: k.cim,
    allapot: k.allapot,
    allapot_nev: nevek[k.allapot] ?? (k.allapot_nev || k.allapot),
    ok: k.ok,
    hely: k.allapot === "elfogadva" ? Number(k.hely) | 0 : 0,
    ido: oraPerc(Number(k.ido)),
  };
}

async function diakAllapot(db, eszkoz) {
  const g = await gep(db);
  const elerheto = gepElerheto(g);
  const napi = Math.max(1, Number(g.napi) | 0);
  const nap = ma();
  const [sajat, mai] = await Promise.all([
    db.prepare("SELECT * FROM keresek WHERE eszkoz = ? AND nap = ? ORDER BY ido DESC LIMIT 30").bind(eszkoz, nap).all(),
    szam(db, MAI_SZAM_SQL, eszkoz, nap),
  ]);
  return {
    aktiv: elerheto && Boolean(g.aktiv),
    elerheto,
    auto: Boolean(g.auto),
    cim: String(g.cim),
    napi,
    maradek: Math.max(0, napi - mai),
    max_perc: Number(g.max_perc) | 0,
    tiltva: (g.tiltott_telefonok || []).includes(await telefonKulcs(eszkoz)),
    sajat: sajat.results.map(nyilvanos),
  };
}

async function korlatHiba(db, eszkoz, ip, napi) {
  if (await szam(db, MAI_SZAM_SQL, eszkoz, ma()) >= napi) {
    return new KeresHiba(429, "daily_limit", `Ma már nem kérhetsz több számot (napi ${napi}).`);
  }
  if (await szam(db, IP_SQL, ip, most() - 3600) >= IP_ORANKENT) {
    return new KeresHiba(429, "rate_limited", "Erről a hálózatról most túl sok kérés jött, próbáld később.");
  }
  if (await szam(db, SOR_SQL) >= MAX_VARAKOZO) {
    return new KeresHiba(429, "queue_full", "Most túl sok kérés vár, próbáld később.");
  }
  return null;
}

async function ujKeres(db, eszkoz, ip, nyersSzoveg, nyersNev) {
  if (typeof nyersSzoveg !== "string" || typeof nyersNev !== "string") {
    throw new KeresHiba(422, "validation_error", "Hibás kérés.");
  }
  const g = await gep(db);
  if (!gepElerheto(g)) {
    throw new KeresHiba(503, "offline", "Az iskolarádió most nem elérhető, próbáld később.");
  }
  if (!g.aktiv) {
    throw new KeresHiba(409, "disabled", "A zenekérés most nincs bekapcsolva.");
  }
  const szoveg = szokoz(nyersSzoveg);
  const nev = szokoz(nyersNev);
  if (szoveg === "") {
    throw new KeresHiba(422, "validation_error", "Írd be a szám címét vagy a YouTube-linkjét.");
  }
  if (hossz(szoveg) > MAX_SZOVEG || hossz(nev) > MAX_NEV) {
    throw new KeresHiba(422, "validation_error", `Legfeljebb ${MAX_SZOVEG} karakter lehet a kérés, ${MAX_NEV} a név.`);
  }
  youtubeEllenoriz(szoveg);
  if ((g.tiltott_telefonok || []).includes(await telefonKulcs(eszkoz))) {
    throw new KeresHiba(403, "device_blocked", "Erről a telefonról most nem kérhetsz számot.");
  }
  const napi = Math.max(1, Number(g.napi) | 0);
  const elozetes = await korlatHiba(db, eszkoz, ip, napi);
  if (elozetes) {
    throw elozetes;
  }
  const t = most();
  const nap = ma();
  const eredmeny = await db.prepare(
    `INSERT INTO keresek (azon, szoveg, nev, eszkoz, ip, ido, nap)
     SELECT ?, ?, ?, ?, ?, ?, ?
     WHERE (${MAI_SZAM_SQL.replace("COUNT(*) AS n", "COUNT(*)")}) < ?
       AND (${IP_SQL.replace("COUNT(*) AS n", "COUNT(*)")}) < ?
       AND (${SOR_SQL.replace("COUNT(*) AS n", "COUNT(*)")}) < ?`,
  ).bind(veletlenAzon(), szoveg, nev, eszkoz, ip, t, nap, eszkoz, nap, napi, ip, t - 3600, IP_ORANKENT, MAX_VARAKOZO).run();
  if (!eredmeny.meta.changes) {
    throw (await korlatHiba(db, eszkoz, ip, napi)) || new KeresHiba(429, "queue_full", "Most túl sok kérés vár, próbáld később.");
  }
}

async function lejartTakaritas(db) {
  const t = most();
  await db.batch([
    db.prepare("DELETE FROM keresek WHERE ido < ?").bind(t - MEGORZES_NAP * 86400),
    db.prepare(`UPDATE keresek SET allapot = 'elutasitva', allapot_nev = 'Elutasítva',
      ok = 'A rádió nem tudta feldolgozni, próbáld újra.' WHERE allapot = 'kereses' AND ido < ?`).bind(t - ATADATLAN_LEJAR_MP),
  ]);
}

async function gepSzinkron(db, adat) {
  const b = adat.beallitasok;
  if (!b || typeof b !== "object" || Array.isArray(b)) {
    throw new KeresHiba(422, "validation_error", "Hiányoznak a beállítások.");
  }
  const korlat = (v, alap, min, max) => {
    const n = Number.parseInt(v ?? alap, 10);
    return Math.max(min, Math.min(max, Number.isFinite(n) ? n : 0));
  };
  const tiltott = (Array.isArray(b.tiltott_telefonok) ? b.tiltott_telefonok : [])
    .filter((t) => typeof t === "string" && /^[0-9a-f]{32}$/.test(t)).slice(0, 500);
  const uj = {
    aktiv: Boolean(b.aktiv ?? false),
    auto: Boolean(b.auto ?? true),
    cim: vag(szokoz(String(b.cim ?? "Közgáz FM")), 60),
    napi: korlat(b.napi, 3, 1, 20),
    max_perc: korlat(b.max_perc, 7, 1, 30),
    tiltott_telefonok: tiltott,
    verzio: vag(String(adat.verzio ?? ""), 20),
  };
  const regi = await gep(db);
  const t = most();
  const { utolso, ...regiTartalom } = regi;
  const valtozott = JSON.stringify(regiTartalom) !== JSON.stringify(uj);
  const muveletek = [];
  if (valtozott || t - Number(utolso) >= GEP_IRAS_MP) {
    muveletek.push(db.prepare(`INSERT INTO ertekek (kulcs, ertek) VALUES ('gep', ?)
      ON CONFLICT(kulcs) DO UPDATE SET ertek = excluded.ertek`).bind(JSON.stringify({ ...uj, utolso: t })));
  }
  for (const a of (Array.isArray(adat.allapotok) ? adat.allapotok : []).slice(0, 500)) {
    if (!a || typeof a.azon !== "string" || !ERVENYES_ALLAPOTOK.includes(a.allapot)) {
      continue;
    }
    muveletek.push(db.prepare("UPDATE keresek SET allapot = ?, allapot_nev = ?, cim = ?, ok = ?, hely = ?, atadva = 1 WHERE azon = ?")
      .bind(a.allapot, vag(a.allapot_nev ?? "", 60), vag(a.cim ?? "", 200), vag(a.ok ?? "", 200),
        Math.min(Math.max(Number(a.hely) | 0, 0), 999), a.azon));
  }
  if (muveletek.length) {
    await db.batch(muveletek);
  }
  await lejartTakaritas(db);
  const { results } = await db.prepare(`SELECT azon, szoveg, nev, eszkoz, ip, ido FROM keresek
    WHERE atadva = 0 AND allapot = 'kereses' ORDER BY ido LIMIT 20`).all();
  return {
    uj: results.map((k) => ({ azon: k.azon, szoveg: k.szoveg, nev: k.nev, eszkoz: k.eszkoz, ip: k.ip, ido: isoIdo(Number(k.ido)) })),
    ido: isoIdo(t),
  };
}

const BIZTONSAGI = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "X-Frame-Options": "DENY",
  "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Cache-Control": "no-store",
};

function valasz(statusz, test, extra = {}) {
  return new Response(JSON.stringify(test), {
    status: statusz,
    headers: { ...BIZTONSAGI, "Content-Type": "application/json; charset=utf-8", ...extra },
  });
}

const hiba = (statusz, kod, uzenet, extra) => valasz(statusz, { error: { code: kod, message: uzenet } }, extra);

function engedettOrigin(request, env) {
  const origin = request.headers.get("Origin") || "";
  const lista = String(env.KFM_ENGEDETT_ORIGIN || "https://botirocky.github.io").split(",").map((s) => s.trim()).filter(Boolean);
  return origin !== "" && lista.includes(origin) ? origin : null;
}

async function kulcsRendben(request, env) {
  const kulcs = String(env.KFM_GEP_KULCS || "");
  const kapott = request.headers.get("X-Kozgaz-FM-Kulcs") || "";
  if (kulcs.length < 24) {
    return false;
  }
  const [a, b] = await Promise.all([sha256(kulcs), sha256(kapott)]);
  let kul = 0;
  for (let i = 0; i < a.length; i++) {
    kul |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return kul === 0;
}

async function jsonTest(request) {
  const szoveg = await request.text();
  if (szoveg.length > 1_000_000) {
    throw new KeresHiba(413, "too_large", "Túl nagy kérés.");
  }
  let adat;
  try {
    adat = JSON.parse(szoveg);
  } catch {
    adat = null;
  }
  if (!adat || typeof adat !== "object" || Array.isArray(adat)) {
    throw new KeresHiba(400, "bad_json", "Hibás kérés.");
  }
  return adat;
}

async function kezel(request, env) {
  const db = env.DB;
  const ut = new URL(request.url).pathname;
  const modszer = request.method;

  if (ut === "/api/zenek" || ut === "/api/zenek/fajl") {
    if (!(await kulcsRendben(request, env))) {
      await new Promise((r) => setTimeout(r, 300));
      return hiba(401, "unauthorized", "Hibás kulcs.");
    }
    return hiba(503, "no_music", "Ezen a szerveren nincs zenemappa.");
  }

  if (ut === "/api/gep") {
    if (!(await kulcsRendben(request, env))) {
      await new Promise((r) => setTimeout(r, 300));
      return hiba(401, "unauthorized", "Hibás kulcs.");
    }
    if (modszer !== "POST") {
      return hiba(405, "method_not_allowed", "Csak POST.");
    }
    return valasz(200, { data: await gepSzinkron(db, await jsonTest(request)) });
  }

  if (ut === "/api/zenekeres") {
    const origin = request.headers.get("Origin");
    const kulso = engedettOrigin(request, env);
    if (origin && !kulso) {
      return hiba(403, "forbidden", "Hibás kérés.");
    }
    const cors = kulso ? {
      "Access-Control-Allow-Origin": kulso,
      "Vary": "Origin",
      "Access-Control-Allow-Headers": "Content-Type, X-Kozgaz-FM, X-Kozgaz-FM-Eszkoz",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Max-Age": "600",
    } : {};
    if (modszer === "OPTIONS") {
      return new Response(null, { status: 204, headers: { ...BIZTONSAGI, ...cors } });
    }
    const fejlec = request.headers.get("X-Kozgaz-FM-Eszkoz") || "";
    if (!/^[0-9a-f]{64}$/.test(fejlec)) {
      return hiba(400, "bad_device", "Hibás kérés.", cors);
    }
    const eszkoz = await sha256(`kulso:${fejlec}`);
    try {
      if (modszer === "GET") {
        return valasz(200, { data: await diakAllapot(db, eszkoz) }, cors);
      }
      if (modszer !== "POST") {
        return hiba(405, "method_not_allowed", "Nem támogatott művelet.", cors);
      }
      if (request.headers.get("X-Kozgaz-FM") !== "1") {
        return hiba(403, "forbidden", "Hibás kérés.", cors);
      }
      const adat = await jsonTest(request);
      const ip = request.headers.get("CF-Connecting-IP") || "ismeretlen";
      await ujKeres(db, eszkoz, ip, adat.szoveg ?? "", adat.nev ?? "");
      return valasz(200, { data: await diakAllapot(db, eszkoz) }, cors);
    } catch (e) {
      if (e instanceof KeresHiba) {
        return hiba(e.statusz, e.kod, e.message, cors);
      }
      throw e;
    }
  }

  if (ut === "/egeszseg") {
    const g = await gep(db);
    return valasz(200, { data: { ok: true, radio: gepElerheto(g), verzio: g.verzio } });
  }

  if (ut === "/" || ut === "/keres") {
    return Response.redirect(`https://botirocky.github.io/kozgaz-fm/${new URL(request.url).search}`, 302);
  }

  return new Response("Nincs ilyen oldal.", { status: 404, headers: { ...BIZTONSAGI, "Content-Type": "text/plain; charset=utf-8" } });
}

export default {
  async fetch(request, env) {
    try {
      return await kezel(request, env);
    } catch (e) {
      if (e instanceof KeresHiba) {
        return hiba(e.statusz, e.kod, e.message);
      }
      console.error("zenekeres:", e && e.stack ? e.stack : e);
      return hiba(500, "server_error", "Váratlan hiba, próbáld újra.");
    }
  },
};

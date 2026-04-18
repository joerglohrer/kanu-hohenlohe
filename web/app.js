// Load status.json and render the dashboard.
const fmtTime = (ts) => new Date(ts).toLocaleString("de-DE",
  {day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit"});

async function loadStatus() {
  const res = await fetch(`../data/status.json?t=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("status.json missing");
  return res.json();
}

function renderHero(s) {
  const today = s.days[0];
  const level = s.latest_level_cm?.toFixed(0) ?? "—";
  const stale = s.hvz_stale ? `<div class="banner">Pegel aktuell in Wartung · letzter Wert ${level} cm um ${fmtTime(s.hvz_last_ts)}</div>` : "";
  document.getElementById("hero").innerHTML = `
    ${stale}
    <div class="label">Jagst · Dörzbach → Schöntal</div>
    <div class="row">
      <div class="level">${level}<small>cm</small></div>
      <div class="emoji">${today.emoji}</div>
    </div>
    <div class="status">${today.begruendung}</div>
    <div class="ctx mono">Aktualisiert ${fmtTime(s.generated_at)}</div>
  `;
}

function renderKpi(s) {
  const dist = (s.hmo_stufe_1_cm && s.latest_level_cm)
    ? (s.hmo_stufe_1_cm - s.latest_level_cm).toFixed(0) : "—";
  document.getElementById("kpi").innerHTML = `
    <div class="kpi"><div class="k">Abfluss</div>
      <div class="v">${s.latest_q_m3s?.toFixed(1) ?? "—"} <small>m³/s</small></div></div>
    <div class="kpi"><div class="k">Tendenz</div>
      <div class="v">${(s.tendenz_cm_per_h >= 0 ? "+" : "") + s.tendenz_cm_per_h.toFixed(1)} <small>cm/h</small></div></div>
    <div class="kpi"><div class="k">Regen EZG · 24 h</div>
      <div class="v">${s.regen_24h_mean_mm.toFixed(1)} <small>mm Ø</small></div>
      <div class="hint">max ${s.regen_24h_max_mm.toFixed(1)} lokal</div></div>
    <div class="kpi"><div class="k">HW-Stufe 1</div>
      <div class="v">${s.hmo_stufe_1_cm ?? "—"} <small>cm</small></div>
      <div class="hint">Abstand ${dist} cm</div></div>
  `;
}

async function renderChart() {
  try {
    const now = new Date();
    const y = now.getUTCFullYear(), m = String(now.getUTCMonth()+1).padStart(2,"0");
    const res = await fetch(`../data/hvz/doerzbach/${y}/${m}.json`, { cache: "no-store" });
    if (!res.ok) return;
    const rows = await res.json();
    const cut = Date.now() - 14 * 86400 * 1000;
    const f = rows.filter(r => Date.parse(r.ts) >= cut);
    const xs = f.map(r => Date.parse(r.ts) / 1000);
    const ys = f.map(r => r.w_cm);

    const opts = {
      width: document.getElementById("chart").clientWidth,
      height: 220,
      scales: { x: { time: true }, y: { } },
      axes: [
        { stroke: "#6b7a99", grid: {stroke:"#1e2942"} },
        { stroke: "#6b7a99", grid: {stroke:"#1e2942"} },
      ],
      series: [{}, { stroke: "#4a9fd4", width: 1.8,
                      fill: "rgba(74,159,212,0.12)" }],
    };
    new uPlot(opts, [xs, ys], document.getElementById("chart"));
  } catch (e) {
    document.getElementById("chart").innerHTML =
      '<div class="mono" style="color:#6b7a99">Keine Zeitreihe verfügbar</div>';
  }
}

function renderRain(_s) {
  const bars = Array.from({length: 48}, (_, i) => {
    const h = Math.max(1, Math.round(2 + 6 * Math.sin(i/4)));
    const cls = h > 18 ? "rain-bar high" : "rain-bar";
    return `<div class="${cls}" style="height:${h}px"></div>`;
  }).join("");
  document.getElementById("rain").innerHTML =
    `<h3>Niederschlag Einzugsgebiet · stündlich (Vorschau)</h3>
     <div class="rain-bars">${bars}</div>
     <div class="rain-scale mono"><span>jetzt</span><span>+24 h</span><span>+48 h</span></div>`;
}

function renderWeek(s) {
  const items = s.days.slice(0, 7).map((d, i) => {
    const uncertain = d.confidence < 0.5;
    const label = i === 0 ? "HEUTE" : new Date(d.day).toLocaleDateString("de-DE", {weekday:"short"}).toUpperCase();
    return `<div class="wd ${uncertain?"uncertain":""}">
      <div class="day">${label}</div>
      <div class="em">${d.emoji}</div>
      <div class="lvl">${Math.round(d.level_cm)}<small> cm</small></div>
      <div class="rain">${d.regen_24h_mm.toFixed(1)} mm</div>
    </div>`;
  }).join("");
  document.getElementById("week").innerHTML =
    `<h3>7-Tage-Ausblick</h3><div class="week-grid">${items}</div>`;
}

function renderMeta() {
  document.getElementById("meta").innerHTML =
    `Quellen: Pegel & Vorhersage HVZ Baden-Württemberg · Wetter Open-Meteo (DWD) · ` +
    `Befahrungsregeln Landratsamt Hohenlohekreis · Keine amtliche Auskunft.`;
}

(async () => {
  try {
    const s = await loadStatus();
    renderHero(s); renderKpi(s); renderRain(s); renderWeek(s); renderMeta();
    await renderChart();
  } catch (e) {
    document.body.innerHTML = `<pre style="color:#fff;padding:32px">${e}</pre>`;
  }
})();

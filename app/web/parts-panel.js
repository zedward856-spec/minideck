// App-only: a PARTS sheet to show/hide each part of the deck. main.js hands over its scene via
// window.__deck + a "deck-ready" event (hook added by sync_site.py).
(() => {
  const KEY = "minideck.hidden";
  const GROUPS = [
    ["Case", (m) => ["body", "kbplate", "accent", "accent2"].includes(m.role)],
    ["Electronics", (m) => ["native", "dark", "sdcard", "keys"].includes(m.role) && !/inserts/.test(m.label)],
    ["Hardware", () => true],
  ];
  let hidden = new Set();
  try { hidden = new Set(JSON.parse(localStorage.getItem(KEY) || "[]")); } catch (e) { }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify([...hidden])); } catch (e) { } };

  addEventListener("deck-ready", () => {
    const { meta, byName, root, legendPlane } = window.__deck;

    // one row per listed part; the loose screws become two rows
    const items = [];
    for (const n of Object.keys(meta)) {
      const m = meta[n];
      if (n.startsWith("_") || !m.list) continue;
      items.push({ id: n, label: m.label, lid: m.lid, meta: m, nodes: [n] });
    }
    for (const [pre, label, lid] of [["screws_base_", "M2 screws", false], ["screws_lid_", "Bezel screws", true]]) {
      const nodes = Object.keys(meta).filter((n) => n.startsWith(pre));
      if (nodes.length) items.push({ id: pre, label: `${label} ×${nodes.length}`, lid, meta: { role: "metal", label }, nodes });
    }
    // what actually gets hidden: the moving pivot (carries paint fills, legends, the screen video)
    const objs = (it) => it.nodes.map((n) => (byName[n] ? byName[n].pivot : root.getObjectByName(n))).filter(Boolean)
      .concat(it.id === "keycaps" && legendPlane ? [legendPlane] : []);
    const apply = (it) => { const v = !hidden.has(it.id); for (const o of objs(it)) o.visible = v; };

    // ---- UI
    const btn = document.createElement("button");
    btn.id = "partsBtn"; btn.className = "mono"; btn.innerHTML = '<span>parts</span><b id="partsCount"></b>';
    const sheet = document.createElement("div");
    sheet.id = "partsSheet";
    sheet.innerHTML = `
      <div class="ps-head">
        <p class="kicker mono">// visible parts</p>
        <button class="ps-x mono" aria-label="Close">×</button>
      </div>
      <div class="ps-presets mono">
        <button data-p="all">all</button><button data-p="elec">electronics</button>
        <button data-p="case">case</button><button data-p="none">none</button>
      </div>
      <div class="ps-list"></div>`;
    document.body.append(btn, sheet);
    const list = sheet.querySelector(".ps-list");

    const grouped = GROUPS.map(([g]) => [g, []]);
    for (const it of items) grouped[GROUPS.findIndex(([, f]) => f(it.meta))][1].push(it);
    const rows = new Map();
    for (const [g, its] of grouped) {
      if (!its.length) continue;
      const sec = document.createElement("section");
      sec.innerHTML = `<h4 class="mono"><span>${g}</span><button class="mono">toggle</button></h4>`;
      sec.querySelector("button").onclick = () => {
        const anyOn = its.some((it) => !hidden.has(it.id));
        for (const it of its) anyOn ? hidden.add(it.id) : hidden.delete(it.id);
        refresh();
      };
      for (const it of its) {
        const row = document.createElement("label");
        row.className = "ps-row";
        row.innerHTML = `<span>${it.label}${it.lid ? ' <i class="mono">lid</i>' : ""}</span><input type="checkbox"><s></s>`;
        row.querySelector("input").onchange = (e) => { e.target.checked ? hidden.delete(it.id) : hidden.add(it.id); refresh(); };
        sec.appendChild(row); rows.set(it, row);
      }
      list.appendChild(sec);
    }

    const PRESET = {
      all: () => false, none: () => true,
      elec: (it) => GROUPS[1][1](it.meta) === false,
      case: (it) => !GROUPS[0][1](it.meta),
    };
    sheet.querySelectorAll(".ps-presets button").forEach((b) => b.onclick = () => {
      hidden = new Set(items.filter(PRESET[b.dataset.p]).map((it) => it.id)); refresh();
    });

    function refresh() {
      for (const [it, row] of rows) { row.querySelector("input").checked = !hidden.has(it.id); apply(it); }
      const off = items.filter((it) => hidden.has(it.id)).length;
      document.getElementById("partsCount").textContent = off ? `${items.length - off}/${items.length}` : "";
      btn.classList.toggle("filtered", off > 0);
      save();
    }
    // the Android back button closes the sheet first (opening it pushes a history entry)
    const isOpen = () => sheet.classList.contains("open");
    const show = (v) => { sheet.classList.toggle("open", v); btn.classList.toggle("on", v); };
    const open = (v) => {
      if (v === isOpen()) return;
      show(v);
      if (v) history.pushState({ partsSheet: 1 }, "");
      else if (history.state && history.state.partsSheet) history.back();
    };
    addEventListener("popstate", () => show(false));
    btn.onclick = () => open(!isOpen());
    sheet.querySelector(".ps-x").onclick = () => open(false);
    refresh();
  });
})();

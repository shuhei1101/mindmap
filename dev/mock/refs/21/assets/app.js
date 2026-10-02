// mindmap のプレビューのモック: window.MINDMAP（YAML を JSON にしたもの）を、画面ごとの HTML に描く
(() => {
  const M = window.MINDMAP;
  const W = M.workspace;
  const STAGES = W.stages;
  const TARGET = W.target_label;
  const STORE_KEY = "mindmap.preview.v2";

  // ===== 種類・状態・並び順 =====
  const KINDS = [
    { key: "overview", label: "概要" },
    { key: "decisions", label: "検討事項" },
    { key: "tasks", label: "タスク" },
    { key: "research", label: "調査" },
    { key: "docs", label: "資料" },
    { key: "terms", label: "用語集" },
    { key: "notes", label: "メモ" },
    { key: "logs", label: "会話ログ" },
  ];
  const PREFIX = { D: "decisions", T: "tasks", R: "research", A: "docs", G: "terms", N: "notes", L: "logs" };
  const STATUS_ORDER = ["要見直し", "未決定", "進行中", "保留", "未整理", "未着手", "決定済み", "完了", "対象外", "取り下げ", "中止"];
  const IMPACT = ["大", "中", "小"];
  const CONF = ["高", "中", "低"];
  const RESOLVED = new Set(["決定済み", "完了"]);
  const CLOSED = new Set(["取り下げ", "対象外", "完了", "中止"]);
  const CLOSED_LABEL = { decisions: "取り下げ・対象外を表示" };
  const DEFAULT_VIEW = { decisions: "map", tasks: "board", docs: "cards" };
  const DOC_STATUS = ["下書き", "確認中", "完成"];
  const BOARD_COLS = { decisions: ["要見直し", "未決定", "保留", "未整理", "決定済み", "対象外", "取り下げ"], tasks: ["未着手", "進行中", "保留", "完了", "中止"] };
  const KIND_NOUN = { decisions: "検討事項", tasks: "タスク", research: "調査", docs: "資料", terms: "用語", notes: "メモ", logs: "会話ログ" };
  const RECORD_KINDS = ["research", "terms", "notes", "logs"];

  // ===== 画面: 1 画面 = 1 枚の HTML。タブは画面の HTML へのリンクにし、移ると履歴に積む =====
  const SCREEN = document.body.dataset.screen;
  const PAGES = document.body.dataset.pages;  // pages/ への相対パス
  const SCREEN_OF = { overview: "overview", decisions: "decisions", tasks: "tasks", docs: "docs", research: "records", terms: "records", notes: "records", logs: "records", graph: "graph" };
  const MOCK_VARIANT = "standard";
  const pageUrl = (tab, params = {}) => {
    const p = new URLSearchParams(params);
    if (SCREEN_OF[tab] === "records") p.set("kind", tab);
    if (state.sim) p.set("sim", state.sim);
    const h = p.toString();
    return `${PAGES}${SCREEN_OF[tab]}/21/${MOCK_VARIANT}/index.html${h ? "#" + h : ""}`;
  };
  const defaultView = (tab) => DEFAULT_VIEW[tab] || "table";

  // ===== 索引 =====
  const byId = new Map();
  for (const k of Object.values(PREFIX)) for (const it of M[k]) byId.set(it.id, { kind: k, it });
  const dependents = new Map();
  for (const { it } of byId.values()) for (const d of it.depends_on || []) {
    if (!dependents.has(d)) dependents.set(d, []);
    dependents.get(d).push(it.id);
  }
  const isResolved = (id) => {
    const e = byId.get(id);
    // 状態を持たない種類（調査・用語集・メモ・会話ログ）は前提として常に決まっている
    return !!e && (e.it.status === undefined || RESOLVED.has(e.it.status));
  };
  const isReady = (it) => (it.depends_on || []).every(isResolved);
  // 後続の件数: 依存をたどった先の、終わっていない項目の数
  const followers = (id) => {
    const seen = new Set();
    const stack = [...(dependents.get(id) || [])];
    while (stack.length) {
      const x = stack.pop();
      if (seen.has(x)) continue;
      seen.add(x);
      stack.push(...(dependents.get(x) || []));
    }
    return [...seen].filter((x) => !CLOSED.has(byId.get(x).it.status)).length;
  };
  const referrers = (id) => [...byId.values()].filter(({ it }) =>
    ["related", "depends_on", "sources", "for"].some((k) => (it[k] || []).includes(id)) || it.result === id).map(({ it }) => it.id);

  // ===== 小道具 =====
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const ICONS = {
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    back: '<path d="m15 18-6-6 6-6"/>',
    chev: '<path d="m9 6 6 6-6 6"/>',
    filter: '<path d="M4 5h16l-6 7.5V19l-4-2v-4.5Z"/>',
    pin: '<path d="M9 4h6l-1 5 3 3v2H7v-2l3-3Z"/><path d="M12 14v6"/>',
    up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
    down: '<path d="M12 5v14M6 13l6 6 6-6"/>',
    updown: '<path d="m8 9 4-4 4 4M8 15l4 4 4-4"/>',
    cols: '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M9 4v16M15 4v16"/>',
    bookmark: '<path d="M6 4h12v16l-6-4-6 4Z"/>',
    table: '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10h18M9 10v10"/>',
    board: '<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="11" rx="1"/><rect x="17" y="4" width="4" height="7" rx="1"/>',
    graph: '<circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="7" r="2"/><circle cx="6" cy="20" r="2"/><circle cx="19" cy="19" r="2"/><path d="M9.5 10.5 5.6 7.2M14.6 10.9l3.6-2.6M10 14.4l-2.6 4M14.3 14.2l3.3 3.4"/>',
    expand: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
    shrink: '<path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"/>',
    check: '<path d="m5 12 5 5 9-10"/>',
    checked: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 3 3 5-6"/>',
    unchecked: '<rect x="4" y="4" width="16" height="16" rx="3"/>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    copy: '<rect x="9" y="9" width="12" height="12" rx="1"/><path d="M5 15V4a1 1 0 0 1 1-1h11"/>',
    orbit: '<circle cx="12" cy="12" r="2.5"/><ellipse cx="12" cy="12" rx="10" ry="4.5" transform="rotate(-25 12 12)"/><circle cx="20" cy="8.5" r="1.4"/>',
    cards: '<rect x="3" y="4" width="8" height="7" rx="1"/><rect x="13" y="4" width="8" height="7" rx="1"/><rect x="3" y="13" width="8" height="7" rx="1"/><rect x="13" y="13" width="8" height="7" rx="1"/>',
    map: '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.5 12h3l4-5M11.5 12l4 5"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    link: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    pause: '<path d="M8 5v14M16 5v14"/>',
    play: '<path d="m7 5 12 7-12 7Z"/>',
    flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
    alert: '<path d="M12 3 2 20h20Z"/><path d="M12 10v4M12 17h.01"/>',
    next: '<circle cx="12" cy="12" r="9"/><path d="M10 8l4 4-4 4"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5Z"/><path d="m3 13 9 5 9-5"/>',
    follow: '<path d="M5 5v6a4 4 0 0 0 4 4h10"/><path d="m15 11 4 4-4 4"/>',
    deps: '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.5 6H14a4 4 0 0 1 4 4v5.5"/>',
    box: '<path d="M3 7l9-4 9 4v10l-9 4-9-4Z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
    home: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>',
    decision: '<circle cx="12" cy="12" r="8"/><path d="m9 12 2 2 4-4"/>',
    task: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/>',
    research: '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/><path d="M8 10.5h5"/>',
    doc: '<path d="M6 3h8l4 4v14H6Z"/><path d="M14 3v4h4"/>',
    term: '<path d="M4 5h11a3 3 0 0 1 3 3v12H7a3 3 0 0 1-3-3Z"/><path d="M4 17a3 3 0 0 1 3-3h11"/>',
    note: '<path d="M5 4h14v12l-4 4H5Z"/><path d="M15 20v-4h4"/>',
    log: '<path d="M4 6h16v10H9l-5 4Z"/>',
  };
  const TAB_ICON = { overview: "home", decisions: "decision", tasks: "task", research: "research", docs: "doc", terms: "term", notes: "note", logs: "log" };
  const icon = (n) => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n]}</svg>`;
  // 状態の印: 色だけに頼らず形も変える
  const MARKS = {
    "決定済み": '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>',
    "完了": '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/><path d="m2.8 5.1 1.5 1.5 3-3" stroke="var(--surface)" stroke-width="1.4" fill="none"/>',
    "未決定": '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/>',
    "未着手": '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" stroke-width="1.6"/>',
    "進行中": '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>',
    "要見直し": '<path d="M5 .3 9.7 5 5 9.7.3 5Z" fill="var(--st-review)"/>',
    "保留": '<rect x="1.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/><rect x="6.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/>',
    "未整理": '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-loose)" stroke-width="1.6" stroke-dasharray="2 1.6"/>',
    "取り下げ": '<path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" stroke-width="1.6"/>',
    "対象外": '<path d="M1 5h8" stroke="var(--st-off)" stroke-width="1.8"/>',
    "中止": '<path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" stroke-width="1.6"/>',
    "下書き": '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" stroke-width="1.6" stroke-dasharray="2 1.6"/>',
    "確認中": '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>',
    "完成": '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>',
  };
  const mark = (st) => (MARKS[st] ? `<svg class="mark" viewBox="0 0 10 10" aria-hidden="true">${MARKS[st]}</svg>` : "");
  const status = (st) => (st ? `<span class="st" data-st="${esc(st)}">${mark(st)}${esc(st)}</span>` : "");
  const impact = (w) => w ? `<span class="impact" title="影響度 ${esc(w)}"><span aria-hidden="true">${[0, 1, 2].map((i) => `<i class="${i < 3 - IMPACT.indexOf(w) ? "on" : ""}"></i>`).join("")}</span>${esc(w)}</span>` : "";
  const tags = (arr) => (arr || []).map((t) => `<span class="tag">${esc(t)}</span>`).join("");
  const titleOf = (id) => byId.get(id)?.it.title ?? "（該当なし）";
  const idlinks = (arr) => (arr || []).map((id) => `<button class="idlink" data-act="open" data-id="${esc(id)}" title="${esc(titleOf(id))}">${esc(id)}</button>`).join("");
  const oi = (list, v) => { const i = list.indexOf(v); return i < 0 ? 999 : i; };
  // 描画のライブラリが読めたか。モックでは操作列の「ライブラリが読めない」で、読めなかった状態を見せる
  const libOk = (name) => state.sim !== "nolib" && !!window[name];
  const libError = (names, what, alt) => `<div class="lib-error" role="alert"><span>${what}を表示できません。読めなかったライブラリ: ${names.map((n) => `<b>${esc(n)}</b>`).join("・")}</span><span class="muted">${alt}</span></div>`;
  const renderMd = (src) => {
    if (!src) return "";
    // CDN のライブラリを読めなかったときは、読めなかったライブラリの名前を出して原文を見せる
    if (!libOk("marked") || !libOk("DOMPurify")) {
      const missing = [!libOk("marked") && "marked", !libOk("DOMPurify") && "DOMPurify", src.includes("```mermaid") && state.sim === "nolib" && "mermaid"].filter(Boolean);
      return libError(missing, "本文", "ネットワークの接続を確かめて、ページを読み込み直してください。下は本文の原文です。") + `<pre class="md-raw">${esc(src)}</pre>`;
    }
    return `<div class="md">${window.DOMPurify.sanitize(window.marked.parse(src))}</div>`;
  };

  // ===== 端末に残す設定（列の表示・固定・保存した条件・テーマ・動き） =====
  const prefs = (() => { try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch { return {}; } })();
  const savePrefs = () => { try { localStorage.setItem(STORE_KEY, JSON.stringify(prefs)); } catch { /* 保存できない環境では今の画面だけで保つ */ } };
  prefs.cols ??= {}; prefs.views ??= {};

  // ===== 列の定義 =====
  const C = {
    id: { key: "id", label: "ID", pri: 1, nowrap: true, get: (r) => r.id, cell: (r) => `<span class="mono">${esc(r.id)}</span>` },
    title: (label = "タイトル") => ({ key: "title", label, pri: 1, fixed: true, min: "16em", get: (r) => r.title, cell: (r) => `<button class="row-open" data-act="open" data-id="${r.id}">${esc(r.title)}</button>` }),
    status: { key: "status", label: "状態", pri: 1, nowrap: true, filter: true, order: STATUS_ORDER, get: (r) => r.status, cell: (r) => status(r.status) },
    target: { key: "target", label: TARGET, pri: 4, nowrap: true, filter: true, get: (r) => r.target, cell: (r) => esc(r.target) },
    category: { key: "category", label: "カテゴリー", pri: 2, nowrap: true, filter: true, get: (r) => r.category, cell: (r) => esc(r.category) },
    stage: { key: "stage", label: "フェーズ", pri: 2, nowrap: true, filter: true, order: STAGES, get: (r) => r.stage, cell: (r) => esc(r.stage) },
    tags: { key: "tags", label: "タグ", pri: 4, filter: true, multi: true, get: (r) => r.tags || [], cell: (r) => tags(r.tags) },
    updated: { key: "updated", label: "更新日", pri: 5, hidden: true, nowrap: true, get: (r) => r.updated, cell: (r) => `<span class="mono">${esc(r.updated)}</span>` },
  };
  const COLUMNS = {
    decisions: [
      C.id, C.title(), C.status,
      { key: "ready", label: "着手できる", pri: 2, nowrap: true, filter: true, order: ["はい", "いいえ"], get: (r) => (isReady(r) ? "はい" : "いいえ"), cell: (r) => (isReady(r) ? "はい" : '<span class="muted">いいえ</span>') },
      { key: "answer", label: "決定内容", pri: 3, min: "16em", get: (r) => r.answer || "", cell: (r) => (r.answer ? esc(r.answer) : '<span class="muted">—</span>') },
      C.target, C.category, C.stage,
      { key: "weight", label: "影響度", pri: 3, nowrap: true, filter: true, order: IMPACT, get: (r) => r.weight, cell: (r) => impact(r.weight) },
      { key: "followers", label: "後続の件数", pri: 4, num: true, get: (r) => followers(r.id), cell: (r) => `<span class="mono">${followers(r.id)}</span>` },
      C.tags, C.updated,
    ],
    tasks: [
      C.id, C.title(), C.status,
      { key: "kind", label: "種類", pri: 2, nowrap: true, filter: true, get: (r) => r.kind, cell: (r) => esc(r.kind) },
      { key: "for", label: "関連する検討事項", pri: 3, get: (r) => (r.for || []).join(" "), cell: (r) => idlinks(r.for) || '<span class="muted">—</span>' },
      { key: "depends_on", label: "前提", pri: 3, get: (r) => (r.depends_on || []).join(" "), cell: (r) => idlinks(r.depends_on) || '<span class="muted">—</span>' },
      C.target, C.category, C.stage, C.tags, C.updated,
    ],
    research: [
      C.id, C.title(),
      { key: "conclusion", label: "結論", pri: 2, min: "18em", get: (r) => r.conclusion, cell: (r) => esc(r.conclusion) },
      { key: "confidence", label: "確度", pri: 2, nowrap: true, filter: true, order: CONF, get: (r) => r.confidence, cell: (r) => esc(r.confidence) },
      C.target, C.category, C.stage, C.tags, C.updated,
    ],
    docs: [
      C.id, C.title(),
      { key: "deliverable", label: "成果物", pri: 2, nowrap: true, filter: true, order: ["成果物", "成果物以外"], get: (r) => (r.deliverable ? "成果物" : "成果物以外"), cell: (r) => (r.deliverable ? `<span class="deliv-badge">${icon("box")}成果物</span>` : '<span class="muted">—</span>') },
      { key: "status", label: "状態", pri: 1, nowrap: true, filter: true, order: DOC_STATUS, get: (r) => r.status, cell: (r) => status(r.status) },
      { key: "kind", label: "種類", pri: 2, nowrap: true, filter: true, get: (r) => r.kind, cell: (r) => esc(r.kind) },
      { key: "related", label: "関連", pri: 3, get: (r) => (r.related || []).join(" "), cell: (r) => idlinks(r.related) },
      C.category, C.stage, C.tags, C.updated,
    ],
    terms: [
      C.id, C.title("用語"),
      { key: "meaning", label: "意味", pri: 1, min: "18em", get: (r) => r.meaning, cell: (r) => esc(r.meaning) },
      { key: "aliases", label: "別名", pri: 3, get: (r) => (r.aliases || []).join(" "), cell: (r) => tags(r.aliases) || '<span class="muted">—</span>' },
      { key: "avoid", label: "使わない表記", pri: 3, get: (r) => (r.avoid || []).join(" "), cell: (r) => tags(r.avoid) || '<span class="muted">—</span>' },
      C.tags,
    ],
    notes: [
      C.id, C.title(),
      { key: "content", label: "内容", pri: 2, min: "18em", get: (r) => r.content, cell: (r) => esc(r.content) },
      C.tags,
      { key: "related", label: "関連", pri: 3, get: (r) => (r.related || []).join(" "), cell: (r) => idlinks(r.related) },
    ],
    logs: [
      C.id,
      { key: "date", label: "日付", pri: 2, nowrap: true, get: (r) => r.date, cell: (r) => `<span class="mono">${esc(r.date)}</span>` },
      C.title(),
      { key: "related", label: "更新した項目", pri: 3, get: (r) => (r.related || []).join(" "), cell: (r) => idlinks(r.related) },
    ],
  };

  // ===== 画面の状態 =====
  const state = { zoom: 1, tab: "overview", view: "table", panel: null, full: false, sim: "", mapQ: "", tables: {}, mapShow: new Set(["要見直し", "未決定", "未整理", "保留"]), deps: true, linkTypes: new Set(["dep", "rel", "src", "for"]) };
  for (const k of Object.keys(COLUMNS)) state.tables[k] = { q: "", filters: {}, sort: null, showClosed: k !== "decisions" };
  const colPrefs = (kind) => (prefs.cols[kind] ??= { hidden: COLUMNS[kind].filter((c) => c.hidden).map((c) => c.key), pin: 0 });

  // URL のハッシュに、共有したいもの（タブ・表示形式・開いている項目）を持つ
  // 画面はページで決まる。ハッシュには表示形式・開いている項目（と調査・用語集・メモ・会話ログのどれか）を持つ
  // 概要から絞って開くときの条件（f.{列}）は、開いたときに読むだけで保存しない
  const readHash = (first) => {
    const p = new URLSearchParams(location.hash.slice(1) || (first ? document.body.dataset.initial || "" : ""));
    state.tab = SCREEN === "records" ? (RECORD_KINDS.includes(p.get("kind")) ? p.get("kind") : "research") : SCREEN;
    state.view = ["map", "board", "cards", "table"].includes(p.get("view")) ? p.get("view") : defaultView(state.tab);
    const id = p.get("id");
    state.panel = id && byId.has(id) ? id : null;
    state.full = !!state.panel && p.get("full") === "1";
    state.sim = p.get("sim") === "nolib" ? "nolib" : "";
    if (first) {
      const t = state.tables[state.tab];
      for (const [k, v] of p) if (k.startsWith("f.") && t) t.filters[k.slice(2)] = new Set(v.split("|"));
      state.initSearch = p.get("search");
      state.initViewer = p.get("viewer") === "1";
    }
  };
  const hashOf = () => {
    const p = new URLSearchParams();
    if (SCREEN === "records") p.set("kind", state.tab);
    if (state.view !== defaultView(state.tab)) p.set("view", state.view);
    if (state.panel) p.set("id", state.panel);
    if (state.full) p.set("full", "1");
    if (state.sim) p.set("sim", state.sim);
    const h = p.toString();
    return h ? "#" + h : location.pathname;
  };

  // ===== 表の行の取り出し =====
  const matchQ = (r, q) => !q || q.toLowerCase().split(/\s+/).filter(Boolean).every((t) => JSON.stringify(r).toLowerCase().includes(t));
  const rowsFor = (kind, exceptKey) => {
    const t = state.tables[kind];
    return M[kind].filter((r) => {
      if (!t.showClosed && r.status && CLOSED.has(r.status)) return false;
      if (!matchQ(r, t.q)) return false;
      for (const [key, set] of Object.entries(t.filters)) {
        if (key === exceptKey || !set.size) continue;
        const col = COLUMNS[kind].find((c) => c.key === key);
        const v = col.get(r);
        if (col.multi ? !v.some((x) => set.has(x)) : !set.has(v)) return false;
      }
      return true;
    });
  };
  const sortRows = (kind, rows) => {
    const s = state.tables[kind].sort;
    if (!s) return rows;
    const col = COLUMNS[kind].find((c) => c.key === s.key);
    const val = (r) => (col.order ? oi(col.order, col.get(r)) : col.get(r));
    const dir = s.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = val(a), y = val(b);
      return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "ja")) * dir;
    });
  };

  // ===== タブ =====
  const keepPanel = () => (state.panel ? { id: state.panel } : {});
  const renderTabs = () => {
    document.getElementById("brand-sub").textContent = W.summary;
    const cur = (k) => (state.tab === k ? ' aria-current="page"' : "");
    document.getElementById("tabs").innerHTML = KINDS.map((k) =>
      `<a class="tab" href="${pageUrl(k.key, keepPanel())}"${cur(k.key)}>${icon(TAB_ICON[k.key])}${k.label}${M[k.key] ? `<span class="count">${M[k.key].length}</span>` : ""}</a>`).join("")
      + `<span class="tab-gap"></span><a class="tab tab-special" href="${pageUrl("graph", keepPanel())}"${cur("graph")}>${icon("orbit")}つながり</a>`;
  };

  // ===== 概要: 区画をタイルに分け、数字と見出しで一目で読めるようにする =====
  const renderOverview = () => {
    const ds = M.decisions;
    const gi = STAGES.indexOf(W.goal.stage);
    const live = (d) => !CLOSED.has(d.status);
    const inGoal = ds.filter((d) => live(d) && STAGES.indexOf(d.stage) <= gi);
    const done = inGoal.filter((d) => d.status === "決定済み").length;
    const next = ds.filter((d) => d.status === "未決定" && isReady(d))
      .sort((a, b) => oi(STAGES, a.stage) - oi(STAGES, b.stage) || oi(IMPACT, a.weight) - oi(IMPACT, b.weight) || followers(b.id) - followers(a.id));
    const review = ds.filter((d) => d.status === "要見直し");
    const holdDs = ds.filter((x) => x.status === "保留"), holdTs = M.tasks.filter((x) => x.status === "保留");
    const holds = [...holdDs, ...holdTs];
    const all = (href, n, label = "すべて表示") => `<a class="t-link" href="${href}">${label}（${n} 件）</a>`;
    const running = M.tasks.filter((t) => t.status === "進行中");

    const nextHtml = next.length
      ? `<ol class="next-list">${next.slice(0, 3).map((d) => `<li><button data-act="open" data-id="${d.id}"><span class="nl-ttl">${esc(d.title)}</span><span class="nl-meta"><span>${esc(d.category)} · ${esc(d.stage)}</span>${impact(d.weight)}<span class="fol" title="後続の件数">${icon("follow")}${followers(d.id)}</span></span><span class="go" aria-hidden="true">${icon("chev")}</span></button></li>`).join("")}</ol>`
      : `<p class="empty">すぐに検討できる項目はありません。</p>`;
    const stageRows = STAGES.map((sg, i) => {
      const all = ds.filter((d) => live(d) && d.stage === sg);
      const ok = all.filter((d) => d.status === "決定済み").length;
      return `<li class="${i > gi ? "out" : ""}"><span>${esc(sg)}</span><i><b style="width:${all.length ? (ok / all.length) * 100 : 0}%"></b></i><span class="mono">${ok}/${all.length}</span></li>`;
    }).join("");
    const mini = (items, empty, side) => items.length
      ? `<ul class="mini">${items.slice(0, 3).map((x) => `<li><button data-act="open" data-id="${x.id}">${mark(x.status)}<span class="mt">${esc(x.title)}</span><span class="go" aria-hidden="true">${icon("chev")}</span></button>${side ? side(x) : ""}</li>`).join("")}</ul>`
      : `<p class="empty">${empty}</p>`;
    // カテゴリー × フェーズの表。対象（システム）ごとに見出しを立てる
    const catTable = W.targets.map((t) => {
      const rows = W.categories.filter((c) => c.target === t.name).map((c) => {
        const all = ds.filter((d) => live(d) && d.category === c.name);
        if (!all.length) return "";
        const ok = all.filter((d) => d.status === "決定済み").length;
        const cells = STAGES.map((sg) => {
          const a = all.filter((d) => d.stage === sg), o = a.filter((d) => d.status === "決定済み").length;
          return a.length ? `<td><a class="cell" href="${pageUrl("decisions", { view: "table", "f.category": c.name, "f.stage": sg })}" aria-label="${esc(c.name)} の ${esc(sg)}: ${o}/${a.length} 件決定済み"><i><b style="width:${(o / a.length) * 100}%"></b></i><span class="mono">${o}/${a.length}</span></a></td>` : `<td><span class="muted">—</span></td>`;
        }).join("");
        return `<tr><th scope="row"><a class="cat-link" href="${pageUrl("decisions", { view: "table", "f.category": c.name })}">${esc(c.name)}</a></th>${cells}<td class="tot mono">${ok}/${all.length}</td></tr>`;
      }).join("");
      return rows ? `<tbody><tr class="tgt"><th colspan="${STAGES.length + 2}" scope="rowgroup">${esc(TARGET)}: ${esc(t.name)}</th></tr>${rows}</tbody>` : "";
    }).join("");
    // 成果物は資料のうち印の付いたもの。できたものにチェックを付け、5 件を超えたら資料の一覧へ
    const deliv = M.docs.filter((d) => d.deliverable).concat(W.goal.deliverables.filter((x) => !M.docs.some((d) => d.deliverable && d.title === x.title)));
    const isDone = (x) => x.status === "完成";
    const doneN = deliv.filter(isDone).length;
    const deliverHtml = `<div class="deliv"><div class="deliv-head">${icon("box")}成果物<span class="mono">${doneN}/${deliv.length}</span>${deliv.length > 5 ? all(pageUrl("docs", { "f.deliverable": "成果物" }), deliv.length) : ""}</div>
      <ul class="checklist">${deliv.slice(0, 5).map((x) => `<li class="${isDone(x) ? "done" : ""}">${icon(isDone(x) ? "checked" : "unchecked")}${x.id ? `<button data-act="open" data-id="${x.id}">${esc(x.title)}</button>` : `<span>${esc(x.title)}</span>`}</li>`).join("")}</ul></div>`;
    return `
      <header class="hero">
        <p class="hero-sub">${esc(W.field)} · ゴールは${esc(W.goal.stage)}のフェーズまで</p>
        <h1>${esc(W.summary)}</h1>
      </header>
      <div class="bento">
        <section class="tile t-next" aria-labelledby="h-next">
          <div class="t-head"><h2 id="h-next">${icon("next")}次に検討する項目</h2>${next.length > 3 ? all(pageUrl("decisions", { view: "table", "f.status": "未決定", "f.ready": "はい" }), next.length) : ""}</div>
          ${nextHtml}
        </section>
        <section class="tile t-goal" aria-labelledby="h-goal">
          <h2 id="h-goal">${icon("flag")}ゴールまで</h2>
          <p class="big">${done}<small> / ${inGoal.length}</small></p>
          <p class="big-sub">決定済み</p>
          <ul class="stage-rows">${stageRows}</ul>
          ${deliverHtml}
        </section>
        <section class="tile t-small" aria-labelledby="h-review">
          <div class="t-head"><h2 id="h-review">${icon("alert")}要見直し</h2>${review.length ? all(pageUrl("decisions", { view: "table", "f.status": "要見直し" }), review.length) : ""}</div><p class="num">${review.length}</p>
          ${mini(review, "なし")}
        </section>
        <section class="tile t-small" aria-labelledby="h-hold">
          <div class="t-head"><h2 id="h-hold">${icon("pause")}保留</h2><span class="t-links">${holdDs.length ? all(pageUrl("decisions", { view: "table", "f.status": "保留" }), holdDs.length, "検討事項") : ""}${holdTs.length ? all(pageUrl("tasks", { view: "table", "f.status": "保留" }), holdTs.length, "タスク") : ""}</span></div><p class="num">${holds.length}</p>
          ${mini(holds, "なし", (x) => { const w = (x.depends_on || []).filter((id) => !isResolved(id)); return `<span class="wait">${w.length ? `決定待ち ${idlinks(w)}` : "再開可能"}</span>`; })}
        </section>
        <section class="tile t-small" aria-labelledby="h-run">
          <div class="t-head"><h2 id="h-run">${icon("play")}進行中のタスク</h2>${running.length ? all(pageUrl("tasks", { view: "table", "f.status": "進行中" }), running.length) : ""}</div><p class="num">${running.length}</p>
          ${mini(running, "なし")}
        </section>
        <section class="tile t-cat" aria-labelledby="h-cat">
          <h2 id="h-cat">${icon("layers")}カテゴリー別の進み具合</h2>
          <div class="cat-wrap"><table class="cat-table"><thead><tr><th scope="col">カテゴリー</th>${STAGES.map((x) => `<th scope="col">${esc(x)}</th>`).join("")}<th scope="col" class="tot">決定済み</th></tr></thead>${catTable}</table></div>
        </section>
      </div>`;
  };

  // ===== 表のタブ =====
  const visibleCols = (kind) => { const h = new Set(colPrefs(kind).hidden); return COLUMNS[kind].filter((c) => !h.has(c.key)); };
  const segment = (kind) => {
    const opts = kind === "decisions" ? [["map", "マップ"], ["board", "ボード"], ["table", "表"]] : kind === "tasks" ? [["board", "ボード"], ["table", "表"]] : kind === "docs" ? [["cards", "カード"], ["table", "表"]] : null;
    if (!opts) return "";
    return `<div class="segment" role="group" aria-label="表示形式">${opts.map(([v, l]) => `<button data-act="view" data-view="${v}" aria-pressed="${state.view === v}">${icon(v)}${l}</button>`).join("")}</div>`;
  };
  const closedCheck = (kind) => CLOSED_LABEL[kind]
    ? `<label class="check"><input type="checkbox" data-act="closed" ${state.tables[kind].showClosed ? "checked" : ""}>${CLOSED_LABEL[kind]}</label>` : "";
  const renderToolbar = (kind) => `<div class="toolbar">${segment(kind)}
      <label class="sr-only" for="q-${kind}">キーワードで絞り込み</label>
      <input class="input grow" id="q-${kind}" data-act="q" type="search" placeholder="キーワード" value="${esc(state.tables[kind].q)}">
      ${state.view === "table" ? closedCheck(kind) : ""}
      <span class="spacer"></span>
      ${state.view !== "table" ? `<button class="btn" data-act="facets" aria-label="絞り込み">${icon("filter")}<span class="lbl">絞り込み</span></button>` : ""}
      ${state.view === "table" ? `<button class="btn" data-act="cols" aria-label="表示する列">${icon("cols")}<span class="lbl">表示する列</span></button>` : ""}
    </div>`;
  const renderChips = (kind) => {
    const t = state.tables[kind];
    const chips = [];
    if (t.q) chips.push(`<span class="chip">キーワード: ${esc(t.q)}<button data-act="unq" aria-label="キーワードを解除">${icon("x")}</button></span>`);
    for (const [key, set] of Object.entries(t.filters)) {
      const col = COLUMNS[kind].find((c) => c.key === key);
      for (const v of set) chips.push(`<span class="chip">${esc(col.label)}: ${esc(v)}<button data-act="unchip" data-key="${esc(key)}" data-val="${esc(v)}" aria-label="${esc(col.label)}: ${esc(v)} の条件を解除">${icon("x")}</button></span>`);
    }
    return `<div class="chips">${chips.length ? chips.join("") + `<button class="btn ghost" data-act="clearall">すべて解除</button>` : ""}</div>`;
  };
  const renderTable = (kind) => {
    const t = state.tables[kind];
    const cols = visibleCols(kind);
    const pin = colPrefs(kind).pin;
    const rows = sortRows(kind, rowsFor(kind));
    const th = cols.map((c, i) => {
      const s = t.sort?.key === c.key ? t.sort.dir : null;
      const fOn = t.filters[c.key]?.size > 0;
      const sIcon = s === "asc" ? icon("up") : s === "desc" ? icon("down") : `<span class="sort-hint">${icon("updown")}</span>`;
      const pinned = i === pin - 1;
      return `<th scope="col" data-pri="${c.pri}" data-col="${i}" class="${c.num ? "num " : ""}${i < pin ? "pinned" : ""}" aria-sort="${s === "asc" ? "ascending" : s === "desc" ? "descending" : "none"}"${c.min ? ` style="min-width:${c.min}"` : ""}>
        <div class="th-in"><button class="th-sort" data-act="sort" data-key="${c.key}">${esc(c.label)}${sIcon}</button>
        ${c.filter ? `<button class="th-tool" data-act="colfilter" data-key="${c.key}" aria-pressed="${fOn}" aria-label="${esc(c.label)}で絞り込み">${icon("filter")}</button>` : ""}
        <button class="th-tool pin" data-act="pin" data-idx="${i}" aria-pressed="${pinned}" aria-label="${pinned ? `${esc(c.label)}までの固定を解除` : `${esc(c.label)}まで固定`}">${icon("pin")}</button></div></th>`;
    }).join("");
    const body = rows.length
      ? rows.map((r) => `<tr class="${r.status && CLOSED.has(r.status) ? "dim " : ""}${state.panel === r.id ? "selected" : ""}" data-id="${r.id}">${cols.map((c, i) =>
          `<td data-pri="${c.pri}" data-col="${i}" class="${c.num ? "num " : ""}${c.nowrap ? "nowrap " : ""}${i < pin ? "pinned" : ""}">${c.cell(r)}</td>`).join("")}</tr>`).join("")
      : `<tr><td colspan="${cols.length}" class="no-match-cell"><div class="no-match">該当する${KIND_NOUN[kind]}はありません。別の条件を試してください。</div></td></tr>`;
    return `<div class="table-wrap" data-kind="${kind}"><table class="grid"><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table></div>`;
  };
  const applyPins = () => {
    const wrap = document.querySelector(".table-wrap");
    if (!wrap) return;
    // 該当なしの文言は、横に送っても表の枠の幅で左に留める
    wrap.style.setProperty("--wrap-w", wrap.clientWidth + "px");
    const pin = colPrefs(wrap.dataset.kind).pin;
    let left = 0;
    [...wrap.querySelectorAll("thead th")].forEach((th, i) => {
      if (i >= pin) return;
      wrap.querySelectorAll(`[data-col="${i}"]`).forEach((el) => { el.style.left = left + "px"; el.classList.toggle("pin-edge", i === pin - 1); });
      left += th.getBoundingClientRect().width;
    });
  };

  // ===== ボード（タスク） =====
  const boardRows = (kind) => {
    const t = state.tables[kind], keep = t.showClosed;
    t.showClosed = true;
    const rows = rowsFor(kind);
    t.showClosed = keep;
    return rows;
  };
  const boardCard = (kind, r) => kind === "decisions"
    ? `<button class="card" data-act="open" data-id="${r.id}"><div class="c-ttl">${esc(r.title)}</div><div class="c-meta"><span class="mono">${r.id}</span><span>${esc(r.category)} · ${esc(r.stage)}</span>${impact(r.weight)}</div>${(r.depends_on || []).length ? `<div class="c-for">${r.depends_on.map((id) => `<div><span class="mono">${id}</span> ${esc(titleOf(id))}</div>`).join("")}</div>` : ""}</button>`
    : `<button class="card" data-act="open" data-id="${r.id}"><div class="c-ttl">${esc(r.title)}</div><div class="c-meta"><span class="mono">${r.id}</span><span>${esc(r.kind)}</span><span>${esc(r.category)}</span></div>${(r.for || []).length ? `<div class="c-for">${r.for.map((id) => `<div><span class="mono">${id}</span> ${esc(titleOf(id))}</div>`).join("")}</div>` : ""}</button>`;
  const renderBoard = (kind = "tasks") => {
    const rows = boardRows(kind);
    const cols = BOARD_COLS[kind];
    return `<div class="board" style="--cols:${cols.length}">${cols.map((st) => {
      const cards = rows.filter((r) => r.status === st);
      return `<section class="board-col" aria-label="${st}"><h3>${mark(st)}${st}<span class="n">${cards.length}</span></h3>${cards.length ? cards.map((r) => boardCard(kind, r)).join("") : `<p class="empty">なし</p>`}</section>`;
    }).join("")}</div>`;
  };

  // ===== 資料のカード =====
  const renderDocCards = () => {
    const rows = [...rowsFor("docs")].sort((a, b) => (b.deliverable ? 1 : 0) - (a.deliverable ? 1 : 0));
    return rows.length ? `<div class="doc-grid">${rows.map((r) => `<button class="card doc-card${r.deliverable ? " deliv-card" : ""}" data-act="open" data-id="${r.id}">${r.deliverable ? `<span class="deliv-badge">${icon("box")}成果物</span>` : ""}<span class="doc-kind">${icon(r.kind === "図" ? "graph" : "cards")}${esc(r.kind)}</span><span class="c-ttl">${esc(r.title)}</span><span class="c-meta"><span class="mono">${r.id}</span>${status(r.status)}<span>${esc(r.category)} · ${esc(r.stage)}</span></span>${(r.related || []).length ? `<span class="c-for">${r.related.map((id) => `<span><span class="mono">${id}</span> ${esc(titleOf(id))}</span>`).join("")}</span>` : ""}</button>`).join("")}</div>`
      : `<p class="no-match">該当する資料はありません。別の条件を試してください。</p>`;
  };

  // ===== マップ =====
  const NODE = { root: [220, 52], target: [130, 40], cat: [150, 34], stage: [118, 26], item: [236, 48] };
  const layoutCache = new Map();
  const mapItems = () => M.decisions.filter((d) => state.mapShow.has(d.status));
  // 対象 → カテゴリー → フェーズ → 検討事項 の木を ELK の入力にする
  const buildGraph = (items) => {
    const nodes = [], edges = [];
    const add = (id, kind, label, extra = {}) => nodes.push({ id, width: NODE[kind][0], height: NODE[kind][1], kind, label, ...extra });
    add("root", "root", W.summary);
    for (const t of W.targets) {
      const tid = "t:" + t.name;
      const cats = W.categories.filter((c) => c.target === t.name && items.some((d) => d.category === c.name));
      if (!cats.length) continue;
      add(tid, "target", t.name); edges.push({ id: `root>${tid}`, sources: ["root"], targets: [tid] });
      for (const c of cats) {
        const cid = "c:" + c.name;
        add(cid, "cat", c.name); edges.push({ id: `${tid}>${cid}`, sources: [tid], targets: [cid] });
        for (const s of STAGES) {
          const ds = items.filter((d) => d.category === c.name && d.stage === s);
          if (!ds.length) continue;
          const sid = `s:${c.name}:${s}`;
          add(sid, "stage", s); edges.push({ id: `${cid}>${sid}`, sources: [cid], targets: [sid] });
          for (const d of ds) { add(d.id, "item", d.title, { d }); edges.push({ id: `${sid}>${d.id}`, sources: [sid], targets: [d.id] }); }
        }
      }
    }
    return { id: "graph", layoutOptions: { "elk.algorithm": "layered", "elk.direction": "RIGHT", "elk.edgeRouting": "ORTHOGONAL", "elk.layered.spacing.nodeNodeBetweenLayers": "36", "elk.spacing.nodeNode": "10", "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES", "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF", "elk.layered.nodePlacement.bk.fixedAlignment": "BALANCED", "elk.padding": "[top=24,left=24,bottom=24,right=24]" }, children: nodes, edges };
  };
  const layoutKey = () => [...state.mapShow].sort().join(",");
  const ensureLayout = async () => {
    const key = layoutKey();
    if (layoutCache.has(key)) return layoutCache.get(key);
    const res = await new window.ELK().layout(buildGraph(mapItems()));
    layoutCache.set(key, res);
    return res;
  };
  const depPath = (a, b) => {
    // 同じ列どうしは、節の右側にふくらむ弧でつなぐ
    if (Math.abs(a.x - b.x) < 10) {
      const x = a.x + a.width, y1 = a.y + a.height / 2, y2 = b.y + b.height / 2, bulge = 28 + Math.min(60, Math.abs(y2 - y1) / 6);
      return `M${x},${y1} C${x + bulge},${y1} ${x + bulge},${y2} ${x},${y2}`;
    }
    const x1 = a.x + a.width, y1 = a.y + a.height / 2, x2 = b.x, y2 = b.y + b.height / 2;
    const dx = Math.max(60, Math.abs(x2 - x1) / 2);
    return `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;
  };
  let mapParent = new Map();
  // フォーカスした節について、根までの枝と前提・後続の依存の線を強調し、ほかを薄くする
  const highlight = (id) => {
    const canvas = document.getElementById("map-canvas");
    if (!canvas) return;
    canvas.querySelectorAll(".rel").forEach((el) => el.classList.remove("rel"));
    canvas.classList.toggle("focusing", !!id);
    if (!id) return;
    const chain = new Set([id]);
    for (let x = id; mapParent.has(x); x = mapParent.get(x)) chain.add(mapParent.get(x));
    const near = new Set(chain);
    canvas.querySelectorAll(".edge-dep").forEach((el) => {
      if (el.dataset.s === id || el.dataset.t === id) { el.classList.add("rel"); near.add(el.dataset.s); near.add(el.dataset.t); }
    });
    canvas.querySelectorAll(".edge-tree").forEach((el) => { if (chain.has(el.dataset.s) && chain.has(el.dataset.t)) el.classList.add("rel"); });
    canvas.querySelectorAll("[data-node]").forEach((el) => { if (near.has(el.dataset.node)) el.classList.add("rel"); });
  };
  let lastMapSel;
  const drawMap = (g, keep) => {
    const canvas = document.getElementById("map-canvas");
    if (!canvas) return;
    const pos = new Map(g.children.map((n) => [n.id, n]));
    const sel = state.panel && pos.has(state.panel) ? state.panel : null;
    const tree = g.edges.map((e) => {
      const s = e.sections[0];
      const pts = [s.startPoint, ...(s.bendPoints || []), s.endPoint];
      return `<path class="edge-tree" data-s="${esc(e.sources[0])}" data-t="${esc(e.targets[0])}" d="M${pts.map((p) => `${p.x},${p.y}`).join(" L")}"/>`;
    }).join("");
    // 依存の線: 前提 → 後続。選んだ項目に関わる線だけを強め、線の上を点が流れる
    const deps = [];
    for (const n of g.children) {
      if (n.kind !== "item") continue;
      for (const pre of n.d.depends_on || []) {
        if (!pos.has(pre)) continue;
        if (!state.deps && !(sel && (sel === pre || sel === n.id))) continue;
        const pid = `dep-${pre}-${n.id}`;
        deps.push(`<path id="${pid}" class="edge-dep" data-s="${esc(pre)}" data-t="${esc(n.id)}" d="${depPath(pos.get(pre), n)}"/>`);
      }
    }
    const nodes = g.children.map((n) => {
      const style = `left:${n.x}px;top:${n.y}px;width:${n.width}px;height:${n.height}px`;
      if (n.kind !== "item") return `<div class="map-node n-${n.kind}" data-node="${esc(n.id)}" style="${style}"><span class="lbl">${esc(n.label)}</span></div>`;
      const d = n.d;
      return `<button class="map-node n-item${sel === d.id ? " sel" : ""}${CLOSED.has(d.status) ? " off" : ""}${mapHit(d) ? " hit" : ""}" data-node="${d.id}" style="${style}" data-act="open" data-id="${d.id}" title="${esc(d.title)}（${esc(d.status)}）"><span class="r1">${mark(d.status)}<span class="lbl">${esc(d.title)}</span></span><span class="r2"><span class="mono">${d.id}</span><span>${esc(d.status)}</span><span>影響度 ${esc(d.weight)}</span></span></button>`;
    }).join("");
    // 拡大率: 「全体を表示」は、マップの枠に木の全体が収まる倍率にする
    const wrap = document.getElementById("map-wrap");
    const z = state.zoom === "fit" ? Math.min(1, (wrap.clientWidth - 16) / g.width, (wrap.clientHeight - 16) / g.height) : state.zoom;
    const sizer = document.getElementById("map-sizer");
    sizer.style.width = g.width * z + 240 + "px";
    sizer.style.height = g.height * z + 160 + "px";
    canvas.style.width = g.width + "px";
    canvas.style.height = g.height + "px";
    canvas.style.transform = `scale(${z})`;
    canvas.innerHTML = `<svg class="edges" width="${g.width}" height="${g.height}" aria-hidden="true">${tree}${deps.join("")}</svg>${nodes}`;
    mapParent = new Map(g.edges.map((e) => [e.targets[0], e.sources[0]]));
    // 選んだ項目からつながる依存の線の上に、選んだ項目から外へ向かって小さな玉を流す
    if (sel) {
      const svg = canvas.querySelector("svg.edges");
      svg.querySelectorAll(".edge-dep").forEach((el) => {
        const out = el.dataset.s === sel, inn = el.dataset.t === sel;
        if (!out && !inn) return;
        for (const begin of [0, 0.8]) svg.insertAdjacentHTML("beforeend", `<circle class="flow-dot" r="2.6"><animateMotion dur="3.2s" begin="${begin * 2}s" repeatCount="indefinite" ${inn ? 'keyPoints="1;0" keyTimes="0;1" calcMode="linear"' : ""}><mpath href="#${el.id}"/></animateMotion></circle>`);
      });
    }
    highlight(sel);
    // 選んだ項目が変わったら、その節がマップの中央に来るように送る（ページ自体は動かさない）
    if (sel && sel !== lastMapSel) {
      const n = pos.get(sel);
      wrap.scrollTo({ left: (n.x + n.width / 2) * z - wrap.clientWidth / 2, top: (n.y + n.height / 2) * z - wrap.clientHeight / 2 });
    } else if (!sel && lastMapSel === undefined) {
      // 開いた直後は根が見える位置にする
      const r = pos.get("root");
      wrap.scrollTo({ left: 0, top: (r.y + r.height / 2) * z - wrap.clientHeight / 2 });
    } else if (keep) wrap.scrollTo({ left: keep.l || 0, top: keep.t || 0 });
    lastMapSel = sel;
  };
  const mapHit = (d) => !!state.mapQ && d.title.toLowerCase().includes(state.mapQ.toLowerCase());
  const mapToolbar = () => {
    const counts = Object.fromEntries(STATUS_ORDER.map((s) => [s, M.decisions.filter((d) => d.status === s).length]));
    const hits = Object.fromEntries(STATUS_ORDER.map((s) => [s, M.decisions.filter((d) => d.status === s && mapHit(d)).length]));
    const legend = STATUS_ORDER.filter((s) => counts[s]).map((s) =>
      `<label><input type="checkbox" data-act="mapst" value="${s}" ${state.mapShow.has(s) ? "checked" : ""}>${mark(s)}${s}<span class="n">${counts[s]}</span>${hits[s] ? `<span class="hit-n" aria-label="キーワードに当たった項目 ${hits[s]} 件">${hits[s]}</span>` : ""}</label>`).join("");
    const toggle = `<button class="btn" data-act="deps" aria-pressed="${state.deps}" title="依存関係の線を表示">${icon("deps")}<span class="lbl">依存関係</span></button>`;
    return `<div class="toolbar">${segment("decisions")}<label class="sr-only" for="map-q">名前で強調するキーワード</label><input class="input map-q" id="map-q" data-act="mapq" type="search" placeholder="名前で強調" value="${esc(state.mapQ)}"><span class="spacer"></span>${toggle}</div>
      <div class="map-tools"><div class="legend" role="group" aria-label="表示する状態">${legend}</div></div>`;
  };
  const renderMapShell = () => {
    // 狭い幅で使う、字下げした縦の一覧
    const items = mapItems();
    const outline = `<ul>${W.targets.map((t) => `<li><div class="o-t">${esc(t.name)}</div><ul>${W.categories.filter((c) => c.target === t.name && items.some((d) => d.category === c.name)).map((c) =>
      `<li><div class="o-c">${esc(c.name)}</div><ul>${STAGES.filter((s) => items.some((d) => d.category === c.name && d.stage === s)).map((s) =>
        `<li><div class="o-s">${esc(s)}</div><ul>${items.filter((d) => d.category === c.name && d.stage === s).map((d) =>
          `<li><button data-act="open" data-id="${d.id}">${mark(d.status)}<span>${esc(d.title)}</span></button></li>`).join("")}</ul></li>`).join("")}</ul></li>`).join("")}</ul></li>`).join("")}</ul>`;
    return `${mapToolbar()}
      ${libOk("ELK") ? "" : libError(["elkjs"], "マップ", "表示形式を表に切り替えると、検討事項を読めます。")}
      <div class="map-frame"${libOk("ELK") ? "" : " hidden"}><div class="map-wrap" id="map-wrap"><div class="map-sizer" id="map-sizer"><div class="map-canvas" id="map-canvas" role="group" aria-label="検討事項のマップ"></div></div></div>
        <div class="zoom" role="group" aria-label="拡大率"><button class="icon-btn" data-act="zoom" data-z="out" aria-label="縮小">−</button><button class="btn ghost" data-act="zoom" data-z="fit" aria-pressed="${state.zoom === "fit"}">全体を表示</button><button class="icon-btn" data-act="zoom" data-z="in" aria-label="拡大">＋</button></div></div>
      <nav class="map-outline" aria-label="検討事項の一覧">${outline}</nav>`;
  };

  // ===== つながり: すべての項目と関連を、軽い自前の 3D（キャンバスへの透視投影）で見る =====
  // 線の種類: 見た目（実線・点線・破線・一点鎖線）で見分ける
  const LINK_TYPES = [["dep", "依存", "前提 → 後続"], ["rel", "関連", "関連として挙げた項目"], ["src", "根拠", "会話ログ・調査から"], ["for", "進めるタスク", "タスク → 進める検討事項"]];
  const LINK_DASH = { dep: [], rel: [1.5, 3], src: [6, 4], for: [10, 3, 2, 3] };
  const linkSample = (k) => `<svg class="ls" viewBox="0 0 28 6" aria-hidden="true"><path d="M1 3h26" stroke="currentColor" stroke-width="1.8" stroke-dasharray="${LINK_DASH[k].join(" ")}" fill="none"/></svg>`;
  const linkTypesPop = () => `<h3>表示する線の種類</h3>${LINK_TYPES.map(([k, l, d]) => `<label><input type="checkbox" data-act="ltype" value="${k}" ${state.linkTypes.has(k) ? "checked" : ""}>${linkSample(k)}<span>${l}<span class="ls-sub">${d}</span></span></label>`).join("")}`;
  const KIND_VAR = { decisions: "--k-dec", tasks: "--k-task", research: "--k-res", docs: "--k-doc", terms: "--k-term", notes: "--k-note", logs: "--k-log" };
  state.graphKinds ??= new Set(["decisions", "tasks", "research", "docs", "logs"]);
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const allLinks = () => {
    const out = [], seen = new Set();
    const add = (a, b, type) => {
      if (!byId.has(a) || !byId.has(b) || a === b) return;
      const key = [a, b].sort().join("|");
      if (seen.has(key)) return;
      seen.add(key); out.push({ a, b, type });
    };
    for (const { it } of byId.values()) {
      for (const d of it.depends_on || []) add(d, it.id, "dep");
      for (const d of it.for || []) add(it.id, d, "for");
      for (const d of it.sources || []) add(d, it.id, "src");
      if (it.result) add(it.id, it.result, "src");
      for (const d of it.related || []) add(it.id, d, "rel");
    }
    return out;
  };
  let G = null;  // 描いているグラフの状態（タブを離れたら捨てる）
  const it = (n) => n.it.title;
  const FONT_N = '400 10px "JetBrains Mono", "Noto Sans JP", monospace';
  const FONT_B = '500 10px "JetBrains Mono", "Noto Sans JP", monospace';
  const buildGraph3 = () => {
    const nodes = [...byId.values()].filter(({ kind, it }) => state.graphKinds.has(kind) && !CLOSED.has(it.status))
      .map(({ kind, it }, i, arr) => {
        // 球面上に散らして置く（黄金角の螺旋）
        const t = (i + 0.5) / arr.length, phi = Math.acos(1 - 2 * t), th = Math.PI * (1 + Math.sqrt(5)) * i;
        return { id: it.id, kind, it, x: 120 * Math.sin(phi) * Math.cos(th), y: 120 * Math.cos(phi), z: 120 * Math.sin(phi) * Math.sin(th), vx: 0, vy: 0, vz: 0, deg: 0 };
      });
    const idx = new Map(nodes.map((n, i) => [n.id, i]));
    const links = allLinks().filter((l) => state.linkTypes.has(l.type) && idx.has(l.a) && idx.has(l.b)).map((l) => ({ ...l, s: nodes[idx.get(l.a)], t: nodes[idx.get(l.b)] }));
    for (const l of links) { l.s.deg++; l.t.deg++; }
    for (const n of nodes) { n.r = 4 + Math.sqrt(n.deg) * 2.2; n.label = it(n).length > 22 ? it(n).slice(0, 21) + "…" : it(n); }
    return {
      nodes, idx, links,
      // 回転は「目標」と「今」を分け、今を目標へ毎コマ少しずつ寄せる（動き出しも止まり際もなめらかにする）
      rot: { yaw: 0.6, pitch: -0.25, yawT: 0.6, pitchT: -0.25, vy: 0, vp: 0 },
      dist: 520, distT: 520, center: { x: 0, y: 0, z: 0 }, centerT: { x: 0, y: 0, z: 0 },
      born: performance.now(), lastInput: 0, hover: null, focus: null, alpha: 1,
    };
  };
  // 力学の 1 歩: 互いに離れ、線でつながったものは引き合い、中心へ寄る。注目している項目のつながりは近くへ引き寄せる
  const stepForces = (g) => {
    const ns = g.nodes, sel = g.focus;
    if (g.alpha < 0.004) return;
    for (let i = 0; i < ns.length; i++) for (let j = i + 1; j < ns.length; j++) {
      const a = ns[i], b = ns[j]; let dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
      const d2 = dx * dx + dy * dy + dz * dz + 1, f = (4400 / d2) * g.alpha;
      dx *= f; dy *= f; dz *= f; a.vx += dx; a.vy += dy; a.vz += dz; b.vx -= dx; b.vy -= dy; b.vz -= dz;
    }
    for (const l of g.links) {
      const near = sel && (l.a === sel || l.b === sel);
      const want = near ? 48 : l.type === "dep" ? 84 : l.type === "rel" ? 140 : 110;
      let dx = l.t.x - l.s.x, dy = l.t.y - l.s.y, dz = l.t.z - l.s.z;
      const d = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1, k = ((d - want) / d) * (near ? 0.018 : 0.03) * g.alpha;
      dx *= k; dy *= k; dz *= k;
      // 注目している項目自体は動かさず、つながる側だけを寄せる
      if (l.a !== sel) { l.s.vx += dx; l.s.vy += dy; l.s.vz += dz; }
      if (l.b !== sel) { l.t.vx -= dx; l.t.vy -= dy; l.t.vz -= dz; }
    }
    for (const n of ns) {
      if (n.id === sel) { n.vx = n.vy = n.vz = 0; continue; }
      n.vx -= n.x * 0.012 * g.alpha; n.vy -= n.y * 0.012 * g.alpha; n.vz -= n.z * 0.012 * g.alpha;
      n.vx *= 0.9; n.vy *= 0.9; n.vz *= 0.9; n.x += n.vx * 0.28; n.y += n.vy * 0.28; n.z += n.vz * 0.28;
    }
    g.alpha *= 0.994;
  };
  // 注目（マウスを乗せる・選ぶ）が変わったら、つながりが寄ってくるよう少し動かす
  const setFocus = (id) => {
    if (!G || G.focus === id) return;
    G.focus = id;
  };
  const PULL_KEEP = 0.45;  // 寄せた先: 元の距離の 45% のところ
  const PULL_EASE = 0.03;  // 毎コマ、目標へ 3% ずつ寄せる
  // 注目している玉につながる玉を、注目している玉の近くへゆっくり寄せる。注目が外れると元の位置へ戻す
  const pullNear = (g) => {
    const sel = g.focus && g.idx.has(g.focus) ? g.focus : null;
    const near = new Set();
    if (sel) for (const l of g.links) { if (l.a === sel) near.add(l.b); if (l.b === sel) near.add(l.a); }
    const S = sel ? g.nodes[g.idx.get(sel)].home : null;
    for (const n of g.nodes) {
      const h = n.home;
      const t = S && near.has(n.id) ? { x: S.x + (h.x - S.x) * PULL_KEEP, y: S.y + (h.y - S.y) * PULL_KEEP, z: S.z + (h.z - S.z) * PULL_KEEP } : h;
      n.x += (t.x - n.x) * PULL_EASE; n.y += (t.y - n.y) * PULL_EASE; n.z += (t.z - n.z) * PULL_EASE;
    }
  };
  const graphSelect = () => {
    if (!G) return;
    const n = G.nodes[G.idx.get(state.panel)];
    setFocus(n ? n.id : G.hover?.id ?? null);
    G.distT = n ? G.fit * 0.38 : G.fit;
    if (!n) G.centerT = { x: 0, y: 0, z: 0 };
  };
  const graphColors = () => {
    const v = (k) => css(k);
    return { kind: Object.fromEntries(Object.entries(KIND_VAR).map(([k, x]) => [k, v(x)])), label: v("--g-label"), line: v("--g-line"), dot: v("--g-dot"), ring: v("--accent") };
  };
  const drawGraph3 = () => {
    const cv = document.getElementById("fg3");
    if (!cv) return;
    G = buildGraph3();
    for (let i = 0; i < 260; i++) stepForces(G);   // 先に形を整えてから見せる
    // 形を整えた位置を元の位置として覚え、以降は力の計算を止める
    for (const n of G.nodes) n.home = { x: n.x, y: n.y, z: n.z };
    G.alpha = 0;
    // 全体が枠に収まる距離（外れた玉に引っぱられないよう、近い順に 9 割目の玉までの半径を使う）
    const radii = G.nodes.map((n) => Math.hypot(n.x, n.y, n.z)).sort((a, b) => a - b);
    const R = Math.max(40, radii[Math.floor(radii.length * 0.9)] || 40);
    G.fit = G.dist = G.distT = ((700 * R) / (Math.min(cv.clientWidth, cv.clientHeight) * 0.42) + R * 0.4) * 0.72;
    G.colors = graphColors();
    if (state.panel) graphSelect();
    const ctx = cv.getContext("2d");
    let W = 0, H = 0, dpr = 1;
    const resize = () => { dpr = Math.min(2, devicePixelRatio || 1); W = cv.clientWidth; H = cv.clientHeight; cv.width = W * dpr; cv.height = H * dpr; };
    resize(); new ResizeObserver(resize).observe(cv);
    const f0 = () => 700 / G.fit;  // 全体が収まる距離で見たときの倍率（玉と文字の大きさの基準）
    const proj = (n) => {
      const c = G.center, x = n.x - c.x, y = n.y - c.y, z = n.z - c.z;
      const cy = Math.cos(G.rot.yaw), sy = Math.sin(G.rot.yaw), cp = Math.cos(G.rot.pitch), sp = Math.sin(G.rot.pitch);
      const x1 = x * cy - z * sy, z1 = x * sy + z * cy, y1 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
      const f = 700 / (z2 + G.dist);
      return { sx: W / 2 + x1 * f, sy: H / 2 + y1 * f, f, z: z2 };
    };
    // 画面の向きのずれを、いまの向きで世界の座標のずれに戻す
    const screenToWorld = (dx, dy) => {
      const cy = Math.cos(G.rot.yaw), sy = Math.sin(G.rot.yaw), cp = Math.cos(G.rot.pitch), sp = Math.sin(G.rot.pitch);
      const y = dy * cp, z1 = -dy * sp;
      return { x: dx * cy + z1 * sy, y, z: -dx * sy + z1 * cy };
    };
    const radOf = (n, p) => n.r * 1.05 * (p.f / f0());
    const onScreen = (x, y, m) => x > -m && y > -m && x < W + m && y < H + m;
    const hit = (x, y) => {
      let best = null, bd = 1e9;
      for (const n of G.nodes) { const p = proj(n); if (p.z + G.dist <= 10) continue; if (Math.hypot(p.sx - x, p.sy - y) < Math.max(8, radOf(n, p)) + 4 && p.z < bd) { best = n; bd = p.z; } }
      return best;
    };
    // 操作: ドラッグは目標の向きを動かし、離すと勢いが少しずつ弱まりながら回り続ける
    let drag = null, moved = 0;
    cv.onpointerdown = (e) => { drag = { x: e.clientX, y: e.clientY, t: performance.now() }; moved = 0; cv.setPointerCapture(e.pointerId); G.lastInput = performance.now(); G.rot.vy = G.rot.vp = 0; };
    cv.onpointermove = (e) => {
      const r = cv.getBoundingClientRect();
      if (drag) {
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y, now = performance.now(), dt = Math.max(8, now - drag.t);
        moved += Math.abs(dx) + Math.abs(dy);
        G.rot.yawT += dx * 0.0032; G.rot.pitchT = Math.max(-1.3, Math.min(1.3, G.rot.pitchT + dy * 0.0032));
        G.rot.vy = (dx * 0.0032) * (16 / dt); G.rot.vp = (dy * 0.0032) * (16 / dt);
        drag = { x: e.clientX, y: e.clientY, t: now }; G.lastInput = now;
        return;
      }
      const h = hit(e.clientX - r.left, e.clientY - r.top);
      if (h !== G.hover) { G.hover = h; if (!state.panel) setFocus(h ? h.id : null); }
      cv.style.cursor = h ? "pointer" : "grab";
    };
    cv.onpointerleave = () => { if (!drag && G.hover) { G.hover = null; if (!state.panel) setFocus(null); } };
    cv.onpointerup = (e) => {
      const r = cv.getBoundingClientRect();
      if (drag && moved < 5) { const h = hit(e.clientX - r.left, e.clientY - r.top); if (h) openPanel(h.id); else if (state.panel) closePanel(); }
      if (drag && performance.now() - drag.t > 80) G.rot.vy = G.rot.vp = 0;  // 止めてから離したときは滑らせない
      drag = null;
    };
    // ホイール: マウスのある位置へ向かって寄る・離れる（距離も中心も目標へなめらかに寄せる）
    cv.onwheel = (e) => {
      e.preventDefault();
      const r = cv.getBoundingClientRect(), mx = e.clientX - r.left - W / 2, my = e.clientY - r.top - H / 2;
      const old = G.distT, next = Math.max(G.fit * 0.15, Math.min(G.fit * 2.5, old * Math.exp(e.deltaY * 0.0016)));
      if (!state.panel) {
        const f = 700 / old, w = screenToWorld((mx / f) * (1 - next / old), (my / f) * (1 - next / old));
        G.centerT = { x: G.centerT.x + w.x, y: G.centerT.y + w.y, z: G.centerT.z + w.z };
      }
      G.distT = next; G.lastInput = performance.now();
      // 中心は群れの中に収める
      const lim = G.fit * 0.35, m = Math.hypot(G.centerT.x, G.centerT.y, G.centerT.z);
      if (m > lim) G.centerT = { x: (G.centerT.x * lim) / m, y: (G.centerT.y * lim) / m, z: (G.centerT.z * lim) / m };
      if (next >= G.fit * 0.95 && !state.panel) G.centerT = { x: 0, y: 0, z: 0 };
    };
    cv.ondblclick = () => { if (!state.panel) { G.centerT = { x: 0, y: 0, z: 0 }; G.distT = G.fit; } };
    const frame = (now) => {
      if (!G || !document.getElementById("fg3")) { G = null; return; }
      if (document.hidden) { requestAnimationFrame(frame); return; }
      pullNear(G);
      const R0 = G.rot;
      if (!drag) {
        // 離した後の滑り（勢いはゆっくり弱まる）と、何もしていないときのごくゆっくりした自動の回転
        R0.yawT += R0.vy; R0.pitchT = Math.max(-1.3, Math.min(1.3, R0.pitchT + R0.vp));
        R0.vy *= 0.955; R0.vp *= 0.93;
        if (now - G.lastInput > 2500 && !G.hover) R0.yawT += 0.00018;
      }
      R0.yaw += (R0.yawT - R0.yaw) * 0.07; R0.pitch += (R0.pitchT - R0.pitch) * 0.07;
      const n0 = G.nodes[G.idx.get(state.panel)];
      if (n0) G.centerT = { x: n0.x, y: n0.y, z: n0.z };
      for (const k of ["x", "y", "z"]) G.center[k] += (G.centerT[k] - G.center[k]) * 0.025;
      G.dist += (G.distT - G.dist) * 0.04;
      const born = Math.min(1, (now - G.born) / 1400), ease = 1 - Math.pow(1 - born, 3);  // 開いたときは中心から広がる
      const sel = G.focus && G.idx.has(G.focus) ? G.focus : null;
      const near = new Set(sel ? [sel] : []);
      if (sel) for (const l of G.links) { if (l.a === sel) near.add(l.b); if (l.b === sel) near.add(l.a); }
      const C = G.colors, k0 = f0();

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      const P = new Map(G.nodes.map((n) => [n.id, proj({ x: n.x * ease + G.center.x * (1 - ease), y: n.y * ease + G.center.y * (1 - ease), z: n.z * ease + G.center.z * (1 - ease) })]));
      // つながる玉どうしを、ごく薄い線で結ぶ（遠いほど薄い）
      ctx.lineWidth = 0.9; ctx.strokeStyle = C.line;
      for (const l of G.links) {
        ctx.setLineDash(LINK_DASH[l.type]);
        const a = P.get(l.a), b = P.get(l.b);
        if (a.z + G.dist <= 10 || b.z + G.dist <= 10) continue;
        if ((a.sx < 0 && b.sx < 0) || (a.sx > W && b.sx > W) || (a.sy < 0 && b.sy < 0) || (a.sy > H && b.sy > H)) continue;
        const dep = Math.max(0, Math.min(1, 1.25 - ((a.z + b.z) / 2 + G.dist) / (G.dist * 2.2)));
        ctx.globalAlpha = 0.32 * dep * Math.min(l.s.fade ?? 1, l.t.fade ?? 1);
        ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy); ctx.stroke();
      }
      // 注目している項目とつながる線と、そこを流れる小さな玉（注目している項目から外へ、ゆっくり）
      if (sel) for (const l of G.links) {
        if (l.a !== sel && l.b !== sel) continue;
        const from = P.get(sel), to = P.get(l.a === sel ? l.b : l.a);
        if (from.z + G.dist <= 10 || to.z + G.dist <= 10) continue;
        ctx.globalAlpha = 1; ctx.strokeStyle = C.line; ctx.lineWidth = 1.3; ctx.setLineDash(LINK_DASH[l.type]);
        ctx.beginPath(); ctx.moveTo(from.sx, from.sy); ctx.lineTo(to.sx, to.sy); ctx.stroke(); ctx.setLineDash([]);
        for (const off of [0, 0.5]) {
          const t = ((now / 4200) + off + (l.a.length % 7) * 0.13) % 1;
          ctx.globalAlpha = 0.9 * Math.sin(Math.PI * t); ctx.fillStyle = C.dot;
          ctx.beginPath(); ctx.arc(from.sx + (to.sx - from.sx) * t, from.sy + (to.sy - from.sy) * t, 1.8, 0, Math.PI * 2); ctx.fill();
        }
      }
      ctx.setLineDash([]);
      // 奥から順に描く。遠いほど小さく薄く、注目しているときはつながらないものを沈める
      const order = [...G.nodes].sort((a, b) => P.get(b.id).z - P.get(a.id).z);
      ctx.textAlign = "center"; ctx.textBaseline = "bottom"; ctx.letterSpacing = "0.8px";
      for (const n of order) {
        const p = P.get(n.id);
        if (p.z + G.dist <= 10) continue;
        const r0 = radOf(n, p);
        if (!onScreen(p.sx, p.sy, r0 + 40) || r0 > Math.max(W, H)) continue;
        const depth = Math.max(0.15, Math.min(1, 1.25 - (p.z + G.dist) / (G.dist * 2.2)));
        n.fade ??= 1;
        n.fade += ((sel && !near.has(n.id) ? 0.18 : 1) - n.fade) * 0.03;
        const dim = n.fade;
        // 文字の大きさは画面全体の拡大率で揃える（手前の玉だけ文字が巨大にならないように）
        const rad = Math.max(1.2, radOf(n, p) * ease);
        // 手前に来すぎた玉は薄くして、奥を隠さないようにする
        const close = Math.min(1, Math.max(0, ((p.z + G.dist) / G.dist - 0.08) / 0.2));
        if (close <= 0.02) continue;
        ctx.globalAlpha = (0.35 + 0.55 * depth) * dim * close;
        ctx.fillStyle = C.kind[n.kind];
        ctx.beginPath(); ctx.arc(p.sx, p.sy, rad, 0, Math.PI * 2); ctx.fill();
        if (n.id === state.panel || n === G.hover) { ctx.globalAlpha = 0.9; ctx.strokeStyle = C.ring; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(p.sx, p.sy, rad + 4, 0, Math.PI * 2); ctx.stroke(); }
        // 名前: 大きさは拡大率に合わせる。いつもは薄く、注目している項目とつながる項目ははっきり出す
        const strong = near.has(n.id) || n === G.hover;
        // 文字は玉と同じ倍率で大きさが変わる。玉の幅に英字 6 文字ほどが入る大きさにする
        const sc = p.f / k0, fs = 4.6 * sc;
        const la = (strong ? 0.85 : 0.42 * dim) * Math.pow(depth, 1.4) * Math.max(0, Math.min(1, (fs - 3.5) / 2.5));
        if (la > 0.03 && ease > 0.9 && onScreen(p.sx, p.sy - rad, 400)) {
          ctx.globalAlpha = la * close; ctx.fillStyle = n.id === state.panel ? C.ring : C.label;
          ctx.font = n.id === state.panel || n === G.hover ? FONT_B : FONT_N;
          ctx.setTransform(dpr * fs / 10, 0, 0, dpr * fs / 10, dpr * p.sx, dpr * (p.sy - rad - 3 * sc));
          ctx.fillText(n.label, 0, 0);
          ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }
      }
      ctx.globalAlpha = 1;
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  };
  const renderGraphTab = () => {
    const counts = Object.fromEntries(Object.keys(KIND_VAR).map((k) => [k, M[k].filter((it) => !CLOSED.has(it.status)).length]));
    const chips = Object.keys(KIND_VAR).map((k) => `<label><input type="checkbox" data-act="gkind" value="${k}" ${state.graphKinds.has(k) ? "checked" : ""}><span class="kdot" style="background:var(${KIND_VAR[k]})"></span>${KINDS.find((x) => x.key === k).label}<span class="n">${counts[k]}</span></label>`).join("");
    return `<div class="map-tools"><div class="legend" role="group" aria-label="表示する種類">${chips}</div><span class="spacer"></span>
      <button class="btn" type="button" data-act="ltypes" aria-haspopup="true">${icon("filter")}線の種類<span class="mono">${state.linkTypes.size}/${LINK_TYPES.length}</span></button></div>
      <div class="map-frame space" data-bg="nebula"><canvas class="g3-wrap" id="fg3" role="img" aria-label="すべての項目のつながり"></canvas></div>`;
  };

  // ===== 詳細パネル =====
  const list = (ids) => (ids && ids.length)
    ? `<ul class="d-list">${ids.map((id) => `<li>${idlinks([id])}<span class="t">${esc(titleOf(id))}</span>${status(byId.get(id)?.it.status)}</li>`).join("")}</ul>` : `<p class="empty">なし</p>`;
  const sec = (label, html) => `<section class="d-sec"><h3>${label}</h3>${html}</section>`;
  const options = (opts) => opts.map((o) => {
    const res = o.adopted === true ? "採用" : o.adopted === false ? "不採用" : "検討中";
    const rows = [["メリット", o.pros], ["デメリット", o.cons], ["備考", o.note], ["理由", o.reason]].filter(([, v]) => v);
    return `<div class="opt ${o.adopted === true ? "adopted" : o.adopted === false ? "rejected" : ""}"><div class="o-head"><span class="key">${esc(o.key)}</span>${esc(o.content)}<span class="res">${res}</span></div>${rows.length ? `<dl>${rows.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>` : ""}</div>`;
  }).join("");
  const renderPanelBody = (id) => {
    const { kind, it } = byId.get(id);
    const meta = [[TARGET, it.target], ["カテゴリー", it.category], ["フェーズ", it.stage], ["影響度", it.weight], ["種類", it.kind], ["確度", it.confidence], ["日付", it.date], ["更新日", it.updated]]
      .filter(([, v]) => v).map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("") + (it.tags?.length ? `<dt>タグ</dt><dd>${tags(it.tags)}</dd>` : "");
    let h = "";
    if (kind === "decisions") {
      h += it.lead ? `<p class="d-lead">${esc(it.lead)}</p>` : "";
      h += it.answer ? `<div class="d-answer"><b>決定内容</b>${esc(it.answer)}</div>` : "";
      h += it.reason ? `<div class="d-answer"><b>理由</b>${esc(it.reason)}</div>` : "";
      h += it.options?.length ? sec("案", options(it.options)) : "";
      h += it.body ? sec("本文", renderMd(M.bodies[it.body])) : "";
      h += sec("前提", list(it.depends_on));
      h += sec("後続の項目", list(dependents.get(id)));
      h += sec("関連タスク", list(M.tasks.filter((t) => (t.for || []).includes(id)).map((t) => t.id)));
      h += it.sources?.length ? sec("経緯（会話ログ）", list(it.sources)) : "";
    } else if (kind === "tasks") {
      h += it.reason ? `<div class="d-answer"><b>理由</b>${esc(it.reason)}</div>` : "";
      h += sec("関連する検討事項", list(it.for));
      h += sec("前提", list(it.depends_on));
      h += it.result ? sec("結果", list([it.result])) : "";
    } else if (kind === "research") {
      h += `<p class="d-lead">${esc(it.question)}</p><div class="d-answer"><b>結論</b>${esc(it.conclusion)}</div>`;
      h += it.angles?.length ? sec("調査の観点", tags(it.angles)) : "";
      h += it.body ? sec("本文", renderMd(M.bodies[it.body])) : "";
    } else if (kind === "docs") {
      h += sec("本文", renderMd(M.bodies[it.body]));
    } else if (kind === "terms") {
      h += `<div class="d-answer"><b>意味</b>${esc(it.meaning)}</div>` + sec("別名", tags(it.aliases) || '<p class="empty">なし</p>') + sec("使わない表記", tags(it.avoid) || '<p class="empty">なし</p>');
    } else if (kind === "notes") {
      h += `<p>${esc(it.content)}</p>`;
    } else if (kind === "logs") {
      h += it.body ? sec("要約", renderMd(M.bodies[it.body])) : sec("要約", '<p class="empty">なし</p>');
    }
    if (it.links?.length) h += sec("リンク", `<ul class="d-list">${it.links.map((l) => `<li>${icon("link")}<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.title)}</a></li>`).join("")}</ul>`);
    if (it.related?.length) h += sec(kind === "logs" ? "更新した項目" : "関連", list(it.related));
    const back = referrers(id).filter((x) => !(it.related || []).includes(x) && !(dependents.get(id) || []).includes(x));
    if (back.length) h += sec("この項目を参照している項目", list(back));
    return `${status(it.status)}${it.deliverable ? `<span class="deliv-badge">${icon("box")}成果物</span>` : ""}<h2 class="d-title">${esc(it.title)}</h2><dl class="d-meta">${meta}</dl>${h}`;
  };
  const fullDlg = document.getElementById("full");
  const renderPanel = () => {
    const panel = document.getElementById("panel");
    document.body.classList.toggle("panel-open", !!state.panel && !state.full);
    if (!state.panel) { panel.classList.remove("open"); if (fullDlg.open) fullDlg.close(); return; }
    const { kind } = byId.get(state.panel);
    // 全画面のときはパネルを隠し、同じ中身をモーダルに描く
    const host = state.full ? fullDlg : panel;
    panel.classList.toggle("open", !state.full);
    if (state.full && !fullDlg.open) fullDlg.showModal();
    if (!state.full && fullDlg.open) fullDlg.close();
    host.querySelector(".panel-kind").innerHTML = `${KINDS.find((k) => k.key === kind).label} <span class="mono">${esc(state.panel)}</span>`;
    host.querySelector(".full-viewer")?.remove();
    const body = host.querySelector(".panel-body");
    body.hidden = false;
    body.innerHTML = renderPanelBody(state.panel);
    body.scrollTop = 0;
    panel.classList.toggle("wide", kind === "docs");
    const blocks = body.querySelectorAll("code.language-mermaid");
    if (blocks.length) loadMermaid().then((mm) => {
      blocks.forEach((c, i) => {
        const fig = document.createElement("figure");
        fig.className = "diagram";
        fig.innerHTML = `<div class="dg-tools"><button class="icon-btn" data-act="dgzoom" aria-label="図を拡大して見る" title="拡大して見る">${icon("expand")}</button><button class="btn ghost" data-act="dgraw" aria-pressed="false">Raw</button><button class="icon-btn" data-act="dgcopy" aria-label="原文をコピー" title="原文をコピー">${icon("copy")}</button></div><div class="mermaid"></div><pre class="dg-raw" hidden></pre>`;
        fig.querySelector(".mermaid").textContent = c.textContent;
        fig.querySelector(".dg-raw").textContent = c.textContent;
        c.closest("pre").replaceWith(fig);
      });
      // 図の色はデザイン方針のトークンに揃える（辺のラベルの地は面、文字は本文の色）
      mm.initialize({ startOnLoad: false, securityLevel: "strict", theme: "base", fontFamily: "Noto Sans JP, sans-serif", themeVariables: {
        darkMode: prefs.theme === "dark", background: css("--surface"), primaryColor: css("--surface-2"), primaryTextColor: css("--text"), primaryBorderColor: css("--border"),
        secondaryColor: css("--surface-2"), tertiaryColor: css("--surface"), lineColor: css("--text-2"), textColor: css("--text"), edgeLabelBackground: css("--surface"),
        clusterBkg: css("--surface-2"), clusterBorder: css("--border"), nodeTextColor: css("--text"),
      } });
      mm.run({ nodes: body.querySelectorAll(".mermaid") }).then(() => {
        body.querySelectorAll(".diagram .mermaid").forEach((m) => m.setAttribute("data-act", "dgzoom"));
        // 図の拡大を開いた状態のモックでは、最初の図を拡大して見せる
        if (state.initViewer) { state.initViewer = false; openViewer(body.querySelector(".diagram .mermaid svg")); }
      });
    }).catch(() => blocks.forEach((c) => c.closest("pre").insertAdjacentHTML("beforebegin", libError(["mermaid"], "図", "下は図の原文です。"))));
  };

  let mermaidP = null;
  const loadMermaid = () => mermaidP ??= new Promise((ok, ng) => {
    if (state.sim === "nolib") { ng(new Error("mermaid")); return; }
    const sc = Object.assign(document.createElement("script"), { src: "https://cdn.jsdelivr.net/npm/mermaid@12.0.0/dist/mermaid.min.js", integrity: "sha384-xzghz1GQ5u9HCpVskeDPqMsdogD1yvuMQbEK53+wi+G70+6J1AG0L2cfi9PHjDWI", crossOrigin: "anonymous" });
    sc.onload = () => ok(window.mermaid); sc.onerror = ng;
    document.head.append(sc);
  });

  // ===== 図の拡大表示 =====
  const viewerDlg = document.getElementById("viewer");
  let viewer = viewerDlg;  // いま図を拡大している場所（モーダルか、全画面の中）
  const vs = { z: 1, x: 0, y: 0 };
  const applyViewer = () => { viewer.querySelector(".v-stage").style.transform = `translate(${vs.x}px, ${vs.y}px) scale(${vs.z})`; viewer.querySelector(".v-pct").textContent = `${Math.round(vs.z * 100)}%`; };
  const closeFullViewer = () => { fullDlg.querySelector(".full-viewer")?.remove(); fullDlg.querySelector(".panel-body").hidden = false; viewer = viewerDlg; };
  const openViewer = (svg) => {
    if (!svg) return;
    if (state.full) {
      // モーダルから別のモーダルを開かないため、全画面の中身を図の拡大に切り替える
      fullDlg.querySelector(".panel-body").hidden = true;
      fullDlg.querySelector(".panel-head").insertAdjacentHTML("afterend", `<div class="full-viewer">${viewerDlg.innerHTML.replace(/<form method="dialog">[\s\S]*?<\/form>/, `<button class="btn ghost" data-act="vclose">${icon("back")}本文へ戻る</button>`)}</div>`);
      viewer = fullDlg.querySelector(".full-viewer");
    } else viewer = viewerDlg;
    const stage = viewer.querySelector(".v-stage");
    stage.innerHTML = svg.outerHTML;
    const copy = stage.firstElementChild, vb = svg.viewBox.baseVal;
    copy.removeAttribute("style");
    copy.setAttribute("width", vb.width); copy.setAttribute("height", vb.height);
    Object.assign(vs, { z: 1, x: 0, y: 0 });
    if (viewer === viewerDlg) viewerDlg.showModal();
    // 開いたときは、窓に収まる大きさにする
    const box = viewer.querySelector(".v-canvas").getBoundingClientRect(), r = stage.firstElementChild.getBoundingClientRect();
    vs.z = Math.min(3, (box.width - 64) / r.width, (box.height - 64) / r.height);
    vs.x = (box.width - r.width * vs.z) / 2; vs.y = (box.height - r.height * vs.z) / 2;
    applyViewer();
  };
  const viewerZoom = (d) => { vs.z = d === "fit" ? 1 : Math.max(0.2, Math.min(6, vs.z * (d === "in" ? 1.25 : 0.8))); applyViewer(); };
  document.addEventListener("wheel", (e) => {
    if (!e.target.closest(".v-canvas")) return;
    e.preventDefault();
    const box = viewer.querySelector(".v-canvas").getBoundingClientRect(), mx = e.clientX - box.left, my = e.clientY - box.top;
    const k = e.deltaY < 0 ? 1.12 : 0.89, nz = Math.max(0.2, Math.min(6, vs.z * k));
    vs.x = mx - (mx - vs.x) * (nz / vs.z); vs.y = my - (my - vs.y) * (nz / vs.z); vs.z = nz; applyViewer();
  }, { passive: false });
  let vdrag = null;
  document.addEventListener("pointerdown", (e) => {
    if (!e.target.closest(".v-canvas") || e.target.closest("button, .v-bar, text, foreignObject, .node, .nodeLabel, .edgeLabel, .label")) return;
    e.preventDefault();
    vdrag = { x: e.clientX - vs.x, y: e.clientY - vs.y }; viewer.classList.add("dragging");
  });
  addEventListener("pointermove", (e) => { if (vdrag) { vs.x = e.clientX - vdrag.x; vs.y = e.clientY - vdrag.y; applyViewer(); } });
  addEventListener("pointerup", () => { vdrag = null; viewer.classList.remove("dragging"); });

  fullDlg.addEventListener("cancel", (e) => {
    if (fullDlg.querySelector(".full-viewer")) { e.preventDefault(); closeFullViewer(); return; }
    e.preventDefault(); state.full = false; state.panel = null; render();
  });

  // ===== 描画の入口: 同じ画面の描き直しでは、スクロールの位置を保つ =====
  let lastScreen = "";
  const render = () => {
    const screen = `${state.tab}|${state.view}`;
    const same = screen === lastScreen;
    const wrap = document.querySelector(".table-wrap, .map-wrap, .board");
    const keep = same && wrap ? { l: wrap.scrollLeft, t: wrap.scrollTop, y: scrollY } : same ? { y: scrollY } : null;
    renderTabs();
    const main = document.getElementById("main");
    const k = state.tab;
    if (same && k === "graph" && G && document.getElementById("fg3")) {
      renderPanel(); graphSelect(); lastScreen = screen;
      if (location.hash !== hashOf()) history.replaceState(null, "", hashOf());
      return;
    }
    main.classList.toggle("map-view", k === "decisions" && state.view === "map");
    if (k === "overview") main.innerHTML = renderOverview();
    else if (k === "decisions" && state.view === "map") main.innerHTML = renderMapShell();
    else if (k === "graph") main.innerHTML = renderGraphTab();
    else if (k === "decisions" && state.view === "board") main.innerHTML = renderToolbar(k) + renderChips(k) + renderBoard("decisions");
    else if (k === "docs" && state.view === "cards") main.innerHTML = renderToolbar(k) + renderChips(k) + renderDocCards();
    else if (k === "tasks" && state.view === "board") main.innerHTML = renderToolbar(k) + renderChips(k) + renderBoard("tasks");
    else main.innerHTML = renderToolbar(k) + renderChips(k) + renderTable(k);
    renderPanel();
    applyPins();
    if (k === "graph") drawGraph3();
    if (k === "decisions" && state.view === "map" && libOk("ELK")) ensureLayout().then((g) => drawMap(g, keep));
    renderMockbar();
    if (keep) {
      const w2 = document.querySelector(".table-wrap, .board");
      if (w2 && keep.l !== undefined) { w2.scrollLeft = keep.l; w2.scrollTop = keep.t; }
      scrollTo(0, keep.y);
    } else scrollTo(0, 0);
    lastScreen = screen;
    if (location.hash !== hashOf()) history.replaceState(null, "", hashOf());
  };
  const renderMockbar = () => {
    const bar = document.getElementById("mock-states");
    bar.innerHTML = [["", "通常"], ["nolib", "描画のライブラリが読めない"]].map(([v, l]) => `<button type="button" data-act="sim" data-sim="${v}" aria-pressed="${state.sim === v}">${l}</button>`).join("");
  };
  const openPanel = (id) => {
    const narrow = matchMedia("(max-width: 900px)").matches;
    state.panel = id;
    // 狭い幅では詳細を別画面として履歴に積み、端末の戻る操作で一覧へ戻す
    if (narrow) history.pushState(null, "", hashOf());
    render();
    document.querySelector(`tr[data-id="${id}"]`)?.scrollIntoView({ block: "nearest" });
  };
  const closePanel = () => {
    if (matchMedia("(max-width: 900px)").matches && history.length > 1 && state.panel) { history.back(); return; }
    state.panel = null; render();
  };

  // ===== ポップオーバー =====
  const pop = document.getElementById("pop");
  const POP_GAP = 6, POP_MARGIN = 8;
  const openPop = (anchor, html) => {
    pop.innerHTML = html;
    if (!pop.matches(":popover-open")) pop.showPopover();
    const r = anchor.getBoundingClientRect();
    pop.style.maxHeight = "";
    const w = pop.offsetWidth, h = pop.offsetHeight;
    pop.style.left = Math.max(8, Math.min(r.left, innerWidth - w - 8)) + "px";
    // 下に収まれば下、上に収まれば上に開く。どちらにも収まらないときは広い側に開き、高さをそこまでにして中を送る（開いた元のボタンは覆わない）
    const below = innerHeight - r.bottom - POP_GAP - POP_MARGIN, above = r.top - POP_GAP - POP_MARGIN;
    const side = h <= below ? "below" : h <= above ? "above" : below >= above ? "below" : "above";
    if (h > (side === "below" ? below : above)) pop.style.maxHeight = (side === "below" ? below : above) + "px";
    pop.style.top = (side === "below" ? r.bottom + POP_GAP : r.top - POP_GAP - pop.offsetHeight) + "px";
  };
  const filterPop = (kind, key) => {
    const col = COLUMNS[kind].find((c) => c.key === key);
    const counts = new Map();
    for (const r of rowsFor(kind, key)) for (const v of col.multi ? col.get(r) : [col.get(r)]) counts.set(v, (counts.get(v) || 0) + 1);
    const vals = [...new Set(M[kind].flatMap((r) => (col.multi ? col.get(r) : [col.get(r)])))].filter(Boolean)
      .sort((a, b) => (col.order ? oi(col.order, a) - oi(col.order, b) : String(a).localeCompare(String(b), "ja")));
    const set = state.tables[kind].filters[key] || new Set();
    return `<h3>${esc(col.label)}で絞り込み</h3>${vals.map((v) => `<label><input type="checkbox" data-act="fval" data-kind="${kind}" data-key="${key}" value="${esc(v)}" ${set.has(v) ? "checked" : ""}>${key === "status" ? mark(v) : ""}${esc(v)}<span class="n">${counts.get(v) || 0}</span></label>`).join("")}
      <div class="pop-foot"><button class="btn ghost" data-act="fclear" data-kind="${kind}" data-key="${key}">この列の条件を解除</button></div>`;
  };
  // カードやボードで使う絞り込み: 絞り込める列をまとめて 1 つのポップオーバーに出す
  const facetsPop = (kind) => COLUMNS[kind].filter((c) => c.filter).map((c) => filterPop(kind, c.key).replace(/<div class="pop-foot">[\s\S]*?<\/div>/, "")).join("");
  const colsPop = (kind) => {
    const h = new Set(colPrefs(kind).hidden);
    return `<h3>表示する列</h3>${COLUMNS[kind].map((c) => `<label><input type="checkbox" data-act="colvis" data-kind="${kind}" value="${c.key}" ${h.has(c.key) ? "" : "checked"} ${c.fixed ? "disabled" : ""}>${esc(c.label)}</label>`).join("")}
      <div class="pop-foot"><button class="btn ghost" data-act="colreset" data-kind="${kind}">列・並べ替え・固定を初期設定に戻す</button></div>`;
  };

  // ===== 検索 =====
  const dlg = document.getElementById("search");
  const sq = document.getElementById("search-q");
  const openSearch = () => { dlg.showModal(); sq.select(); renderSearch(); };
  const renderSearch = () => {
    const q = sq.value.trim();
    const out = document.getElementById("search-results");
    if (!q) { out.innerHTML = `<p class="empty" style="padding:8px">ID・タイトル・本文の語で、すべての項目を探します。</p>`; return; }
    const html = KINDS.filter((k) => M[k.key]).map((k) => {
      const hits = M[k.key].filter((r) => matchQ(r, q)).slice(0, 8);
      return hits.length ? `<h3>${k.label}</h3>` + hits.map((r) => `<button class="sr-item" data-act="sopen" data-id="${r.id}"><span class="mono">${r.id}</span><span>${mark(r.status)} ${esc(r.title)}<br><span class="sr-sub">${esc(r.answer || r.conclusion || r.meaning || r.content || r.lead || "")}</span></span></button>`).join("") : "";
    }).join("");
    out.innerHTML = html || `<p class="no-match">該当する項目はありません。別の条件を試してください。</p>`;
  };

  // ===== テーマ =====
  prefs.theme ??= matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  const applyTheme = () => {
    document.documentElement.dataset.theme = prefs.theme;
    const b = document.getElementById("theme-btn");
    b.innerHTML = icon(prefs.theme === "dark" ? "sun" : "moon");
    b.setAttribute("aria-label", prefs.theme === "dark" ? "ライトに切り替え" : "ダークに切り替え");
  };

  // ===== 操作 =====
  document.addEventListener("click", (e) => {
    if (e.target === dlg) { dlg.close(); return; }  // 検索の外側を押したら閉じる
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const a = el.dataset.act;
    const kind = el.dataset.kind || state.tab;
    const t = state.tables[kind];
    switch (a) {
      case "view": state.view = el.dataset.view; render(); break;
      case "open": openPanel(el.dataset.id); break;
      case "close": closePanel(); break;
      case "sort": { const k = el.dataset.key, s = t.sort; t.sort = !s || s.key !== k ? { key: k, dir: "asc" } : s.dir === "asc" ? { key: k, dir: "desc" } : null; render(); break; }
      case "pin": { const i = Number(el.dataset.idx), p = colPrefs(kind); p.pin = p.pin === i + 1 ? 0 : i + 1; savePrefs(); render(); break; }
      case "colfilter": openPop(el, filterPop(kind, el.dataset.key)); break;
      case "fclear": delete t.filters[el.dataset.key]; pop.hidePopover(); render(); break;
      case "cols": openPop(el, colsPop(kind)); break;
      case "colreset": delete prefs.cols[kind]; t.sort = null; savePrefs(); pop.hidePopover(); render(); break;
      case "unchip": t.filters[el.dataset.key].delete(el.dataset.val); render(); break;
      case "unq": t.q = ""; render(); break;
      case "clearall": t.q = ""; t.filters = {}; render(); break;
      case "facets": openPop(el, facetsPop(kind)); break;
      case "zoom": {
        const cur = state.zoom === "fit" ? 0.6 : state.zoom, zd = el.dataset.z;
        state.zoom = zd === "fit" ? (state.zoom === "fit" ? 1 : "fit") : Math.max(0.4, Math.min(1.5, Math.round((cur + (zd === "in" ? 0.15 : -0.15)) * 100) / 100));
        render(); break;
      }
      case "deps": state.deps = !state.deps; render(); break;
      case "full": state.full = !state.full; render(); break;
      case "fclose": state.full = false; state.panel = null; render(); break;
      case "vclose": closeFullViewer(); break;
      case "ltypes": openPop(el, linkTypesPop()); break;
      case "sim": state.sim = el.dataset.sim; layoutCache.clear(); lastScreen = ""; history.replaceState(null, "", hashOf()); render(); break;
      case "dgraw": { const f = el.closest(".diagram"), on = el.getAttribute("aria-pressed") !== "true"; el.setAttribute("aria-pressed", on); f.querySelector(".mermaid").hidden = on; f.querySelector(".dg-raw").hidden = !on; break; }
      case "dgcopy": { const f = el.closest(".diagram"); navigator.clipboard?.writeText(f.querySelector(".dg-raw").textContent).then(() => { el.innerHTML = icon("check"); setTimeout(() => (el.innerHTML = icon("copy")), 1400); }); break; }
      case "dgzoom": openViewer(el.closest(".diagram").querySelector(".mermaid svg")); break;
      case "vzoom": viewerZoom(el.dataset.z); break;
      case "search": openSearch(); break;
      case "sopen": {
        dlg.close();
        const kk = byId.get(el.dataset.id).kind;
        // 結果の項目が別の画面にあるときは、その画面の HTML を開く（画面を移るので履歴に積む）
        if (SCREEN_OF[kk] !== SCREEN || (SCREEN === "records" && kk !== state.tab)) location.href = pageUrl(kk, { id: el.dataset.id });
        else openPanel(el.dataset.id);
        break;
      }
      case "theme": prefs.theme = prefs.theme === "dark" ? "light" : "dark"; savePrefs(); applyTheme(); if (G) G.colors = graphColors(); break;
    }
  });
  document.addEventListener("change", (e) => {
    const el = e.target, a = el.dataset.act;
    if (a === "closed") { state.tables[state.tab].showClosed = el.checked; render(); }
    if (a === "ltype") {
      el.checked ? state.linkTypes.add(el.value) : state.linkTypes.delete(el.value);
      lastScreen = ""; render();
      openPop(document.querySelector('[data-act="ltypes"]'), linkTypesPop());
    }
    if (a === "gkind") { el.checked ? state.graphKinds.add(el.value) : state.graphKinds.delete(el.value); lastScreen = ""; render(); }
    if (a === "mapst") { el.checked ? state.mapShow.add(el.value) : state.mapShow.delete(el.value); lastScreen = ""; render(); }
    if (a === "fval") {
      const set = (state.tables[el.dataset.kind].filters[el.dataset.key] ??= new Set());
      el.checked ? set.add(el.value) : set.delete(el.value);
      render();
      const facets = document.querySelector('[data-act="facets"]');
      if (facets) openPop(facets, facetsPop(el.dataset.kind));
      else openPop(document.querySelector(`[data-act="colfilter"][data-key="${el.dataset.key}"]`), filterPop(el.dataset.kind, el.dataset.key));
    }
    if (a === "colvis") {
      const p = colPrefs(el.dataset.kind);
      p.hidden = el.checked ? p.hidden.filter((k) => k !== el.value) : [...p.hidden, el.value];
      savePrefs(); render(); openPop(document.querySelector('[data-act="cols"]'), colsPop(el.dataset.kind));
    }
  });
  let qTimer;
  document.addEventListener("input", (e) => {
    if (e.target === sq) { renderSearch(); return; }
    if (e.target.dataset.act === "mapq") {
      clearTimeout(qTimer);
      const v = e.target.value;
      qTimer = setTimeout(() => {
        state.mapQ = v; lastScreen = ""; render();
        const inp = document.getElementById("map-q"); inp.focus(); inp.setSelectionRange(v.length, v.length);
      }, 150);
      return;
    }
    if (e.target.dataset.act !== "q") return;
    clearTimeout(qTimer);
    const v = e.target.value;
    qTimer = setTimeout(() => {
      state.tables[state.tab].q = v; render();
      const inp = document.getElementById(`q-${state.tab}`); inp.focus(); inp.setSelectionRange(v.length, v.length);
    }, 150);
  });
  document.addEventListener("keydown", (e) => {
    const typing = /INPUT|TEXTAREA/.test(document.activeElement?.tagName);
    if (e.key === "/" && !typing && !dlg.open) { e.preventDefault(); openSearch(); }
    if ((e.key === "Enter" || e.key === " ") && e.target.matches?.("tr[data-act]")) { e.preventDefault(); e.target.click(); }
    if (e.key === "Enter" && e.target === sq) document.querySelector("#search-results .sr-item")?.click();
    if (e.key === "Escape" && state.panel && !state.full && !dlg.open && !viewerDlg.open && !pop.matches(":popover-open")) closePanel();
  });
  addEventListener("resize", applyPins);
  // マップの背景（節以外）をつかんで動かす
  let drag = null;
  document.addEventListener("pointerdown", (e) => {
    const wrap = e.target.closest("#map-wrap, .board");
    if (!wrap || e.button !== 0 || e.target.closest("button")) return;
    drag = { wrap, x: e.clientX, y: e.clientY, l: wrap.scrollLeft, t: wrap.scrollTop };
    wrap.classList.add("dragging");
    wrap.setPointerCapture(e.pointerId);
  });
  document.addEventListener("pointermove", (e) => {
    if (!drag) return;
    drag.wrap.scrollLeft = drag.l - (e.clientX - drag.x);
    drag.wrap.scrollTop = drag.t - (e.clientY - drag.y);
  });
  document.addEventListener("pointerup", () => { drag?.wrap.classList.remove("dragging"); drag = null; });
  addEventListener("hashchange", () => { readHash(false); render(); });

  readHash(true);
  applyTheme();
  render();
  // 検索を開いた状態のモック
  if (state.initSearch) { openSearch(); sq.value = state.initSearch; renderSearch(); }
})();

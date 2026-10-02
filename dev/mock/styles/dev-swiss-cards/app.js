// デザインスタイルの候補のサンプル画面: 明暗の切り替え・部品の押下・つながりの描画

const THEME_KEY = "mindmap-theme";
const root = document.documentElement;
const darkQuery = matchMedia("(prefers-color-scheme: dark)");
const themeBtn = document.getElementById("theme-btn");
const colorSchemeMeta = document.querySelector('meta[name="color-scheme"]');

/** 今の明暗を返す */
const currentTheme = () => root.dataset.theme || (darkQuery.matches ? "dark" : "light");

/** テーマのボタンの名前とアイコンを今の明暗に合わせる */
const syncThemeButton = () => {
  const dark = currentTheme() === "dark";
  themeBtn.setAttribute("aria-label", dark ? "ライトにする" : "ダークにする");
  themeBtn.querySelector(".i-moon").style.display = dark ? "none" : "";
  themeBtn.querySelector(".i-sun").style.display = dark ? "" : "none";
};

themeBtn.addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  colorSchemeMeta.content = next;
  localStorage.setItem(THEME_KEY, next);
  syncThemeButton();
  drawGraph();
});
darkQuery.addEventListener("change", () => { syncThemeButton(); drawGraph(); });

// 表示形式の切り替え: 押したものだけを選んだ状態にする
document.querySelectorAll(".segment").forEach((seg) => {
  seg.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
  });
});

// 押し直しで戻せる道具（ピン留め・列の絞り込み・種類の表示）
document.querySelectorAll("[data-toggle]").forEach((btn) => {
  btn.addEventListener("click", () => {
    btn.setAttribute("aria-pressed", String(btn.getAttribute("aria-pressed") !== "true"));
    // 種類の表示を変えたときは、つながりを描き直す
    if (btn.dataset.kind) drawGraph();
  });
});

// 行の項目を押すと、その行を選んだ状態にする
document.querySelectorAll(".row-open").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("table.grid tr.selected").forEach((tr) => tr.classList.remove("selected"));
    btn.closest("tr").classList.add("selected");
  });
});

// 全体の検索: 入口の押下と / キーで開く
const search = document.getElementById("search");
/** 検索を開き、入力にフォーカスを移す */
const openSearch = () => { search.showModal(); search.querySelector("input").focus(); };
document.querySelector(".search-trigger").addEventListener("click", openSearch);
document.addEventListener("keydown", (e) => {
  // 入力の中で打った / は検索を開かない
  if (e.key === "/" && !e.target.closest("input, textarea") && !search.open) { e.preventDefault(); openSearch(); }
});
// closedby に対応しないブラウザでは、外側の押下で閉じる
if (!("closedBy" in HTMLDialogElement.prototype)) {
  search.addEventListener("click", (e) => { if (e.target === search) search.close(); });
}

// ===== つながり（見本は止まった 1 枚だけを描く） =====
const canvas = document.getElementById("graph");
const NODE_COUNT = 64;
const EDGE_COUNT = 90;
const SEED = 7;
const CAMERA_DIST = 3.2;
const ROTATE_Y = 0.6;
const ROTATE_X = -0.35;
const SPREAD = 0.42;
const BASE_RADIUS = 7;
const LABEL_FONT_PX = 10;
const LABEL_FADE_DEPTH = 0.45;
const GRAIN_DOTS = 2400;
const KINDS = [
  { key: "dec", weight: 34 }, { key: "task", weight: 8 }, { key: "res", weight: 4 }, { key: "doc", weight: 3 },
  { key: "term", weight: 6 }, { key: "note", weight: 3 }, { key: "log", weight: 7 },
];
const LABELS = ["最上位の軸の呼び名", "デザインスタイル", "スクリプトのコマンドと引数", "aituber/tmp を移す", "やりたいことと aituber の関わり", "会話ログの本文の置き方", "フェーズの名前", "ワークスペースのフォルダ構成"];

/** 種を決めた乱数を返す */
const seeded = (seed) => () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };

/** 玉と線を 1 回だけ作る */
const buildGraph = () => {
  const rand = seeded(SEED);
  const total = KINDS.reduce((s, k) => s + k.weight, 0);
  const nodes = Array.from({ length: NODE_COUNT }, (_, i) => {
    // 種類は件数の比で選ぶ
    let r = rand() * total;
    const kind = KINDS.find((k) => (r -= k.weight) < 0) || KINDS[0];
    // 球の中へ散らす
    const u = rand() * 2 - 1, th = rand() * Math.PI * 2, rad = Math.cbrt(rand());
    const s = Math.sqrt(1 - u * u) * rad;
    return { kind: kind.key, x: s * Math.cos(th), y: u * rad, z: s * Math.sin(th), size: 0.6 + rand() * 0.9, label: i < LABELS.length ? LABELS[i] : "" };
  });
  const edges = Array.from({ length: EDGE_COUNT }, () => [Math.floor(rand() * NODE_COUNT), Math.floor(rand() * NODE_COUNT)]).filter(([a, b]) => a !== b);
  return { nodes, edges };
};
const graph = buildGraph();

/** CSS の変数の値を読む */
const cssVar = (name) => getComputedStyle(root).getPropertyValue(name).trim();

/** 地を描く（ライトは紙のざらつき、ダークは淡い光のにじみ） */
const drawGround = (ctx, w, h) => {
  ctx.fillStyle = cssVar("--g-bg");
  ctx.fillRect(0, 0, w, h);
  const center = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.max(w, h) * 0.6);
  center.addColorStop(0, cssVar("--g-bg-center"));
  center.addColorStop(1, cssVar("--g-bg"));
  ctx.fillStyle = center;
  ctx.fillRect(0, 0, w, h);
  const glow = ctx.createRadialGradient(w * 0.5, h * 0.45, 0, w * 0.5, h * 0.45, Math.min(w, h) * 0.5);
  glow.addColorStop(0, cssVar("--g-glow"));
  glow.addColorStop(1, "rgba(0, 0, 0, 0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, w, h);
  // ざらつき: 決まった位置に細かな点を置く
  const rand = seeded(SEED + 1);
  ctx.fillStyle = cssVar("--g-grain");
  for (let i = 0; i < GRAIN_DOTS; i++) ctx.fillRect(rand() * w, rand() * h, 1, 1);
};

/** 3D の点を画面へ透視で写す */
const project = (n, w, h) => {
  const cy = Math.cos(ROTATE_Y), sy = Math.sin(ROTATE_Y), cx = Math.cos(ROTATE_X), sx = Math.sin(ROTATE_X);
  const x1 = n.x * cy - n.z * sy, z1 = n.x * sy + n.z * cy;
  const y2 = n.y * cx - z1 * sx, z2 = n.y * sx + z1 * cx;
  const scale = CAMERA_DIST / (CAMERA_DIST + z2);
  const unit = Math.min(w, h) * SPREAD;
  return { sx: w / 2 + x1 * unit * scale * (w / h > 1 ? 1.6 : 1), sy: h / 2 + y2 * unit * scale, scale, depth: z2 };
};

/** つながりを止まった 1 枚で描く */
function drawGraph() {
  const dpr = devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * dpr; canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  drawGround(ctx, w, h);
  const shown = new Set([...document.querySelectorAll(".legend [data-kind]")].filter((b) => b.getAttribute("aria-pressed") === "true").map((b) => b.dataset.kind));
  const pts = graph.nodes.map((n) => ({ ...n, ...project(n, w, h) }));
  // 何も選んでいないときも、つながる玉どうしをごく薄い線で結ぶ
  ctx.strokeStyle = cssVar("--g-line");
  ctx.lineWidth = 1;
  for (const [a, b] of graph.edges) {
    if (!shown.has(pts[a].kind) || !shown.has(pts[b].kind)) continue;
    ctx.beginPath(); ctx.moveTo(pts[a].sx, pts[a].sy); ctx.lineTo(pts[b].sx, pts[b].sy); ctx.stroke();
  }
  // 奥から順に玉と文字を置く
  for (const p of [...pts].sort((a, b) => b.depth - a.depth)) {
    if (!shown.has(p.kind)) continue;
    const r = BASE_RADIUS * p.size * p.scale;
    ctx.fillStyle = cssVar(`--k-${p.kind}`);
    ctx.beginPath(); ctx.arc(p.sx, p.sy, r, 0, Math.PI * 2); ctx.fill();
    // 遠い玉の文字は薄くし、ある距離で消す
    if (p.label && p.depth < LABEL_FADE_DEPTH) {
      ctx.globalAlpha = Math.min(1, (LABEL_FADE_DEPTH - p.depth) * 1.6);
      ctx.fillStyle = cssVar("--g-label");
      ctx.font = `${LABEL_FONT_PX * p.scale}px ${cssVar("--font-mono")}`;
      ctx.textAlign = "center";
      ctx.fillText(p.label, p.sx, p.sy - r - 4);
      ctx.globalAlpha = 1;
    }
  }
}

syncThemeButton();
drawGraph();
addEventListener("resize", drawGraph);
// Web フォントが揃ったら、文字を描き直す
document.fonts.ready.then(drawGraph);

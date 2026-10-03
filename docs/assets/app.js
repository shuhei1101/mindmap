/* ============================================================================
 * ai-monitor ドキュメントサイト 共通スクリプト
 *
 * docs/ 配下すべてのページで読み込む単一 JS。
 * 各機能は「対象 DOM が無ければ何もしない」形で並べており、
 * Mock demo / Jekyll 描画ページ / 公開ドキュメントなど、ページ種別を問わず同じファイルで動く。
 * 上タブの生成だけは _layouts/default.html の Liquid が担う（ここでは扱わない）。
 *
 * 本文の Markdown → HTML の変換は Jekyll 側で完了している。ここで変換するのは言語指定が markdown のコードブロックの中身だけ。
 *
 * 提供する機能:
 *   1.  パンくずリスト     ... [data-breadcrumb] があれば URL 階層から自動生成
 *   2.  テーブルソート・フィルタ ... table にヘッダクリックの昇降ソートと絞り込みを付与
 *   3.  見出しアンカー     ... h2-h4 に # リンクを追加、クリックで URL をコピー
 *   4.  コードコピー       ... pre 右上のコピーボタン
 *   5.  コールアウト       ... GitHub Alert 記法の引用に種別の class を付ける
 *   6.  表の横スクロール   ... table を .table-frame と .table-wrap の二重で包み、列数の多い表は最終列を畳む。列のピン留めと見出し行の追従を付ける
 *   7.  Mermaid 描画・拡大 ... code.language-mermaid をレンダリングし、押下で全画面拡大
 *   8.  目次               ... [data-toc] に h2/h3 を並べ、現在位置ハイライト
 *   9.  サイドバー         ... [data-sidebar-source] の目次表からセクション別に生成
 *   10. ドロワー・幅の切り替え ... 720px / 960px でサイドバー・目次の置き場所を切り替える
 *   11. ダークモード切替   ... [data-theme-toggle] で light/dark 切替、localStorage 保存
 *   12. コード言語ラベル   ... pre 左上に言語名を表示
 *   13. 見出し単位の検索   ... /search.json をロードして検索モーダルで見出し単位に絞り込み
 *   14. 起票               ... 読んでいるページから Issue の下書きを作り、GitHub の起票画面を開く
 *   15. トップに戻る       ... [data-back-to-top] のボタンをスクロール量で表示切替
 *   16. Mock demo 用       ... 検索・行クリック・新規追加・編集モード・トースト
 *   17. コード内の Markdown ... markdown のコードブロックの中身を描き、元のコードとの切り替えを付ける
 *   18. 図の再掲           ... 段落にリンク 1 本だけを置いた位置へ、リンク先の見出しの下の図を置く
 * ============================================================================ */

/* ---------- 定数 ---------- */
const TOAST_DISPLAY_MS = 1800;
const BACK_TO_TOP_THRESHOLD_PX = 300;
const MOBILE_WIDTH = 720;
const TOC_INLINE_WIDTH = 960;
const mobileQuery = window.matchMedia(`(max-width: ${MOBILE_WIDTH}px)`);
const tocInlineQuery = window.matchMedia(`(max-width: ${TOC_INLINE_WIDTH}px)`);

/* 幅の切り替えで動かす器への参照と、開いているドロワーを閉じる手段 */
const layout = { nav: null, toc: null, tocInline: null, tocAside: null, article: null, closeDrawer: null };

/* パンくず階層のラベル辞書。URL セグメント → 表示名。未登録は素通し。 */
const BREADCRUMB_LABELS = {
  "": "トップ",
  "docs": "ドキュメント",
  "mock": "モック",
  "pages": "画面",
  "components": "コンポーネント",
  "styles": "スタイル",
  "issues": "Issue",
  "assets": "アセット",
};


/* ============================================================================
 * 1. パンくずリスト
 * ---------------------------------------------------------------------------- */

/** ルート（末尾スラッシュ付き）とパス配下のセグメントに分割する */
function splitPathBySiteRoot() {
  // _layouts/default.html が data-site-root="{{ '/' | relative_url }}" を注入する
  // GitHub Pages（project pages）だと "/ai-monitor/"、ローカルルート配信だと "/"
  const bodyRoot = document.body?.dataset?.siteRoot || "/";
  const siteRoot = bodyRoot.endsWith("/") ? bodyRoot : bodyRoot + "/";

  const pathname = decodeURIComponent(window.location.pathname);
  // 末尾のファイル名を落として必ずディレクトリ形にする
  const dir = pathname.endsWith("/") ? pathname : pathname.replace(/\/[^\/]*$/, "/");

  // site root 直下の相対パスを取り出す
  const rel = dir.startsWith(siteRoot) ? dir.slice(siteRoot.length) : dir.replace(/^\//, "");
  const segs = rel.split("/").filter(Boolean);
  return { siteRoot, segs };
}

/** その中間層セグメントを「非リンクの中間表示」にするかどうか */
function isNonLinkableSegment(seg, index, segs) {
  // pages/{画面名}/issues/ は index.md を置かない中間層（規約）→ リンクにしない
  return seg === "issues" && segs[index - 2] === "pages";
}

/** URL パスの各セグメントを辿ってパンくずリンクを組み立てる */
function buildBreadcrumb() {
  const host = document.querySelector("[data-breadcrumb]");
  if (!host) return;

  const { siteRoot, segs } = splitPathBySiteRoot();

  const parts = [];
  parts.push(`<a href="${siteRoot}">${BREADCRUMB_LABELS[""]}</a>`);

  // 各セグメントの累積 URL を絶対パス（site root からの絶対）で組む
  let acc = siteRoot;
  segs.forEach((seg, i) => {
    acc += seg + "/";
    const label = BREADCRUMB_LABELS[seg] || seg;
    const isLast = i === segs.length - 1;
    parts.push(`<span class="sep">/</span>`);
    if (isLast || isNonLinkableSegment(seg, i, segs)) {
      // 現在地 or 中間層 → リンクにしない
      parts.push(`<span class="current">${label}</span>`);
    } else {
      parts.push(`<a href="${acc}">${label}</a>`);
    }
  });

  host.innerHTML = parts.join("");
}


/* ============================================================================
 * 2. テーブルソート・フィルタ
 * ---------------------------------------------------------------------------- */

/** 指定スコープ内のテーブルにソートとフィルタを付与する */
function enhanceTables(scope) {
  scope.querySelectorAll("table").forEach((table) => {
    // 二重適用防止
    if (table.dataset.enhanced === "true") return;
    table.dataset.enhanced = "true";
    bindTableSort(table);
    injectTableFilter(table);
  });
}

/** テーブルヘッダをクリックで昇降ソートできるようにする */
function bindTableSort(table) {
  const thead = table.tHead;
  const tbody = table.tBodies[0];
  if (!thead || !tbody) return;

  Array.from(thead.rows[0].cells).forEach((th, colIdx) => {
    th.classList.add("sortable");
    th.addEventListener("click", () => {
      // 現状の方向を判定して反転（初回は昇順）
      const asc = !th.classList.contains("sort-asc");
      // 他のヘッダの矢印はクリア
      Array.from(thead.rows[0].cells).forEach((h) => h.classList.remove("sort-asc", "sort-desc"));
      th.classList.add(asc ? "sort-asc" : "sort-desc");

      const rows = Array.from(tbody.rows);
      rows.sort((a, b) => compareCells(a.cells[colIdx], b.cells[colIdx], asc));
      rows.forEach((row) => tbody.appendChild(row));
    });
  });
}

/** セル内容を数値優先で比較する */
function compareCells(a, b, asc) {
  const av = (a?.textContent || "").trim();
  const bv = (b?.textContent || "").trim();
  const an = Number(av);
  const bn = Number(bv);
  let result;
  if (!Number.isNaN(an) && !Number.isNaN(bn) && av !== "" && bv !== "") {
    result = an - bn;
  } else {
    result = av.localeCompare(bv, "ja");
  }
  return asc ? result : -result;
}

/** テーブル上に検索ボックスを挿入し、入力語で行を絞り込む */
function injectTableFilter(table) {
  const tbody = table.tBodies[0];
  if (!tbody || tbody.rows.length < 2) return; // 行が少なければフィルタ不要

  const input = document.createElement("input");
  input.type = "search";
  input.className = "table-filter";
  input.placeholder = "この表を絞り込む...";
  table.parentNode.insertBefore(input, table);

  input.addEventListener("input", () => {
    const keyword = input.value.trim().toLowerCase();
    Array.from(tbody.rows).forEach((row) => {
      const text = row.textContent.toLowerCase();
      row.classList.toggle("hidden", keyword !== "" && !text.includes(keyword));
    });
  });
}


/* ============================================================================
 * 3. 見出しアンカーリンク
 * ---------------------------------------------------------------------------- */

/** 日本語見出しからも使えるスラッグを生成する */
function slugify(text) {
  return text
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    // URL で問題になる記号だけ落とす。日本語文字はそのまま残す（modern browser は decode 済で扱う）
    .replace(/[^\p{L}\p{N}\-_.]/gu, "");
}

/* 識別子を割り当てる見出し */
const ANCHORED_HEADINGS = "h2, h3, h4";

/** 範囲の見出しを文書順に見て、重ならない識別子を決めて返す（見出しは書き換えない） */
function resolveHeadingIds(root) {
  const used = new Set();
  const resolved = [];

  root.querySelectorAll(ANCHORED_HEADINGS).forEach((h) => {
    // kramdown の自動 id は日本語を落とす（例: "section"）ため、本文から生成した slug を優先する
    const id = slugify(h.textContent || "") || h.id;
    if (!id) return;
    // 重複回避
    let unique = id;
    let n = 2;
    while (used.has(unique)) unique = `${id}-${n++}`;
    used.add(unique);
    resolved.push({ heading: h, id: unique });
  });
  return resolved;
}

/** h2〜h4 に id と # リンクを付与する */
function insertHeadingAnchors() {
  const root = document.querySelector(".markdown-body");
  if (!root) return;

  resolveHeadingIds(root).forEach(({ heading: h, id: unique }) => {
    h.id = unique;

    const a = document.createElement("a");
    a.className = "heading-anchor";
    a.href = `#${unique}`;
    a.setAttribute("aria-label", "この見出しへのリンクをコピー");
    a.textContent = "#";
    // クリック時に URL をクリップボードへコピー（ページ遷移はそのまま）
    a.addEventListener("click", () => {
      const url = window.location.origin + window.location.pathname + `#${unique}`;
      navigator.clipboard?.writeText(url).then(() => showToast(`URL をコピー: #${unique}`));
    });
    h.appendChild(a);
  });
}


/* ============================================================================
 * 4. コードブロックのコピーボタン
 * ---------------------------------------------------------------------------- */

/** `<pre><code>` の右上にコピーボタンを差し込む */
function addCodeCopyButtons() {
  document.querySelectorAll(".markdown-body pre").forEach((pre) => {
    if (pre.dataset.copyReady === "true") return;
    pre.dataset.copyReady = "true";
    codeActions(pre).appendChild(createCopyButton(() => pre.querySelector("code")?.innerText ?? pre.innerText));
  });
}

/** 入れ物の右上に置く、ボタンを並べる入れ物を返す（無ければ作る） */
function codeActions(container) {
  const existing = container.querySelector(":scope > .code-actions");
  if (existing) return existing;
  const actions = document.createElement("div");
  actions.className = "code-actions";
  container.appendChild(actions);
  // 入れ物を position: relative にして右上に置く
  container.style.position = "relative";
  return actions;
}

/** 押すと中身を写しへ入れるボタンを作る */
function createCopyButton(getText) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "code-copy";
  btn.textContent = "コピー";
  btn.addEventListener("click", async () => {
    try {
      // 安全な接続では navigator.clipboard、使えない配信（http の資料の配信 等）では選択範囲を使う写し方で写す
      if (window.isSecureContext && navigator.clipboard) {
        await navigator.clipboard.writeText(getText());
      } else if (!copyWithSelection(getText())) {
        throw new Error("選択範囲を使う写し方で写せなかった");
      }
      btn.textContent = "コピー済";
      window.setTimeout(() => { btn.textContent = "コピー"; }, 1500);
    } catch {
      btn.textContent = "失敗";
    }
  });
  return btn;
}

/** 画面に出さないテキスト欄を選択して写しへ入れ、写せたかを返す */
function copyWithSelection(text) {
  const area = document.createElement("textarea");
  area.value = text;
  // 画面に出さず、スクロール位置も動かさない
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  const copied = document.execCommand("copy");
  area.remove();
  return copied;
}


/* ============================================================================
 * 5. コールアウト
 * ---------------------------------------------------------------------------- */

/* 引用の先頭に置く印から、付ける class と見出しを引く辞書 */
const CALLOUT_KINDS = {
  NOTE: { className: "callout-note", label: "ノート" },
  TIP: { className: "callout-tip", label: "ヒント" },
  IMPORTANT: { className: "callout-important", label: "重要" },
  WARNING: { className: "callout-warn", label: "警告" },
  CAUTION: { className: "callout-danger", label: "危険" },
};
const CALLOUT_PATTERN = /^\[!([A-Z]+)\]\s*/;

/** 引用の先頭の印を読み、種別の class と見出しを付ける */
function markCallouts(article) {
  article.querySelectorAll("blockquote").forEach((quote) => {
    const head = quote.querySelector("p");
    if (!head || !head.firstChild || head.firstChild.nodeType !== Node.TEXT_NODE) return;
    const matched = head.firstChild.nodeValue.match(CALLOUT_PATTERN);
    if (!matched) return;
    const kind = CALLOUT_KINDS[matched[1]];
    if (!kind) return;

    // マーカーと直後の改行を落として、種別の見出しへ差し替える
    head.firstChild.nodeValue = head.firstChild.nodeValue.replace(CALLOUT_PATTERN, "");
    if (head.firstChild.nodeValue === "" && head.firstChild.nextSibling?.tagName === "BR") {
      head.firstChild.nextSibling.remove();
      head.firstChild.remove();
    }
    const title = document.createElement("div");
    title.className = "callout-title";
    title.textContent = kind.label;
    quote.classList.add("callout", kind.className);
    quote.prepend(title);
  });
}


/* ============================================================================
 * 6. 表の横スクロール
 * ---------------------------------------------------------------------------- */

const WIDE_TABLE_COLUMNS = 7;

/** 表を、動かない外側の枠とスクロールする内側の入れ物の二重で包み、列数の多い表には最終列の開閉を、どの表にも列のピン留めと見出し行の追従を付ける */
function wrapTables(article) {
  const tables = [...article.querySelectorAll("table")];
  tables.forEach((table) => {
    // 動かない外側の枠とスクロールする内側の入れ物の二重で包む
    const frame = document.createElement("div");
    frame.className = "table-frame";
    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    table.replaceWith(frame);
    frame.appendChild(wrap);
    wrap.appendChild(table);
    // 見出しの列数が多い表は、狭い幅で最終列を畳む印を付けて行の押下を割り当てる
    if (table.querySelectorAll("thead th").length >= WIDE_TABLE_COLUMNS) {
      frame.classList.add("is-wide");
      enableLastColumnToggle(table);
    }
    // 列見出しにピン留めボタンを置く
    enableColumnPin(table);
    // 内側の入れ物が表からはみ出している場合、外側の枠に動かせることを示す印を付ける
    if (table.scrollWidth > wrap.clientWidth) frame.classList.add("is-scrollable");
  });
  // 包んだ表の見出し行を縦のスクロールに追従させる
  followTableHeads(tables);
}

/** 列数の多い表で、行の押下に最終列の開閉を割り当てる */
function enableLastColumnToggle(table) {
  table.querySelectorAll("tbody tr").forEach((row) => {
    row.addEventListener("click", () => row.classList.toggle("is-open"));
  });
}

/** 列見出しごとにピン留めボタンを置き、押した列とその左の列を表の左端に留める */
function enableColumnPin(table) {
  // 見出しの行が無ければ何もしない
  const head = table.tHead?.rows[0];
  if (!head) return;

  // 見出しごとにピン留めボタンを置く
  const buttons = [...head.cells].map((th, index) => {
    const label = th.textContent.trim();
    const button = document.createElement("button");
    button.type = "button";
    button.className = "table-pin";
    button.textContent = "📌";
    button.dataset.label = label;
    // 押下を見出しの並べ替えへ伝えずに、固定する範囲を入れ直す
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const pinned = table.dataset.pinIndex === String(index);
      table.dataset.pinIndex = pinned ? "" : String(index);
      refresh();
    });
    th.appendChild(button);
    return button;
  });

  /** 固定中の列のボタンだけを押された状態にし、セルの位置を入れ直す */
  function refresh() {
    buttons.forEach((button, index) => {
      const pinned = table.dataset.pinIndex === String(index);
      button.setAttribute("aria-pressed", String(pinned));
      button.title = pinned ? "列の固定を解除" : "この列より左を固定";
      button.setAttribute("aria-label", pinned ? `${button.dataset.label} までの固定を解除` : `${button.dataset.label} より左を固定`);
    });
    layoutPinned(table);
  }
  refresh();

  // 見出し行のセルの大きさが変わるたびに、1 回の通知でセルの位置を入れ直す
  const observer = new ResizeObserver(() => layoutPinned(table));
  [...head.cells].forEach((th) => observer.observe(th));
}

/** 固定する範囲の列のセルを、手前の列の幅の合計の位置に留める */
function layoutPinned(table) {
  const rows = [...table.rows];
  // 全てのセルから固定の印と左端からの位置を外す
  rows.forEach((row) => {
    [...row.cells].forEach((cell) => {
      cell.classList.remove("is-pinned", "is-pin-edge");
      cell.style.left = "";
    });
  });
  // 固定する範囲が無ければ終える
  if (!table.dataset.pinIndex) return;

  // 1 列目から固定する列まで、見出しと本体の同じ列のセルを手前の列の幅の合計の位置に留める
  const pinIndex = Number(table.dataset.pinIndex);
  const headCells = table.tHead.rows[0].cells;
  let left = 0;
  for (let index = 0; index <= pinIndex; index += 1) {
    rows.forEach((row) => {
      const cell = row.cells[index];
      // セルの足りない行は飛ばす
      if (!cell) return;
      cell.classList.add("is-pinned");
      cell.classList.toggle("is-pin-edge", index === pinIndex);
      cell.style.left = `${left}px`;
    });
    left += headCells[index].getBoundingClientRect().width;
  }
}

/** 縦のスクロールに合わせて、表の見出し行を上タブのすぐ下へ送る */
function followTableHeads(tables) {
  // 見出しの行を持つ表が無ければ何もしない
  const targets = tables.filter((table) => table.tHead);
  if (targets.length === 0) return;
  const tabbar = document.querySelector(".tabbar");
  let scheduled = false;

  /** 表ごとの送り量を決め直す */
  function update() {
    scheduled = false;
    const tabbarBottom = tabbar.getBoundingClientRect().bottom;
    targets.forEach((table) => {
      const rect = table.getBoundingClientRect();
      const headHeight = table.tHead.getBoundingClientRect().height;
      // 上タブの下端から表の上端までの差を、0 から「表の高さ − 見出し行の高さ」までに収める
      const offset = Math.min(Math.max(tabbarBottom - rect.top, 0), rect.height - headHeight);
      // 送り量を表に入れる（見出し行のセルがその分だけ縦へずれる）
      table.style.setProperty("--head-offset", `${offset}px`);
    });
  }

  // スクロールと幅の変更と表の大きさの変更のたびに、描画 1 回分にまとめて決め直す
  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(update);
  };
  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule);
  const observer = new ResizeObserver(schedule);
  targets.forEach((table) => observer.observe(table));
}


/* ============================================================================
 * 7. Mermaid 描画・拡大
 * ---------------------------------------------------------------------------- */

const ZOOM_SCALE = "200%";

/** click 構文のリンク先 .md を Pages の .html に書き換える（Jekyll の relative_links はコードブロック内に効かないため） */
function rewriteMermaidLinks(holder) {
  holder.querySelectorAll("a").forEach((a) => {
    const attr = a.hasAttribute("href") ? "href" : "xlink:href";
    const href = a.getAttribute(attr);
    if (!href) return;
    a.setAttribute(attr, href.replace(/\.md(#|$)/, ".html$1"));
  });
}

/** 図の元のコードを描き、図の中のリンクと押下での拡大を効かせる */
async function renderMermaid(article) {
  if (!window.mermaid) return;
  const blocks = article.querySelectorAll("pre > code.language-mermaid");
  if (blocks.length === 0) return;

  // securityLevel: loose で click 構文をリンクとして描画する（GitHub 上では strict のため飾りになる）
  // suppressErrorRendering を外すと、構文エラーの図が body へ描かれたまま残る
  window.mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    suppressErrorRendering: true,
    theme: document.documentElement.dataset.theme === "dark" ? "dark" : "default",
  });

  for (const [i, code] of blocks.entries()) {
    const pre = code.parentElement;
    const src = code.textContent;
    // div.mermaid-holder を pre の直前に置き、pre は元のコードの表示として隠しておく（元テキストは data-mermaid-src に退避）
    const holder = document.createElement("div");
    holder.className = "mermaid-holder";
    holder.dataset.mermaidSrc = src;
    holder.textContent = "図を描いています...";
    pre.before(holder);
    pre.hidden = true;
    try {
      const id = `mermaid-${Date.now()}-${i}`;
      const { svg, bindFunctions } = await window.mermaid.render(id, src);
      holder.innerHTML = svg;
      rewriteMermaidLinks(holder);
      // click が URL 形式なら <a> で描かれるが、コールバック形式は bindFunctions を呼ばないとハンドラが結ばれない
      bindFunctions?.(holder);
      holder.addEventListener("click", (event) => openZoom(holder, event));
      bindViewToggle(holder, pre, CODE_VIEW_LABELS.diagram);
    } catch (e) {
      holder.className = "mermaid-error";
      holder.innerHTML = `<p>図を描けませんでした: ${e?.message ?? e}</p><pre>${src}</pre>`;
    }
  }
}

/** テーマ切替時に既存の Mermaid ホルダーを再描画する */
async function rerenderMermaid() {
  if (!window.mermaid) return;
  const holders = document.querySelectorAll(".mermaid-holder[data-mermaid-src]");
  if (holders.length === 0) return;
  window.mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    suppressErrorRendering: true,
    theme: document.documentElement.dataset.theme === "dark" ? "dark" : "default",
  });
  for (const [i, holder] of holders.entries()) {
    const src = holder.dataset.mermaidSrc;
    // 描き直しで中身ごと置き換わるので、操作ボタン群を退避しておく
    const actions = holder.querySelector(":scope > .code-actions");
    try {
      const id = `mermaid-re-${Date.now()}-${i}`;
      const { svg, bindFunctions } = await window.mermaid.render(id, src);
      holder.innerHTML = svg;
      rewriteMermaidLinks(holder);
      bindFunctions?.(holder);
      if (actions) holder.appendChild(actions);
    } catch (e) {
      holder.className = "mermaid-error";
      holder.innerHTML = `<p>図を描けませんでした: ${e?.message ?? e}</p><pre>${src}</pre>`;
    }
  }
}

/** 図を画面いっぱいに重ねて出し、閉じる手段を配る */
function openZoom(holder, event) {
  // URL 形式の click は <a>、コールバック形式は .clickable として描かれる。リンクの移動と操作ボタンの押下を優先する
  if (event.target.closest("a, .clickable, .code-actions")) return;

  const overlay = document.createElement("div");
  overlay.className = "zoom-overlay";
  // 操作ボタン群は複製せず、図だけを重ねる
  overlay.innerHTML = holder.querySelector("svg")?.outerHTML ?? "";
  const close = document.createElement("button");
  close.className = "overlay-close";
  close.textContent = "✕";
  overlay.appendChild(close);

  const svg = overlay.querySelector("svg");
  if (svg) {
    svg.style.width = ZOOM_SCALE;
    // mermaid が SVG へ inline で入れる max-width に負けるので、こちらも inline で外す
    svg.style.maxWidth = "none";
  }

  const dismiss = () => {
    overlay.remove();
    document.removeEventListener("keydown", onKey);
  };
  const onKey = (key) => {
    if (key.key === "Escape") dismiss();
  };
  close.addEventListener("click", dismiss);
  document.addEventListener("keydown", onKey);

  document.body.appendChild(overlay);
}


/* ============================================================================
 * 8. 目次
 * ---------------------------------------------------------------------------- */

/** 本文の見出しから目次の並びを作る */
function renderToc(article) {
  const list = document.createElement("ul");
  article.querySelectorAll("h2, h3").forEach((h) => {
    if (!h.id) return;
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `#${h.id}`;
    // アンカー "#" は本文だけ取り出す
    a.textContent = h.textContent.replace(/#$/, "").trim();
    if (h.tagName === "H3") a.className = "toc-h3";
    li.appendChild(a);
    list.appendChild(li);
  });
  return list;
}

const TOC_ACTIVE_RATIO = 0.2;
const TOC_LANDING_TOLERANCE_PX = 2;

/** 目次を置き、スクロール位置に応じて現在地を 1 つだけ示す */
function buildToc() {
  const aside = document.querySelector("[data-toc]");
  const article = document.querySelector(".markdown-body");
  if (!aside || !article) return;

  const headings = Array.from(article.querySelectorAll("h2, h3"));
  if (headings.length < 2) {
    // 見出し 1 個以下では目次不要
    return;
  }
  aside.hidden = false;

  const toc = renderToc(article);
  const inline = document.createElement("details");
  inline.className = "toc-inline";
  inline.innerHTML = "<summary>目次</summary>";

  layout.toc = toc;
  layout.tocAside = aside;
  layout.tocInline = inline;
  layout.article = article;

  const links = Array.from(toc.querySelectorAll("a"));
  const linkById = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));

  // 飛んできた見出しが、飛んだときの位置に留まっていればその見出しを返す
  const jumpedId = (line) => {
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!target || !headings.includes(target)) return null;
    const top = target.getBoundingClientRect().top;
    const landing = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
    // 着地の位置のまま（次の見出しが近くて線を越えていても、飛んだ先を示す）
    if (Math.abs(top - landing) <= TOC_LANDING_TOLERANCE_PX) return target.id;
    // ページの末尾では着地まで上がれないので、画面に入っていれば飛んだ先を示す
    const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 1;
    return atBottom && top > line && top < window.innerHeight ? target.id : null;
  };

  const updateActive = () => {
    const line = window.innerHeight * TOC_ACTIVE_RATIO;
    let currentId = null;
    for (const h of headings) {
      if (h.getBoundingClientRect().top > line) break;
      currentId = h.id;
    }
    currentId = jumpedId(line) || currentId;
    links.forEach((a) => a.classList.remove("active"));
    if (currentId) linkById.get(currentId)?.classList.add("active");
  };

  window.addEventListener("scroll", updateActive, { passive: true });
  window.addEventListener("resize", updateActive);
  window.addEventListener("hashchange", () => window.requestAnimationFrame(updateActive));
  updateActive();
}


/* ============================================================================
 * 9. サイドバー
 * ---------------------------------------------------------------------------- */

const OPEN_STATE_KEY = "docsSidebar";

/** 目次表の隠し要素からサイドバーの要素を組み立てる（表が無ければ null） */
function renderSidebar(source, tab, currentPage) {
  if (!source) return null;

  const nav = document.createElement("nav");
  nav.className = "docnav";

  // どのセクションにも属さない行（source 直下の表）を、セクションより前に置く
  const looseTable = source.querySelector(":scope > table");
  if (looseTable) {
    const looseRows = [...looseTable.querySelectorAll("tbody tr")];
    nav.appendChild(buildPageList(looseRows, currentPage, tab));
  }

  source.querySelectorAll("[data-section]").forEach((section) => {
    const name = section.dataset.section;
    const rows = [...section.querySelectorAll("tbody tr")];
    const holdsCurrent = rows.some((row) => pageName(row) === currentPage);
    nav.appendChild(buildSection(tab, name, groupRows(rows), currentPage, holdsCurrent));
  });

  if (!nav.hasChildNodes()) return null;
  return nav;
}

/** 目次表の行を分類列でまとめる（分類列を持たない表はキーが空文字の 1 グループ） */
function groupRows(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const cell = row.querySelector('[data-col="分類"]');
    const category = cell ? cell.textContent.trim() : "";
    if (!groups.has(category)) groups.set(category, []);
    groups.get(category).push(row);
  });
  return groups;
}

/** 目次表の行のページ列からページ名を取り出す */
function pageName(row) {
  return row.querySelector('[data-col="ページ"]').textContent.trim();
}

/** セクション 1 つ分の開閉ブロックを作る */
function buildSection(tab, name, groups, currentPage, holdsCurrent) {
  const key = `${tab}:${name}`;
  const open = resolveOpen(key, holdsCurrent);

  const button = openButton(name, open);
  const body = document.createElement("div");
  body.hidden = !open;

  groups.forEach((rows, category) => {
    if (category) {
      body.appendChild(buildSubsection(tab, key, category, rows, currentPage, holdsCurrent));
      return;
    }
    body.appendChild(buildPageList(rows, currentPage, tab));
  });

  bindToggle(button, body, key);
  const section = document.createElement("div");
  section.className = "docnav-section";
  section.append(button, body);
  return section;
}

/** 分類 1 つ分の開閉ブロックを作る */
function buildSubsection(tab, sectionKey, name, rows, currentPage, holdsCurrent) {
  const key = `${sectionKey}/${name}`;
  const holdsCurrentPage = holdsCurrent && rows.some((row) => pageName(row) === currentPage);
  const open = resolveOpen(key, holdsCurrentPage);

  const button = openButton(name, open);
  const list = buildPageList(rows, currentPage, tab);
  list.hidden = !open;

  bindToggle(button, list, key);
  const wrap = document.createElement("div");
  wrap.className = "docnav-subsection";
  wrap.append(button, list);
  return wrap;
}

/** セクション・分類の見出しになる開閉ボタンを作る */
function openButton(name, open) {
  const button = document.createElement("button");
  button.type = "button";
  button.setAttribute("aria-expanded", String(open));
  const label = document.createElement("span");
  label.textContent = name;
  const caret = document.createElement("span");
  caret.className = "docnav-caret";
  caret.textContent = "▸";
  button.append(label, caret);
  return button;
}

/** ボタンの押下に、中身の開閉と状態の記録を割り当てる */
function bindToggle(button, body, key) {
  button.addEventListener("click", () => {
    const next = button.getAttribute("aria-expanded") !== "true";
    button.setAttribute("aria-expanded", String(next));
    body.hidden = !next;
    localStorage.setItem(`${OPEN_STATE_KEY}:${key}`, String(next));
  });
}

/** セクション・分類を開いた状態で描くかを決める（現在地を含む場合は記録より優先して開く） */
function resolveOpen(key, holdsCurrent) {
  if (holdsCurrent) return true;
  return localStorage.getItem(`${OPEN_STATE_KEY}:${key}`) === "true";
}

/** 目次表の行順でページの並びを作る */
function buildPageList(rows, currentPage, tab) {
  const list = document.createElement("ul");
  list.className = "docnav-pages";
  rows.forEach((row) => {
    const name = pageName(row);
    const href = row.querySelector('[data-col="ページ"] a')?.getAttribute("href") || "#";
    const item = document.createElement("li");
    const a = document.createElement("a");
    a.textContent = name;
    if (name === currentPage) {
      a.setAttribute("aria-current", "page");
    } else {
      a.href = href;
    }
    // 今のタブのフォルダの外へ移るリンクには、別のページへ移る印を付ける
    if (isOutsideTab(href, tab)) a.classList.add("docnav-external");
    item.appendChild(a);
    list.appendChild(item);
  });
  return list;
}


/** リンク先が今のタブのフォルダの外（別のタブ・外部のサイト）かを返す */
function isOutsideTab(href, tab) {
  if (href === "#") return false;
  const url = new URL(href, window.location.href);
  // 別のサイト: 外
  if (url.origin !== window.location.origin) return true;
  // 同じサイト: パスにタブのフォルダを含まなければ外
  const segments = decodeURIComponent(url.pathname).split("/");
  return !segments.includes(tab);
}


/* ============================================================================
 * 10. ドロワー・幅の切り替え
 * ---------------------------------------------------------------------------- */

/** サイドバーを本文の上へ重ねて出し、背景の押下と戻る操作で閉じられるようにする */
function openDrawer(nav) {
  nav.hidden = false;
  const backdrop = document.createElement("div");
  backdrop.className = "drawer-backdrop";
  document.body.appendChild(backdrop);
  history.pushState({ drawer: true }, "");

  const close = () => {
    nav.hidden = true;
    backdrop.remove();
    window.removeEventListener("popstate", close);
    layout.closeDrawer = null;
  };
  layout.closeDrawer = close;
  backdrop.addEventListener("click", () => {
    close();
    history.back();
  });
  window.addEventListener("popstate", close);
}

/** 幅に応じてサイドバーと目次の置き場所を切り替える */
function applyWidth() {
  // ドロワーを開いたまま広い幅へ変わった場合、閉じて積んだ履歴を戻す
  if (!mobileQuery.matches && layout.closeDrawer) {
    layout.closeDrawer();
    history.back();
  }
  if (layout.nav) layout.nav.hidden = mobileQuery.matches;

  if (!layout.toc) return;
  if (tocInlineQuery.matches) {
    layout.tocInline.appendChild(layout.toc);
    layout.article.prepend(layout.tocInline);
    return;
  }
  layout.tocInline.remove();
  layout.tocAside.appendChild(layout.toc);
}


/* ============================================================================
 * 11. ダークモード切替
 * ---------------------------------------------------------------------------- */

const THEME_STORAGE_KEY = "docs-theme";

/** 現在のテーマを html[data-theme] に反映 */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  // Mermaid にも反映（再描画）
  if (window.mermaid && typeof window.mermaid.initialize === "function") {
    window.mermaid.initialize({ startOnLoad: false, securityLevel: "loose", theme: theme === "dark" ? "dark" : "default" });
  }
}

/** ボタン + localStorage + OS 設定でテーマを決める */
function bindThemeToggle() {
  const btn = document.querySelector("[data-theme-toggle]");
  // OS 設定 → localStorage の順で初期値
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initial = stored || (prefersDark ? "dark" : "light");
  applyTheme(initial);
  if (!btn) return;

  btn.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem(THEME_STORAGE_KEY, next);
    // 既存の mermaid をテーマ変更後に再描画（グラフを破棄して再生成）
    rerenderMermaid();
  });
}


/* ============================================================================
 * 12. コードブロックの言語ラベル
 * ---------------------------------------------------------------------------- */

/** code か構文ハイライトの外枠の class="language-xxx" から言語名を取り出して pre 左上に付ける */
function addCodeLangLabels() {
  document.querySelectorAll(".markdown-body pre").forEach((pre) => {
    // 言語の印は code 自身か、rouge が pre.highlight を包む外枠のどちらかに付いている
    const langHolder = pre.classList.contains("highlight")
      ? pre.closest(".highlighter-rouge")
      : pre.querySelector(":scope > code[class*='language-']");
    if (!langHolder) return;
    if (pre.dataset.langReady === "true") return;
    pre.dataset.langReady = "true";

    const m = /language-([^\s]+)/.exec(langHolder.className);
    if (!m) return;
    const lang = m[1];
    // mermaid はラベル不要（図として表示するので）
    if (lang === "mermaid") return;

    const label = document.createElement("span");
    label.className = "code-lang";
    label.textContent = lang;
    pre.style.position = "relative";
    pre.appendChild(label);
  });
}


/* ============================================================================
 * 13. 見出し単位の検索
 * ---------------------------------------------------------------------------- */

const SEARCH_RESULT_MAX = 10;
const RECENT_SEARCH_KEY = "docsRecentSearches";
const RECENT_SEARCH_MAX = 5;

let searchIndexCache = null;

/** search.json を初回だけ fetch する（取りに行っている最中の Promise も控える） */
async function loadSearchIndex() {
  if (searchIndexCache) return searchIndexCache;
  const url = document.body?.dataset?.searchIndex;
  if (!url) return [];
  searchIndexCache = fetch(url)
    .then((res) => {
      if (!res.ok) throw new Error("search index fetch failed");
      return res.json();
    })
    .catch(() => {
      // 次の呼び出しで取りに行き直せるよう、失敗した控えは残さない
      searchIndexCache = null;
      return [];
    });
  return searchIndexCache;
}

/** 検索語で索引を絞り、当てはまりの強い順に上位を返す */
function filterSearch(entries, query) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return entries
    .map((e) => {
      const inHeading = e.heading.toLowerCase().includes(q);
      const inPage = `${e.title} ${e.path}`.toLowerCase().includes(q);
      const inContent = e.content.toLowerCase().includes(q);
      if (!inHeading && !inPage && !inContent) return null;
      // 見出し一致を最上位、次に題名 / パス、最後に本文
      const score = (inHeading ? 0 : 100) + (inPage ? 0 : 50);
      return { entry: e, score };
    })
    .filter(Boolean)
    .sort((a, b) => a.score - b.score)
    .slice(0, SEARCH_RESULT_MAX)
    .map((x) => x.entry);
}

/** 結果を入れ物へ並べる。0 件のときはその旨を出す */
function renderResults(container, entries, keyword) {
  container.innerHTML = "";
  if (entries.length === 0) {
    const empty = document.createElement("p");
    empty.className = "search-empty";
    empty.textContent = `「${keyword}」に当たる見出しはありません`;
    container.appendChild(empty);
    return;
  }
  entries.forEach((e) => {
    const a = document.createElement("a");
    a.className = "search-hit";
    a.setAttribute("role", "option");
    a.href = resultHref(e);
    a.innerHTML = `<span class="search-crumb"><span class="search-crumb-page">${escapeHtml(e.title)}</span> › <span class="search-crumb-heading">${highlightMatch(e.heading, keyword)}</span></span><span class="search-excerpt">${highlightMatch(e.content, keyword)}</span>`;
    container.appendChild(a);
  });
}

/** 項目の URL に、その見出しが本文で持つ id を付けた行き先を作る */
function resultHref(entry) {
  if (entry.headingSeq === 0) return entry.url;
  let id = slugify(entry.heading);
  if (entry.headingSeq >= 2) id += `-${entry.headingSeq}`;
  return `${entry.url}#${id}`;
}

/** 文字列の中で検索語に当たった箇所を強調した HTML を返す */
function highlightMatch(text, query) {
  const q = query.trim();
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (!q || i < 0) return escapeHtml(text);
  return `${escapeHtml(text.slice(0, i))}<mark>${escapeHtml(text.slice(i, i + q.length))}</mark>${escapeHtml(text.slice(i + q.length))}`;
}

/** 記録から最近の検索語を読む */
function readRecentSearches() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_SEARCH_KEY) || "[]");
  } catch {
    return [];
  }
}

/** 結果を開いたときの検索語を、最近の検索の先頭へ足す */
function pushRecentSearch(query) {
  const q = query.trim();
  if (!q) return;
  const next = [q, ...readRecentSearches().filter((r) => r !== q)].slice(0, RECENT_SEARCH_MAX);
  localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(next));
}

/** 検索語が空のときに、最近の検索を押せる形で並べる */
function renderRecentSearches(container, input) {
  const recent = readRecentSearches();
  if (recent.length === 0) {
    container.innerHTML = `<p class="search-empty">検索語を入れると、見出しごとに結果が並びます</p>`;
    return;
  }
  container.innerHTML = `<p class="search-group">最近の検索</p>` +
    recent.map((r) => `<button type="button" class="search-recent" data-recent="${escapeHtml(r)}">🕘 ${escapeHtml(r)}</button>`).join("");
  container.querySelectorAll("[data-recent]").forEach((b) => {
    b.addEventListener("click", () => {
      input.value = b.dataset.recent;
      input.dispatchEvent(new Event("input"));
      input.focus();
    });
  });
}

/** 入力・キー操作・押下を結果の入れ物へ紐付け、今の検索語で描き直す手段を返す */
function bindResultList(container, input, close) {
  let items = [];
  let selected = -1;

  const select = (i) => {
    selected = i;
    container.querySelectorAll(".search-hit").forEach((el, n) => {
      el.classList.toggle("is-selected", n === i);
      el.setAttribute("aria-selected", String(n === i));
      if (n === i) el.scrollIntoView({ block: "nearest" });
    });
  };

  const open = (entry) => {
    pushRecentSearch(input.value);
    close();
    location.href = resultHref(entry);
  };

  const render = async () => {
    const query = input.value;
    if (query.trim() === "") {
      renderRecentSearches(container, input);
      items = [];
      selected = -1;
      return;
    }
    if (!searchIndexCache) {
      container.innerHTML = `<p class="search-loading" role="status">索引を読み込んでいます...</p>`;
    }
    const entries = await loadSearchIndex();
    if (input.value !== query) return;
    items = filterSearch(entries, query);
    renderResults(container, items, query);
    container.querySelectorAll(".search-hit").forEach((el, i) => {
      el.addEventListener("mousemove", () => select(i));
      el.addEventListener("click", () => {
        pushRecentSearch(input.value);
        close();
      });
    });
    select(items.length ? 0 : -1);
  };

  input.addEventListener("input", render);
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && items.length) {
      e.preventDefault();
      select((selected + 1) % items.length);
    } else if (e.key === "ArrowUp" && items.length) {
      e.preventDefault();
      select((selected - 1 + items.length) % items.length);
    } else if (e.key === "Enter" && selected >= 0) {
      e.preventDefault();
      open(items[selected]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      close();
    }
  });

  return render;
}

/** 入力欄・結果・キー操作の案内を持つモーダルを組み立て、開く手段を返す */
function buildSearchModal() {
  const modal = document.createElement("div");
  modal.className = "search-modal";
  modal.hidden = true;
  modal.innerHTML = `
    <div class="search-modal-backdrop" data-modal-close></div>
    <div class="search-modal-dialog" role="dialog" aria-label="全ページ検索">
      <div class="search-modal-head">
        <input type="search" placeholder="見出しを検索..." aria-label="全ページ検索">
        <button type="button" class="ghost search-modal-close" data-modal-close>閉じる</button>
      </div>
      <div class="search-modal-results" role="listbox"></div>
      <p class="search-modal-keys"><kbd>↑</kbd><kbd>↓</kbd> 選ぶ　<kbd>Enter</kbd> 開く　<kbd>Esc</kbd> 閉じる</p>
    </div>`;
  document.body.appendChild(modal);

  const input = modal.querySelector("input");
  const close = () => {
    modal.hidden = true;
    document.body.classList.remove("search-modal-open");
  };
  const render = bindResultList(modal.querySelector(".search-modal-results"), input, close);
  modal.querySelectorAll("[data-modal-close]").forEach((el) => el.addEventListener("click", close));

  return {
    open() {
      modal.hidden = false;
      document.body.classList.add("search-modal-open");
      render();
      input.focus();
      input.select();
    },
  };
}

/** ヘッダーの入力欄・検索アイコン・Ctrl+K を、同じモーダルへ繋ぐ */
function bindSearchEntries() {
  const modal = buildSearchModal();
  const headerInput = document.querySelector("[data-search-input]");
  if (headerInput) {
    // 入力欄は押すとモーダルを開くだけの見た目にする
    headerInput.readOnly = true;
    headerInput.addEventListener("focus", () => {
      headerInput.blur();
      modal.open();
    });
  }
  document.querySelector("[data-search-toggle]")?.addEventListener("click", () => modal.open());
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      modal.open();
    }
  });
}

/** 結果に出す文字列の記号を無害な表記へ置き換える */
function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}


/* ============================================================================
 * 14. 起票
 * ---------------------------------------------------------------------------- */

const ISSUE_DRAFT_KEY = "issue-draft";
const ISSUE_URL_MAX = 6000;
const ISSUE_TRUNCATED_NOTE = "\n\n…（長さの上限を超えたため、引用の末尾を切り詰めました）";

/* 開いている起票サイドバーの入力への参照（閉じても要素ごと残す） */
const issueDraft = { panel: null, title: null, body: null, warn: null };

/** 器が持つ付けるラベルを並びのまま配列で返す */
function issueLabels() {
  return (document.body?.dataset?.issueLabels || "").split(",");
}

/** 起票サイドバーを組み立てて閉じた状態で置く */
function buildIssuePanel() {
  const panel = document.createElement("aside");
  panel.className = "issue-panel";
  panel.hidden = true;
  panel.setAttribute("aria-label", "Issue を書く");
  const badges = issueLabels().map((label) => `<span class="badge">${escapeHtml(label)}</span>`).join("");
  panel.innerHTML = `
    <div class="issue-panel-head">
      <h2>Issue を書く</h2>
      <button type="button" class="ghost" data-issue-close aria-label="閉じる">✕</button>
    </div>
    <label class="issue-field">
      <span>題名</span>
      <input type="text" data-issue-title>
    </label>
    <label class="issue-field">
      <span>本文</span>
      <textarea data-issue-body rows="12"></textarea>
    </label>
    <p class="issue-warn" data-issue-warn hidden>本文が長いため、GitHub で開くときに引用の末尾を切り詰めます</p>
    <div class="issue-meta">
      <span>付くラベル</span>
      ${badges}
    </div>
    <p class="issue-hint">GitHub の起票画面が別のタブで開きます。送る前にそこで内容を直せます。</p>
    <div class="issue-actions">
      <button type="button" class="ghost" data-issue-clear>クリア</button>
      <button type="button" class="primary" data-issue-submit>GitHub で開く</button>
    </div>`;
  document.querySelector(".docs-layout")?.appendChild(panel);

  issueDraft.panel = panel;
  issueDraft.title = panel.querySelector("[data-issue-title]");
  issueDraft.body = panel.querySelector("[data-issue-body]");
  issueDraft.warn = panel.querySelector("[data-issue-warn]");
  issueDraft.body.value = issueBodyTemplate(null, null);
  // 残した下書きがあれば入力欄へ戻す（ページを移ったときと再読み込みしたとき）
  restoreIssueDraft();

  panel.querySelector("[data-issue-close]").addEventListener("click", closeIssuePanel);
  panel.querySelector("[data-issue-clear]").addEventListener("click", clearIssuePanel);
  panel.querySelector("[data-issue-submit]").addEventListener("click", submitIssue);
  issueDraft.body.addEventListener("input", updateIssueWarn);
  issueDraft.title.addEventListener("input", updateIssueWarn);
  // 題名と本文の入力のたびに下書きを残す
  issueDraft.body.addEventListener("input", saveIssueDraft);
  issueDraft.title.addEventListener("input", saveIssueDraft);
}

/** 題名と本文を同じタブの sessionStorage へ残す */
function saveIssueDraft() {
  try {
    sessionStorage.setItem(ISSUE_DRAFT_KEY, JSON.stringify({ title: issueDraft.title.value, body: issueDraft.body.value }));
  } catch {
    // sessionStorage が使えない: 残さずに続ける
  }
}

/** sessionStorage に残した題名と本文を入力欄へ戻す */
function restoreIssueDraft() {
  let draft;
  try {
    draft = JSON.parse(sessionStorage.getItem(ISSUE_DRAFT_KEY) || "null");
  } catch {
    // 読めない・JSON として壊れている: 何もしない
    return;
  }
  if (!draft) return;
  issueDraft.title.value = draft.title || "";
  issueDraft.body.value = draft.body || issueBodyTemplate(null, null);
}

/** 該当箇所と内容の 1 ブロックを組み立てる */
function issueBodyTemplate(heading, quote) {
  const pagePath = document.body?.dataset?.pagePath || "";
  const lines = ["### 該当箇所", "", `- ページ: \`${pagePath}\``];
  if (heading) lines.push(`- 見出し: ${heading}`);
  if (quote) {
    lines.push("", ...quote.split("\n").map((l) => `> ${l}`));
  }
  lines.push("", "### 内容", "", "", "", "---", "");
  return lines.join("\n");
}

/** サイドバーを開き、引用があれば本文へ足す */
function openIssuePanel(heading, quote) {
  const { panel, body, title } = issueDraft;
  if (quote) {
    // 何も書いていなければ初期値ごと差し替え、書きかけなら末尾へ引用を足す
    const untouched = body.value.trim() === "" || body.value === issueBodyTemplate(null, null);
    body.value = untouched
      ? issueBodyTemplate(heading, quote)
      : `${body.value.trimEnd()}\n\n${issueBodyTemplate(heading, quote)}`;
  }
  panel.hidden = false;
  document.body.classList.add("issue-open");
  updateIssueWarn();
  title.focus();
}

/** サイドバーを閉じる（入力は残す） */
function closeIssuePanel() {
  issueDraft.panel.hidden = true;
  document.body.classList.remove("issue-open");
}

/** 題名・本文・長さの注意を初期状態へ戻す */
function clearIssuePanel() {
  issueDraft.title.value = "";
  issueDraft.body.value = issueBodyTemplate(null, null);
  issueDraft.warn.hidden = true;
  // 残した下書きも消す
  try {
    sessionStorage.removeItem(ISSUE_DRAFT_KEY);
  } catch {
    // sessionStorage が使えない: 消すものも無い
  }
}

/** 題名・本文・固定のラベルを問い合わせに載せた起票画面の URL を作る */
function buildIssueUrl(title, body) {
  const repo = document.body?.dataset?.issueRepo || "";
  const params = new URLSearchParams({ title, body, labels: issueLabels().join(",") });
  return `https://github.com/${repo}/issues/new?${params.toString()}`;
}

/** URL の長さが上限を超えるときだけ、本文の末尾を切り詰めた URL を返す */
function fitIssueUrl(title, body) {
  const full = buildIssueUrl(title, body);
  if (full.length <= ISSUE_URL_MAX) return full;
  let lo = 0;
  let hi = body.length;
  // 収まる本文の長さを二分探索で求める
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (buildIssueUrl(title, body.slice(0, mid) + ISSUE_TRUNCATED_NOTE).length <= ISSUE_URL_MAX) lo = mid;
    else hi = mid - 1;
  }
  return buildIssueUrl(title, body.slice(0, lo) + ISSUE_TRUNCATED_NOTE);
}

/** 今の入力で組み立てた URL が上限を超えるときだけ注意を出す */
function updateIssueWarn() {
  const url = buildIssueUrl(issueDraft.title.value, issueDraft.body.value);
  issueDraft.warn.hidden = url.length <= ISSUE_URL_MAX;
}

/** 組み立てた URL を別のタブで開き、サイドバーの入力を消す */
function submitIssue() {
  const url = fitIssueUrl(issueDraft.title.value, issueDraft.body.value);
  window.open(url, "_blank", "noopener");
  clearIssuePanel();
}

/** 選択範囲より前にある最後の見出しの文字列を返す */
function headingBefore(node) {
  const article = document.querySelector(".markdown-body");
  const headings = [...article.querySelectorAll("h2, h3")];
  let found = null;
  headings.forEach((h) => {
    // 描いた markdown の中の見出しは本文の見出しではないので候補にしない
    if (h.closest(".markdown-preview")) return;
    // 見出しが選択範囲より前にあれば候補にする
    if (h.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING) found = h;
  });
  return found ? found.textContent.replace(/#$/, "").trim() : null;
}

/** 本文を選んだときに、選択の近くへ「Issue を書く」を出す */
function bindSelectionEntry() {
  const article = document.querySelector(".markdown-body");
  if (!article) return;
  const pop = document.createElement("button");
  pop.type = "button";
  pop.className = "primary selection-issue";
  pop.textContent = "Issue を書く";
  pop.hidden = true;
  document.body.appendChild(pop);

  let pending = null;
  document.addEventListener("selectionchange", () => {
    const sel = document.getSelection();
    const text = sel?.toString().trim();
    if (!text || !article.contains(sel.anchorNode)) {
      pop.hidden = true;
      return;
    }
    const rect = sel.getRangeAt(0).getBoundingClientRect();
    pending = { heading: headingBefore(sel.anchorNode), quote: text };
    pop.style.top = `${window.scrollY + rect.bottom + 8}px`;
    pop.style.left = `${window.scrollX + rect.left}px`;
    pop.hidden = false;
  });
  // 押した瞬間に選択が外れないよう、mousedown で既定の動作を止める
  pop.addEventListener("mousedown", (e) => e.preventDefault());
  pop.addEventListener("click", () => {
    pop.hidden = true;
    openIssuePanel(pending.heading, pending.quote);
    document.getSelection().removeAllRanges();
  });
}

/** ヘッダーの起票ボタンと、選択範囲からの入口を繋ぐ */
function bindIssueEntries() {
  buildIssuePanel();
  document.querySelector("[data-issue-open]")?.addEventListener("click", () => openIssuePanel(null, null));
  bindSelectionEntry();
}


/* ============================================================================
 * 15. トップに戻るボタン
 * ---------------------------------------------------------------------------- */

/** スクロール量で表示切替し、クリックで先頭へスムーズスクロール */
function bindBackToTop() {
  const btn = document.querySelector("[data-back-to-top]");
  if (!btn) return;

  const update = () => {
    btn.classList.toggle("visible", window.scrollY > BACK_TO_TOP_THRESHOLD_PX);
  };
  window.addEventListener("scroll", update, { passive: true });
  update();

  btn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}


/* ============================================================================
 * 16. Mock demo 用ハンドラ
 * 対象 DOM が無いページでは何もしない（早期 return）。
 * ---------------------------------------------------------------------------- */

/** 検索ボックスの入力語で顧客一覧の行を絞り込む */
function bindSearchFilter() {
  const input = document.getElementById("search");
  if (!input) return;
  input.addEventListener("input", () => {
    const keyword = input.value.trim().toLowerCase();
    document.querySelectorAll("#customer-table tbody tr").forEach((row) => {
      const text = row.textContent.toLowerCase();
      row.classList.toggle("hidden", keyword !== "" && !text.includes(keyword));
    });
  });
}

/** 行クリックで疑似遷移トーストを表示する */
function bindRowClick() {
  document.querySelectorAll("#customer-table tbody tr").forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target instanceof HTMLInputElement) return;
      const id = row.dataset.id;
      showToast(`顧客 ${id} を選択しました（モック）`);
    });
  });
}

/** 新規追加ボタンでトーストを一時表示する */
function bindNewButton() {
  const button = document.getElementById("new-btn");
  if (!button) return;
  button.addEventListener("click", () => {
    showToast("新規追加ダイアログを開きました（モック）");
  });
}

/** 詳細画面の編集モードを切り替える */
function bindEditMode() {
  const editBtn = document.getElementById("edit-btn");
  const cancelBtn = document.getElementById("cancel-btn");
  const saveBtn = document.getElementById("save-btn");
  if (!editBtn || !cancelBtn || !saveBtn) return;

  /** 編集可能フィールドの readonly 属性を切り替える */
  function setEditing(editing) {
    document.querySelectorAll(".field-value input, .field-value textarea").forEach((field) => {
      if (editing) field.removeAttribute("readonly");
      else field.setAttribute("readonly", "readonly");
    });
    editBtn.hidden = editing;
    cancelBtn.hidden = !editing;
    saveBtn.hidden = !editing;
  }

  editBtn.addEventListener("click", () => setEditing(true));
  cancelBtn.addEventListener("click", () => setEditing(false));
  saveBtn.addEventListener("click", () => {
    setEditing(false);
    showToast("変更を保存しました（モック）");
  });
}

/** 画面下部のトーストを一定時間表示する */
function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast._timer);
  showToast._timer = window.setTimeout(() => {
    toast.hidden = true;
  }, TOAST_DISPLAY_MS);
}


/* ============================================================================
 * エントリポイント
 * ---------------------------------------------------------------------------- */

/** Mock demo 画面用にトースト要素が無ければ差し込む（他画面の共通機能でも使うため） */
function ensureToastElement() {
  if (document.getElementById("toast")) return;
  const t = document.createElement("div");
  t.className = "toast";
  t.id = "toast";
  t.hidden = true;
  document.body.appendChild(t);
}


/* ============================================================================
 * 17. コード内の Markdown
 * ---------------------------------------------------------------------------- */

/* 中身を描いて見せる言語指定 */
const MARKDOWN_LANGS = ["markdown", "md"];

/* 描いた HTML の無害化の設定。<style> を残すと本文の外までスタイルが効く */
const MARKDOWN_SANITIZE_CONFIG = { FORBID_TAGS: ["style"] };

/* 描いた表示と元のコードの切り替えで、利用者の目に触れる文言 */
const CODE_VIEW_LABELS = {
  badge: "Markdown プレビュー",
  raw: "raw",
  preview: "プレビュー",
  diagram: "図",
};

/** 言語指定が markdown のコードブロックの中身を描き、元のコードとの切り替えを付ける */
function renderMarkdownBlocks(article) {
  // ライブラリを取れなかったときは元のコードのまま出す
  if (!window.marked || !window.DOMPurify) return;

  article.querySelectorAll("pre").forEach((pre) => {
    // 言語の印は code 自身か、rouge が pre.highlight を包む外枠のどちらかに付いている
    const code = pre.querySelector(":scope > code");
    const langHolder = pre.classList.contains("highlight") ? pre.closest(".highlighter-rouge") : code;
    const lang = /language-([^\s]+)/.exec(langHolder?.className ?? "")?.[1];
    if (!code || !MARKDOWN_LANGS.includes(lang)) return;

    const src = code.textContent;
    const preview = document.createElement("div");
    preview.className = "markdown-preview";
    preview.innerHTML = window.DOMPurify.sanitize(window.marked.parse(src), MARKDOWN_SANITIZE_CONFIG);

    const badge = document.createElement("span");
    badge.className = "markdown-preview-badge";
    badge.textContent = CODE_VIEW_LABELS.badge;
    preview.prepend(badge);
    codeActions(preview).appendChild(createCopyButton(() => src));

    pre.before(preview);
    pre.hidden = true;
    bindViewToggle(preview, pre, CODE_VIEW_LABELS.preview);
  });
}

/** 描いた表示と元のコードの両方へ、互いに切り替えるボタンを置く */
function bindViewToggle(rendered, raw, backLabel) {
  const toRaw = document.createElement("button");
  toRaw.type = "button";
  toRaw.className = "code-view-toggle";
  toRaw.textContent = CODE_VIEW_LABELS.raw;
  codeActions(rendered).appendChild(toRaw);

  const toRendered = document.createElement("button");
  toRendered.type = "button";
  toRendered.className = "code-view-toggle";
  toRendered.textContent = backLabel;
  codeActions(raw).appendChild(toRendered);

  // 押した側を隠して、もう一方を見せる
  toRaw.addEventListener("click", () => {
    rendered.hidden = true;
    raw.hidden = false;
  });
  toRendered.addEventListener("click", () => {
    raw.hidden = true;
    rendered.hidden = false;
  });
}

/* ============================================================================
 * 18. 図の再掲
 * ---------------------------------------------------------------------------- */

/** リンクの断片を除いた場所を作る */
function withoutHash(url) {
  const bare = new URL(url);
  bare.hash = "";
  return bare;
}

/** 段落にリンク 1 本だけを置いた位置へ、リンク先の見出しの下の図を置く */
async function embedDiagrams(article) {
  // 再掲のリンクを持つ段落: 中身がリンク 1 本だけで、断片を持ち、同じ配信の別のページを指す
  const targets = [];
  article.querySelectorAll(":scope > p").forEach((p) => {
    const link = p.firstElementChild;
    if (p.childElementCount !== 1 || link.tagName !== "A") return;
    if (p.textContent.trim() !== link.textContent.trim()) return;
    const url = new URL(link.href, location.href);
    if (url.hash.length <= 1) return;
    if (url.origin !== location.origin || url.pathname === location.pathname) return;
    targets.push({ paragraph: p, url });
  });
  if (targets.length === 0) return;

  // 同じページを指すリンクで 1 度だけ読むための入れ物
  const cache = new Map();

  await Promise.all(targets.map(async ({ paragraph, url }) => {
    // 断片をパーセントデコードする。デコードできなければ段落を残す
    let fragment;
    try {
      fragment = decodeURIComponent(url.hash.slice(1));
    } catch (e) {
      console.warn("再掲のリンクの断片をデコードできません", url.href, e);
      return;
    }

    // リンク先のページを読む。読めなければ段落を残す
    const pageUrl = withoutHash(url);
    const doc = await fetchSourcePage(pageUrl, cache);
    if (!doc) return;

    // 断片が指す見出しの下の図を取り出す。取り出せなければ段落を残す
    const extracted = extractDiagramSources(doc, fragment);
    if (!extracted) return;

    // 図ごとにリンクを直して枠に入れ、段落を枠の並びで置き換える
    const figures = extracted.sources.map((source) =>
      buildEmbedFigure(rebaseDiagramLinks(source, pageUrl), extracted, pageUrl));
    paragraph.replaceWith(...figures);
  }));
}

/** 再掲の元のページを、今のページと同じ配信から読む */
async function fetchSourcePage(url, cache) {
  // 同じ場所の読み込みが入れ物にあれば、その結果を返す
  if (cache.has(url.href)) return cache.get(url.href);

  const loading = (async () => {
    try {
      const res = await fetch(url);
      // 応答が成功でない場合は読めなかったものとして扱う
      if (!res.ok) return null;
      return new DOMParser().parseFromString(await res.text(), "text/html");
    } catch (e) {
      console.warn("再掲の元のページを読めません", url.href, e);
      return null;
    }
  })();
  cache.set(url.href, loading);
  return loading;
}

/** 断片が指す見出しの下にある図の元のコードを、文書順に集める */
function extractDiagramSources(doc, fragment) {
  // 元のページの本文を探す
  const body = doc.querySelector(".markdown-body");
  if (!body) return null;

  // 断片と一致する最初の見出しを探す
  const found = resolveHeadingIds(body).find(({ id }) => id === fragment);
  if (!found) return null;
  const { heading, id } = found;

  // 見出しの次の要素から、深さが同じか浅い見出しに当たるまで辿って図の元のコードを集める
  const depth = Number(heading.tagName[1]);
  const sources = [];
  for (let el = heading.nextElementSibling; el; el = el.nextElementSibling) {
    if (/^H[1-6]$/.test(el.tagName) && Number(el.tagName[1]) <= depth) break;
    el.querySelectorAll("pre > code.language-mermaid").forEach((code) => sources.push(code.textContent));
  }
  if (sources.length === 0) return null;

  // ページの題名は本文の h1、無ければ文書の title
  const pageTitle = body.querySelector("h1")?.textContent.trim() || doc.title;
  return { pageTitle, headingText: heading.textContent.trim(), headingId: id, sources };
}

/** 図の元のコードの中のリンクを、差し込み先のページでも同じ先を指す形へ直す */
function rebaseDiagramLinks(source, fromUrl) {
  return source.replace(/(\bclick\s+\S+\s+(?:href\s+)?")([^"]*)(")/g, (whole, head, link, tail) => {
    // スキーム付きの絶対 URL はそのままにする
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(link)) return whole;
    // 相対リンクは元の場所を基準に解決し、配信のルートからのパスと断片へ置き換える
    let resolved;
    try {
      resolved = new URL(link, fromUrl);
    } catch (e) {
      // 解決できないリンクはその行をそのままにして、他のリンクと図の再掲は続ける
      console.warn("図の中のリンクを解決できません", link, e);
      return whole;
    }
    return `${head}${resolved.pathname}${resolved.search}${resolved.hash}${tail}`;
  });
}

/** 図の元のコードと再掲元の表示を、1 つの枠に組む */
function buildEmbedFigure(source, extracted, pageUrl) {
  // 自ページの図と同じ形にして、Mermaid の描画が同じ描き方で拾えるようにする
  const pre = document.createElement("pre");
  const code = document.createElement("code");
  code.className = "language-mermaid";
  code.textContent = source;
  pre.appendChild(code);

  // 図の下に、再掲元の見出しへのリンクを置く
  const from = new URL(pageUrl);
  from.hash = extracted.headingId;
  const link = document.createElement("a");
  link.href = `${from.pathname}${from.search}${from.hash}`;
  link.textContent = `${extracted.pageTitle} › ${extracted.headingText}`;
  const caption = document.createElement("figcaption");
  caption.className = "embed-caption";
  caption.append("再掲元: ", link);

  const figure = document.createElement("figure");
  figure.className = "embed-figure";
  figure.append(pre, caption);
  return figure;
}


async function init() {
  ensureToastElement();

  // 1. テーマを先に決める（フラッシュ抑止）
  bindThemeToggle();

  // 2. 器を組み立てる
  buildBreadcrumb();
  const article = document.querySelector(".markdown-body");
  const docsLayout = document.querySelector(".docs-layout");
  const sidebarSource = document.querySelector("[data-sidebar-source]");
  const nav = renderSidebar(sidebarSource, document.body.dataset.tab, document.body.dataset.page);
  const drawerToggle = document.querySelector("[data-drawer-toggle]");
  if (nav && docsLayout) {
    docsLayout.prepend(nav);
    layout.nav = nav;
    drawerToggle?.addEventListener("click", () => openDrawer(nav));
  } else {
    docsLayout?.classList.add("no-sidebar");
    if (drawerToggle) drawerToggle.hidden = true;
  }
  bindBackToTop();

  // 3. 本文へ後処理を掛ける
  if (article) {
    markCallouts(article);
    wrapTables(article);
  }
  enhanceTables(document);
  insertHeadingAnchors();            // まず見出しに id を振る（TOC がそれを使う）
  addCodeCopyButtons();
  addCodeLangLabels();

  // 4. 見出しが確定してから目次を置く
  buildToc();

  // 5. markdown のコードブロックの中身を描く（描いた見出しを目次に載せず、描いた中の Mermaid も図にするため、目次の後・図の前）
  if (article) renderMarkdownBlocks(article);

  // 6. 検索と起票の入口を紐付ける
  bindSearchEntries();
  bindIssueEntries();

  // 7. 幅に応じて器の置き場所を決め、以降の幅の変化にも追随させる
  applyWidth();
  mobileQuery.addEventListener("change", applyWidth);
  tocInlineQuery.addEventListener("change", applyWidth);

  // 8. モックのページであればデモの操作を紐付ける
  bindSearchFilter();
  bindRowClick();
  bindNewButton();
  bindEditMode();

  // 9. 別ページの見出しの図をリンクの位置へ置く（置いた図も描くため、図を描く前。元のページの応答待ちが、ここまでの処理を止めないよう最後の方に置く）
  if (article) await embedDiagrams(article);

  // 10. 再掲で加わったコードへコピーのボタンを付ける（付け終えたコードは飛ばす）
  addCodeCopyButtons();

  // 11. 図を描く
  if (article) await renderMermaid(article);
}

document.addEventListener("DOMContentLoaded", init);

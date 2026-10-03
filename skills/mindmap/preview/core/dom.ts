// 画面が共通で使う要素の組み立てと、アイコン・状態の印。

namespace MindmapPreview {
  /** 要素の属性の値。関数は `on` で始まる名前のイベントのリスナーとして付ける */
  export type AttrValue = string | number | boolean | null | undefined | EventListener;

  /** 要素の属性（名前 → 値） */
  export type Attrs = Record<string, AttrValue>;

  /** 要素の中に入れるもの。偽の値は入れない */
  export type Child = Node | string | number | null | undefined | false;

  /** 要素を作る。属性とイベントのリスナーを付け、子を並べる */
  export function h<K extends keyof HTMLElementTagNameMap>(
    tag: K,
    attrs?: Attrs | null,
    ...children: Child[]
  ): HTMLElementTagNameMap[K] {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attrs ?? {})) {
      // 値が無い・偽の属性は付けない
      if (value === null || value === undefined || value === false) continue;
      if (typeof value === "function") {
        // `onclick` → click のリスナー
        element.addEventListener(name.slice(2), value);
      } else if (name === "class") {
        element.className = String(value);
      } else {
        element.setAttribute(name, value === true ? "" : String(value));
      }
    }
    append(element, ...children);
    return element;
  }

  /** 要素の中に子を足す（文字は textContent として入れる） */
  export function append(parent: Element, ...children: Child[]): void {
    for (const child of children) {
      if (child === null || child === undefined || child === false) continue;
      parent.append(typeof child === "number" ? String(child) : child);
    }
  }

  /** アイコンの名前 → SVG の中身（線の絵） */
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
    table: '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10h18M9 10v10"/>',
    board: '<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="11" rx="1"/><rect x="17" y="4" width="4" height="7" rx="1"/>',
    expand: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
    shrink: '<path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"/>',
    check: '<path d="m5 12 5 5 9-10"/>',
    checked: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 3 3 5-6"/>',
    unchecked: '<rect x="4" y="4" width="16" height="16" rx="3"/>',
    copy: '<rect x="9" y="9" width="12" height="12" rx="1"/><path d="M5 15V4a1 1 0 0 1 1-1h11"/>',
    orbit: '<circle cx="12" cy="12" r="2.5"/><ellipse cx="12" cy="12" rx="10" ry="4.5" transform="rotate(-25 12 12)"/><circle cx="20" cy="8.5" r="1.4"/>',
    cards: '<rect x="3" y="4" width="8" height="7" rx="1"/><rect x="13" y="4" width="8" height="7" rx="1"/><rect x="3" y="13" width="8" height="7" rx="1"/><rect x="13" y="13" width="8" height="7" rx="1"/>',
    map: '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.5 12h3l4-5M11.5 12l4 5"/>',
    graph: '<circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="7" r="2"/><circle cx="6" cy="20" r="2"/><circle cx="19" cy="19" r="2"/><path d="M9.5 10.5 5.6 7.2M14.6 10.9l3.6-2.6M10 14.4l-2.6 4M14.3 14.2l3.3 3.4"/>',
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
  } as const;

  /** アイコンの名前 */
  export type IconName = keyof typeof ICONS;

  /** 24px の枠に描いた線のアイコン（読み上げ名は付けず、装飾として隠す） */
  export function icon(name: IconName): SVGSVGElement {
    const holder = document.createElement("template");
    holder.innerHTML = `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
    return holder.content.firstElementChild as SVGSVGElement;
  }

  /** 状態 → 10px の枠に描く印（色に加えて形でも区別する） */
  const MARKS: Record<string, string> = {
    決定済み: '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>',
    完了: '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/><path d="m2.8 5.1 1.5 1.5 3-3" stroke="var(--surface)" stroke-width="1.4" fill="none"/>',
    未決定: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/>',
    未着手: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" stroke-width="1.6"/>',
    進行中: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>',
    要見直し: '<path d="M5 .3 9.7 5 5 9.7.3 5Z" fill="var(--st-review)"/>',
    保留: '<rect x="1.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/><rect x="6.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/>',
    未整理: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-loose)" stroke-width="1.6" stroke-dasharray="2 1.6"/>',
    取り下げ: '<path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" stroke-width="1.6"/>',
    対象外: '<path d="M1 5h8" stroke="var(--st-off)" stroke-width="1.8"/>',
    中止: '<path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" stroke-width="1.6"/>',
    下書き: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" stroke-width="1.6" stroke-dasharray="2 1.6"/>',
    確認中: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>',
    完成: '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>',
  };

  /** 状態の印。知らない状態は印なし（null） */
  export function statusMark(status: string | undefined): SVGSVGElement | null {
    const body = status === undefined ? undefined : MARKS[status];
    if (body === undefined) return null;
    const holder = document.createElement("template");
    holder.innerHTML = `<svg class="mark" viewBox="0 0 10 10" aria-hidden="true">${body}</svg>`;
    return holder.content.firstElementChild as SVGSVGElement;
  }

  /** 印と状態の名前を並べた表示。状態を持たない項目は空の断片 */
  export function statusBadge(status: string | undefined): Node {
    if (status === undefined) return document.createDocumentFragment();
    return h("span", { class: "st", "data-st": status }, statusMark(status), status);
  }

  /** 影響度（大・中・小）の 3 本の目盛りと文字 */
  export function impactBadge(weight: string | undefined): Node {
    if (weight === undefined) return document.createDocumentFragment();
    const levels = ["大", "中", "小"];
    const filled = 3 - levels.indexOf(weight);
    const bars = [0, 1, 2].map((index) => h("i", { class: index < filled ? "on" : "" }));
    return h(
      "span",
      { class: "impact", title: `影響度 ${weight}` },
      h("span", { "aria-hidden": "true" }, ...bars),
      weight,
    );
  }

  /** タグを並べる */
  export function tagList(values: readonly string[] | undefined): Node {
    const fragment = document.createDocumentFragment();
    for (const value of values ?? []) fragment.append(h("span", { class: "tag" }, value));
    return fragment;
  }

  /** 成果物の印（箱のアイコンと文字） */
  export function deliverableBadge(): HTMLElement {
    return h("span", { class: "deliv-badge" }, icon("box"), "成果物");
  }

  /** 「該当なし」など、空のときの 1 行 */
  export function emptyNote(text: string): HTMLElement {
    return h("p", { class: "empty" }, text);
  }

  /** 背景（ボタンなどの上でない所）をつかんで、スクロールする要素を動かせるようにする */
  export function enableDragScroll(scroller: HTMLElement): void {
    let drag: { x: number; y: number; left: number; top: number } | null = null;
    scroller.addEventListener("pointerdown", (event) => {
      // 左ボタンで、押せるものの上でないとき
      if (event.button !== 0 || (event.target as Element).closest("button, a, input, label")) return;
      drag = { x: event.clientX, y: event.clientY, left: scroller.scrollLeft, top: scroller.scrollTop };
      scroller.classList.add("dragging");
      scroller.setPointerCapture(event.pointerId);
    });
    scroller.addEventListener("pointermove", (event) => {
      if (drag === null) return;
      scroller.scrollLeft = drag.left - (event.clientX - drag.x);
      scroller.scrollTop = drag.top - (event.clientY - drag.y);
    });
    const release = (): void => {
      drag = null;
      scroller.classList.remove("dragging");
    };
    scroller.addEventListener("pointerup", release);
    scroller.addEventListener("pointercancel", release);
  }

  /** 詳細パネルで開いている項目の ID（表の行・カード・マップの節に「選択中」の印を付けるために持つ） */
  let selectedItemId: string | null = null;

  /** 開いている項目の ID */
  export function currentSelection(): string | null {
    return selectedItemId;
  }

  /** 開いている項目を変え、描いてある行・カード・節の「選択中」の印を付け替える */
  export function markSelected(id: string | null): void {
    selectedItemId = id;
    for (const element of document.querySelectorAll<HTMLElement>("main [data-id]")) {
      element.classList.toggle("selected", element.dataset["id"] === id);
    }
  }
}

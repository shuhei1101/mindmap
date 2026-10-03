// 表と、並べ替え・絞り込みの計算。列の見出しで並べ替え・絞り込み・ピン留めでき、表の上に条件のチップを並べる。

namespace MindmapPreview {
  /** 表の行（埋め込みのデータの項目そのもの） */
  export type Row = { id: string } & Record<string, unknown>;

  /** 列が行から取る値（配列の列は、要素のどれかが条件にあれば絞り込みに合う） */
  export type CellValue = string | number | readonly string[] | null | undefined;

  /** 列の定義 */
  export type Column = {
    /** 列の識別子。並べ替え・絞り込み・ピン留めの対象を指す */
    key: string;
    /** 見出しの文字 */
    label: string;
    /** 値で絞り込めるか。絞り込みのボタンを出す */
    filterable?: boolean;
    /** 表示する列から外せないか（タイトルの列。行を押して詳細を開くボタンにする） */
    fixed?: boolean;
    /** 初期設定で隠すか */
    hidden?: boolean;
    /** 値の並び（並べ替え・絞り込みの値の順） */
    order?: readonly string[];
    /** 数値の列か（右寄せ） */
    num?: boolean;
    /** セルを折り返さないか */
    nowrap?: boolean;
    /** 列の最小の幅（CSS の値） */
    minWidth?: string;
    /** 狭い幅で隠す順（大きいほど先に隠す） */
    priority?: number;
    /** 行から値を取る */
    get: (row: Row) => CellValue;
    /** セルを描く。無ければ値を文字にする */
    cell?: (row: Row) => Node | string;
  };

  /** 並べ替えている列と向き */
  export type SortState = { key: string; dir: "asc" | "desc" } | null;

  /** 列の `key` → 選んだ値の配列 */
  export type Filters = Record<string, string[]>;

  /** 表で開いているポップオーバー */
  export type TablePopover = { type: "filter"; key: string } | { type: "columns" };

  /** 表のイベントごとのコールバック（使う側が描き直す） */
  export type TableHandlers = {
    /** 見出しの文字を押したとき（昇順 → 降順 → 解除は使う側が巡る） */
    sort: (key: string) => void;
    /** 絞り込みを変えたとき。key が null のときは全ての条件を外す */
    filter: (change: { key: string | null; values: string[] }) => void;
    /** ピン留めのボタンを押したとき（固定中の列をもう一度押すと外す） */
    pin: (key: string) => void;
    /** 表示する列を付け外ししたとき（隠している列の key） */
    columns: (hiddenColumns: string[]) => void;
    /** 初期設定に戻すを押したとき */
    reset: () => void;
    /** 行のタイトルを押したとき */
    open: (id: string) => void;
    /** ポップオーバーを開いた・閉じたとき（描き直しても開いたままにするために、使う側が持つ） */
    popover?: (popover: TablePopover | null) => void;
  };

  /** 表の引数 */
  export type TableProps = {
    /** 項目の種類。該当なしの文言に使う */
    kind: Kind;
    columns: Column[];
    /** 行にする項目 */
    rows: Row[];
    sort?: SortState;
    filters?: Filters;
    /** 左端からこの列までを横スクロールでも固定する列の key */
    pinTo?: string | null;
    /** 隠している列の key。無ければ `columns[].hidden` が真の列 */
    hiddenColumns?: string[];
    /** 開いているポップオーバー */
    popover?: TablePopover | null;
    on: TableHandlers;
  };

  /** 列が行から取る値を、文字の配列にする */
  function valuesOf(column: Column, row: Row): string[] {
    const value = column.get(row);
    if (value === null || value === undefined) return [];
    return Array.isArray(value) ? value.map(String) : [String(value)];
  }

  /** 値を文字で比べる順（`order` を持つ列はその並びの順、無ければ日本語の順） */
  function compareValues(column: Column, a: string, b: string): number {
    if (column.order) {
      const rank = (value: string) => {
        const index = column.order?.indexOf(value) ?? -1;
        return index < 0 ? (column.order?.length ?? 0) : index;
      };
      return rank(a) - rank(b);
    }
    return a.localeCompare(b, "ja");
  }

  /** 列ごとの条件に合う行を返す（列の中はどれかに当たればよく、列の間は全てに当たる） */
  export function filterRows({
    rows,
    columns,
    filters,
  }: {
    rows: Row[];
    columns: Column[];
    filters: Filters;
  }): Row[] {
    const active = Object.entries(filters).filter(([, values]) => values.length > 0);
    return rows.filter((row) =>
      active.every(([key, wanted]) => {
        const column = columns.find((candidate) => candidate.key === key);
        // 知らない列の条件は無視する
        if (column === undefined) return true;
        return valuesOf(column, row).some((value) => wanted.includes(value));
      }),
    );
  }

  /** 列の値で行を並べ替える（元の配列は変えない。同じ値は元の順） */
  export function sortRows({
    rows,
    columns,
    sort,
  }: {
    rows: Row[];
    columns: Column[];
    sort: SortState;
  }): Row[] {
    if (sort === null) return [...rows];
    const column = columns.find((candidate) => candidate.key === sort.key);
    if (column === undefined) return [...rows];
    const direction = sort.dir === "asc" ? 1 : -1;
    const compare = (a: Row, b: Row): number => {
      const x = column.get(a);
      const y = column.get(b);
      // 数値は数の順
      if (typeof x === "number" && typeof y === "number") return x - y;
      return compareValues(column, valuesOf(column, a).join(" "), valuesOf(column, b).join(" "));
    };
    return rows
      .map((row, position) => ({ row, position }))
      .sort((a, b) => direction * compare(a.row, b.row) || a.position - b.position)
      .map(({ row }) => row);
  }

  /** 絞り込みのポップオーバーに出す、列の値ごとの件数を返す（その列以外の条件で絞った行で数える） */
  export function filterCounts({
    rows,
    columns,
    filters,
    key,
  }: {
    rows: Row[];
    columns: Column[];
    filters: Filters;
    key: string;
  }): { value: string; count: number }[] {
    const column = columns.find((candidate) => candidate.key === key);
    if (column === undefined) return [];
    const others = Object.fromEntries(Object.entries(filters).filter(([name]) => name !== key));
    const counts = new Map<string, number>();
    // 選べる値は全ての行の値（件数が 0 のものも出す）
    for (const row of rows) for (const value of valuesOf(column, row)) counts.set(value, 0);
    for (const row of filterRows({ rows, columns, filters: others })) {
      for (const value of valuesOf(column, row)) counts.set(value, (counts.get(value) ?? 0) + 1);
    }
    return [...counts]
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => compareValues(column, a.value, b.value));
  }

  /** ポップオーバーを開いた元のボタンの上か下に置く（収まる側に開き、どちらも収まらないときは広い側で高さを抑える） */
  export function positionPopover(pop: HTMLElement, anchor: Element): void {
    const gap = 6;
    const margin = 8;
    const rect = anchor.getBoundingClientRect();
    pop.style.maxHeight = "";
    const { offsetWidth: width, offsetHeight: height } = pop;
    pop.style.left = `${Math.max(margin, Math.min(rect.left, innerWidth - width - margin))}px`;
    const below = innerHeight - rect.bottom - gap - margin;
    const above = rect.top - gap - margin;
    const openBelow = height <= below || (height > above && below >= above);
    const room = openBelow ? below : above;
    if (height > room) pop.style.maxHeight = `${room}px`;
    pop.style.top = `${openBelow ? rect.bottom + gap : rect.top - gap - pop.offsetHeight}px`;
  }

  /** 描き直す前に控えた、表の入れ物のスクロールの位置（種類ごと。描いた後に戻す） */
  const pendingScroll = new Map<Kind, { left: number; top: number }>();

  /** 表の項目の見出しのアイコン */
  function sortIcon(direction: "asc" | "desc" | null): Node {
    if (direction === "asc") return icon("up");
    if (direction === "desc") return icon("down");
    return h({ tag: "span", attrs: { class: "sort-hint" }, children: [icon("updown")] });
  }

  /** 項目の表を返す。操作は引数のコールバックで知らせ、描き直しは使う側が行う */
  export function table({
    kind,
    columns,
    rows,
    sort = null,
    filters = {},
    pinTo = null,
    hiddenColumns,
    popover = null,
    on,
  }: TableProps): HTMLElement {
    const hidden = new Set(
      hiddenColumns ?? columns.filter((column) => column.hidden).map((column) => column.key),
    );
    const visible = columns.filter((column) => !hidden.has(column.key));
    // 固定する列の数（左端から pinTo の列まで）
    const pinned = pinTo === null ? 0 : visible.findIndex((column) => column.key === pinTo) + 1;
    const shownRows = sortRows({ rows: filterRows({ rows, columns, filters }), columns, sort });

    const root = h({ tag: "div", attrs: { class: "table-block", "data-kind": kind } });
    const wrap = h({ tag: "div", attrs: { class: "table-wrap" } });

    /** 操作の前に、表の入れ物のスクロールの位置を控える（描き直した後に戻す） */
    const remember = (): void => {
      pendingScroll.set(kind, { left: wrap.scrollLeft, top: wrap.scrollTop });
    };

    // ===== 条件のチップと、表示する列のボタン =====
    const chips: HTMLElement[] = [];
    for (const [key, values] of Object.entries(filters)) {
      const column = columns.find((candidate) => candidate.key === key);
      for (const value of values) {
        chips.push(
          h({
            tag: "span",
            attrs: { class: "chip" },
            children: [
              `${column?.label ?? key}: ${value}`,
              h({
                tag: "button",
                attrs: {
                  type: "button",
                  "aria-label": `${column?.label ?? key}: ${value} の条件を外す`,
                  onclick: () => {
                    remember();
                    on.filter({ key, values: values.filter((candidate) => candidate !== value) });
                  },
                },
                children: [icon("x")],
              }),
            ],
          }),
        );
      }
    }
    if (chips.length > 0) {
      chips.push(
        h({
          tag: "button",
          attrs: {
            class: "btn ghost",
            type: "button",
            onclick: () => {
              remember();
              on.filter({ key: null, values: [] });
            },
          },
          children: ["すべて外す"],
        }),
      );
    }
    const pop = h({ tag: "div", attrs: { class: "pop", popover: "auto" } });
    // 開いたポップオーバーの元のボタンを探す
    const anchorOf = (spec: TablePopover): Element | null =>
      root.querySelector(
        spec.type === "columns" ? '[data-popover="columns"]' : `[data-popover="filter:${spec.key}"]`,
      );
    /** ポップオーバーの中身を作って開く */
    const showPopover = (spec: TablePopover): void => {
      pop.replaceChildren(
        spec.type === "columns"
          ? columnsPopoverBody()
          : filterPopoverBody(spec.key),
      );
      if (!pop.matches(":popover-open")) pop.showPopover();
      const anchor = anchorOf(spec);
      if (anchor !== null) positionPopover(pop, anchor);
    };
    /** 表示する列のポップオーバーの中身 */
    const columnsPopoverBody = (): Node => {
      const boxes = columns.map((column) =>
        h({
          tag: "label",
          children: [
            h({
              tag: "input",
              attrs: {
                type: "checkbox",
                checked: !hidden.has(column.key),
                disabled: column.fixed === true,
                onchange: (event: Event) => {
                  const checked = (event.target as HTMLInputElement).checked;
                  remember();
                  on.columns(
                    checked
                      ? [...hidden].filter((key) => key !== column.key)
                      : [...hidden, column.key],
                  );
                },
              },
            }),
            column.label,
          ],
        }),
      );
      return h({
        tag: "div",
        children: [
          h({ tag: "h3", children: ["表示する列"] }),
          ...boxes,
          h({
            tag: "div",
            attrs: { class: "pop-foot" },
            children: [
              h({
                tag: "button",
                attrs: {
                  class: "btn ghost",
                  type: "button",
                  onclick: () => {
                    remember();
                    on.reset();
                  },
                },
                children: ["列・並べ替え・固定を初期設定に戻す"],
              }),
            ],
          }),
        ],
      });
    };
    /** 列の絞り込みのポップオーバーの中身（値ごとの件数つき） */
    const filterPopoverBody = (key: string): Node => {
      const column = columns.find((candidate) => candidate.key === key);
      const chosen = filters[key] ?? [];
      const options = filterCounts({ rows, columns, filters, key }).map(({ value, count }) =>
        h({
          tag: "label",
          children: [
            h({
              tag: "input",
              attrs: {
                type: "checkbox",
                checked: chosen.includes(value),
                onchange: (event: Event) => {
                  const checked = (event.target as HTMLInputElement).checked;
                  remember();
                  on.filter({
                    key,
                    values: checked ? [...chosen, value] : chosen.filter((item) => item !== value),
                  });
                },
              },
            }),
            key === "status" ? statusMark(value) : null,
            value,
            h({ tag: "span", attrs: { class: "n" }, children: [count] }),
          ],
        }),
      );
      return h({
        tag: "div",
        children: [h({ tag: "h3", children: [`${column?.label ?? key}で絞り込み`] }), ...options],
      });
    };
    // ポップオーバーを閉じたら、使う側にも知らせる（描き直しで消えたときは知らせない）
    pop.addEventListener("toggle", (event) => {
      if ((event as ToggleEvent).newState === "closed" && pop.isConnected) on.popover?.(null);
    });
    /** ポップオーバーを開き、使う側にも知らせる */
    const openPopover = (spec: TablePopover): void => {
      showPopover(spec);
      on.popover?.(spec);
    };

    root.append(
      h({
        tag: "div",
        attrs: { class: "table-toolbar" },
        children: [
          h({ tag: "div", attrs: { class: "chips" }, children: [...chips] }),
          h({
            tag: "button",
            attrs: {
              class: "btn",
              type: "button",
              "data-popover": "columns",
              "aria-label": "表示する列",
              onclick: () => openPopover({ type: "columns" }),
            },
            children: [
              icon("cols"),
              h({ tag: "span", attrs: { class: "lbl" }, children: ["表示する列"] }),
            ],
          }),
        ],
      }),
    );

    // ===== 見出し =====
    const headers = visible.map((column, position) => {
      const direction = sort !== null && sort.key === column.key ? sort.dir : null;
      const isFiltered = (filters[column.key] ?? []).length > 0;
      const isPinned = position === pinned - 1;
      return h({
        tag: "th",
        attrs: {
          scope: "col",
          class: [column.num ? "num" : "", position < pinned ? "pinned" : ""].join(" ").trim(),
          "data-col": position,
          "data-pri": column.priority ?? 1,
          "aria-sort":
            direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none",
          style: column.minWidth === undefined ? null : `min-width:${column.minWidth}`,
        },
        children: [
          h({
            tag: "div",
            attrs: { class: "th-in" },
            children: [
              h({
                tag: "button",
                attrs: {
                  class: "th-sort",
                  type: "button",
                  "data-sort": column.key,
                  onclick: () => {
                    remember();
                    on.sort(column.key);
                  },
                },
                children: [column.label, sortIcon(direction)],
              }),
              column.filterable === true
                ? h({
                  tag: "button",
                  attrs: {
                    class: "th-tool",
                    type: "button",
                    "data-popover": `filter:${column.key}`,
                    "aria-pressed": String(isFiltered),
                    "aria-label": `${column.label}で絞り込み`,
                    onclick: () => openPopover({ type: "filter", key: column.key }),
                  },
                  children: [icon("filter")],
                })
                : null,
              h({
                tag: "button",
                attrs: {
                  class: "th-tool pin",
                  type: "button",
                  "data-pin": column.key,
                  "aria-pressed": String(isPinned),
                  "aria-label": `${column.label}まで固定`,
                  onclick: () => {
                    remember();
                    on.pin(column.key);
                  },
                },
                children: [icon("pin")],
              }),
            ],
          }),
        ],
      });
    });

    // ===== 行 =====
    /** セルの中身 */
    const cellContent = (column: Column, row: Row): Node | string => {
      const content =
        column.cell?.(row) ?? valuesOf(column, row).join(column.num === true ? "" : "、");
      if (column.fixed !== true) return content;
      // タイトルの列は、押すと詳細を開くボタンにする
      return h({
        tag: "button",
        attrs: { class: "row-open", type: "button", "data-id": row.id, onclick: () => on.open(row.id) },
        children: [content],
      });
    };
    const body =
      shownRows.length > 0
        ? shownRows.map((row) =>
            h({
              tag: "tr",
              attrs: { "data-id": row.id, class: row.id === currentSelection() ? "selected" : "" },
              children: [
                ...visible.map((column, position) =>
                  h({
                    tag: "td",
                    attrs: {
                      "data-col": position,
                      "data-pri": column.priority ?? 1,
                      class: [
                        column.num ? "num" : "",
                        column.nowrap ? "nowrap" : "",
                        position < pinned ? "pinned" : "",
                      ]
                        .join(" ")
                        .trim(),
                    },
                    children: [cellContent(column, row)],
                  }),
                ),
              ],
            }),
          )
        : [
            h({
              tag: "tr",
              children: [
                h({
                  tag: "td",
                  attrs: { colspan: visible.length, class: "no-match-cell" },
                  children: [
                    h({
                      tag: "div",
                      attrs: { class: "no-match" },
                      children: [`該当する${KIND_LABEL[kind]}はありません。別の条件を試してください。`],
                    }),
                  ],
                }),
              ],
            }),
          ];
    wrap.append(
      h({
        tag: "table",
        attrs: { class: "grid" },
        children: [
          h({ tag: "thead", children: [h({ tag: "tr", children: [...headers] })] }),
          h({ tag: "tbody", children: [...body] }),
        ],
      }),
    );
    root.append(wrap, pop);

    // ===== 配置: 固定した列の左端の位置・該当なしの文言の幅・控えたスクロールの位置 =====
    let saved = pendingScroll.get(kind);
    pendingScroll.delete(kind);
    new ResizeObserver(() => {
      wrap.style.setProperty("--wrap-w", `${wrap.clientWidth}px`);
      let left = 0;
      headers.forEach((header, position) => {
        if (position >= pinned) return;
        for (const cell of wrap.querySelectorAll<HTMLElement>(`[data-col="${position}"]`)) {
          cell.style.left = `${left}px`;
          cell.classList.toggle("pin-edge", position === pinned - 1);
        }
        left += header.getBoundingClientRect().width;
      });
      // 控えたスクロールの位置は、描いた後の最初の 1 回だけ戻す
      if (saved !== undefined) {
        wrap.scrollLeft = saved.left;
        wrap.scrollTop = saved.top;
        saved = undefined;
      }
    }).observe(wrap);

    // 開いたままにするポップオーバーを、表が文書に入った後に開く
    if (popover !== null) queueMicrotask(() => showPopover(popover));
    return root;
  }

  // ───── 画面が共通で使う列 ─────

  /** 行から文字の値を取る */
  function text(row: Row, key: string): string | undefined {
    const value = row[key];
    return typeof value === "string" ? value : undefined;
  }

  /** 行から文字の配列を取る */
  function texts(row: Row, key: string): string[] {
    const value = row[key];
    return Array.isArray(value) ? value.map(String) : [];
  }

  /** 項目の ID を並べたセル（押すと詳細を開く）。無ければ「—」 */
  export function idLinksCell(ids: string[], open: (id: string) => void): Node {
    if (ids.length === 0) return h({ tag: "span", attrs: { class: "muted" }, children: ["—"] });
    const fragment = document.createDocumentFragment();
    for (const id of ids) {
      fragment.append(h({
        tag: "button",
        attrs: { class: "idlink", type: "button", onclick: () => open(id) },
        children: [id],
      }));
    }
    return fragment;
  }

  /** どの表にもある列（ID・タイトル・状態・対象・カテゴリー・フェーズ・タグ）を作る関数の集まり */
  export function commonColumns(settings: Settings): {
    id: Column;
    title: (label?: string) => Column;
    status: (order: readonly string[]) => Column;
    target: Column;
    category: Column;
    phase: Column;
    tags: Column;
    text: (key: string, label: string, options?: Partial<Column>) => Column;
  } {
    return {
      id: {
        key: "id",
        label: "ID",
        nowrap: true,
        get: (row) => row.id,
        cell: (row) => h({ tag: "span", attrs: { class: "mono" }, children: [row.id] }),
      },
      title: (label = "タイトル") => ({
        key: "title",
        label,
        fixed: true,
        minWidth: "16em",
        get: (row) => text(row, "title"),
      }),
      status: (order) => ({
        key: "status",
        label: "状態",
        nowrap: true,
        filterable: true,
        order,
        get: (row) => text(row, "status"),
        cell: (row) => statusBadge(text(row, "status")),
      }),
      target: {
        key: "target",
        label: settings.target_label,
        nowrap: true,
        filterable: true,
        priority: 4,
        get: (row) => text(row, "target"),
      },
      category: {
        key: "category",
        label: "カテゴリー",
        nowrap: true,
        filterable: true,
        priority: 2,
        get: (row) => text(row, "category"),
      },
      phase: {
        key: "phase",
        label: "フェーズ",
        nowrap: true,
        filterable: true,
        order: settings.phases,
        priority: 2,
        get: (row) => text(row, "phase"),
      },
      tags: {
        key: "tags",
        label: "タグ",
        filterable: true,
        priority: 4,
        get: (row) => texts(row, "tags"),
        cell: (row) => tagList(texts(row, "tags")),
      },
      text: (key, label, options = {}) => ({
        key,
        label,
        priority: 3,
        get: (row) => text(row, key),
        ...options,
      }),
    };
  }

  /** 行から文字の配列を取る（画面の列の定義で使う） */
  export function rowTexts(row: Row, key: string): string[] {
    return texts(row, key);
  }

  // ───── 画面が使う、状態を持った表 ─────

  /** 端末に残す、表ごとの表示する列とピン留め */
  export type TablePrefs = { hidden: string[]; pinTo: string | null };

  /** 表の状態（並べ替え・絞り込み・ポップオーバーは開いている間だけ、表示する列とピン留めは端末に残す） */
  type TableState = {
    sort: SortState;
    filters: Filters;
    popover: TablePopover | null;
    hidden: string[] | undefined;
    pinTo: string | null;
  };

  /** 種類ごとの表の状態 */
  const tableStates = new Map<Kind, TableState>();

  /** 表示する列とピン留めを変えたときの知らせ先（null は初期設定に戻したとき） */
  let prefsListener: ((kind: Kind, prefs: TablePrefs | null) => void) | null = null;

  /** 端末に残した表示する列とピン留めを入れ、変わったときの知らせ先を決める */
  export function restoreTablePrefs(
    saved: Record<string, TablePrefs>,
    listener: (kind: Kind, prefs: TablePrefs | null) => void,
  ): void {
    prefsListener = listener;
    for (const [kind, prefs] of Object.entries(saved)) {
      const state = tableState(kind as Kind);
      state.hidden = prefs.hidden;
      state.pinTo = prefs.pinTo;
    }
  }

  /** 種類の表の状態（無ければ作る） */
  export function tableState(kind: Kind): TableState {
    let state = tableStates.get(kind);
    if (state === undefined) {
      state = { sort: null, filters: {}, popover: null, hidden: undefined, pinTo: null };
      tableStates.set(kind, state);
    }
    return state;
  }

  /** 状態を持つ表を返す。操作に応じて自分で描き直し、表示する列とピン留めは端末に残す */
  export function managedTable({
    kind,
    columns,
    rows,
    open,
    initialFilters,
  }: {
    kind: Kind;
    columns: Column[];
    rows: Row[];
    open: (id: string) => void;
    /** 開いたときの絞り込み（ハッシュの `f.{列}`）。あれば今の絞り込みと置き換える */
    initialFilters?: Filters;
  }): HTMLElement {
    const state = tableState(kind);
    // 画面を描き直したときは、前のポップオーバーを開いたままにしない
    state.popover = null;
    if (initialFilters !== undefined && Object.keys(initialFilters).length > 0) {
      state.filters = { ...initialFilters };
    }
    const slot = h({ tag: "div", attrs: { class: "table-slot" } });
    /** 端末に残す値が変わったことを知らせる */
    const persist = (): void => {
      prefsListener?.(kind, { hidden: state.hidden ?? [], pinTo: state.pinTo });
    };
    const render = (): void => {
      slot.replaceChildren(
        table({
          kind,
          columns,
          rows,
          sort: state.sort,
          filters: state.filters,
          pinTo: state.pinTo,
          hiddenColumns: state.hidden,
          popover: state.popover,
          on: {
            sort: (key) => {
              // 昇順 → 降順 → 解除
              if (state.sort === null || state.sort.key !== key) state.sort = { key, dir: "asc" };
              else state.sort = state.sort.dir === "asc" ? { key, dir: "desc" } : null;
              render();
            },
            filter: ({ key, values }) => {
              if (key === null) state.filters = {};
              else if (values.length === 0) delete state.filters[key];
              else state.filters = { ...state.filters, [key]: values };
              render();
            },
            pin: (key) => {
              state.pinTo = state.pinTo === key ? null : key;
              persist();
              render();
            },
            columns: (hidden) => {
              state.hidden = hidden;
              persist();
              render();
            },
            reset: () => {
              state.sort = null;
              state.hidden = undefined;
              state.pinTo = null;
              state.popover = null;
              prefsListener?.(kind, null);
              render();
            },
            open,
            popover: (popover) => {
              state.popover = popover;
            },
          },
        }),
      );
    };
    render();
    return slot;
  }
}

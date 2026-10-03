// タスク。ボード（既定）と表で見る。

namespace MindmapPreview {
  /** 画面が受ける、表示形式の切り替えと項目を開く操作 */
  export type ScreenProps = {
    index: RecordIndex;
    /** 表示形式と絞り込み */
    route: Route;
    on: {
      /** 項目を詳細パネルで開く */
      open: (id: string) => void;
      /** 表示形式を切り替える */
      view: (view: View) => void;
    };
  };

  /** 状態の並びの順に、状態ごとの項目を返す（項目が 0 件の列も返す。列の中は連番の順） */
  export function boardColumns({
    items,
    statuses,
  }: {
    items: Item[];
    statuses: string[];
  }): { status: string; items: Item[] }[] {
    return statuses.map((status) => ({
      status,
      items: items
        .filter((item) => item.status === status)
        .sort((a, b) => compareIds(a.id, b.id)),
    }));
  }

  /** ボードのカード（押すと詳細を開く）。`links` が項目を指す ID の並びなら、その題を添える */
  export function boardCard({
    index,
    item,
    meta,
    links,
    open,
  }: {
    index: RecordIndex;
    item: Item;
    meta: (string | undefined)[];
    links: string[];
    open: (id: string) => void;
  }): HTMLElement {
    return h(
      "button",
      {
        class: item.id === currentSelection() ? "card selected" : "card",
        type: "button",
        "data-id": item.id,
        onclick: () => open(item.id),
      },
      h("div", { class: "c-ttl" }, item.title),
      h(
        "div",
        { class: "c-meta" },
        h("span", { class: "mono" }, item.id),
        ...meta.filter(Boolean).map((value) => h("span", null, value)),
      ),
      links.length > 0
        ? h(
            "div",
            { class: "c-for" },
            ...links.map((id) =>
              h("div", null, h("span", { class: "mono" }, id), ` ${titleOf(index, id)}`),
            ),
          )
        : null,
    );
  }

  /** 状態ごとの列にカードを並べたボード。横に送れ、背景のドラッグで動かせる */
  export function board({
    columns,
    card,
  }: {
    columns: { status: string; items: Item[] }[];
    card: (item: Item) => HTMLElement;
  }): HTMLElement {
    const element = h(
      "div",
      { class: "board", style: `--cols:${columns.length}` },
      ...columns.map(({ status, items }) =>
        h(
          "section",
          { class: "board-col", "aria-label": status },
          h("h3", null, statusMark(status), status, h("span", { class: "n" }, items.length)),
          ...(items.length > 0 ? items.map(card) : [emptyNote("なし")]),
        ),
      ),
    );
    enableDragScroll(element);
    return element;
  }

  /** 表示形式の切り替えを置いた道具の行 */
  export function toolbar(views: { key: View; label: string }[], route: Route, onView: (view: View) => void): HTMLElement {
    return h("div", { class: "toolbar" }, viewSwitch({ views, current: route.view, onChange: onView }));
  }

  /** タスクの画面を返す */
  export function tasksScreen({ index, route, on }: ScreenProps): HTMLElement {
    const common = commonColumns(index.data.settings);
    const columns: Column[] = [
      common.id,
      common.title(),
      common.status(TASK_STATUSES),
      common.text("kind", "種類", { filterable: true, nowrap: true, priority: 2 }),
      {
        key: "for",
        label: "進める検討事項",
        priority: 3,
        get: (row) => rowTexts(row, "for"),
        cell: (row) => idLinksCell(rowTexts(row, "for"), on.open),
      },
      common.target,
      common.category,
      common.phase,
      common.tags,
    ];
    const content =
      route.view === "board"
        ? board({
            columns: boardColumns({ items: index.data.tasks, statuses: [...TASK_STATUSES] }),
            card: (item) =>
              boardCard({
                index,
                item,
                meta: [item.kind, item.category],
                links: item.for ?? [],
                open: on.open,
              }),
          })
        : managedTable({
            kind: "tasks",
            columns,
            rows: index.data.tasks,
            open: on.open,
            initialFilters: route.filters,
          });
    return h(
      "div",
      { class: "screen tasks" },
      toolbar(
        [
          { key: "board", label: "ボード" },
          { key: "table", label: "表" },
        ],
        route,
        on.view,
      ),
      content,
    );
  }
}

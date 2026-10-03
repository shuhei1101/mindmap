// 調査・用語集・メモ・会話ログ。種類ごとの列を持つ表だけを出す。

namespace MindmapPreview {
  /** 表だけを持つ画面の種類 */
  type RecordKind = "research" | "terms" | "notes" | "logs";

  /** 調査・用語集・メモ・会話ログの画面を返す。種類は `route.tab` で決まる */
  export function recordsScreen({
    index,
    route,
    on,
  }: {
    index: RecordIndex;
    route: Route;
    on: { open: (id: string) => void };
  }): HTMLElement {
    const kind = route.tab as RecordKind;
    const common = commonColumns(index.data.settings);
    const related = (label: string): Column => ({
      key: "related",
      label,
      priority: 3,
      get: (row) => rowTexts(row, "related"),
      cell: (row) => idLinksCell(rowTexts(row, "related"), on.open),
    });
    const columnsOf: Record<RecordKind, Column[]> = {
      research: [
        common.id,
        common.title(),
        common.text("question", "問い", { minWidth: "16em" }),
        common.text("conclusion", "結論", { minWidth: "18em" }),
        common.text("confidence", "確度", {
          filterable: true,
          nowrap: true,
          priority: 2,
          order: ["高", "中", "低"],
        }),
        common.tags,
      ],
      terms: [
        common.id,
        common.title("用語"),
        common.text("meaning", "意味", { minWidth: "18em", priority: 1 }),
        {
          key: "aliases",
          label: "別名",
          priority: 3,
          get: (row) => rowTexts(row, "aliases"),
          cell: (row) => tagList(rowTexts(row, "aliases")),
        },
        {
          key: "avoid",
          label: "使わない表記",
          priority: 3,
          get: (row) => rowTexts(row, "avoid"),
          cell: (row) => tagList(rowTexts(row, "avoid")),
        },
        common.tags,
      ],
      notes: [
        common.id,
        common.title(),
        common.text("content", "内容", { minWidth: "18em", priority: 2 }),
        common.tags,
        related("関連"),
      ],
      logs: [
        common.id,
        common.text("date", "日付", { nowrap: true, priority: 2 }),
        common.title(),
        related("更新した項目"),
      ],
    };
    return h({
      tag: "div",
      attrs: { class: "screen records" },
      children: [
        managedTable({
          kind,
          columns: columnsOf[kind],
          rows: index.data[kind],
          open: on.open,
          initialFilters: route.filters,
        }),
      ],
    });
  }
}

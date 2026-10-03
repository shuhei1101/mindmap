"use strict";
// 調査・用語集・メモ・会話ログ。種類ごとの列を持つ表だけを出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 調査・用語集・メモ・会話ログの画面を返す。種類は `route.tab` で決まる */
    function recordsScreen({ index, route, on, }) {
        const kind = route.tab;
        const common = MindmapPreview.commonColumns(index.data.settings);
        const related = (label) => ({
            key: "related",
            label,
            priority: 3,
            get: (row) => MindmapPreview.rowTexts(row, "related"),
            cell: (row) => MindmapPreview.idLinksCell(MindmapPreview.rowTexts(row, "related"), on.open),
        });
        const columnsOf = {
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
                    get: (row) => MindmapPreview.rowTexts(row, "aliases"),
                    cell: (row) => MindmapPreview.tagList(MindmapPreview.rowTexts(row, "aliases")),
                },
                {
                    key: "avoid",
                    label: "使わない表記",
                    priority: 3,
                    get: (row) => MindmapPreview.rowTexts(row, "avoid"),
                    cell: (row) => MindmapPreview.tagList(MindmapPreview.rowTexts(row, "avoid")),
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
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "screen records" },
            children: [
                MindmapPreview.managedTable({
                    kind,
                    columns: columnsOf[kind],
                    rows: index.data[kind],
                    open: on.open,
                    initialFilters: route.filters,
                }),
            ],
        });
    }
    MindmapPreview.recordsScreen = recordsScreen;
})(MindmapPreview || (MindmapPreview = {}));

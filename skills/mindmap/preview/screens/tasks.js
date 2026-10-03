"use strict";
// タスク。ボード（既定）と表で見る。
var MindmapPreview;
(function (MindmapPreview) {
    /** 状態の並びの順に、状態ごとの項目を返す（項目が 0 件の列も返す。列の中は連番の順） */
    function boardColumns({ items, statuses, }) {
        return statuses.map((status) => ({
            status,
            items: items
                .filter((item) => item.status === status)
                .sort((a, b) => MindmapPreview.compareIds(a.id, b.id)),
        }));
    }
    MindmapPreview.boardColumns = boardColumns;
    /** ボードのカード（押すと詳細を開く）。`links` が項目を指す ID の並びなら、その題を添える */
    function boardCard({ index, item, meta, links, open, }) {
        return MindmapPreview.h("button", {
            class: item.id === MindmapPreview.currentSelection() ? "card selected" : "card",
            type: "button",
            "data-id": item.id,
            onclick: () => open(item.id),
        }, MindmapPreview.h("div", { class: "c-ttl" }, item.title), MindmapPreview.h("div", { class: "c-meta" }, MindmapPreview.h("span", { class: "mono" }, item.id), ...meta.filter(Boolean).map((value) => MindmapPreview.h("span", null, value))), links.length > 0
            ? MindmapPreview.h("div", { class: "c-for" }, ...links.map((id) => MindmapPreview.h("div", null, MindmapPreview.h("span", { class: "mono" }, id), ` ${MindmapPreview.titleOf(index, id)}`)))
            : null);
    }
    MindmapPreview.boardCard = boardCard;
    /** 状態ごとの列にカードを並べたボード。横に送れ、背景のドラッグで動かせる */
    function board({ columns, card, }) {
        const element = MindmapPreview.h("div", { class: "board", style: `--cols:${columns.length}` }, ...columns.map(({ status, items }) => MindmapPreview.h("section", { class: "board-col", "aria-label": status }, MindmapPreview.h("h3", null, MindmapPreview.statusMark(status), status, MindmapPreview.h("span", { class: "n" }, items.length)), ...(items.length > 0 ? items.map(card) : [MindmapPreview.emptyNote("なし")]))));
        MindmapPreview.enableDragScroll(element);
        return element;
    }
    MindmapPreview.board = board;
    /** 表示形式の切り替えを置いた道具の行 */
    function toolbar(views, route, onView) {
        return MindmapPreview.h("div", { class: "toolbar" }, MindmapPreview.viewSwitch({ views, current: route.view, onChange: onView }));
    }
    MindmapPreview.toolbar = toolbar;
    /** タスクの画面を返す */
    function tasksScreen({ index, route, on }) {
        const common = MindmapPreview.commonColumns(index.data.settings);
        const columns = [
            common.id,
            common.title(),
            common.status(MindmapPreview.TASK_STATUSES),
            common.text("kind", "種類", { filterable: true, nowrap: true, priority: 2 }),
            {
                key: "for",
                label: "進める検討事項",
                priority: 3,
                get: (row) => MindmapPreview.rowTexts(row, "for"),
                cell: (row) => MindmapPreview.idLinksCell(MindmapPreview.rowTexts(row, "for"), on.open),
            },
            common.target,
            common.category,
            common.phase,
            common.tags,
        ];
        const content = route.view === "board"
            ? board({
                columns: boardColumns({ items: index.data.tasks, statuses: [...MindmapPreview.TASK_STATUSES] }),
                card: (item) => boardCard({
                    index,
                    item,
                    meta: [item.kind, item.category],
                    links: item.for ?? [],
                    open: on.open,
                }),
            })
            : MindmapPreview.managedTable({
                kind: "tasks",
                columns,
                rows: index.data.tasks,
                open: on.open,
                initialFilters: route.filters,
            });
        return MindmapPreview.h("div", { class: "screen tasks" }, toolbar([
            { key: "board", label: "ボード" },
            { key: "table", label: "表" },
        ], route, on.view), content);
    }
    MindmapPreview.tasksScreen = tasksScreen;
})(MindmapPreview || (MindmapPreview = {}));

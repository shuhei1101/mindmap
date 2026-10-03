"use strict";
// 資料。カード（既定）と表で見る。成果物を先頭に印付きで並べ、資料の状態を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 成果物を先頭に、それぞれ連番の順に並べた資料を返す */
    function orderDocs(docs) {
        return [...docs].sort((a, b) => Number(b.deliverable === true) - Number(a.deliverable === true) || MindmapPreview.compareIds(a.id, b.id));
    }
    MindmapPreview.orderDocs = orderDocs;
    /** 成果物の列の値 */
    const DELIVERABLE_VALUES = ["成果物", "成果物以外"];
    /** 資料の画面を返す */
    function docsScreen({ index, route, on }) {
        const common = MindmapPreview.commonColumns(index.data.settings);
        const columns = [
            common.id,
            common.title(),
            {
                key: "deliverable",
                label: "成果物",
                nowrap: true,
                filterable: true,
                order: DELIVERABLE_VALUES,
                priority: 2,
                get: (row) => (row["deliverable"] === true ? "成果物" : "成果物以外"),
                cell: (row) => row["deliverable"] === true ? MindmapPreview.deliverableBadge() : MindmapPreview.h("span", { class: "muted" }, "—"),
            },
            common.status(MindmapPreview.DOC_STATUSES),
            common.text("kind", "種類", { filterable: true, nowrap: true, priority: 2 }),
            common.target,
            common.category,
            common.phase,
            common.tags,
        ];
        const toolbarElement = MindmapPreview.toolbar([
            { key: "cards", label: "カード" },
            { key: "table", label: "表" },
        ], route, on.view);
        if (route.view === "table") {
            return MindmapPreview.h("div", { class: "screen docs" }, toolbarElement, MindmapPreview.managedTable({
                kind: "docs",
                columns,
                rows: index.data.docs,
                open: on.open,
                initialFilters: route.filters,
            }));
        }
        // ===== カード: 絞り込みは表と同じ条件を使う =====
        const state = MindmapPreview.tableState("docs");
        if (Object.keys(route.filters).length > 0)
            state.filters = { ...route.filters };
        const ordered = orderDocs(index.data.docs);
        const grid = MindmapPreview.h("div", { class: "doc-grid" });
        const chips = MindmapPreview.h("div", { class: "chips" });
        const pop = MindmapPreview.h("div", { class: "pop", popover: "auto" });
        const filterButton = MindmapPreview.h("button", {
            class: "btn",
            type: "button",
            "aria-label": "絞り込み",
            onclick: () => {
                fillPopover();
                pop.showPopover();
                MindmapPreview.positionPopover(pop, filterButton);
            },
        }, MindmapPreview.icon("filter"), MindmapPreview.h("span", { class: "lbl" }, "絞り込み"));
        /** 絞り込める列の値を、列ごとに件数つきで並べる */
        const fillPopover = () => {
            pop.replaceChildren(...columns
                .filter((column) => column.filterable === true)
                .map((column) => MindmapPreview.h("div", null, MindmapPreview.h("h3", null, `${column.label}で絞り込み`), ...MindmapPreview.filterCounts({
                rows: ordered,
                columns,
                filters: state.filters,
                key: column.key,
            }).map(({ value, count }) => MindmapPreview.h("label", null, MindmapPreview.h("input", {
                type: "checkbox",
                checked: (state.filters[column.key] ?? []).includes(value),
                onchange: (event) => {
                    const chosen = state.filters[column.key] ?? [];
                    const checked = event.target.checked;
                    const values = checked ? [...chosen, value] : chosen.filter((v) => v !== value);
                    if (values.length === 0)
                        delete state.filters[column.key];
                    else
                        state.filters = { ...state.filters, [column.key]: values };
                    render();
                    fillPopover();
                },
            }), column.key === "status" ? MindmapPreview.statusMark(value) : null, value, MindmapPreview.h("span", { class: "n" }, count))))));
        };
        /** カードと条件のチップを、今の絞り込みで描く */
        const render = () => {
            const shown = MindmapPreview.filterRows({ rows: ordered, columns, filters: state.filters });
            grid.replaceChildren(...(shown.length > 0
                ? shown.map((row) => docCard(index, row, on.open))
                : [MindmapPreview.h("p", { class: "no-match" }, "該当する資料はありません。別の条件を試してください。")]));
            const items = [];
            for (const [key, values] of Object.entries(state.filters)) {
                const label = columns.find((column) => column.key === key)?.label ?? key;
                for (const value of values) {
                    items.push(MindmapPreview.h("span", { class: "chip" }, `${label}: ${value}`, MindmapPreview.h("button", {
                        type: "button",
                        "aria-label": `${label}: ${value} の条件を外す`,
                        onclick: () => {
                            const rest = values.filter((v) => v !== value);
                            if (rest.length === 0)
                                delete state.filters[key];
                            else
                                state.filters = { ...state.filters, [key]: rest };
                            render();
                        },
                    }, MindmapPreview.icon("x"))));
                }
            }
            if (items.length > 0) {
                items.push(MindmapPreview.h("button", {
                    class: "btn ghost",
                    type: "button",
                    onclick: () => {
                        state.filters = {};
                        render();
                    },
                }, "すべて外す"));
            }
            chips.replaceChildren(...items);
        };
        render();
        toolbarElement.append(MindmapPreview.h("span", { class: "spacer" }), filterButton);
        return MindmapPreview.h("div", { class: "screen docs" }, toolbarElement, chips, grid, pop);
    }
    MindmapPreview.docsScreen = docsScreen;
    /** 資料のカード（成果物の印・種類・状態・カテゴリー・フェーズ・タグ） */
    function docCard(index, doc, open) {
        return MindmapPreview.h("button", {
            class: `card doc-card${doc.deliverable === true ? " deliv-card" : ""}`,
            type: "button",
            "data-id": doc.id,
            onclick: () => open(doc.id),
        }, doc.deliverable === true ? MindmapPreview.deliverableBadge() : null, MindmapPreview.h("span", { class: "doc-kind" }, MindmapPreview.icon(doc.kind === "図" ? "graph" : "cards"), doc.kind ?? ""), MindmapPreview.h("span", { class: "c-ttl" }, doc.title), MindmapPreview.h("span", { class: "c-meta" }, MindmapPreview.h("span", { class: "mono" }, doc.id), MindmapPreview.statusBadge(doc.status), MindmapPreview.h("span", null, [doc.category, doc.phase].filter(Boolean).join(" · "))), (doc.tags ?? []).length > 0 ? MindmapPreview.h("span", { class: "c-tags" }, MindmapPreview.tagList(doc.tags)) : null);
    }
})(MindmapPreview || (MindmapPreview = {}));

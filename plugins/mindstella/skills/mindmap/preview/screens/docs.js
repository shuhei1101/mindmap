"use strict";
// 資料。カード（既定）・ボード・表で見る。納品物を先頭に印付きで並べ、資料の状態を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 納品物を先頭に、それぞれ連番の順に並べた資料を返す */
    function orderDocs(docs) {
        return [...docs].sort((a, b) => Number(b.deliverable === true) - Number(a.deliverable === true) || MindmapPreview.compareIds(a.id, b.id));
    }
    MindmapPreview.orderDocs = orderDocs;
    /** 納品物の列の値 */
    const DELIVERABLE_VALUES = ["納品物", "納品物以外"];
    /** 資料の画面を返す */
    function docsScreen({ index, route, on }) {
        const common = MindmapPreview.commonColumns(index.data.settings);
        const columns = [
            common.id,
            common.title(),
            {
                key: "deliverable",
                label: "納品物",
                nowrap: true,
                filterable: true,
                order: DELIVERABLE_VALUES,
                priority: 2,
                get: (row) => (row["deliverable"] === true ? "納品物" : "納品物以外"),
                cell: (row) => row["deliverable"] === true ? MindmapPreview.deliverableBadge() : MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["—"] }),
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
            { key: "board", label: "ボード" },
            { key: "table", label: "表" },
        ], route, on.view);
        if (route.view === "table") {
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "screen docs" },
                children: [
                    toolbarElement,
                    MindmapPreview.managedTable({
                        kind: "docs",
                        columns,
                        rows: index.data.docs,
                        open: on.open,
                        initialFilters: route.filters,
                    }),
                ],
            });
        }
        // ===== カードとボード: 絞り込みは表と同じ条件を使う =====
        const state = MindmapPreview.tableState("docs");
        if (Object.keys(route.filters).length > 0)
            state.filters = { ...route.filters };
        const ordered = orderDocs(index.data.docs);
        const chips = MindmapPreview.h({ tag: "div", attrs: { class: "chips" } });
        const pop = MindmapPreview.h({ tag: "div", attrs: { class: "pop", popover: "auto" } });
        const filterButton = MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "btn",
                type: "button",
                "aria-label": "絞り込み",
                onclick: () => {
                    fillPopover();
                    pop.showPopover();
                    MindmapPreview.positionPopover(pop, filterButton);
                },
            },
            children: [
                MindmapPreview.icon("filter"),
                MindmapPreview.h({ tag: "span", attrs: { class: "lbl" }, children: ["絞り込み"] }),
            ],
        });
        /** 絞り込める列の値を、列ごとに件数つきで並べる */
        const fillPopover = () => {
            pop.replaceChildren(...columns
                .filter((column) => column.filterable === true)
                .map((column) => MindmapPreview.h({
                tag: "div",
                children: [
                    MindmapPreview.h({ tag: "h3", children: [`${column.label}で絞り込み`] }),
                    ...MindmapPreview.filterCounts({
                        rows: ordered,
                        columns,
                        filters: state.filters,
                        key: column.key,
                    }).map(({ value, count }) => MindmapPreview.h({
                        tag: "label",
                        children: [
                            MindmapPreview.h({
                                tag: "input",
                                attrs: {
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
                                },
                            }),
                            column.key === "status" ? MindmapPreview.statusMark(value) : null,
                            value,
                            MindmapPreview.h({ tag: "span", attrs: { class: "n" }, children: [count] }),
                        ],
                    })),
                ],
            })));
        };
        /** カードの並びかボードを、今の絞り込みで描く */
        const drawContent = () => {
            const shown = MindmapPreview.filterRows({ rows: ordered, columns, filters: state.filters });
            if (route.view === "board") {
                // 列ごとに納品物を先頭に並べ直す
                return MindmapPreview.board({
                    columns: MindmapPreview.boardColumns({ items: shown, statuses: [...MindmapPreview.DOC_STATUSES] }).map((column) => ({
                        status: column.status,
                        items: orderDocs(column.items),
                    })),
                    card: (item) => docCard({ index, doc: item, open: on.open, inBoard: true }),
                    emptyText: "資料はありません。",
                });
            }
            return MindmapPreview.h({
                tag: "div",
                attrs: { class: "doc-grid" },
                children: shown.length > 0
                    ? shown.map((row) => docCard({ index, doc: row, open: on.open, inBoard: false }))
                    : [MindmapPreview.h({ tag: "p", attrs: { class: "no-match" }, children: ["該当する資料はありません。別の条件を試してください。"] })],
            });
        };
        let content = drawContent();
        /** カードの並びかボードと条件のチップを、今の絞り込みで描き直す */
        const render = () => {
            const next = drawContent();
            content.replaceWith(next);
            content = next;
            drawChips();
        };
        /** 条件のチップを、今の絞り込みで描く */
        const drawChips = () => {
            const items = [];
            for (const [key, values] of Object.entries(state.filters)) {
                const label = columns.find((column) => column.key === key)?.label ?? key;
                for (const value of values) {
                    items.push(MindmapPreview.h({
                        tag: "span",
                        attrs: { class: "chip" },
                        children: [
                            `${label}: ${value}`,
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    type: "button",
                                    "aria-label": `${label}: ${value} の条件を解除`,
                                    onclick: () => {
                                        const rest = values.filter((v) => v !== value);
                                        if (rest.length === 0)
                                            delete state.filters[key];
                                        else
                                            state.filters = { ...state.filters, [key]: rest };
                                        render();
                                    },
                                },
                                children: [MindmapPreview.icon("x")],
                            }),
                        ],
                    }));
                }
            }
            if (items.length > 0) {
                items.push(MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "btn ghost",
                        type: "button",
                        onclick: () => {
                            state.filters = {};
                            render();
                        },
                    },
                    children: ["すべて解除"],
                }));
            }
            chips.replaceChildren(...items);
        };
        drawChips();
        toolbarElement.append(MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }), filterButton);
        return MindmapPreview.h({ tag: "div", attrs: { class: "screen docs" }, children: [toolbarElement, chips, content, pop] });
    }
    MindmapPreview.docsScreen = docsScreen;
    /** 資料のカード（納品物の印・種類・状態・カテゴリー・フェーズ・タグ）。ボードの中では列で状態が分かるので状態の印を出さず、開いている資料に選択の印を付ける */
    function docCard({ index, doc, open, inBoard, }) {
        return MindmapPreview.h({
            tag: "button",
            attrs: {
                class: `card doc-card${doc.deliverable === true ? " deliv-card" : ""}${inBoard && doc.id === MindmapPreview.currentSelection() ? " selected" : ""}`,
                type: "button",
                "data-id": doc.id,
                onclick: () => open(doc.id),
            },
            children: [
                doc.deliverable === true ? MindmapPreview.deliverableBadge() : null,
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "doc-kind" },
                    children: [MindmapPreview.icon(doc.kind === "図" ? "graph" : "cards"), doc.kind ?? ""],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "c-ttl" }, children: [doc.title] }),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "c-meta" },
                    children: [
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [doc.id] }),
                        inBoard ? null : MindmapPreview.statusBadge(doc.status),
                        MindmapPreview.h({ tag: "span", children: [[doc.category, doc.phase].filter(Boolean).join(" · ")] }),
                    ],
                }),
                (doc.tags ?? []).length > 0 ? MindmapPreview.h({ tag: "span", attrs: { class: "c-tags" }, children: [MindmapPreview.tagList(doc.tags)] }) : null,
            ],
        });
    }
})(MindmapPreview || (MindmapPreview = {}));

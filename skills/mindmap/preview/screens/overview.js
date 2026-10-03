"use strict";
// 概要。次に検討する項目・ゴールまで・要見直し・保留・進行中のタスク・カテゴリー別の進み具合のタイルを並べる。
var MindmapPreview;
(function (MindmapPreview) {
    /** 縦に積む幅で出す、次に検討する項目の件数 */
    const NEXT_STACKED_COUNT = 3;
    /** 成果物のチェックリストに出す件数（これを超えたら資料を成果物で絞って開く） */
    const DELIVERABLE_LIMIT = 5;
    /** 小さなタイルに出す件数 */
    const MINI_LIMIT = 3;
    /** 次に検討する項目をタイルに横に並べる幅 */
    const WIDE_QUERY = "(min-width: 1101px)";
    /** 絞った表へ移る `Route`（画面の既定の表示形式で開く） */
    function tableRoute(tab, filters, view = "table") {
        return { tab, view, id: null, full: false, filters };
    }
    /** 「すべて表示（N 件）」のボタン */
    function showAll(count, onClick) {
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: "t-link", type: "button", onclick: onClick },
            children: [`すべて表示（${count} 件）`],
        });
    }
    /** 見出し（アイコンと名前）と、右端の「すべて表示」 */
    function tileHead(id, iconName, title, link) {
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "t-head" },
            children: [MindmapPreview.h({ tag: "h2", attrs: { id }, children: [MindmapPreview.icon(iconName), title] }), link],
        });
    }
    /** 1 行が項目のボタンの一覧（押すと詳細を開く） */
    function miniList(items, emptyText, open) {
        if (items.length === 0)
            return MindmapPreview.emptyNote(emptyText);
        return MindmapPreview.h({
            tag: "ul",
            attrs: { class: "mini" },
            children: [
                ...items.slice(0, MINI_LIMIT).map((item) => MindmapPreview.h({
                    tag: "li",
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { type: "button", "data-id": item.id, onclick: () => open(item.id) },
                            children: [
                                MindmapPreview.statusMark(item.status),
                                MindmapPreview.h({ tag: "span", attrs: { class: "mt" }, children: [item.title] }),
                                MindmapPreview.h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [MindmapPreview.icon("chev")] }),
                            ],
                        }),
                    ],
                })),
            ],
        });
    }
    /** 決定済みの数の棒（0〜100%） */
    function bar(settled, total) {
        const ratio = total === 0 ? 0 : (settled / total) * 100;
        return MindmapPreview.h({ tag: "i", children: [MindmapPreview.h({ tag: "b", attrs: { style: `width:${ratio}%` } })] });
    }
    /** 次に検討する項目のタイル */
    function nextTile({ index, on }) {
        const candidates = index.data.derived.next;
        const list = MindmapPreview.h({
            tag: "ol",
            attrs: { class: "next-list" },
            children: [
                ...candidates.map((candidate) => {
                    const item = index.byId.get(candidate.id)?.item;
                    return MindmapPreview.h({
                        tag: "li",
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: { type: "button", "data-id": candidate.id, onclick: () => on.open(candidate.id) },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "nl-ttl" }, children: [candidate.title] }),
                                    MindmapPreview.h({
                                        tag: "span",
                                        attrs: { class: "nl-meta" },
                                        children: [
                                            MindmapPreview.h({ tag: "span", children: [[item?.category, candidate.phase].filter(Boolean).join(" · ")] }),
                                            MindmapPreview.impactBadge(candidate.weight ?? undefined),
                                            MindmapPreview.h({
                                                tag: "span",
                                                attrs: { class: "fol", title: "後続の件数" },
                                                children: [MindmapPreview.icon("follow"), candidate.followers],
                                            }),
                                        ],
                                    }),
                                    MindmapPreview.h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [MindmapPreview.icon("chev")] }),
                                ],
                            }),
                        ],
                    });
                }),
            ],
        });
        const tile = MindmapPreview.h({
            tag: "section",
            attrs: { class: "tile t-next", "aria-labelledby": "h-next" },
            children: [
                tileHead("h-next", "next", "次に検討する項目", candidates.length > 0
                    ? showAll(candidates.length, () => on.navigate(tableRoute("decisions", { status: ["未決定"], ready: ["はい"] })))
                    : null),
                candidates.length > 0 ? list : MindmapPreview.emptyNote("次に検討する項目はありません"),
            ],
        });
        // 横に並べる幅ではタイルの枠に収まるだけ、縦に積む幅では上位の数件だけを出す
        const fit = () => {
            const items = [...list.children];
            for (const item of items)
                item.hidden = false;
            if (matchMedia(WIDE_QUERY).matches) {
                const limit = tile.getBoundingClientRect().bottom - Number.parseFloat(getComputedStyle(tile).paddingBottom);
                for (const item of items)
                    if (item.getBoundingClientRect().bottom > limit)
                        item.hidden = true;
            }
            else {
                items.forEach((item, position) => {
                    item.hidden = position >= NEXT_STACKED_COUNT;
                });
            }
        };
        new ResizeObserver(fit).observe(tile);
        return tile;
    }
    /** ゴールまでのタイル（決定済みの数・フェーズごとの棒・成果物のチェックリスト） */
    function goalTile({ index, on }) {
        const { goal } = index.data.derived;
        const settled = goal.phase_progress.reduce((sum, cell) => sum + cell.settled, 0);
        const total = goal.phase_progress.reduce((sum, cell) => sum + cell.total, 0);
        const { deliverables } = index.data.settings.goal;
        const remaining = new Set(goal.remaining_deliverables.map((entry) => entry.title));
        const doneCount = deliverables.filter((entry) => !remaining.has(entry.title)).length;
        const checklist = deliverables.slice(0, DELIVERABLE_LIMIT).map((entry) => {
            const done = !remaining.has(entry.title);
            const label = entry.doc !== undefined && index.byId.has(entry.doc)
                ? MindmapPreview.h({
                    tag: "button",
                    attrs: { type: "button", onclick: () => on.open(entry.doc) },
                    children: [entry.title],
                })
                : MindmapPreview.h({ tag: "span", children: [entry.title] });
            return MindmapPreview.h({
                tag: "li",
                attrs: { class: done ? "done" : "" },
                children: [MindmapPreview.icon(done ? "checked" : "unchecked"), label],
            });
        });
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "tile t-goal", "aria-labelledby": "h-goal" },
            children: [
                MindmapPreview.h({ tag: "h2", attrs: { id: "h-goal" }, children: [MindmapPreview.icon("flag"), "ゴールまで"] }),
                MindmapPreview.h({
                    tag: "p",
                    attrs: { class: "big" },
                    children: [settled, MindmapPreview.h({ tag: "small", children: [` / ${total}`] })],
                }),
                MindmapPreview.h({ tag: "p", attrs: { class: "big-sub" }, children: ["決定済み"] }),
                MindmapPreview.h({
                    tag: "ul",
                    attrs: { class: "stage-rows" },
                    children: [
                        ...goal.phase_progress.map((cell) => MindmapPreview.h({
                            tag: "li",
                            children: [
                                MindmapPreview.h({ tag: "span", children: [cell.phase] }),
                                bar(cell.settled, cell.total),
                                MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [`${cell.settled}/${cell.total}`] }),
                            ],
                        })),
                    ],
                }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "deliv" },
                    children: [
                        MindmapPreview.h({
                            tag: "div",
                            attrs: { class: "deliv-head" },
                            children: [
                                MindmapPreview.icon("box"),
                                "成果物",
                                MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [`${doneCount}/${deliverables.length}`] }),
                                deliverables.length > DELIVERABLE_LIMIT
                                    ? showAll(deliverables.length, () => on.navigate(tableRoute("docs", { deliverable: ["成果物"] }, "cards")))
                                    : null,
                            ],
                        }),
                        MindmapPreview.h({ tag: "ul", attrs: { class: "checklist" }, children: [...checklist] }),
                    ],
                }),
            ],
        });
    }
    /** 件数と名前の小さなタイル（要見直し・保留・進行中のタスク） */
    function smallTile({ id, iconName, title, items, link, open, }) {
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "tile t-small", "aria-labelledby": id },
            children: [
                tileHead(id, iconName, title, items.length > 0 ? showAll(items.length, link) : null),
                MindmapPreview.h({ tag: "p", attrs: { class: "num" }, children: [items.length] }),
                miniList(items, "なし", open),
            ],
        });
    }
    /** カテゴリー別の進み具合の表（カテゴリーを行、フェーズを列にする） */
    function progressTile({ index, on }) {
        const { settings, derived } = index.data;
        const rowOf = (entry) => MindmapPreview.h({
            tag: "tr",
            children: [
                MindmapPreview.h({
                    tag: "th",
                    attrs: { scope: "row" },
                    children: [
                        MindmapPreview.h({
                            tag: "button",
                            attrs: {
                                class: "cat-link",
                                type: "button",
                                onclick: () => on.navigate(tableRoute("decisions", { category: [entry.category] })),
                            },
                            children: [entry.category],
                        }),
                    ],
                }),
                ...entry.cells.map((cell) => cell.total === 0
                    ? MindmapPreview.h({ tag: "td", children: [MindmapPreview.h({ tag: "span", attrs: { class: "muted" }, children: ["—"] })] })
                    : MindmapPreview.h({
                        tag: "td",
                        children: [
                            MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "cell",
                                    type: "button",
                                    "aria-label": `${entry.category} の ${cell.phase}: ${cell.settled}/${cell.total} 件決定済み`,
                                    onclick: () => on.navigate(tableRoute("decisions", {
                                        category: [entry.category],
                                        phase: [cell.phase],
                                    })),
                                },
                                children: [
                                    bar(cell.settled, cell.total),
                                    MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [`${cell.settled}/${cell.total}`] }),
                                ],
                            }),
                        ],
                    })),
                MindmapPreview.h({ tag: "td", attrs: { class: "tot mono" }, children: [`${entry.settled}/${entry.total}`] }),
            ],
        });
        // 対象ごとに見出しの行を立て、その対象のカテゴリーを続ける
        const groups = settings.targets.flatMap((target) => {
            const entries = derived.progress.filter((entry) => entry.total > 0 &&
                settings.categories.some((category) => category.name === entry.category && category.target === target.name));
            return entries.length === 0
                ? []
                : [
                    MindmapPreview.h({
                        tag: "tbody",
                        children: [
                            MindmapPreview.h({
                                tag: "tr",
                                attrs: { class: "tgt" },
                                children: [
                                    MindmapPreview.h({
                                        tag: "th",
                                        attrs: { colspan: settings.phases.length + 2, scope: "rowgroup" },
                                        children: [`${settings.target_label}: ${target.name}`],
                                    }),
                                ],
                            }),
                            ...entries.map(rowOf),
                        ],
                    }),
                ];
        });
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "tile t-cat", "aria-labelledby": "h-cat" },
            children: [
                MindmapPreview.h({ tag: "h2", attrs: { id: "h-cat" }, children: [MindmapPreview.icon("layers"), "カテゴリー別の進み具合"] }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "cat-wrap" },
                    children: [
                        MindmapPreview.h({
                            tag: "table",
                            attrs: { class: "cat-table" },
                            children: [
                                MindmapPreview.h({
                                    tag: "thead",
                                    children: [
                                        MindmapPreview.h({
                                            tag: "tr",
                                            children: [
                                                MindmapPreview.h({ tag: "th", attrs: { scope: "col" }, children: ["カテゴリー"] }),
                                                ...settings.phases.map((phase) => MindmapPreview.h({ tag: "th", attrs: { scope: "col" }, children: [phase] })),
                                                MindmapPreview.h({ tag: "th", attrs: { scope: "col", class: "tot" }, children: ["決定済み"] }),
                                            ],
                                        }),
                                    ],
                                }),
                                ...groups,
                            ],
                        }),
                    ],
                }),
            ],
        });
    }
    /** 概要の画面を返す */
    function overviewScreen(props) {
        const { index, on } = props;
        const { settings } = index.data;
        const decisions = index.data.decisions;
        const review = decisions.filter((item) => item.status === "要見直し");
        const hold = decisions.filter((item) => item.status === "保留");
        const running = index.data.tasks.filter((item) => item.status === "進行中");
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "overview" },
            children: [
                MindmapPreview.h({
                    tag: "header",
                    attrs: { class: "hero" },
                    children: [
                        MindmapPreview.h({
                            tag: "p",
                            attrs: { class: "hero-sub" },
                            children: [`${settings.field} · ゴールは${settings.goal.phase}のフェーズまで`],
                        }),
                        MindmapPreview.h({ tag: "h1", children: [settings.summary] }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "bento" },
                    children: [
                        nextTile(props),
                        goalTile(props),
                        smallTile({
                            id: "h-review",
                            iconName: "alert",
                            title: "要見直し",
                            items: review,
                            link: () => on.navigate(tableRoute("decisions", { status: ["要見直し"] })),
                            open: on.open,
                        }),
                        smallTile({
                            id: "h-hold",
                            iconName: "pause",
                            title: "保留",
                            items: hold,
                            link: () => on.navigate(tableRoute("decisions", { status: ["保留"] })),
                            open: on.open,
                        }),
                        smallTile({
                            id: "h-run",
                            iconName: "play",
                            title: "進行中のタスク",
                            items: running,
                            link: () => on.navigate(tableRoute("tasks", { status: ["進行中"] })),
                            open: on.open,
                        }),
                        progressTile(props),
                    ],
                }),
            ],
        });
    }
    MindmapPreview.overviewScreen = overviewScreen;
})(MindmapPreview || (MindmapPreview = {}));

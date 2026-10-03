"use strict";
// 詳細パネルと詳細の全画面。項目 1 件の中身（案・本文・図・関係する項目）を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 項目の ID を、押すと開くボタンにする */
    function idButton(id, open) {
        return MindmapPreview.h({
            tag: "button",
            attrs: { class: "idlink", type: "button", onclick: () => open(id) },
            children: [id],
        });
    }
    /** 項目の ID の並びを、ID・題・状態の一覧にする */
    function itemList(index, ids, open) {
        return MindmapPreview.h({
            tag: "ul",
            attrs: { class: "d-list" },
            children: [
                ...ids.map((id) => MindmapPreview.h({
                    tag: "li",
                    children: [
                        idButton(id, open),
                        MindmapPreview.h({ tag: "span", attrs: { class: "t" }, children: [MindmapPreview.titleOf(index, id)] }),
                        MindmapPreview.statusBadge(index.byId.get(id)?.item.status),
                    ],
                })),
            ],
        });
    }
    /** 見出しの付いた節 */
    function section(label, content) {
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "d-sec" },
            children: [MindmapPreview.h({ tag: "h3", children: [label] }), content],
        });
    }
    /** 検討事項の案をカードの縦並びにする（採用 / 不採用と理由を出す） */
    function optionCards(options) {
        return MindmapPreview.h({
            tag: "div",
            children: [
                ...options.map((option) => {
                    const result = option.adopted === true ? "採用" : option.adopted === false ? "不採用" : "検討中";
                    const rows = [
                        ["メリット", option.pros],
                        ["デメリット", option.cons],
                        ["備考", option.note],
                        ["理由", option.reason],
                    ];
                    const shown = rows.filter((row) => row[1] !== undefined && row[1] !== "");
                    return MindmapPreview.h({
                        tag: "div",
                        attrs: {
                            class: `opt${option.adopted === true ? " adopted" : option.adopted === false ? " rejected" : ""}`,
                        },
                        children: [
                            MindmapPreview.h({
                                tag: "div",
                                attrs: { class: "o-head" },
                                children: [
                                    MindmapPreview.h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                                    option.content,
                                    MindmapPreview.h({ tag: "span", attrs: { class: "res" }, children: [result] }),
                                ],
                            }),
                            shown.length > 0
                                ? MindmapPreview.h({
                                    tag: "dl",
                                    children: [
                                        ...shown.flatMap(([label, value]) => [MindmapPreview.h({ tag: "dt", children: [label] }), MindmapPreview.h({ tag: "dd", children: [value] })]),
                                    ],
                                })
                                : null,
                        ],
                    });
                }),
            ],
        });
    }
    /** 見出しの下の、項目のキー（対象・カテゴリー・フェーズ・影響度・種類・確度・日付・更新日・タグ）の一覧 */
    function metaList(item, settings) {
        const pairs = [
            [settings.target_label, item.target],
            ["カテゴリー", item.category],
            ["フェーズ", item.phase],
            ["影響度", item.weight],
            ["種類", item.kind],
            ["確度", item.confidence],
            ["日付", item.date],
            ["更新日", item.updated],
        ];
        const rows = pairs.flatMap(([label, value]) => value === undefined || value === "" ? [] : [MindmapPreview.h({ tag: "dt", children: [label] }), MindmapPreview.h({ tag: "dd", children: [value] })]);
        if ((item.tags ?? []).length > 0)
            rows.push(MindmapPreview.h({ tag: "dt", children: ["タグ"] }), MindmapPreview.h({ tag: "dd", children: [MindmapPreview.tagList(item.tags)] }));
        return MindmapPreview.h({ tag: "dl", attrs: { class: "d-meta" }, children: [...rows] });
    }
    /** 項目の中身（種類ごと）。本文は Markdown と図を描く */
    function detailBody({ id, index, on }) {
        const entry = index.byId.get(id);
        const body = MindmapPreview.h({ tag: "div", attrs: { class: "detail" } });
        if (entry === undefined)
            return body;
        const { kind, item } = entry;
        const related = MindmapPreview.relatedItems({ id, index });
        const labelled = (label, value) => value === undefined || value === ""
            ? null
            : MindmapPreview.h({
                tag: "div",
                attrs: { class: "d-answer" },
                children: [MindmapPreview.h({ tag: "b", children: [label] }), value],
            });
        /** 本文の節。本文の図を描き、図の道具（拡大・Raw・コピー）を動かす */
        const bodySection = (label) => {
            const source = index.data.bodies[item.body ?? ""];
            if (source === undefined)
                return null;
            const rendered = MindmapPreview.renderMarkdown(source);
            lowerHeadings(rendered);
            void MindmapPreview.renderDiagrams(rendered);
            rendered.addEventListener("click", (event) => {
                const button = event.target.closest("[data-act]");
                const figure = button?.closest(".diagram");
                if (button === null || button === undefined || figure === null || figure === undefined)
                    return;
                const act = button.dataset["act"];
                const original = figure.querySelector(".dg-raw")?.textContent ?? "";
                if (act === "diagram-zoom") {
                    const svgElement = figure.querySelector(".mermaid svg");
                    if (svgElement !== null)
                        on.diagram(svgElement);
                }
                else if (act === "diagram-raw") {
                    // 図と mermaid の原文を切り替える
                    const pressed = button.getAttribute("aria-pressed") !== "true";
                    button.setAttribute("aria-pressed", String(pressed));
                    figure.querySelector(".mermaid").hidden = pressed;
                    figure.querySelector(".dg-raw").hidden = !pressed;
                }
                else if (act === "diagram-copy") {
                    void navigator.clipboard?.writeText(original).then(() => {
                        button.replaceChildren(MindmapPreview.icon("check"));
                        window.setTimeout(() => button.replaceChildren(MindmapPreview.icon("copy")), 1400);
                    });
                }
            });
            return section(label, rendered);
        };
        /** 関係する項目の節（1 件以上あるときだけ） */
        const relation = (label, ids) => ids.length === 0 ? null : section(label, itemList(index, ids, on.open));
        MindmapPreview.append({
            parent: body,
            children: [
                MindmapPreview.statusBadge(item.status),
                MindmapPreview.h({
                    tag: "h2",
                    attrs: { class: "d-title" },
                    children: [item.title, item.deliverable === true ? MindmapPreview.deliverableBadge() : null],
                }),
                metaList(item, index.data.settings),
            ],
        });
        if (kind === "decisions") {
            MindmapPreview.append({
                parent: body,
                children: [
                    item.lead === undefined ? null : MindmapPreview.h({ tag: "p", attrs: { class: "d-lead" }, children: [item.lead] }),
                    labelled("決定内容", item.answer),
                    labelled("理由", item.reason),
                    (item.options ?? []).length > 0 ? section("案", optionCards(item.options ?? [])) : null,
                    bodySection("本文"),
                    relation("前提", related.prerequisites),
                    relation("後続の項目", related.successors),
                    relation("関連タスク", related.tasks),
                    relation("経緯（会話ログ）", related.logs),
                ],
            });
        }
        else if (kind === "tasks") {
            MindmapPreview.append({
                parent: body,
                children: [
                    labelled("理由", item.reason),
                    relation("進める検討事項", item.for ?? []),
                    relation("前提", related.prerequisites),
                    relation("結果", item.result === undefined ? [] : [item.result]),
                ],
            });
        }
        else if (kind === "research") {
            MindmapPreview.append({
                parent: body,
                children: [
                    item.question === undefined ? null : MindmapPreview.h({ tag: "p", attrs: { class: "d-lead" }, children: [item.question] }),
                    labelled("結論", item.conclusion),
                    (item.angles ?? []).length > 0 ? section("調査の観点", MindmapPreview.tagList(item.angles)) : null,
                    bodySection("本文"),
                ],
            });
        }
        else if (kind === "docs") {
            MindmapPreview.append({ parent: body, children: [bodySection("本文")] });
        }
        else if (kind === "terms") {
            MindmapPreview.append({
                parent: body,
                children: [
                    labelled("意味", item.meaning),
                    (item.aliases ?? []).length > 0 ? section("別名", MindmapPreview.tagList(item.aliases)) : null,
                    (item.avoid ?? []).length > 0 ? section("使わない表記", MindmapPreview.tagList(item.avoid)) : null,
                ],
            });
        }
        else if (kind === "notes") {
            MindmapPreview.append({
                parent: body,
                children: [
                    item.content === undefined ? null : MindmapPreview.h({ tag: "p", children: [item.content] }),
                ],
            });
        }
        else {
            MindmapPreview.append({ parent: body, children: [bodySection("要約")] });
        }
        if ((item.links ?? []).length > 0) {
            MindmapPreview.append({
                parent: body,
                children: [
                    section("リンク", MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "d-list" },
                        children: [
                            ...(item.links ?? []).map((link) => MindmapPreview.h({
                                tag: "li",
                                children: [
                                    MindmapPreview.icon("link"),
                                    MindmapPreview.h({
                                        tag: "a",
                                        attrs: { href: link.url, target: "_blank", rel: "noopener" },
                                        children: [link.title],
                                    }),
                                ],
                            })),
                        ],
                    })),
                ],
            });
        }
        MindmapPreview.append({
            parent: body,
            children: [
                relation(kind === "logs" ? "更新した項目" : "関連", related.related),
                relation("この項目を参照している項目", related.referencedBy),
            ],
        });
        return body;
    }
    /** 見出し（前へ・次へ・全画面・閉じる）を作る */
    function detailHead({ id, index, full, on }) {
        const entry = index.byId.get(id);
        const trail = history.state;
        const position = trail?.position ?? 0;
        const length = trail?.items.length ?? 1;
        const arrow = (label, glyph, disabled, handler) => MindmapPreview.h({
            tag: "button",
            attrs: {
                class: "icon-btn",
                type: "button",
                "data-act": glyph === "←" ? "back" : "forward",
                "aria-label": label,
                title: label,
                disabled,
                onclick: handler,
            },
            children: [glyph],
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "panel-head" },
            children: [
                full
                    ? null
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: { class: "icon-btn panel-back", type: "button", "aria-label": "一覧へ戻る", onclick: on.close },
                        children: [MindmapPreview.icon("back")],
                    }),
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "panel-kind" },
                    children: [
                        entry === undefined ? "" : `${MindmapPreview.KIND_LABEL[entry.kind]} `,
                        MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [id] }),
                    ],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                arrow("前に見た項目へ戻る", "←", position <= 0, on.back),
                arrow("次に見た項目へ進む", "→", position >= length - 1, on.forward),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "icon-btn panel-full",
                        type: "button",
                        "data-act": "full",
                        "aria-label": full ? "元の大きさに戻す" : "全画面で表示",
                        title: full ? "元の大きさに戻す" : "全画面で表示",
                        onclick: () => on.full(!full),
                    },
                    children: [MindmapPreview.icon(full ? "shrink" : "expand")],
                }),
                full
                    ? null
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "icon-btn panel-close-x",
                            type: "button",
                            "data-act": "close",
                            "aria-label": "詳細を閉じる",
                            onclick: on.close,
                        },
                        children: [MindmapPreview.icon("x")],
                    }),
            ],
        });
    }
    /** 詳細パネルの節の見出し（h3）の下に、本文の見出し（h1〜h6）を並べるための段の差 */
    const BODY_HEADING_OFFSET = 3;
    /** 見出しの要素の最も下の段（h6） */
    const LOWEST_HEADING_LEVEL = 6;
    /** 本文の見出しを、パネルの節の見出しより下の段（h4〜h6）に下げる。見た目は元の段のまま（`data-md-level`） */
    function lowerHeadings(root) {
        for (const heading of root.querySelectorAll("h1, h2, h3, h4, h5, h6")) {
            const level = Number(heading.tagName.slice(1));
            const lowered = Math.min(level + BODY_HEADING_OFFSET, LOWEST_HEADING_LEVEL);
            const replacement = MindmapPreview.h({
                tag: `h${lowered}`,
                attrs: {
                    "data-md-level": level,
                    // h6 を超える段は、読み上げの段で伝える
                    "aria-level": level + BODY_HEADING_OFFSET > LOWEST_HEADING_LEVEL ? level + BODY_HEADING_OFFSET : null,
                },
                children: [...heading.childNodes],
            });
            heading.replaceWith(replacement);
        }
    }
    /** 詳細パネル（全画面のときは中央のモーダル）を返す。文書に入れた後、全画面は `showModal()` で開く */
    function detailPanel(props) {
        const { id, index, full, on } = props;
        const kind = index.byId.get(id)?.kind;
        const body = MindmapPreview.h({ tag: "div", attrs: { class: "panel-body" }, children: [detailBody(props)] });
        const head = detailHead(props);
        if (!full) {
            return MindmapPreview.h({
                tag: "aside",
                attrs: { class: `panel${kind === "docs" ? " wide" : ""}`, "aria-label": "詳細" },
                children: [head, body],
            });
        }
        const dialog = MindmapPreview.h({ tag: "dialog", attrs: { class: "full", "aria-label": "詳細の全画面" }, children: [head, body] });
        // Esc は閉じずに元の大きさ（詳細パネル）に戻す。外側（後ろの幕）を押したときも同じ
        dialog.addEventListener("cancel", (event) => {
            event.preventDefault();
            on.full(false);
        });
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog)
                on.full(false);
        });
        return dialog;
    }
    MindmapPreview.detailPanel = detailPanel;
})(MindmapPreview || (MindmapPreview = {}));

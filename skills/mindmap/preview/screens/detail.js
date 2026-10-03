"use strict";
// 詳細パネルと詳細の全画面。項目 1 件の中身（案・本文・図・関係する項目）を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** 項目の ID を、押すと開くボタンにする */
    function idButton(id, open) {
        return MindmapPreview.h("button", { class: "idlink", type: "button", onclick: () => open(id) }, id);
    }
    /** 項目の ID の並びを、ID・題・状態の一覧にする */
    function itemList(index, ids, open) {
        return MindmapPreview.h("ul", { class: "d-list" }, ...ids.map((id) => MindmapPreview.h("li", null, idButton(id, open), MindmapPreview.h("span", { class: "t" }, MindmapPreview.titleOf(index, id)), MindmapPreview.statusBadge(index.byId.get(id)?.item.status))));
    }
    /** 見出しの付いた節 */
    function section(label, content) {
        return MindmapPreview.h("section", { class: "d-sec" }, MindmapPreview.h("h3", null, label), content);
    }
    /** 検討事項の案をカードの縦並びにする（採用 / 不採用と理由を出す） */
    function optionCards(options) {
        return MindmapPreview.h("div", null, ...options.map((option) => {
            const result = option.adopted === true ? "採用" : option.adopted === false ? "不採用" : "検討中";
            const rows = [
                ["メリット", option.pros],
                ["デメリット", option.cons],
                ["備考", option.note],
                ["理由", option.reason],
            ];
            const shown = rows.filter((row) => row[1] !== undefined && row[1] !== "");
            return MindmapPreview.h("div", {
                class: `opt${option.adopted === true ? " adopted" : option.adopted === false ? " rejected" : ""}`,
            }, MindmapPreview.h("div", { class: "o-head" }, MindmapPreview.h("span", { class: "key" }, option.key), option.content, MindmapPreview.h("span", { class: "res" }, result)), shown.length > 0
                ? MindmapPreview.h("dl", null, ...shown.flatMap(([label, value]) => [MindmapPreview.h("dt", null, label), MindmapPreview.h("dd", null, value)]))
                : null);
        }));
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
        const rows = pairs.flatMap(([label, value]) => value === undefined || value === "" ? [] : [MindmapPreview.h("dt", null, label), MindmapPreview.h("dd", null, value)]);
        if ((item.tags ?? []).length > 0)
            rows.push(MindmapPreview.h("dt", null, "タグ"), MindmapPreview.h("dd", null, MindmapPreview.tagList(item.tags)));
        return MindmapPreview.h("dl", { class: "d-meta" }, ...rows);
    }
    /** 項目の中身（種類ごと）。本文は Markdown と図を描く */
    function detailBody({ id, index, on }) {
        const entry = index.byId.get(id);
        const body = MindmapPreview.h("div", { class: "detail" });
        if (entry === undefined)
            return body;
        const { kind, item } = entry;
        const related = MindmapPreview.relatedItems({ id, index });
        const labelled = (label, value) => value === undefined || value === ""
            ? null
            : MindmapPreview.h("div", { class: "d-answer" }, MindmapPreview.h("b", null, label), value);
        /** 本文の節。本文の図を描き、図の道具（拡大・Raw・コピー）を動かす */
        const bodySection = (label) => {
            const source = index.data.bodies[item.body ?? ""];
            if (source === undefined)
                return null;
            const rendered = MindmapPreview.renderMarkdown(source);
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
        MindmapPreview.append(body, MindmapPreview.statusBadge(item.status), MindmapPreview.h("h2", { class: "d-title" }, item.title, item.deliverable === true ? MindmapPreview.deliverableBadge() : null), metaList(item, index.data.settings));
        if (kind === "decisions") {
            MindmapPreview.append(body, item.lead === undefined ? null : MindmapPreview.h("p", { class: "d-lead" }, item.lead), labelled("決定内容", item.answer), labelled("理由", item.reason), (item.options ?? []).length > 0 ? section("案", optionCards(item.options ?? [])) : null, bodySection("本文"), relation("前提", related.prerequisites), relation("後続の項目", related.successors), relation("関連タスク", related.tasks), relation("経緯（会話ログ）", related.logs));
        }
        else if (kind === "tasks") {
            MindmapPreview.append(body, labelled("理由", item.reason), relation("進める検討事項", item.for ?? []), relation("前提", related.prerequisites), relation("結果", item.result === undefined ? [] : [item.result]));
        }
        else if (kind === "research") {
            MindmapPreview.append(body, item.question === undefined ? null : MindmapPreview.h("p", { class: "d-lead" }, item.question), labelled("結論", item.conclusion), (item.angles ?? []).length > 0 ? section("調査の観点", MindmapPreview.tagList(item.angles)) : null, bodySection("本文"));
        }
        else if (kind === "docs") {
            MindmapPreview.append(body, bodySection("本文"));
        }
        else if (kind === "terms") {
            MindmapPreview.append(body, labelled("意味", item.meaning), (item.aliases ?? []).length > 0 ? section("別名", MindmapPreview.tagList(item.aliases)) : null, (item.avoid ?? []).length > 0 ? section("使わない表記", MindmapPreview.tagList(item.avoid)) : null);
        }
        else if (kind === "notes") {
            MindmapPreview.append(body, item.content === undefined ? null : MindmapPreview.h("p", null, item.content));
        }
        else {
            MindmapPreview.append(body, bodySection("要約"));
        }
        if ((item.links ?? []).length > 0) {
            MindmapPreview.append(body, section("リンク", MindmapPreview.h("ul", { class: "d-list" }, ...(item.links ?? []).map((link) => MindmapPreview.h("li", null, MindmapPreview.icon("link"), MindmapPreview.h("a", { href: link.url, target: "_blank", rel: "noopener" }, link.title))))));
        }
        MindmapPreview.append(body, relation(kind === "logs" ? "更新した項目" : "関連", related.related), relation("この項目を参照している項目", related.referencedBy));
        return body;
    }
    /** 見出し（前へ・次へ・全画面・閉じる）を作る */
    function detailHead({ id, index, full, on }) {
        const entry = index.byId.get(id);
        const trail = history.state;
        const position = trail?.position ?? 0;
        const length = trail?.items.length ?? 1;
        const arrow = (label, glyph, disabled, handler) => MindmapPreview.h("button", {
            class: "icon-btn",
            type: "button",
            "data-act": glyph === "←" ? "back" : "forward",
            "aria-label": label,
            title: label,
            disabled,
            onclick: handler,
        }, glyph);
        return MindmapPreview.h("div", { class: "panel-head" }, full
            ? null
            : MindmapPreview.h("button", { class: "icon-btn panel-back", type: "button", "aria-label": "一覧へ戻る", onclick: on.close }, MindmapPreview.icon("back")), MindmapPreview.h("span", { class: "panel-kind" }, entry === undefined ? "" : `${MindmapPreview.KIND_LABEL[entry.kind]} `, MindmapPreview.h("span", { class: "mono" }, id)), MindmapPreview.h("span", { class: "spacer" }), arrow("前に見た項目へ戻る", "←", position <= 0, on.back), arrow("次に見た項目へ進む", "→", position >= length - 1, on.forward), MindmapPreview.h("button", {
            class: "icon-btn panel-full",
            type: "button",
            "data-act": "full",
            "aria-label": full ? "元の大きさに戻す" : "全画面で表示",
            title: full ? "元の大きさに戻す" : "全画面で表示",
            onclick: () => on.full(!full),
        }, MindmapPreview.icon(full ? "shrink" : "expand")), full
            ? null
            : MindmapPreview.h("button", {
                class: "icon-btn panel-close-x",
                type: "button",
                "data-act": "close",
                "aria-label": "詳細を閉じる",
                onclick: on.close,
            }, MindmapPreview.icon("x")));
    }
    /** 詳細パネル（全画面のときは中央のモーダル）を返す。文書に入れた後、全画面は `showModal()` で開く */
    function detailPanel(props) {
        const { id, index, full, on } = props;
        const kind = index.byId.get(id)?.kind;
        const body = MindmapPreview.h("div", { class: "panel-body" }, detailBody(props));
        const head = detailHead(props);
        if (!full) {
            return MindmapPreview.h("aside", { class: `panel${kind === "docs" ? " wide" : ""}`, "aria-label": "詳細" }, head, body);
        }
        const dialog = MindmapPreview.h("dialog", { class: "full", "aria-label": "詳細の全画面" }, head, body);
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

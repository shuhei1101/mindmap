"use strict";
// 全体の検索。ID・タイトル・本文で、全種類の項目を探すモーダル。
var MindmapPreview;
(function (MindmapPreview) {
    /** 結果 1 件に添える、項目の要約 */
    function summaryOf(item) {
        return item.answer ?? item.conclusion ?? item.meaning ?? item.content ?? item.lead ?? "";
    }
    /** 全体の検索のモーダルを返す。文書に入れた後、`showModal()` で開く */
    function searchDialog({ index, on }) {
        const input = MindmapPreview.h("input", {
            type: "text",
            placeholder: "ID・タイトル・本文で探す",
            autocomplete: "off",
            "aria-label": "検索する語",
        });
        const results = MindmapPreview.h("div", { class: "search-results" });
        const dialog = MindmapPreview.h("dialog", { class: "search", closedby: "any", "aria-label": "すべての項目を検索" }, MindmapPreview.h("div", { class: "search-head" }, MindmapPreview.icon("search"), input, MindmapPreview.h("button", { class: "icon-btn", type: "button", "aria-label": "検索を閉じる", onclick: () => dialog.close() }, MindmapPreview.icon("x"))), results);
        /** 結果のボタン */
        const buttons = () => [...results.querySelectorAll(".sr-item")];
        /** 検索の言葉で結果を描き直す */
        const render = () => {
            const query = input.value.trim();
            if (query === "") {
                results.replaceChildren(MindmapPreview.emptyNote("ID・タイトル・本文の語で、すべての項目を探します。"));
                return;
            }
            const hits = MindmapPreview.searchItems({ query, index });
            if (hits.length === 0) {
                results.replaceChildren(MindmapPreview.h("p", { class: "no-match" }, "該当する項目はありません。"));
                return;
            }
            const groups = MindmapPreview.KIND_KEYS.flatMap((kind) => {
                const ofKind = hits.filter((hit) => hit.kind === kind);
                return ofKind.length === 0
                    ? []
                    : [
                        MindmapPreview.h("h3", null, MindmapPreview.KIND_LABEL[kind]),
                        ...ofKind.map((hit) => {
                            const item = index.byId.get(hit.id)?.item;
                            return MindmapPreview.h("button", { class: "sr-item", type: "button", "data-id": hit.id, onclick: () => on.open(hit.id) }, MindmapPreview.h("span", { class: "mono" }, hit.id), MindmapPreview.h("span", null, MindmapPreview.statusMark(item?.status), ` ${hit.title}`, MindmapPreview.h("br"), MindmapPreview.h("span", { class: "sr-sub" }, item === undefined ? "" : summaryOf(item))));
                        }),
                    ];
            });
            results.replaceChildren(...groups);
        };
        input.addEventListener("input", render);
        // Enter で先頭の結果を開き、↓ で結果へ移る。結果の中は ↑ ↓ で選ぶ
        input.addEventListener("keydown", (event) => {
            if (event.key === "Enter")
                buttons()[0]?.click();
            if (event.key === "ArrowDown") {
                event.preventDefault();
                buttons()[0]?.focus();
            }
        });
        results.addEventListener("keydown", (event) => {
            const list = buttons();
            const position = list.indexOf(document.activeElement);
            if (event.key === "ArrowDown") {
                event.preventDefault();
                list[Math.min(list.length - 1, position + 1)]?.focus();
            }
            else if (event.key === "ArrowUp") {
                event.preventDefault();
                if (position <= 0)
                    input.focus();
                else
                    list[position - 1]?.focus();
            }
        });
        // 閉じたら（Esc・外側の押下・閉じるボタン）、使う側にも知らせる
        dialog.addEventListener("close", on.close);
        dialog.addEventListener("toggle", () => {
            if (dialog.open)
                input.select();
        });
        render();
        return dialog;
    }
    MindmapPreview.searchDialog = searchDialog;
})(MindmapPreview || (MindmapPreview = {}));

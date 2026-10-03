// 全体の検索。ID・タイトル・本文で、全種類の項目を探すモーダル。

namespace MindmapPreview {
  /** 全体の検索の引数 */
  export type SearchProps = {
    index: RecordIndex;
    on: {
      /** 結果の項目を開く（その項目のタブと詳細パネルを開く） */
      open: (id: string) => void;
      /** 検索を閉じた */
      close: () => void;
    };
  };

  /** 結果 1 件に添える、項目の要約 */
  function summaryOf(item: Item): string {
    return item.answer ?? item.conclusion ?? item.meaning ?? item.content ?? item.lead ?? "";
  }

  /** 全体の検索のモーダルを返す。文書に入れた後、`showModal()` で開く */
  export function searchDialog({ index, on }: SearchProps): HTMLDialogElement {
    const input = h({
      tag: "input",
      attrs: {
        type: "text",
        placeholder: "ID・タイトル・本文で探す",
        autocomplete: "off",
        "aria-label": "検索する語",
      },
    });
    const results = h({ tag: "div", attrs: { class: "search-results" } });
    const dialog = h({
      tag: "dialog",
      attrs: { class: "search", closedby: "any", "aria-label": "すべての項目を検索" },
      children: [
        h({
          tag: "div",
          attrs: { class: "search-head" },
          children: [
            icon("search"),
            input,
            h({
              tag: "button",
              attrs: { class: "icon-btn", type: "button", "aria-label": "検索を閉じる", onclick: () => dialog.close() },
              children: [icon("x")],
            }),
          ],
        }),
        results,
      ],
    });
    /** 結果のボタン */
    const buttons = (): HTMLElement[] => [...results.querySelectorAll<HTMLElement>(".sr-item")];
    /** 検索の言葉で結果を描き直す */
    const render = (): void => {
      const query = input.value.trim();
      if (query === "") {
        results.replaceChildren(emptyNote("ID・タイトル・本文の語で、すべての項目を探します。"));
        return;
      }
      const hits = searchItems({ query, index });
      if (hits.length === 0) {
        results.replaceChildren(h({ tag: "p", attrs: { class: "no-match" }, children: ["該当する項目はありません。"] }));
        return;
      }
      const groups = KIND_KEYS.flatMap((kind) => {
        const ofKind = hits.filter((hit) => hit.kind === kind);
        return ofKind.length === 0
          ? []
          : [
              h({ tag: "h3", children: [KIND_LABEL[kind]] }),
              ...ofKind.map((hit) => {
                const item = index.byId.get(hit.id)?.item;
                return h({
                  tag: "button",
                  attrs: { class: "sr-item", type: "button", "data-id": hit.id, onclick: () => on.open(hit.id) },
                  children: [
                    h({ tag: "span", attrs: { class: "mono" }, children: [hit.id] }),
                    h({
                      tag: "span",
                      children: [
                        statusMark(item?.status),
                        ` ${hit.title}`,
                        h({ tag: "br" }),
                        h({
                          tag: "span",
                          attrs: { class: "sr-sub" },
                          children: [item === undefined ? "" : summaryOf(item)],
                        }),
                      ],
                    }),
                  ],
                });
              }),
            ];
      });
      results.replaceChildren(...groups);
    };
    input.addEventListener("input", render);
    // Enter で先頭の結果を開き、↓ で結果へ移る。結果の中は ↑ ↓ で選ぶ
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") buttons()[0]?.click();
      if (event.key === "ArrowDown") {
        event.preventDefault();
        buttons()[0]?.focus();
      }
    });
    results.addEventListener("keydown", (event) => {
      const list = buttons();
      const position = list.indexOf(document.activeElement as HTMLElement);
      if (event.key === "ArrowDown") {
        event.preventDefault();
        list[Math.min(list.length - 1, position + 1)]?.focus();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        if (position <= 0) input.focus();
        else list[position - 1]?.focus();
      }
    });
    // 閉じたら（Esc・外側の押下・閉じるボタン）、使う側にも知らせる
    dialog.addEventListener("close", on.close);
    dialog.addEventListener("toggle", () => {
      if (dialog.open) input.select();
    });
    render();
    return dialog;
  }
}

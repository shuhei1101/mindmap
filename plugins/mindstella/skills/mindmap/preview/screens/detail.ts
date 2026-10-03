// 詳細パネルと詳細の全画面。項目 1 件の中身（案・本文・図・関係する項目）を出す。

namespace MindmapPreview {
  /** 詳細パネルの引数 */
  export type DetailProps = {
    /** 項目の ID */
    id: string;
    index: RecordIndex;
    /** 全画面か */
    full: boolean;
    on: {
      /** 項目へ移る（パネルと全画面の中の移動は履歴に積む） */
      open: (id: string) => void;
      /** パネルを閉じる */
      close: () => void;
      /** 全画面表示の入り切り */
      full: (full: boolean) => void;
      /** 見てきた項目を 1 つ戻る */
      back: () => void;
      /** 見てきた項目を 1 つ進む */
      forward: () => void;
      /** 図を拡大して見る */
      diagram: (svg: SVGElement) => void;
    };
  };

  /** 項目の ID を、押すと開くボタンにする */
  function idButton(id: string, open: (id: string) => void): HTMLElement {
    return h({
      tag: "button",
      attrs: { class: "idlink", type: "button", onclick: () => open(id) },
      children: [id],
    });
  }

  /** 項目の ID の並びを、ID・題・状態の一覧にする */
  function itemList(index: RecordIndex, ids: string[], open: (id: string) => void): HTMLElement {
    return h({
      tag: "ul",
      attrs: { class: "d-list" },
      children: [
        ...ids.map((id) =>
          h({
            tag: "li",
            children: [
              idButton(id, open),
              h({ tag: "span", attrs: { class: "t" }, children: [titleOf(index, id)] }),
              statusBadge(index.byId.get(id)?.item.status),
            ],
          }),
        ),
      ],
    });
  }

  /** 見出しの付いた節 */
  function section(label: string, content: Node): HTMLElement {
    return h({
      tag: "section",
      attrs: { class: "d-sec" },
      children: [h({ tag: "h3", children: [label] }), content],
    });
  }

  /** 検討事項の案をカードの縦並びにする（採用 / 不採用と理由を出す） */
  function optionCards(options: Option[]): HTMLElement {
    return h({
      tag: "div",
      children: [
        ...options.map((option) => {
          const result = option.adopted === true ? "採用" : option.adopted === false ? "不採用" : "検討中";
          const rows: [string, string | undefined][] = [
            ["メリット", option.pros],
            ["デメリット", option.cons],
            ["備考", option.note],
            ["理由", option.reason],
          ];
          const shown = rows.filter((row): row is [string, string] => row[1] !== undefined && row[1] !== "");
          return h({
            tag: "div",
            attrs: {
              class: `opt${option.adopted === true ? " adopted" : option.adopted === false ? " rejected" : ""}`,
            },
            children: [
              h({
                tag: "div",
                attrs: { class: "o-head" },
                children: [
                  h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                  option.content,
                  h({ tag: "span", attrs: { class: "res" }, children: [result] }),
                ],
              }),
              shown.length > 0
                ? h({
                  tag: "dl",
                  children: [
                    ...shown.flatMap(([label, value]) => [h({ tag: "dt", children: [label] }), h({ tag: "dd", children: [value] })]),
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
  function metaList(item: Item, settings: Settings): HTMLElement {
    const pairs: [string, string | undefined][] = [
      [settings.target_label, item.target],
      ["カテゴリー", item.category],
      ["フェーズ", item.phase],
      ["影響度", item.weight],
      ["種類", item.kind],
      ["確度", item.confidence],
      ["日付", item.date],
      ["更新日", item.updated],
    ];
    const rows = pairs.flatMap(([label, value]) =>
      value === undefined || value === "" ? [] : [h({ tag: "dt", children: [label] }), h({ tag: "dd", children: [value] })],
    );
    if ((item.tags ?? []).length > 0) rows.push(h({ tag: "dt", children: ["タグ"] }), h({ tag: "dd", children: [tagList(item.tags)] }));
    return h({ tag: "dl", attrs: { class: "d-meta" }, children: [...rows] });
  }

  /** 項目の中身（種類ごと）。本文は Markdown と図を描く */
  function detailBody({ id, index, on }: Omit<DetailProps, "full">): HTMLElement {
    const entry = index.byId.get(id);
    const body = h({ tag: "div", attrs: { class: "detail" } });
    if (entry === undefined) return body;
    const { kind, item } = entry;
    const related = relatedItems({ id, index });
    const labelled = (label: string, value: string | undefined): HTMLElement | null =>
      value === undefined || value === ""
        ? null
        : h({
          tag: "div",
          attrs: { class: "d-answer" },
          children: [h({ tag: "b", children: [label] }), value],
        });
    /** 本文の節。本文の図を描き、図の道具（拡大・Raw・コピー）を動かす */
    const bodySection = (label: string): HTMLElement | null => {
      const source = index.data.bodies[item.body ?? ""];
      if (source === undefined) return null;
      const rendered = renderMarkdown(source);
      lowerHeadings(rendered);
      void renderDiagrams(rendered);
      rendered.addEventListener("click", (event) => {
        const button = (event.target as Element).closest<HTMLElement>("[data-act]");
        const figure = button?.closest(".diagram");
        if (button === null || button === undefined || figure === null || figure === undefined) return;
        const act = button.dataset["act"];
        const original = figure.querySelector(".dg-raw")?.textContent ?? "";
        if (act === "diagram-zoom") {
          const svgElement = figure.querySelector<SVGElement>(".mermaid svg");
          if (svgElement !== null) on.diagram(svgElement);
        } else if (act === "diagram-raw") {
          // 図と mermaid の原文を切り替える
          const pressed = button.getAttribute("aria-pressed") !== "true";
          button.setAttribute("aria-pressed", String(pressed));
          figure.querySelector<HTMLElement>(".mermaid")!.hidden = pressed;
          figure.querySelector<HTMLElement>(".dg-raw")!.hidden = !pressed;
        } else if (act === "diagram-copy") {
          void navigator.clipboard?.writeText(original).then(() => {
            button.replaceChildren(icon("check"));
            window.setTimeout(() => button.replaceChildren(icon("copy")), 1400);
          });
        }
      });
      return section(label, rendered);
    };
    /** 関係する項目の節（1 件以上あるときだけ） */
    const relation = (label: string, ids: string[]): HTMLElement | null =>
      ids.length === 0 ? null : section(label, itemList(index, ids, on.open));

    append({
      parent: body,
      children: [
        statusBadge(item.status),
        h({
          tag: "h2",
          attrs: { class: "d-title" },
          children: [item.title, item.deliverable === true ? deliverableBadge() : null],
        }),
        metaList(item, index.data.settings),
      ],
    });
    if (kind === "decisions") {
      append({
        parent: body,
        children: [
          item.lead === undefined ? null : h({ tag: "p", attrs: { class: "d-lead" }, children: [item.lead] }),
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
    } else if (kind === "tasks") {
      append({
        parent: body,
        children: [
          labelled("理由", item.reason),
          relation("進める検討事項", item.for ?? []),
          relation("前提", related.prerequisites),
          relation("結果", item.result === undefined ? [] : [item.result]),
        ],
      });
    } else if (kind === "research") {
      append({
        parent: body,
        children: [
          item.question === undefined ? null : h({ tag: "p", attrs: { class: "d-lead" }, children: [item.question] }),
          labelled("結論", item.conclusion),
          (item.angles ?? []).length > 0 ? section("調査の観点", tagList(item.angles)) : null,
          bodySection("本文"),
        ],
      });
    } else if (kind === "docs") {
      append({ parent: body, children: [bodySection("本文")] });
    } else if (kind === "terms") {
      append({
        parent: body,
        children: [
          labelled("意味", item.meaning),
          (item.aliases ?? []).length > 0 ? section("別名", tagList(item.aliases)) : null,
          (item.avoid ?? []).length > 0 ? section("使わない表記", tagList(item.avoid)) : null,
        ],
      });
    } else if (kind === "notes") {
      append({
        parent: body,
        children: [
          item.content === undefined ? null : h({ tag: "p", children: [item.content] }),
        ],
      });
    } else {
      append({ parent: body, children: [bodySection("要約")] });
    }
    if ((item.links ?? []).length > 0) {
      append({
        parent: body,
        children: [
          section(
            "リンク",
            h({
              tag: "ul",
              attrs: { class: "d-list" },
              children: [
                ...(item.links ?? []).map((link) =>
                  h({
                    tag: "li",
                    children: [
                      icon("link"),
                      h({
                        tag: "a",
                        attrs: { href: link.url, target: "_blank", rel: "noopener" },
                        children: [link.title],
                      }),
                    ],
                  }),
                ),
              ],
            }),
          ),
        ],
      });
    }
    append({
      parent: body,
      children: [
        relation(kind === "logs" ? "更新した項目" : "関連", related.related),
        relation("参照元", related.referencedBy),
      ],
    });
    return body;
  }

  /** 見出し（前へ・次へ・全画面・閉じる）を作る */
  function detailHead({ id, index, full, on }: DetailProps): HTMLElement {
    const entry = index.byId.get(id);
    const trail = history.state as Trail | null;
    const position = trail?.position ?? 0;
    const length = trail?.items.length ?? 1;
    const arrow = (label: string, glyph: string, disabled: boolean, handler: () => void): HTMLElement =>
      h({
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
    return h({
      tag: "div",
      attrs: { class: "panel-head" },
      children: [
        full
          ? null
          : h({
            tag: "button",
            attrs: { class: "icon-btn panel-back", type: "button", "aria-label": "一覧へ戻る", onclick: on.close },
            children: [icon("back")],
          }),
        h({
          tag: "span",
          attrs: { class: "panel-kind" },
          children: [
            entry === undefined ? "" : `${KIND_LABEL[entry.kind]} `,
            h({ tag: "span", attrs: { class: "mono" }, children: [id] }),
          ],
        }),
        h({ tag: "span", attrs: { class: "spacer" } }),
        arrow("前の項目へ戻る", "←", position <= 0, on.back),
        arrow("次の項目へ進む", "→", position >= length - 1, on.forward),
        h({
          tag: "button",
          attrs: {
            class: "icon-btn panel-full",
            type: "button",
            "data-act": "full",
            "aria-label": "全画面表示",
            title: "全画面表示",
            "aria-pressed": String(full),
            onclick: () => on.full(!full),
          },
          children: [icon("expand")],
        }),
        full
          ? null
          : h({
            tag: "button",
            attrs: {
              class: "icon-btn panel-close-x",
              type: "button",
              "data-act": "close",
              "aria-label": "詳細を閉じる",
              onclick: on.close,
            },
            children: [icon("x")],
          }),
      ],
    });
  }

  /** 詳細パネルの節の見出し（h3）の下に、本文の見出し（h1〜h6）を並べるための段の差 */
  const BODY_HEADING_OFFSET = 3;

  /** 見出しの要素の最も下の段（h6） */
  const LOWEST_HEADING_LEVEL = 6;

  /** 本文の見出しを、パネルの節の見出しより下の段（h4〜h6）に下げる。見た目は元の段のまま（`data-md-level`） */
  function lowerHeadings(root: HTMLElement): void {
    for (const heading of root.querySelectorAll<HTMLElement>("h1, h2, h3, h4, h5, h6")) {
      const level = Number(heading.tagName.slice(1));
      const lowered = Math.min(level + BODY_HEADING_OFFSET, LOWEST_HEADING_LEVEL);
      const replacement = h({
        tag: `h${lowered}` as "h4" | "h5" | "h6",
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
  export function detailPanel(props: DetailProps): HTMLElement {
    const { id, index, full, on } = props;
    const kind = index.byId.get(id)?.kind;
    const body = h({ tag: "div", attrs: { class: "panel-body" }, children: [detailBody(props)] });
    const head = detailHead(props);
    if (!full) {
      return h({
        tag: "aside",
        attrs: { class: `panel${kind === "docs" ? " wide" : ""}`, "aria-label": "詳細" },
        children: [head, body],
      });
    }
    const dialog = h({ tag: "dialog", attrs: { class: "full", "aria-label": "詳細の全画面" }, children: [head, body] });
    // Esc は閉じずに元の大きさ（詳細パネル）に戻す。外側（後ろの幕）を押したときも同じ
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      on.full(false);
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) on.full(false);
    });
    return dialog;
  }
}

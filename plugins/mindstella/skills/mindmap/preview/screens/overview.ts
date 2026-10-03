// 概要。次に検討する項目・ゴールまでの進捗・要見直し・保留・進行中のタスク・カテゴリー別の進捗のタイルを並べる。

namespace MindmapPreview {
  /** 概要の引数 */
  export type OverviewProps = {
    index: RecordIndex;
    on: {
      /** 項目を詳細パネルで開く */
      open: (id: string) => void;
      /** 絞った表へ移る（`Route`） */
      navigate: (route: Route) => void;
    };
  };

  /** 縦に積む幅で出す、次に検討する項目の件数 */
  const NEXT_STACKED_COUNT = 3;

  /** 納品物のチェックリストに出す件数（これを超えたら資料を納品物で絞って開く） */
  const DELIVERABLE_LIMIT = 5;

  /** 小さなタイルに出す件数 */
  const MINI_LIMIT = 3;

  /** 次に検討する項目をタイルに横に並べる幅 */
  const WIDE_QUERY = "(min-width: 1101px)";

  /** 絞った表へ移る `Route`（画面の既定の表示形式で開く） */
  function tableRoute(tab: Tab, filters: Record<string, string[]>, view: View = "table"): Route {
    return { tab, view, id: null, full: false, filters };
  }

  /** 「すべて表示（N 件）」のボタン */
  function showAll(count: number, onClick: () => void): HTMLElement {
    return h({
      tag: "button",
      attrs: { class: "t-link", type: "button", onclick: onClick },
      children: [`すべて表示（${count} 件）`],
    });
  }

  /** 見出し（アイコンと名前）と、右端の「すべて表示」 */
  function tileHead(id: string, iconName: IconName, title: string, link: Node | null): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "t-head" },
      children: [h({ tag: "h2", attrs: { id }, children: [icon(iconName), title] }), link],
    });
  }

  /** 1 行が項目のボタンの一覧（押すと詳細を開く） */
  function miniList(
    items: Item[],
    emptyText: string,
    open: (id: string) => void,
  ): HTMLElement {
    if (items.length === 0) return emptyNote(emptyText);
    return h({
      tag: "ul",
      attrs: { class: "mini" },
      children: [
        ...items.slice(0, MINI_LIMIT).map((item) =>
          h({
            tag: "li",
            children: [
              h({
                tag: "button",
                attrs: { type: "button", "data-id": item.id, onclick: () => open(item.id) },
                children: [
                  statusMark(item.status),
                  h({ tag: "span", attrs: { class: "mt" }, children: [item.title] }),
                  h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [icon("chev")] }),
                ],
              }),
            ],
          }),
        ),
      ],
    });
  }

  /** 決定済みの数の棒（0〜100%） */
  function bar(settled: number, total: number): HTMLElement {
    const ratio = total === 0 ? 0 : (settled / total) * 100;
    return h({ tag: "i", children: [h({ tag: "b", attrs: { style: `width:${ratio}%` } })] });
  }

  /** 次に検討する項目のタイル */
  function nextTile({ index, on }: OverviewProps): HTMLElement {
    const candidates = index.data.derived.next;
    const list = h({
      tag: "ol",
      attrs: { class: "next-list" },
      children: [
        ...candidates.map((candidate) => {
          const item = index.byId.get(candidate.id)?.item;
          return h({
            tag: "li",
            children: [
              h({
                tag: "button",
                attrs: { type: "button", "data-id": candidate.id, onclick: () => on.open(candidate.id) },
                children: [
                  h({ tag: "span", attrs: { class: "nl-ttl" }, children: [candidate.title] }),
                  h({
                    tag: "span",
                    attrs: { class: "nl-meta" },
                    children: [
                      h({ tag: "span", children: [[item?.category, candidate.phase].filter(Boolean).join(" · ")] }),
                      impactBadge(candidate.weight ?? undefined, true),
                      h({
                        tag: "span",
                        attrs: { class: "fol", title: "後続の件数" },
                        children: [icon("follow"), candidate.followers],
                      }),
                    ],
                  }),
                  h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [icon("chev")] }),
                ],
              }),
            ],
          });
        }),
      ],
    });
    const tile = h({
      tag: "section",
      attrs: { id: "tile-next", class: "tile t-next", "aria-labelledby": "h-next" },
      children: [
        tileHead(
          "h-next",
          "next",
          "次に検討する項目",
          candidates.length > 0
            ? showAll(candidates.length, () =>
                on.navigate(tableRoute("decisions", { status: ["未決定"], ready: ["着手可能"] })),
              )
            : null,
        ),
        candidates.length > 0 ? list : emptyNote("次に検討する項目はありません。"),
      ],
    });
    // 横に並べる幅ではタイルの枠に収まるだけ、縦に積む幅では上位の数件だけを出す
    const fit = (): void => {
      const items = [...list.children] as HTMLElement[];
      for (const item of items) item.hidden = false;
      if (matchMedia(WIDE_QUERY).matches) {
        const limit =
          tile.getBoundingClientRect().bottom - Number.parseFloat(getComputedStyle(tile).paddingBottom);
        for (const item of items) if (item.getBoundingClientRect().bottom > limit) item.hidden = true;
      } else {
        items.forEach((item, position) => {
          item.hidden = position >= NEXT_STACKED_COUNT;
        });
      }
    };
    new ResizeObserver(fit).observe(tile);
    return tile;
  }

  /** ゴールまでの進捗のタイル（決定済みの数・フェーズごとの棒・納品物のチェックリスト） */
  function goalTile({ index, on }: OverviewProps): HTMLElement {
    const { goal } = index.data.derived;
    const settled = goal.phase_progress.reduce((sum, cell) => sum + cell.settled, 0);
    const total = goal.phase_progress.reduce((sum, cell) => sum + cell.total, 0);
    const { deliverables } = index.data.settings.goal;
    const remaining = new Set(goal.remaining_deliverables.map((entry) => entry.title));
    const doneCount = deliverables.filter((entry) => !remaining.has(entry.title)).length;
    const checklist = deliverables.slice(0, DELIVERABLE_LIMIT).map((entry) => {
      const done = !remaining.has(entry.title);
      const label =
        entry.doc !== undefined && index.byId.has(entry.doc)
          ? h({
            tag: "button",
            attrs: { type: "button", onclick: () => on.open(entry.doc as string) },
            children: [entry.title],
          })
          : h({ tag: "span", children: [entry.title] });
      return h({
        tag: "li",
        attrs: { class: done ? "done" : "" },
        children: [icon(done ? "checked" : "unchecked"), label],
      });
    });
    return h({
      tag: "section",
      attrs: { id: "tile-goal", class: "tile t-goal", "aria-labelledby": "h-goal" },
      children: [
        h({ tag: "h2", attrs: { id: "h-goal" }, children: [icon("flag"), "ゴールまでの進捗"] }),
        h({
          tag: "p",
          attrs: { class: "big" },
          children: [settled, h({ tag: "small", children: [` / ${total}`] })],
        }),
        h({ tag: "p", attrs: { class: "big-sub" }, children: ["決定済み"] }),
        h({
          tag: "ul",
          attrs: { class: "stage-rows" },
          children: [
            ...goal.phase_progress.map((cell) =>
              h({
                tag: "li",
                children: [
                  h({ tag: "span", children: [cell.phase] }),
                  bar(cell.settled, cell.total),
                  h({ tag: "span", attrs: { class: "mono" }, children: [`${cell.settled}/${cell.total}`] }),
                ],
              }),
            ),
          ],
        }),
        h({
          tag: "div",
          attrs: { class: "deliv" },
          children: [
            h({
              tag: "div",
              attrs: { class: "deliv-head" },
              children: [
                icon("box"),
                "納品物",
                h({ tag: "span", attrs: { class: "mono" }, children: [`${doneCount}/${deliverables.length}`] }),
                deliverables.length > DELIVERABLE_LIMIT
                  ? showAll(deliverables.length, () =>
                      on.navigate(tableRoute("docs", { deliverable: ["納品物"] }, "cards")),
                    )
                  : null,
              ],
            }),
            h({ tag: "ul", attrs: { class: "checklist" }, children: [...checklist] }),
          ],
        }),
      ],
    });
  }

  /** 件数と名前の小さなタイル（要見直し・保留・進行中のタスク） */
  function smallTile({
    tileId,
    id,
    iconName,
    title,
    items,
    emptyText,
    link,
    open,
  }: {
    /** タイルの項目 ID（画面設計） */
    tileId: string;
    /** タイルの見出しの要素の id */
    id: string;
    iconName: IconName;
    title: string;
    items: Item[];
    /** 0 件のときに出す文 */
    emptyText: string;
    link: () => void;
    open: (id: string) => void;
  }): HTMLElement {
    return h({
      tag: "section",
      attrs: { id: tileId, class: "tile t-small", "aria-labelledby": id },
      children: [
        tileHead(id, iconName, title, items.length > 0 ? showAll(items.length, link) : null),
        h({ tag: "p", attrs: { class: "num" }, children: [items.length] }),
        miniList(items, emptyText, open),
      ],
    });
  }

  /** カテゴリー別の進捗の表（カテゴリーを行、フェーズを列にする） */
  function progressTile({ index, on }: OverviewProps): HTMLElement {
    const { settings, derived } = index.data;
    const rowOf = (entry: Derived["progress"][number]): HTMLElement =>
      h({
        tag: "tr",
        children: [
          h({
            tag: "th",
            attrs: { scope: "row" },
            children: [
              h({
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
          ...entry.cells.map((cell) =>
            cell.total === 0
              ? h({ tag: "td", children: [h({ tag: "span", attrs: { class: "muted" }, children: ["—"] })] })
              : h({
                tag: "td",
                children: [
                  h({
                    tag: "button",
                    attrs: {
                      class: "cell",
                      type: "button",
                      "aria-label": `${entry.category} の ${cell.phase}: ${cell.settled}/${cell.total} 件決定済み`,
                      onclick: () =>
                        on.navigate(
                          tableRoute("decisions", {
                            category: [entry.category],
                            phase: [cell.phase],
                          }),
                        ),
                    },
                    children: [
                      bar(cell.settled, cell.total),
                      h({ tag: "span", attrs: { class: "mono" }, children: [`${cell.settled}/${cell.total}`] }),
                    ],
                  }),
                ],
              }),
          ),
          h({ tag: "td", attrs: { class: "tot mono" }, children: [`${entry.settled}/${entry.total}`] }),
        ],
      });
    // 対象ごとに見出しの行を立て、その対象のカテゴリーを続ける
    const groups = settings.targets.flatMap((target) => {
      const entries = derived.progress.filter(
        (entry) =>
          entry.total > 0 &&
          settings.categories.some(
            (category) => category.name === entry.category && category.target === target.name,
          ),
      );
      return entries.length === 0
        ? []
        : [
            h({
              tag: "tbody",
              children: [
                h({
                  tag: "tr",
                  attrs: { class: "tgt" },
                  children: [
                    h({
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
    return h({
      tag: "section",
      attrs: { id: "tile-progress", class: "tile t-cat", "aria-labelledby": "h-cat" },
      children: [
        h({ tag: "h2", attrs: { id: "h-cat" }, children: [icon("layers"), "カテゴリー別の進捗"] }),
        h({
          tag: "div",
          attrs: { class: "cat-wrap" },
          children: [
            h({
              tag: "table",
              attrs: { class: "cat-table" },
              children: [
                h({
                  tag: "thead",
                  children: [
                    h({
                      tag: "tr",
                      children: [
                        h({ tag: "th", attrs: { scope: "col" }, children: ["カテゴリー"] }),
                        ...settings.phases.map((phase) => h({ tag: "th", attrs: { scope: "col" }, children: [phase] })),
                        h({ tag: "th", attrs: { scope: "col", class: "tot" }, children: ["決定済み"] }),
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
  export function overviewScreen(props: OverviewProps): HTMLElement {
    const { index, on } = props;
    const { settings } = index.data;
    const decisions = index.data.decisions;
    const review = decisions.filter((item) => item.status === "要見直し");
    const hold = decisions.filter((item) => item.status === "保留");
    const running = index.data.tasks.filter((item) => item.status === "進行中");
    return h({
      tag: "div",
      attrs: { class: "overview" },
      children: [
        h({
          tag: "header",
          attrs: { class: "hero" },
          children: [
            h({
              tag: "p",
              attrs: { class: "hero-sub" },
              children: [`${settings.field} · ゴールは${settings.goal.phase}のフェーズまで`],
            }),
            h({ tag: "h1", children: [settings.summary] }),
          ],
        }),
        h({
          tag: "div",
          attrs: { class: "bento" },
          children: [
            nextTile(props),
            goalTile(props),
            smallTile({
              tileId: "tile-review",
              id: "h-review",
              iconName: "alert",
              title: "要見直し",
              items: review,
              emptyText: "要見直しの検討事項はありません。",
              link: () => on.navigate(tableRoute("decisions", { status: ["要見直し"] })),
              open: on.open,
            }),
            smallTile({
              tileId: "tile-hold",
              id: "h-hold",
              iconName: "pause",
              title: "保留",
              items: hold,
              emptyText: "保留の検討事項はありません。",
              link: () => on.navigate(tableRoute("decisions", { status: ["保留"] })),
              open: on.open,
            }),
            smallTile({
              tileId: "tile-running",
              id: "h-run",
              iconName: "play",
              title: "進行中のタスク",
              items: running,
              emptyText: "進行中のタスクはありません。",
              link: () => on.navigate(tableRoute("tasks", { status: ["進行中"] })),
              open: on.open,
            }),
            progressTile(props),
          ],
        }),
      ],
    });
  }
}

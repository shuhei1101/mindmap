// 概要。次に検討する項目・ゴールまで・要見直し・保留・進行中のタスク・カテゴリー別の進み具合のタイルを並べる。

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

  /** 成果物のチェックリストに出す件数（これを超えたら資料を成果物で絞って開く） */
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
    return h(
      "button",
      { class: "t-link", type: "button", onclick: onClick },
      `すべて表示（${count} 件）`,
    );
  }

  /** 見出し（アイコンと名前）と、右端の「すべて表示」 */
  function tileHead(id: string, iconName: IconName, title: string, link: Node | null): HTMLElement {
    return h("div", { class: "t-head" }, h("h2", { id }, icon(iconName), title), link);
  }

  /** 1 行が項目のボタンの一覧（押すと詳細を開く） */
  function miniList(
    items: Item[],
    emptyText: string,
    open: (id: string) => void,
  ): HTMLElement {
    if (items.length === 0) return emptyNote(emptyText);
    return h(
      "ul",
      { class: "mini" },
      ...items.slice(0, MINI_LIMIT).map((item) =>
        h(
          "li",
          null,
          h(
            "button",
            { type: "button", "data-id": item.id, onclick: () => open(item.id) },
            statusMark(item.status),
            h("span", { class: "mt" }, item.title),
            h("span", { class: "go", "aria-hidden": "true" }, icon("chev")),
          ),
        ),
      ),
    );
  }

  /** 決定済みの数の棒（0〜100%） */
  function bar(settled: number, total: number): HTMLElement {
    const ratio = total === 0 ? 0 : (settled / total) * 100;
    return h("i", null, h("b", { style: `width:${ratio}%` }));
  }

  /** 次に検討する項目のタイル */
  function nextTile({ index, on }: OverviewProps): HTMLElement {
    const candidates = index.data.derived.next;
    const list = h(
      "ol",
      { class: "next-list" },
      ...candidates.map((candidate) => {
        const item = index.byId.get(candidate.id)?.item;
        return h(
          "li",
          null,
          h(
            "button",
            { type: "button", "data-id": candidate.id, onclick: () => on.open(candidate.id) },
            h("span", { class: "nl-ttl" }, candidate.title),
            h(
              "span",
              { class: "nl-meta" },
              h("span", null, [item?.category, candidate.phase].filter(Boolean).join(" · ")),
              impactBadge(candidate.weight ?? undefined),
              h("span", { class: "fol", title: "後続の件数" }, icon("follow"), candidate.followers),
            ),
            h("span", { class: "go", "aria-hidden": "true" }, icon("chev")),
          ),
        );
      }),
    );
    const tile = h(
      "section",
      { class: "tile t-next", "aria-labelledby": "h-next" },
      tileHead(
        "h-next",
        "next",
        "次に検討する項目",
        candidates.length > 0
          ? showAll(candidates.length, () =>
              on.navigate(tableRoute("decisions", { status: ["未決定"], ready: ["はい"] })),
            )
          : null,
      ),
      candidates.length > 0 ? list : emptyNote("次に検討する項目はありません"),
    );
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

  /** ゴールまでのタイル（決定済みの数・フェーズごとの棒・成果物のチェックリスト） */
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
          ? h(
              "button",
              { type: "button", onclick: () => on.open(entry.doc as string) },
              entry.title,
            )
          : h("span", null, entry.title);
      return h("li", { class: done ? "done" : "" }, icon(done ? "checked" : "unchecked"), label);
    });
    return h(
      "section",
      { class: "tile t-goal", "aria-labelledby": "h-goal" },
      h("h2", { id: "h-goal" }, icon("flag"), "ゴールまで"),
      h("p", { class: "big" }, settled, h("small", null, ` / ${total}`)),
      h("p", { class: "big-sub" }, "決定済み"),
      h(
        "ul",
        { class: "stage-rows" },
        ...goal.phase_progress.map((cell) =>
          h(
            "li",
            null,
            h("span", null, cell.phase),
            bar(cell.settled, cell.total),
            h("span", { class: "mono" }, `${cell.settled}/${cell.total}`),
          ),
        ),
      ),
      h(
        "div",
        { class: "deliv" },
        h(
          "div",
          { class: "deliv-head" },
          icon("box"),
          "成果物",
          h("span", { class: "mono" }, `${doneCount}/${deliverables.length}`),
          deliverables.length > DELIVERABLE_LIMIT
            ? showAll(deliverables.length, () =>
                on.navigate(tableRoute("docs", { deliverable: ["成果物"] }, "cards")),
              )
            : null,
        ),
        h("ul", { class: "checklist" }, ...checklist),
      ),
    );
  }

  /** 件数と名前の小さなタイル（要見直し・保留・進行中のタスク） */
  function smallTile({
    id,
    iconName,
    title,
    items,
    link,
    open,
  }: {
    id: string;
    iconName: IconName;
    title: string;
    items: Item[];
    link: () => void;
    open: (id: string) => void;
  }): HTMLElement {
    return h(
      "section",
      { class: "tile t-small", "aria-labelledby": id },
      tileHead(id, iconName, title, items.length > 0 ? showAll(items.length, link) : null),
      h("p", { class: "num" }, items.length),
      miniList(items, "なし", open),
    );
  }

  /** カテゴリー別の進み具合の表（カテゴリーを行、フェーズを列にする） */
  function progressTile({ index, on }: OverviewProps): HTMLElement {
    const { settings, derived } = index.data;
    const rowOf = (entry: Derived["progress"][number]): HTMLElement =>
      h(
        "tr",
        null,
        h(
          "th",
          { scope: "row" },
          h(
            "button",
            {
              class: "cat-link",
              type: "button",
              onclick: () => on.navigate(tableRoute("decisions", { category: [entry.category] })),
            },
            entry.category,
          ),
        ),
        ...entry.cells.map((cell) =>
          cell.total === 0
            ? h("td", null, h("span", { class: "muted" }, "—"))
            : h(
                "td",
                null,
                h(
                  "button",
                  {
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
                  bar(cell.settled, cell.total),
                  h("span", { class: "mono" }, `${cell.settled}/${cell.total}`),
                ),
              ),
        ),
        h("td", { class: "tot mono" }, `${entry.settled}/${entry.total}`),
      );
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
            h(
              "tbody",
              null,
              h(
                "tr",
                { class: "tgt" },
                h(
                  "th",
                  { colspan: settings.phases.length + 2, scope: "rowgroup" },
                  `${settings.target_label}: ${target.name}`,
                ),
              ),
              ...entries.map(rowOf),
            ),
          ];
    });
    return h(
      "section",
      { class: "tile t-cat", "aria-labelledby": "h-cat" },
      h("h2", { id: "h-cat" }, icon("layers"), "カテゴリー別の進み具合"),
      h(
        "div",
        { class: "cat-wrap" },
        h(
          "table",
          { class: "cat-table" },
          h(
            "thead",
            null,
            h(
              "tr",
              null,
              h("th", { scope: "col" }, "カテゴリー"),
              ...settings.phases.map((phase) => h("th", { scope: "col" }, phase)),
              h("th", { scope: "col", class: "tot" }, "決定済み"),
            ),
          ),
          ...groups,
        ),
      ),
    );
  }

  /** 概要の画面を返す */
  export function overviewScreen(props: OverviewProps): HTMLElement {
    const { index, on } = props;
    const { settings } = index.data;
    const decisions = index.data.decisions;
    const review = decisions.filter((item) => item.status === "要見直し");
    const hold = decisions.filter((item) => item.status === "保留");
    const running = index.data.tasks.filter((item) => item.status === "進行中");
    return h(
      "div",
      { class: "overview" },
      h(
        "header",
        { class: "hero" },
        h("p", { class: "hero-sub" }, `${settings.field} · ゴールは${settings.goal.phase}のフェーズまで`),
        h("h1", null, settings.summary),
      ),
      h(
        "div",
        { class: "bento" },
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
      ),
    );
  }
}

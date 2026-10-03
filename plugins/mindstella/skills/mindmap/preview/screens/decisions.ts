// 検討事項。マップ（既定）・ボード・表で見る。マップは対象 → カテゴリー → フェーズ → 検討事項の木を ELK で配置して描く。

namespace MindmapPreview {
  /** マップの節の種類 */
  type MapNodeKind = "target" | "category" | "phase" | "item";

  /** マップの節（ELK に渡し、配置された座標が入って戻る） */
  export type MapNode = {
    id: string;
    width: number;
    height: number;
    kind: MapNodeKind;
    label: string;
    item?: Item;
    x?: number;
    y?: number;
  };

  /** マップの枝（ELK に渡し、配置された経路が入って戻る） */
  export type MapEdge = {
    id: string;
    sources: string[];
    targets: string[];
    sections?: {
      startPoint: { x: number; y: number };
      endPoint: { x: number; y: number };
      bendPoints?: { x: number; y: number }[];
    }[];
  };

  /** ELK に渡すグラフ（配置の後は `width`・`height` が入る） */
  export type MapGraph = {
    id: string;
    layoutOptions: Record<string, string>;
    children: MapNode[];
    edges: MapEdge[];
    width?: number;
    height?: number;
  };

  /** 節の種類ごとの大きさ（幅・高さ） */
  const NODE_SIZE: Record<MapNodeKind, [number, number]> = {
    target: [130, 40],
    category: [150, 34],
    phase: [118, 26],
    item: [236, 48],
  };

  /** 設定に無い対象・カテゴリー・フェーズに付ける名前 */
  const UNSET = "（未設定）";

  /** 木を左から右へ、直角の枝で並べる ELK の設定 */
  const ELK_OPTIONS: Record<string, string> = {
    "elk.algorithm": "layered",
    "elk.direction": "RIGHT",
    "elk.edgeRouting": "ORTHOGONAL",
    "elk.layered.spacing.nodeNodeBetweenLayers": "36",
    "elk.spacing.nodeNode": "10",
    "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
    "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
    "elk.layered.nodePlacement.bk.fixedAlignment": "BALANCED",
    "elk.padding": "[top=24,left=24,bottom=24,right=24]",
  };

  /** マップで最初に表示する状態（決定済み・対象外・取り下げは隠す） */
  const DEFAULT_SHOWN_STATUSES = ["要見直し", "未決定", "未整理", "保留"];

  /** 拡大・縮小 1 回の倍率の幅と、倍率の範囲 */
  const ZOOM_STEP = 0.15;
  const ZOOM_MIN = 0.4;
  const ZOOM_MAX = 1.5;

  /** マップの狭い幅の境（これ以下は字下げした縦の一覧） */
  const NARROW_QUERY = "(max-width: 900px)";

  /** 表示する状態の検討事項が 1 件も無いときに、マップの枠と字下げの一覧に出す文 */
  const NO_SHOWN_STATUS_TEXT = "表示する状態の検討事項はありません";

  /** 対象 → カテゴリー → フェーズ → 検討事項の木を、表示する状態で絞って返す（ELK に渡す節と枝の形） */
  export function buildDecisionTree({
    index,
    shownStatuses,
  }: {
    index: RecordIndex;
    shownStatuses: Set<string>;
  }): MapGraph {
    const { settings } = index.data;
    const shown = index.data.decisions
      .filter((item) => shownStatuses.has(item.status ?? ""))
      .sort((a, b) => compareIds(a.id, b.id));
    /** 設定の並びの順（設定に無いものは最後） */
    const rankIn = (list: string[], name: string): number => {
      const position = list.indexOf(name);
      return position < 0 ? list.length : position;
    };
    const targetOf = (item: Item): string =>
      settings.categories.find((category) => category.name === item.category)?.target ??
      item.target ??
      UNSET;
    const categoryOf = (item: Item): string => item.category ?? UNSET;
    const phaseOf = (item: Item): string => item.phase ?? UNSET;
    const unique = (values: string[]): string[] => [...new Set(values)];

    const children: MapNode[] = [];
    const edges: MapEdge[] = [];
    const add = (id: string, kind: MapNodeKind, label: string, parent: string | null, item?: Item) => {
      const [width, height] = NODE_SIZE[kind];
      children.push({ id, width, height, kind, label, item });
      if (parent !== null) edges.push({ id: `${parent}>${id}`, sources: [parent], targets: [id] });
    };
    const targets = unique(shown.map(targetOf)).sort(
      (a, b) =>
        rankIn(
          settings.targets.map((target) => target.name),
          a,
        ) -
        rankIn(
          settings.targets.map((target) => target.name),
          b,
        ),
    );
    for (const target of targets) {
      const targetId = `target:${target}`;
      add(targetId, "target", target, null);
      const ofTarget = shown.filter((item) => targetOf(item) === target);
      const categories = unique(ofTarget.map(categoryOf)).sort(
        (a, b) =>
          rankIn(
            settings.categories.map((category) => category.name),
            a,
          ) -
          rankIn(
            settings.categories.map((category) => category.name),
            b,
          ),
      );
      for (const category of categories) {
        const categoryId = `category:${target}/${category}`;
        add(categoryId, "category", category, targetId);
        const ofCategory = ofTarget.filter((item) => categoryOf(item) === category);
        const phases = unique(ofCategory.map(phaseOf)).sort(
          (a, b) => rankIn(settings.phases, a) - rankIn(settings.phases, b),
        );
        for (const phase of phases) {
          const phaseId = `phase:${target}/${category}/${phase}`;
          add(phaseId, "phase", phase, categoryId);
          for (const item of ofCategory.filter((candidate) => phaseOf(candidate) === phase)) {
            add(item.id, "item", item.title, phaseId, item);
          }
        }
      }
    }
    return { id: "graph", layoutOptions: ELK_OPTIONS, children, edges };
  }

  // ───── マップの状態（描き直しても保つ） ─────

  /** マップの状態 */
  const mapState: {
    shownStatuses: Set<string>;
    keyword: string;
    zoom: number | "fit";
    scroll: { left: number; top: number } | null;
    selected: string | null;
  } = {
    shownStatuses: new Set(DEFAULT_SHOWN_STATUSES),
    keyword: "",
    zoom: "fit",
    scroll: null,
    selected: null,
  };

  /** 配置の結果（表示する状態の組み合わせごと） */
  const layoutCache = new Map<string, MapGraph>();

  /** 配置を計算する（同じ状態の組み合わせは取っておく） */
  async function layoutOf(graph: MapGraph, key: string): Promise<MapGraph> {
    const cached = layoutCache.get(key);
    if (cached !== undefined) return cached;
    const laid = (await new ELK().layout(graph as never)) as unknown as MapGraph;
    layoutCache.set(key, laid);
    return laid;
  }

  /** 前提 → 後続の線の道筋（同じ列どうしは、節の右側にふくらむ弧でつなぐ） */
  function dependencyPath(from: MapNode, to: MapNode): string {
    const fromX = (from.x ?? 0) + from.width;
    const fromY = (from.y ?? 0) + from.height / 2;
    // 同じ列
    if (Math.abs((from.x ?? 0) - (to.x ?? 0)) < 10) {
      const toY = (to.y ?? 0) + to.height / 2;
      const bulge = 28 + Math.min(60, Math.abs(toY - fromY) / 6);
      return `M${fromX},${fromY} C${fromX + bulge},${fromY} ${fromX + bulge},${toY} ${fromX},${toY}`;
    }
    const toX = to.x ?? 0;
    const toY = (to.y ?? 0) + to.height / 2;
    const reach = Math.max(60, Math.abs(toX - fromX) / 2);
    return `M${fromX},${fromY} C${fromX + reach},${fromY} ${toX - reach},${toY} ${toX},${toY}`;
  }

  /** SVG の要素を作る */
  function svg<K extends keyof SVGElementTagNameMap>(
    tag: K,
    attrs: Record<string, string>,
  ): SVGElementTagNameMap[K] {
    const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, value);
    return element;
  }

  /** 木の節と枝を、配置された座標で描く。選んだ項目の根までの枝と依存の線を強調し、ほかを薄くする */
  function drawMap({
    laid,
    canvas,
    selected,
    open,
  }: {
    laid: MapGraph;
    canvas: HTMLElement;
    selected: string | null;
    open: (id: string) => void;
  }): void {
    const positions = new Map(laid.children.map((node) => [node.id, node]));
    const parentOf = new Map(laid.edges.map((edge) => [edge.targets[0], edge.sources[0]]));
    // 選んだ項目から根までの節
    const chain = new Set<string>();
    for (let id = selected; id !== null && id !== undefined; id = parentOf.get(id) ?? null) chain.add(id);

    const edgeSvg = svg("svg", {
      class: "edges",
      width: String(laid.width ?? 0),
      height: String(laid.height ?? 0),
      "aria-hidden": "true",
    });
    for (const edge of laid.edges) {
      const section = edge.sections?.[0];
      if (section === undefined) continue;
      const points = [section.startPoint, ...(section.bendPoints ?? []), section.endPoint];
      const [source, target] = [edge.sources[0], edge.targets[0]];
      edgeSvg.append(
        svg("path", {
          class: `edge-tree${chain.has(source) && chain.has(target) ? " rel" : ""}`,
          d: `M${points.map((point) => `${point.x},${point.y}`).join(" L")}`,
        }),
      );
    }
    // 依存の線: 前提 → 後続。選んだ項目に関わる線を強め、その上を小さな玉が流れる
    const near = new Set(chain);
    let flowId = 0;
    for (const node of laid.children) {
      if (node.kind !== "item" || node.item === undefined) continue;
      for (const prerequisite of node.item.depends_on ?? []) {
        const from = positions.get(prerequisite);
        if (from === undefined) continue;
        const related = selected !== null && (selected === prerequisite || selected === node.id);
        const id = `dep-${(flowId += 1)}`;
        edgeSvg.append(
          svg("path", { id, class: `edge-dep${related ? " rel" : ""}`, d: dependencyPath(from, node) }),
        );
        if (related) {
          near.add(prerequisite);
          near.add(node.id);
          // 選んだ項目から外へ向かって、玉をゆっくり流す（入ってくる線は向きを逆にする）
          const incoming = node.id === selected;
          for (const begin of [0, 1.6]) {
            const dot = svg("circle", { class: "flow-dot", r: "2.6" });
            const motion = svg("animateMotion", {
              dur: "3.2s",
              begin: `${begin}s`,
              repeatCount: "indefinite",
              ...(incoming ? { keyPoints: "1;0", keyTimes: "0;1", calcMode: "linear" } : {}),
            });
            motion.append(svg("mpath", { href: `#${id}` }));
            dot.append(motion);
            edgeSvg.append(dot);
          }
        }
      }
    }
    const keyword = mapState.keyword.toLowerCase();
    const nodes = laid.children.map((node) => {
      const style = `left:${node.x ?? 0}px;top:${node.y ?? 0}px;width:${node.width}px;height:${node.height}px`;
      const rel = near.has(node.id) ? " rel" : "";
      if (node.kind !== "item" || node.item === undefined) {
        return h({
          tag: "div",
          attrs: { class: `map-node n-${node.kind}${rel}`, "data-node": node.id, style },
          children: [h({ tag: "span", attrs: { class: "lbl" }, children: [node.label] })],
        });
      }
      const item = node.item;
      const hit = keyword !== "" && item.title.toLowerCase().includes(keyword);
      return h({
        tag: "button",
        attrs: {
          class: `map-node n-item${selected === item.id ? " sel" : ""}${hit ? " hit" : ""}${rel}`,
          type: "button",
          "data-node": item.id,
          style,
          title: `${item.title}（${item.status ?? ""}）`,
          onclick: () => open(item.id),
        },
        children: [
          h({
            tag: "span",
            attrs: { class: "r1" },
            children: [
              statusMark(item.status),
              h({ tag: "span", attrs: { class: "lbl" }, children: [item.title] }),
            ],
          }),
          h({
            tag: "span",
            attrs: { class: "r2" },
            children: [
              h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
              h({ tag: "span", children: [item.status ?? ""] }),
              item.weight === undefined ? null : h({ tag: "span", children: [`影響度 ${item.weight}`] }),
            ],
          }),
        ],
      });
    });
    canvas.classList.toggle("focusing", selected !== null);
    canvas.style.width = `${laid.width ?? 0}px`;
    canvas.style.height = `${laid.height ?? 0}px`;
    canvas.replaceChildren(edgeSvg, ...nodes);
  }

  /** 狭い幅で使う、字下げした縦の一覧 */
  function outline({
    index,
    open,
  }: {
    index: RecordIndex;
    open: (id: string) => void;
  }): HTMLElement {
    const tree = buildDecisionTree({ index, shownStatuses: mapState.shownStatuses });
    const nodeOf = new Map(tree.children.map((node) => [node.id, node]));
    const childrenOf = new Map<string, MapNode[]>();
    for (const edge of tree.edges) {
      const list = childrenOf.get(edge.sources[0]) ?? [];
      const child = nodeOf.get(edge.targets[0]);
      if (child !== undefined) list.push(child);
      childrenOf.set(edge.sources[0], list);
    }
    /** 節と、その下の節を字下げして並べる */
    const entry = (node: MapNode): HTMLElement => {
      const label =
        node.kind === "item" && node.item !== undefined
          ? h({
            tag: "button",
            attrs: { type: "button", "data-id": node.id, onclick: () => open(node.id) },
            children: [statusMark(node.item.status), h({ tag: "span", children: [node.label] })],
          })
          : h({ tag: "div", attrs: { class: `o-${node.kind}` }, children: [node.label] });
      const below = childrenOf.get(node.id) ?? [];
      return h({
        tag: "li",
        children: [
          label,
          below.length > 0 ? h({ tag: "ul", children: [...below.map(entry)] }) : null,
        ],
      });
    };
    const roots = tree.children.filter((node) => node.kind === "target");
    return h({
      tag: "nav",
      attrs: { class: "map-outline", "aria-label": "検討事項の一覧" },
      // 表示する状態の検討事項が無いときは、対象の見出しを並べず空の旨を出す
      children: [roots.length > 0 ? h({ tag: "ul", children: [...roots.map(entry)] }) : emptyNote(NO_SHOWN_STATUS_TEXT)],
    });
  }

  /** マップの道具の行（状態の印・キーワード）と、マップの枠・拡大の道具を作る */
  function mapView({ index, route, on }: ScreenProps): HTMLElement {
    const root = h({ tag: "div", attrs: { class: "map-view-root" } });
    const decisions = index.data.decisions;
    const legend = h({ tag: "div", attrs: { class: "legend", role: "group", "aria-label": "表示する状態" } });
    const frame = h({ tag: "div", attrs: { class: "map-frame" } });
    // 表示する状態の検討事項が無いときに、マップの枠の中央に出す文
    const emptyNotice = h({ tag: "p", attrs: { class: "empty map-empty", hidden: true }, children: [NO_SHOWN_STATUS_TEXT] });
    const canvas = h({ tag: "div", attrs: { id: "decision-map", class: "map-canvas", role: "group", "aria-label": "検討事項のマップ" } });
    const sizer = h({ tag: "div", attrs: { class: "map-sizer" }, children: [canvas] });
    const wrap = h({ tag: "div", attrs: { class: "map-wrap" }, children: [sizer] });
    // 全体を表示のボタン（押された状態を見た目に出す）
    const fitButton = h({
      tag: "button",
      attrs: {
        class: "btn ghost",
        type: "button",
        "aria-pressed": "false",
        onclick: () => {
          mapState.zoom = mapState.zoom === "fit" ? 1 : "fit";
          applyZoom();
        },
      },
      children: ["全体を表示"],
    });
    let outlineElement = outline({ index, open: on.open });
    let current: MapGraph | null = null;

    /** キーワードに当たった検討事項か */
    const isHit = (item: Item): boolean =>
      mapState.keyword !== "" && item.title.toLowerCase().includes(mapState.keyword.toLowerCase());

    /** 状態の印の行（表示 / 非表示の切り替えと、件数・キーワードに当たった件数のバッジ。右端にまとめて切り替える箱） */
    const drawLegend = (): void => {
      const bandStatuses = DECISION_STATUSES.filter((status) => decisions.some((item) => item.status === status));
      legend.replaceChildren(
        ...bandStatuses.map(
          (status) => {
            const total = decisions.filter((item) => item.status === status).length;
            const hits = decisions.filter((item) => item.status === status && isHit(item)).length;
            return h({
              tag: "label",
              children: [
                h({
                  tag: "input",
                  attrs: {
                    type: "checkbox",
                    value: status,
                    checked: mapState.shownStatuses.has(status),
                    onchange: (event: Event) => {
                      if ((event.target as HTMLInputElement).checked) mapState.shownStatuses.add(status);
                      else mapState.shownStatuses.delete(status);
                      void draw(false);
                    },
                  },
                }),
                statusMark(status),
                status,
                h({ tag: "span", attrs: { class: "n" }, children: [total] }),
                hits > 0
                  ? h({
                    tag: "span",
                    attrs: { class: "hit-n", "aria-label": `キーワードに当たった項目 ${hits} 件` },
                    children: [hits],
                  })
                  : null,
              ],
            });
          },
        ),
        toggleAllBox({
          label: "すべての状態を表示",
          shown: mapState.shownStatuses,
          all: bandStatuses,
          onChange: (next) => {
            mapState.shownStatuses = next;
            void draw(false);
          },
        }),
      );
    };

    /** 拡大率を決めて、マップの大きさと拡大を当てる（全体を表示は、枠に木の全体が収まる倍率） */
    const applyZoom = (): void => {
      if (current === null) return;
      const width = current.width ?? 0;
      const height = current.height ?? 0;
      const scale =
        mapState.zoom === "fit"
          ? Math.min(1, (wrap.clientWidth - 16) / width, (wrap.clientHeight - 16) / height)
          : mapState.zoom;
      sizer.style.width = `${width * scale + 240}px`;
      sizer.style.height = `${height * scale + 160}px`;
      canvas.style.transform = `scale(${scale})`;
      fitButton.setAttribute("aria-pressed", String(mapState.zoom === "fit"));
    };

    /** 配置を求めて、マップを描く。選んだ項目が変わったときは、その節が中央に来るようにマップを送る */
    const draw = async (keepScroll: boolean): Promise<void> => {
      drawLegend();
      outlineElement.replaceWith((outlineElement = outline({ index, open: on.open })));
      if (missingLibraries(["elkjs"]).length > 0) return;
      const key = [...mapState.shownStatuses].sort().join(",");
      const graph = buildDecisionTree({ index, shownStatuses: mapState.shownStatuses });
      emptyNotice.hidden = graph.children.length > 0;
      current = await layoutOf(graph, key);
      const previous = { left: wrap.scrollLeft, top: wrap.scrollTop };
      drawMap({ laid: current, canvas, selected: route.id, open: on.open });
      applyZoom();
      const node = route.id === null ? undefined : current.children.find((n) => n.id === route.id);
      const scale = mapState.zoom === "fit" ? Number.parseFloat(canvas.style.transform.slice(6)) : mapState.zoom;
      if (node !== undefined && route.id !== mapState.selected) {
        wrap.scrollTo({
          left: ((node.x ?? 0) + node.width / 2) * scale - wrap.clientWidth / 2,
          top: ((node.y ?? 0) + node.height / 2) * scale - wrap.clientHeight / 2,
        });
      } else if (keepScroll) {
        wrap.scrollTo(previous);
      } else if (mapState.scroll !== null) {
        wrap.scrollTo(mapState.scroll);
      }
      mapState.selected = route.id;
    };

    // ===== 道具の行 =====
    const keyword = h({
      tag: "input",
      attrs: {
        class: "input map-q",
        type: "search",
        placeholder: "名前で強調",
        value: mapState.keyword,
        "aria-label": "名前で強調するキーワード",
      },
    });
    let timer: number | undefined;
    keyword.addEventListener("input", () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        mapState.keyword = keyword.value;
        // 当たった節の色と、状態の印のバッジだけを更新する
        for (const button of canvas.querySelectorAll<HTMLElement>("button.n-item")) {
          const item = index.byId.get(button.dataset["node"] ?? "")?.item;
          button.classList.toggle("hit", item !== undefined && isHit(item));
        }
        drawLegend();
      }, 150);
    });
    const toolbarElement = toolbar(
      [
        { key: "map", label: "マップ" },
        { key: "board", label: "ボード" },
        { key: "table", label: "表" },
      ],
      route,
      on.view,
    );
    toolbarElement.append(keyword);

    /** 拡大・縮小・全体を表示のボタン（マップの枠の外に置く） */
    const zoomBar = h({
      tag: "div",
      attrs: { class: "zoom", role: "group", "aria-label": "拡大率" },
      children: [
        h({
          tag: "button",
          attrs: {
            class: "icon-btn",
            type: "button",
            "aria-label": "縮小",
            onclick: () => {
              const base = mapState.zoom === "fit" ? 0.6 : mapState.zoom;
              mapState.zoom = Math.max(ZOOM_MIN, Math.round((base - ZOOM_STEP) * 100) / 100);
              applyZoom();
            },
          },
          children: ["−"],
        }),
        fitButton,
        h({
          tag: "button",
          attrs: {
            class: "icon-btn",
            type: "button",
            "aria-label": "拡大",
            onclick: () => {
              const base = mapState.zoom === "fit" ? 0.6 : mapState.zoom;
              mapState.zoom = Math.min(ZOOM_MAX, Math.round((base + ZOOM_STEP) * 100) / 100);
              applyZoom();
            },
          },
          children: ["＋"],
        }),
      ],
    });
    wrap.addEventListener("scroll", () => {
      mapState.scroll = { left: wrap.scrollLeft, top: wrap.scrollTop };
    });
    enableDragScroll(wrap);

    // elkjs が読めない: 知らせを出し、表示形式を表に切り替えると読めることを伝える
    const notice =
      missingLibraries(["elkjs"]).length > 0
        ? h({
          tag: "div",
          children: [
            libraryNotice({ names: ["elkjs"], what: "マップ" }),
            emptyNote("表示形式を表に切り替えると、検討事項を読めます。"),
          ],
        })
        : null;
    frame.append(emptyNotice, wrap);
    if (notice !== null) frame.hidden = true;

    append({
      parent: root,
      children: [
        toolbarElement,
        h({ tag: "div", attrs: { class: "map-tools" }, children: [legend] }),
        notice,
        frame,
        zoomBar,
        outlineElement,
      ],
    });
    // 拡大率が「全体を表示」のときは、枠の大きさが変わるたびに倍率を求め直す
    new ResizeObserver(() => {
      if (mapState.zoom === "fit") applyZoom();
    }).observe(wrap);
    void draw(true);
    return root;
  }

  /** 検討事項の画面を返す */
  export function decisionsScreen(props: ScreenProps): HTMLElement {
    const { index, route, on } = props;
    if (route.view === "map") return h({ tag: "div", attrs: { class: "screen decisions" }, children: [mapView(props)] });
    const toolbarElement = toolbar(
      [
        { key: "map", label: "マップ" },
        { key: "board", label: "ボード" },
        { key: "table", label: "表" },
      ],
      route,
      on.view,
    );
    if (route.view === "board") {
      return h({
        tag: "div",
        attrs: { class: "screen decisions" },
        children: [
          toolbarElement,
          board({
            columns: boardColumns({ items: index.data.decisions, statuses: [...DECISION_STATUSES] }),
            card: (item) =>
              boardCard({
                index,
                item,
                meta: [item.category, item.phase],
                links: item.depends_on ?? [],
                open: on.open,
              }),
          }),
        ],
      });
    }
    const common = commonColumns(index.data.settings);
    const columns: Column[] = [
      common.id,
      common.title(),
      common.status(DECISION_STATUSES),
      common.target,
      common.category,
      common.phase,
      {
        key: "weight",
        label: "影響度",
        nowrap: true,
        filterable: true,
        order: ["大", "中", "小"],
        priority: 3,
        get: (row) => (typeof row["weight"] === "string" ? row["weight"] : undefined),
        cell: (row) => impactBadge(typeof row["weight"] === "string" ? row["weight"] : undefined),
      },
      {
        key: "ready",
        label: "着手できる",
        nowrap: true,
        filterable: true,
        order: ["はい", "いいえ"],
        priority: 2,
        // 前提が全て決着した未決定の検討事項（build が計算した次の候補）
        get: (row) => (index.readyIds.has(row.id) ? "はい" : "いいえ"),
      },
      {
        key: "depends_on",
        label: "前提",
        priority: 3,
        get: (row) => rowTexts(row, "depends_on"),
        cell: (row) => idLinksCell(rowTexts(row, "depends_on"), on.open),
      },
      common.tags,
    ];
    return h({
      tag: "div",
      attrs: { class: "screen decisions" },
      children: [
        toolbarElement,
        managedTable({
          kind: "decisions",
          columns,
          rows: index.data.decisions,
          open: on.open,
          initialFilters: route.filters,
        }),
      ],
    });
  }
}

// 起動。埋め込みの記録を読み、URL のハッシュが指す画面を描き、操作を画面の移動と端末の保存領域につなぐ。

namespace MindmapPreview {
  /** 埋め込みのデータの要素の ID */
  const DATA_ELEMENT_ID = "mindmap-data";

  /** 端末の保存領域のキー */
  export const PREFS_KEY = "mindmap-preview";

  /** 端末に残す設定 */
  export type Prefs = {
    /** ライト / ダーク。null は OS の設定に従う */
    theme: Theme | null;
    /** 種類ごとの表示する列とピン留め */
    columns: Record<string, TablePrefs>;
  };

  /** 狭い幅（詳細パネルを別画面として積む幅） */
  const NARROW_QUERY = "(max-width: 900px)";

  /** タブのアイコン */
  const TAB_ICON: Record<Exclude<Tab, "graph">, IconName> = {
    overview: "home",
    decisions: "decision",
    tasks: "task",
    research: "research",
    docs: "doc",
    terms: "term",
    notes: "note",
    logs: "log",
  };

  /** タブの名前（種類の名前は読み込み順によらないよう、呼ばれたときに引く） */
  function tabLabel(key: Exclude<Tab, "graph">): string {
    return key === "overview" ? "概要" : KIND_LABEL[key];
  }

  /** `mindmap-data` の要素の中身を `JSON.parse` して返す */
  export function readEmbeddedData(doc: Document): MindmapData {
    try {
      const element = doc.getElementById(DATA_ELEMENT_ID);
      return JSON.parse(element?.textContent ?? "") as MindmapData;
    } catch {
      throw new Error("記録を読めませんでした。preview.html を書き出し直してください");
    }
  }

  /** 既定の設定 */
  function defaultPrefs(): Prefs {
    return { theme: null, columns: {} };
  }

  /** 端末の保存領域から設定を読む。読めないときは既定を返す */
  export function loadPrefs(storage: Storage): Prefs {
    try {
      const saved = storage.getItem(PREFS_KEY);
      if (saved === null) return defaultPrefs();
      const parsed = JSON.parse(saved) as Partial<Prefs>;
      return { ...defaultPrefs(), ...parsed };
    } catch {
      return defaultPrefs();
    }
  }

  /** 設定を端末の保存領域に残す。保存領域が例外を送るときは何もしない */
  export function savePrefs({ storage, prefs }: { storage: Storage; prefs: Prefs }): void {
    try {
      storage.setItem(PREFS_KEY, JSON.stringify(prefs));
    } catch {
      // 保存できない環境では、開いている間だけ設定を保つ
    }
  }

  /** 端末の保存領域（開けない環境では、何も返さない保存領域） */
  function openStorage(): Storage {
    try {
      return window.localStorage;
    } catch {
      return {
        length: 0,
        clear: () => undefined,
        getItem: () => null,
        key: () => null,
        removeItem: () => undefined,
        setItem: () => undefined,
      };
    }
  }

  /** 記録を読み、ハッシュが指す画面を描き、操作と履歴をつなぐ */
  export function start(): void {
    let data: MindmapData;
    try {
      data = readEmbeddedData(document);
    } catch (error) {
      document.body.prepend(h({ tag: "p", attrs: { class: "md-error" }, children: [(error as Error).message] }));
      return;
    }
    const index = buildIndex(data);
    const storage = openStorage();
    const prefs = loadPrefs(storage);
    const persist = (): void => savePrefs({ storage, prefs });
    restoreTablePrefs(prefs.columns, (kind, tablePrefs) => {
      if (tablePrefs === null) delete prefs.columns[kind];
      else prefs.columns[kind] = tablePrefs;
      persist();
    });
    document.title = `${data.settings.summary} | mindmap`;

    // ===== テーマ =====
    let theme: Theme = prefs.theme ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.dataset["theme"] = theme;

    // ===== 画面の土台 =====
    const top = h({ tag: "div", attrs: { id: "top" } });
    const main = h({ tag: "main", attrs: { class: "content", id: "main" } });
    document.body.prepend(top, main);
    let route = parseHash({ hash: location.hash, index });
    let fullViewer: HTMLElement | null = null;

    // ===== 移動 =====
    /** 詳細パネルを別画面として積む幅か */
    const isNarrow = (): boolean => matchMedia(NARROW_QUERY).matches;

    /** 画面の既定の URL（絞り込みは書かない）に route を書き、画面を描く */
    const go = (next: Route, push: boolean): void => {
      const screenChanged =
        next.tab !== route.tab || next.view !== route.view || Object.keys(next.filters).length > 0;
      const idChanged = next.id !== route.id;
      route = next;
      navigate({ route: { ...route, filters: {} }, push });
      render({ screen: screenChanged || (route.tab === "decisions" && route.view === "map" && idChanged) });
    };

    /** 項目を開く。パネル・全画面の中の移動は履歴に積み、見てきた項目を行き来できるようにする */
    const openItem = (id: string, inPanel: boolean): void => {
      const next: Route = { ...route, id, filters: {} };
      const trail = history.state as Trail | null;
      if (inPanel && route.id !== null) {
        // 今いる履歴にも先の項目を持たせ、戻った後に「→」で進めるようにする
        const items = [...(trail?.items ?? [route.id]).slice(0, (trail?.position ?? 0) + 1), id];
        navigate({ route: { ...route, filters: {} }, push: false, trail: { items, position: trail?.position ?? 0 } });
        route = next;
        navigate({ route: next, push: true, trail: { items, position: items.length - 1 } });
        render({ screen: route.tab === "decisions" && route.view === "map" });
        return;
      }
      route = next;
      // 狭い幅では詳細を別画面として積み、戻る操作で一覧へ戻す
      navigate({ route: next, push: isNarrow(), trail: { items: [id], position: 0 } });
      render({ screen: route.tab === "decisions" && route.view === "map" });
    };

    /** 詳細パネルを閉じる */
    const closeDetail = (): void => {
      if (isNarrow() && history.state !== null && (history.state as Trail).items !== undefined && history.length > 1) {
        history.back();
        return;
      }
      route = { ...route, id: null, full: false, filters: {} };
      navigate({ route, push: false });
      render({ screen: route.tab === "decisions" && route.view === "map" });
    };

    /** 項目を、その種類の画面で開く（画面を移るので履歴に積む） */
    const openFromSearch = (id: string): void => {
      const kind = index.byId.get(id)?.kind;
      if (kind === undefined) return;
      const tab: Tab = kind;
      go({ tab, view: defaultView(tab), id, full: false, filters: {} }, tab !== route.tab);
    };

    // ===== 描く =====
    /** トップバーとタブの帯 */
    const renderTop = (): void => {
      top.replaceChildren(
        topbar({
          title: data.settings.summary,
          tabs: TAB_KEYS.map((key) => ({
            key,
            label: tabLabel(key as Exclude<Tab, "graph">),
            icon: TAB_ICON[key as Exclude<Tab, "graph">],
            count: key === "overview" ? undefined : data[key as Kind].length,
          })),
          current: route.tab,
          theme,
          onNavigate: (tab) => go({ ...route, tab, view: defaultView(tab), filters: {} }, true),
          onSearch: openSearch,
          onTheme: (next) => {
            theme = next;
            prefs.theme = next;
            persist();
            document.documentElement.dataset["theme"] = next;
            renderTop();
          },
        }),
      );
    };

    /** 今の画面 */
    const screenElement = (): HTMLElement => {
      const on = { open: (id: string) => openItem(id, false), view: (view: View) => go({ ...route, view, filters: {} }, false) };
      switch (route.tab) {
        case "overview":
          return overviewScreen({ index, on: { open: on.open, navigate: (next) => go({ ...next, id: route.id }, true) } });
        case "decisions":
          return decisionsScreen({ index, route, on });
        case "tasks":
          return tasksScreen({ index, route, on });
        case "docs":
          return docsScreen({ index, route, on });
        case "graph":
          return graphScreen({ index, on: { open: on.open }, selected: route.id });
        default:
          return recordsScreen({ index, route, on: { open: on.open } });
      }
    };

    /** 本文の領域を描く。画面（タブ・表示形式）が変わったときだけ描き直す */
    const renderMain = (): void => {
      main.classList.toggle("map-view", route.tab === "decisions" && route.view === "map");
      main.replaceChildren(screenElement());
      // 開いたときの絞り込みは一度だけ使い、描き直しで使い回さない
      route = { ...route, filters: {} };
      if (route.tab === "graph") selectGraphItem(route.id);
    };

    /** 詳細パネルと全画面 */
    const renderDetail = (): void => {
      const existing = document.querySelector<HTMLElement>("aside.panel");
      const fullDialog = document.querySelector<HTMLDialogElement>("dialog.full");
      fullViewer = null;
      document.body.classList.toggle("panel-open", route.id !== null && !route.full);
      markSelected(route.id);
      // 開いている項目が無い: パネルも全画面も閉じる
      if (route.id === null) {
        existing?.classList.remove("open");
        fullDialog?.close();
        fullDialog?.remove();
        return;
      }
      const panel = detailPanel({
        id: route.id,
        index,
        full: route.full,
        on: {
          open: (id) => openItem(id, true),
          close: closeDetail,
          full: (full) => {
            // 全画面の中で図を拡大しているときは、本文へ戻る
            if (!full && fullViewer !== null) return closeFullViewer();
            go({ ...route, full }, false);
          },
          back: () => history.back(),
          forward: () => history.forward(),
          diagram: showDiagram,
        },
      });
      if (route.full) {
        existing?.classList.remove("open");
        fullDialog?.remove();
        document.body.append(panel);
        (panel as HTMLDialogElement).showModal();
        return;
      }
      fullDialog?.close();
      fullDialog?.remove();
      if (existing === null) {
        // 初めて開く: すべり込ませるため、置いてから次のコマで開いた状態にする
        document.body.append(panel);
        requestAnimationFrame(() => panel.classList.add("open"));
      } else {
        // 開いたまま項目を移った: すべり込ませずに中身だけを入れ替える
        existing.className = `${panel.className} open`;
        existing.replaceChildren(...panel.children);
      }
    };

    /** 描く（`screen` が真のとき本文の領域も描き直す） */
    const render = ({ screen }: { screen: boolean }): void => {
      renderTop();
      if (screen) {
        const wide = document.querySelector<HTMLElement>(".table-wrap, .map-wrap, .board");
        const keep = wide === null ? 0 : wide.scrollTop;
        renderMain();
        void keep;
      }
      renderDetail();
      if (route.tab === "graph") selectGraphItem(route.id);
    };

    // ===== 図の拡大 =====
    /** 図を拡大して見る。詳細パネルからはモーダル、全画面からは全画面の中身を切り替える */
    const showDiagram = (svg: SVGElement): void => {
      if (route.full) {
        const dialog = document.querySelector<HTMLDialogElement>("dialog.full");
        const body = dialog?.querySelector<HTMLElement>(".panel-body");
        if (dialog === null || dialog === undefined || body === null || body === undefined) return;
        body.hidden = true;
        const viewer = h({
          tag: "div",
          attrs: { class: "full-viewer" },
          children: [diagramViewer({ svg, on: { close: closeFullViewer } })],
        });
        body.after(viewer);
        fullViewer = viewer;
        return;
      }
      const modal = h({ tag: "dialog", attrs: { class: "viewer", "aria-label": "図の拡大" } });
      modal.append(diagramViewer({ svg, on: { close: () => modal.close() } }));
      modal.addEventListener("close", () => modal.remove());
      document.body.append(modal);
      modal.showModal();
    };

    /** 全画面の中の図の拡大を閉じて、本文に戻す */
    const closeFullViewer = (): void => {
      fullViewer?.remove();
      fullViewer = null;
      const body = document.querySelector<HTMLElement>("dialog.full .panel-body");
      if (body !== null) body.hidden = false;
    };

    // ===== 全体の検索 =====
    /** 検索を開く（開いているときは何もしない） */
    const openSearch = (): void => {
      if (document.querySelector("dialog.search") !== null) return;
      const dialog = searchDialog({
        index,
        on: {
          open: (id) => {
            dialog.close();
            openFromSearch(id);
          },
          close: () => dialog.remove(),
        },
      });
      document.body.append(dialog);
      dialog.showModal();
    };

    // ===== 操作と履歴 =====
    document.addEventListener("keydown", (event) => {
      const typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName ?? "");
      if (event.key === "/" && !typing && document.querySelector("dialog[open]") === null) {
        event.preventDefault();
        openSearch();
      }
      // Esc: 重ねる面が無いときは、詳細パネルを閉じる
      if (
        event.key === "Escape" &&
        route.id !== null &&
        !route.full &&
        document.querySelector("dialog[open]") === null &&
        document.querySelector(":popover-open") === null
      ) {
        closeDetail();
      }
    });
    /** ハッシュが変わったとき（戻る・進む・手で書き換えた）、その画面を描く */
    const onLocationChange = (): void => {
      const next = parseHash({ hash: location.hash, index });
      if (toHash(next) === toHash(route)) return;
      const screen = next.tab !== route.tab || next.view !== route.view || (next.tab === "decisions" && next.view === "map" && next.id !== route.id);
      route = next;
      render({ screen });
    };
    addEventListener("popstate", onLocationChange);
    addEventListener("hashchange", onLocationChange);

    // ===== 最初の描き =====
    // 記録に無い項目を指すハッシュは、項目の無いハッシュに置き換える
    const requested = new URLSearchParams(location.hash.replace(/^#/, "")).get("id");
    if (requested !== null && route.id === null) navigate({ route: { ...route, filters: {} }, push: false });
    render({ screen: true });
    // 絞り込みは画面に渡した後、ハッシュから消す
    navigate({ route: { ...route, filters: {} }, push: false });
  }

  // 文書が読み込まれたら起動する（記録の要素が無い文書では、読んだだけでは何もしない）
  if (document.getElementById(DATA_ELEMENT_ID) !== null) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
  }
}

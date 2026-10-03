// URL のハッシュの読み書きと履歴。画面・表示形式・開いている項目・全画面・絞り込みを、`URLSearchParams` の形で持つ。

namespace MindmapPreview {
  /** 画面（タブとつながり） */
  export type Tab =
    | "overview"
    | "decisions"
    | "tasks"
    | "research"
    | "docs"
    | "terms"
    | "notes"
    | "logs"
    | "graph";

  /** タブの帯に並べる画面（つながりは帯の右端に別に置く） */
  export const TAB_KEYS: readonly Tab[] = [
    "overview",
    "decisions",
    "tasks",
    "research",
    "docs",
    "terms",
    "notes",
    "logs",
  ];

  /** 表示形式 */
  export type View = "map" | "board" | "cards" | "table";

  /** 画面の場所（URL のハッシュが指すもの） */
  export type Route = {
    tab: Tab;
    view: View;
    /** 開いている項目 */
    id: string | null;
    /** 詳細を全画面で開いているか */
    full: boolean;
    /** 開いたときの `f.{列}`（書き戻さない） */
    filters: Record<string, string[]>;
  };

  /** 画面ごとの既定の表示形式（書いていない画面は表） */
  export const DEFAULT_VIEW: Partial<Record<Tab, View>> = {
    decisions: "map",
    tasks: "board",
    docs: "cards",
  };

  /** 画面が持つ表示形式（書いていない画面は表だけ） */
  export const VIEWS_OF: Partial<Record<Tab, View[]>> = {
    decisions: ["map", "board", "table"],
    tasks: ["board", "table"],
    docs: ["cards", "board", "table"],
  };

  /** 画面の既定の表示形式 */
  export function defaultView(tab: Tab): View {
    return DEFAULT_VIEW[tab] ?? "table";
  }

  /** 画面が持つ表示形式 */
  export function viewsOf(tab: Tab): View[] {
    return VIEWS_OF[tab] ?? ["table"];
  }

  /** 履歴に持つ、見てきた項目の並びと今の位置（← → のボタンが使う） */
  export type Trail = { items: string[]; position: number };

  /** URL のハッシュを `Route` にする */
  export function parseHash({ hash, index }: { hash: string; index: RecordIndex }): Route {
    const params = new URLSearchParams(hash.replace(/^#/, ""));
    const requestedTab = params.get("tab");
    const tab = (
      [...TAB_KEYS, "graph"].includes(requestedTab as Tab) ? requestedTab : "overview"
    ) as Tab;
    const requestedView = params.get("view");
    const view = (
      viewsOf(tab).includes(requestedView as View) ? requestedView : defaultView(tab)
    ) as View;
    // 記録に無い ID は開かない
    const requestedId = params.get("id");
    const id = requestedId !== null && index.byId.has(requestedId) ? requestedId : null;
    const filters: Record<string, string[]> = {};
    for (const [key, value] of params) {
      if (key.startsWith("f.")) filters[key.slice(2)] = value.split("|");
    }
    return { tab, view, id, full: id !== null && params.get("full") === "1", filters };
  }

  /** `Route` を URL のハッシュにする（既定の値と絞り込みは書かない） */
  export function toHash(route: Route): string {
    const params = new URLSearchParams();
    if (route.tab !== "overview") params.set("tab", route.tab);
    if (route.view !== defaultView(route.tab)) params.set("view", route.view);
    if (route.id !== null) params.set("id", route.id);
    if (route.full) params.set("full", "1");
    const text = params.toString();
    return text === "" ? "" : `#${text}`;
  }

  /** ハッシュを書き換え、履歴に積むか置き換える。履歴の状態に、見てきた項目の並びを持てる */
  export function navigate({
    route,
    push,
    trail,
  }: {
    route: Route;
    push: boolean;
    trail?: Trail;
  }): void {
    const url = `${location.pathname}${location.search}${toHash(route)}`;
    const state = trail ?? history.state;
    if (push) history.pushState(state, "", url);
    else history.replaceState(state, "", url);
  }
}

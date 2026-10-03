// トップバー。話し合いの題名・全体の検索の入口・ライト / ダークの切り替えと、画面を移るタブの帯（右端につながりの入口）を出す。

namespace MindmapPreview {
  /** ライト / ダーク */
  export type Theme = "light" | "dark";

  /** タブの帯に並べる 1 つの画面 */
  export type TopbarTab = {
    key: Tab;
    label: string;
    icon: IconName;
    /** その種類の項目の件数（概要は持たない） */
    count?: number;
  };

  /** トップバーの引数 */
  export type TopbarProps = {
    /** 話し合いの題名（`mindmap.yaml` の `summary`）。1 行で末尾を省略し、全文を `title` 属性に持たせる */
    title: string;
    /** タブの帯に並べる画面（つながりは含めない） */
    tabs: TopbarTab[];
    /** 開いている画面 */
    current: Tab;
    /** 今のライト / ダーク */
    theme: Theme;
    /** タブかつながりの入口を押したとき（開いている詳細パネルは閉じない） */
    onNavigate: (key: Tab) => void;
    /** 検索の入口を押したとき（`/` キーは使う側が受ける） */
    onSearch: () => void;
    /** ライト / ダークのボタンを押したとき（切り替え先を渡す） */
    onTheme: (theme: Theme) => void;
  };

  /** ブランドのマーク（木の形の線画） */
  function brandMark(): SVGSVGElement {
    const holder = document.createElement("template");
    holder.innerHTML =
      '<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="16" r="4"/><path d="M12 16h5M17 16V7h5M17 16v9h5"/><circle cx="25" cy="7" r="2.6"/><circle cx="25" cy="25" r="2.6"/></svg>';
    return holder.content.firstElementChild as SVGSVGElement;
  }

  /** 画面を移るリンク（ハッシュのリンクにして、押したときは使う側が移る） */
  function tabLink(
    { key, label, icon: iconName, count }: TopbarTab,
    current: Tab,
    onNavigate: (key: Tab) => void,
    extraClass = "",
  ): HTMLElement {
    return h({
      tag: "a",
      attrs: {
        class: `tab ${extraClass}`.trim(),
        href: `#${key === "overview" ? "" : `tab=${key}`}`,
        "data-tab": key,
        "aria-current": key === current ? "page" : null,
        onclick: (event) => {
          event.preventDefault();
          onNavigate(key);
        },
      },
      children: [
        icon(iconName),
        label,
        count === undefined ? null : h({ tag: "span", attrs: { class: "count" }, children: [count] }),
      ],
    });
  }

  /** トップバーとタブの帯を返す */
  export function topbar({
    title,
    tabs,
    current,
    theme,
    onNavigate,
    onSearch,
    onTheme,
  }: TopbarProps): HTMLElement {
    const nextTheme: Theme = theme === "dark" ? "light" : "dark";
    const bar = h({
      tag: "header",
      attrs: { class: "topbar" },
      children: [
        h({
          tag: "span",
          attrs: { class: "brand" },
          children: [
            brandMark(),
            h({ tag: "span", attrs: { class: "brand-name" }, children: ["mindmap"] }),
          ],
        }),
        h({ tag: "span", attrs: { class: "brand-sub", title }, children: [title] }),
        h({ tag: "span", attrs: { class: "spacer" } }),
        h({
          tag: "button",
          attrs: {
            class: "search-trigger",
            type: "button",
            "data-act": "search",
            "aria-label": "すべての項目を検索",
            onclick: () => onSearch(),
          },
          children: [
            icon("search"),
            h({ tag: "span", attrs: { class: "label" }, children: ["すべての項目を検索"] }),
            h({ tag: "kbd", children: ["/"] }),
          ],
        }),
        h({
          tag: "button",
          attrs: {
            class: "top-btn",
            type: "button",
            "data-theme": nextTheme,
            "aria-label": theme === "dark" ? "ライトに切り替え" : "ダークに切り替え",
            onclick: () => onTheme(nextTheme),
          },
          children: [icon(theme === "dark" ? "sun" : "moon")],
        }),
      ],
    });
    const tabbar = h({
      tag: "nav",
      attrs: { class: "tabbar", "aria-label": "項目の種類" },
      children: [
        ...tabs.map((tab) => tabLink(tab, current, onNavigate)),
        h({ tag: "span", attrs: { class: "tab-gap" } }),
        tabLink({ key: "graph", label: "つながり", icon: "orbit" }, current, onNavigate, "tab-special"),
      ],
    });
    return h({ tag: "div", attrs: { class: "top" }, children: [bar, tabbar] });
  }
}

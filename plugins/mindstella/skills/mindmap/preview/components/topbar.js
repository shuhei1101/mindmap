"use strict";
// トップバー。話し合いの題名・全体の検索の入口・ライト / ダークの切り替えと、画面を移るタブの帯（右端につながりの入口）を出す。
var MindmapPreview;
(function (MindmapPreview) {
    /** ブランドのマーク（木の形の線画） */
    function brandMark() {
        const holder = document.createElement("template");
        holder.innerHTML =
            '<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="16" r="4"/><path d="M12 16h5M17 16V7h5M17 16v9h5"/><circle cx="25" cy="7" r="2.6"/><circle cx="25" cy="25" r="2.6"/></svg>';
        return holder.content.firstElementChild;
    }
    /** 画面を移るリンク（ハッシュのリンクにして、押したときは使う側が移る） */
    function tabLink({ key, label, icon: iconName, count }, current, onNavigate, extraClass = "") {
        return MindmapPreview.h({
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
                MindmapPreview.icon(iconName),
                label,
                count === undefined ? null : MindmapPreview.h({ tag: "span", attrs: { class: "count" }, children: [count] }),
            ],
        });
    }
    /** トップバーとタブの帯を返す */
    function topbar({ title, tabs, current, theme, onNavigate, onSearch, onTheme, }) {
        const nextTheme = theme === "dark" ? "light" : "dark";
        const bar = MindmapPreview.h({
            tag: "header",
            attrs: { class: "topbar" },
            children: [
                MindmapPreview.h({
                    tag: "span",
                    attrs: { class: "brand" },
                    children: [
                        brandMark(),
                        MindmapPreview.h({ tag: "span", attrs: { class: "brand-name" }, children: ["mindstella"] }),
                    ],
                }),
                MindmapPreview.h({ tag: "span", attrs: { class: "brand-sub", title }, children: [title] }),
                MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "search-trigger",
                        type: "button",
                        "data-act": "search",
                        "aria-label": "すべての項目を検索",
                        onclick: () => onSearch(),
                    },
                    children: [
                        MindmapPreview.icon("search"),
                        MindmapPreview.h({ tag: "span", attrs: { class: "label" }, children: ["すべての項目を検索"] }),
                        MindmapPreview.h({ tag: "kbd", children: ["/"] }),
                    ],
                }),
                MindmapPreview.h({
                    tag: "button",
                    attrs: {
                        class: "top-btn",
                        type: "button",
                        "data-theme": nextTheme,
                        "aria-label": theme === "dark" ? "ライトに切り替え" : "ダークに切り替え",
                        onclick: () => onTheme(nextTheme),
                    },
                    children: [MindmapPreview.icon(theme === "dark" ? "sun" : "moon")],
                }),
            ],
        });
        const tabbar = MindmapPreview.h({
            tag: "nav",
            attrs: { class: "tabbar", "aria-label": "項目の種類" },
            children: [
                ...tabs.map((tab) => tabLink(tab, current, onNavigate)),
                MindmapPreview.h({ tag: "span", attrs: { class: "tab-gap" } }),
                tabLink({ key: "graph", label: "つながり", icon: "orbit" }, current, onNavigate, "tab-special"),
            ],
        });
        return MindmapPreview.h({ tag: "div", attrs: { class: "top" }, children: [bar, tabbar] });
    }
    MindmapPreview.topbar = topbar;
})(MindmapPreview || (MindmapPreview = {}));

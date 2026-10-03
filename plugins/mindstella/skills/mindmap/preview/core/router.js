"use strict";
// URL のハッシュの読み書きと履歴。画面・表示形式・開いている項目・全画面・絞り込みを、`URLSearchParams` の形で持つ。
var MindmapPreview;
(function (MindmapPreview) {
    /** タブの帯に並べる画面（つながりは帯の右端に別に置く） */
    MindmapPreview.TAB_KEYS = [
        "overview",
        "decisions",
        "tasks",
        "research",
        "docs",
        "terms",
        "notes",
        "logs",
    ];
    /** 画面ごとの既定の表示形式（書いていない画面は表） */
    MindmapPreview.DEFAULT_VIEW = {
        decisions: "map",
        tasks: "board",
        docs: "cards",
    };
    /** 画面が持つ表示形式（書いていない画面は表だけ） */
    MindmapPreview.VIEWS_OF = {
        decisions: ["map", "board", "table"],
        tasks: ["board", "table"],
        docs: ["cards", "board", "table"],
    };
    /** 画面の既定の表示形式 */
    function defaultView(tab) {
        return MindmapPreview.DEFAULT_VIEW[tab] ?? "table";
    }
    MindmapPreview.defaultView = defaultView;
    /** 画面が持つ表示形式 */
    function viewsOf(tab) {
        return MindmapPreview.VIEWS_OF[tab] ?? ["table"];
    }
    MindmapPreview.viewsOf = viewsOf;
    /** URL のハッシュを `Route` にする */
    function parseHash({ hash, index }) {
        const params = new URLSearchParams(hash.replace(/^#/, ""));
        const requestedTab = params.get("tab");
        const tab = ([...MindmapPreview.TAB_KEYS, "graph"].includes(requestedTab) ? requestedTab : "overview");
        const requestedView = params.get("view");
        const view = (viewsOf(tab).includes(requestedView) ? requestedView : defaultView(tab));
        // 記録に無い ID は開かない
        const requestedId = params.get("id");
        const id = requestedId !== null && index.byId.has(requestedId) ? requestedId : null;
        const filters = {};
        for (const [key, value] of params) {
            if (key.startsWith("f."))
                filters[key.slice(2)] = value.split("|");
        }
        return { tab, view, id, full: id !== null && params.get("full") === "1", filters };
    }
    MindmapPreview.parseHash = parseHash;
    /** `Route` を URL のハッシュにする（既定の値と絞り込みは書かない） */
    function toHash(route) {
        const params = new URLSearchParams();
        if (route.tab !== "overview")
            params.set("tab", route.tab);
        if (route.view !== defaultView(route.tab))
            params.set("view", route.view);
        if (route.id !== null)
            params.set("id", route.id);
        if (route.full)
            params.set("full", "1");
        const text = params.toString();
        return text === "" ? "" : `#${text}`;
    }
    MindmapPreview.toHash = toHash;
    /** ハッシュを書き換え、履歴に積むか置き換える。履歴の状態に、見てきた項目の並びを持てる */
    function navigate({ route, push, trail, }) {
        const url = `${location.pathname}${location.search}${toHash(route)}`;
        const state = trail ?? history.state;
        if (push)
            history.pushState(state, "", url);
        else
            history.replaceState(state, "", url);
    }
    MindmapPreview.navigate = navigate;
})(MindmapPreview || (MindmapPreview = {}));

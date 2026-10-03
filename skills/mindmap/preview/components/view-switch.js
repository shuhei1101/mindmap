"use strict";
// 表示形式の切り替え。形式ごとに同じ幅のボタンを並べ、選んでいる形式を押された見た目にする。
var MindmapPreview;
(function (MindmapPreview) {
    /** 表示形式 → ボタンのアイコン */
    const VIEW_ICON = {
        map: "map",
        board: "board",
        cards: "cards",
        table: "table",
    };
    /** 表示形式を切り替えるセグメントを返す（描き直しは使う側が行う） */
    function viewSwitch({ views, current, onChange }) {
        const buttons = views.map(({ key, label }) => MindmapPreview.h({
            tag: "button",
            attrs: {
                type: "button",
                "data-view": key,
                "aria-pressed": String(key === current),
                onclick: () => {
                    // 選んでいる形式を押しても何もしない
                    if (key !== current)
                        onChange(key);
                },
            },
            children: [MindmapPreview.icon(VIEW_ICON[key]), label],
        }));
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "segment", role: "group", "aria-label": "表示形式" },
            children: [...buttons],
        });
    }
    MindmapPreview.viewSwitch = viewSwitch;
})(MindmapPreview || (MindmapPreview = {}));

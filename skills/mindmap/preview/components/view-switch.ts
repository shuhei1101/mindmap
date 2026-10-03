// 表示形式の切り替え。形式ごとに同じ幅のボタンを並べ、選んでいる形式を押された見た目にする。

namespace MindmapPreview {
  /** 表示形式の切り替えの引数 */
  export type ViewSwitchProps = {
    /** 並べる表示形式。並びがボタンの並び */
    views: { key: View; label: string }[];
    /** 選んでいる表示形式 */
    current: View;
    /** 選んでいない形式のボタンを押したとき（クリック・Enter・Space） */
    onChange: (key: View) => void;
  };

  /** 表示形式 → ボタンのアイコン */
  const VIEW_ICON: Record<View, IconName> = {
    map: "map",
    board: "board",
    cards: "cards",
    table: "table",
  };

  /** 表示形式を切り替えるセグメントを返す（描き直しは使う側が行う） */
  export function viewSwitch({ views, current, onChange }: ViewSwitchProps): HTMLElement {
    const buttons = views.map(({ key, label }) =>
      h(
        "button",
        {
          type: "button",
          "data-view": key,
          "aria-pressed": String(key === current),
          onclick: () => {
            // 選んでいる形式を押しても何もしない
            if (key !== current) onChange(key);
          },
        },
        icon(VIEW_ICON[key]),
        label,
      ),
    );
    return h("div", { class: "segment", role: "group", "aria-label": "表示形式" }, ...buttons);
  }
}

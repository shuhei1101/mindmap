// 表のストーリー（部品設計『表』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn, userEvent, within } from "storybook/test";

/** ストーリーの表の行（検討事項の項目に近い形） */
type SampleRow = MindmapPreview.Row & { title: string; conf: string; status: string };

/** 確度の並び（並べ替え・絞り込みの値の順） */
const CONFIDENCE_ORDER = ["高", "中", "低"];

/** 表の列の定義 */
const columns: MindmapPreview.Column[] = [
  { key: "id", label: "ID", get: (row) => row.id, nowrap: true },
  { key: "title", label: "タイトル", fixed: true, get: (row) => (row as SampleRow).title },
  {
    key: "conf",
    label: "確度",
    filterable: true,
    order: CONFIDENCE_ORDER,
    get: (row) => (row as SampleRow).conf,
  },
  {
    key: "status",
    label: "状態",
    filterable: true,
    get: (row) => (row as SampleRow).status,
    cell: (row) => MindmapPreview.statusBadge((row as SampleRow).status),
  },
];

/** 表の行 */
const rows: SampleRow[] = [
  { id: "D-1", title: "プレビューの画面の分け方", conf: "高", status: "決定済み" },
  { id: "D-2", title: "つながりで扱う項目の数の上限", conf: "中", status: "未決定" },
  { id: "D-3", title: "資料の状態の値", conf: "高", status: "要見直し" },
  { id: "D-4", title: "デザインスタイルの選び方", conf: "低", status: "保留" },
];

const meta = {
  title: "Preview/Table",
  render: (args) => MindmapPreview.table(args),
  args: {
    kind: "decisions",
    columns,
    rows,
    on: {
      sort: fn(),
      filter: fn(),
      pin: fn(),
      columns: fn(),
      reset: fn(),
      open: fn(),
    },
  },
} satisfies Meta<MindmapPreview.TableProps>;

export default meta;

type Story = StoryObj<MindmapPreview.TableProps>;

/** 通常。並べ替えの印は見出しにホバーかフォーカスしたときだけ出す */
export const Default: Story = {};

/** タイトルで昇順。向きの矢印を出し、`aria-sort="ascending"` */
export const SortedAsc: Story = { args: { sort: { key: "title", dir: "asc" } } };

/** タイトルで降順。`aria-sort="descending"` */
export const SortedDesc: Story = { args: { sort: { key: "title", dir: "desc" } } };

/** 確度 = 高で絞り込み中。絞り込み中の列の道具は押された見た目で、表の上にチップとすべて解除を並べる */
export const Filtered: Story = { args: { filters: { conf: ["高"] } } };

/** ID の列までピン留め。押した列のボタンだけが押された見た目で、固定した列の境に影 */
export const Pinned: Story = { args: { pinTo: "id" } };

/** 長いタイトル。タイトルの列は折り返し、ほかの列は崩れない */
export const LongTitle: Story = {
  args: {
    rows: [
      {
        id: "D-5",
        title:
          "プレビューの画面を、記録の種類ごとにマップ・ボード・カード・表のどれで読み返せるようにするか、狭い幅ではどの列を畳むかを含めて決める",
        conf: "中",
        status: "未決定",
      },
      ...rows,
    ],
  },
};

/** 該当なし（ピン留め中）。表の場所に該当なしと次の操作を書き、横に送っても文言は表の枠の左に留める */
export const NoMatch: Story = { args: { filters: { conf: ["中"] }, pinTo: "id", rows: [rows[0]!] } };

/** 表示する列のポップオーバーを開いている。タイトルの列は外せない */
export const ColumnsPopover: Story = {
  play: async ({ canvasElement }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "表示する列" }));
  },
};

// 表示形式の切り替えのストーリー（部品設計『表示形式の切り替え』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

const meta = {
  title: "Preview/ViewSwitch",
  render: (args) => MindmapPreview.viewSwitch(args),
  args: { onChange: fn() },
} satisfies Meta<MindmapPreview.ViewSwitchProps>;

export default meta;

type Story = StoryObj<MindmapPreview.ViewSwitchProps>;

/** 検討事項（マップ・ボード・表）でマップを選んでいる */
export const Decisions: Story = {
  args: {
    views: [
      { key: "map", label: "マップ" },
      { key: "board", label: "ボード" },
      { key: "table", label: "表" },
    ],
    current: "map",
  },
};

/** タスク（ボード・表）で表を選んでいる。形式の数が違っても 1 つの幅と左端の位置が同じ */
export const Tasks: Story = {
  args: {
    views: [
      { key: "board", label: "ボード" },
      { key: "table", label: "表" },
    ],
    current: "table",
  },
};

/** 資料（カード・ボード・表）でカードを選んでいる */
export const Docs: Story = {
  args: {
    views: [
      { key: "cards", label: "カード" },
      { key: "board", label: "ボード" },
      { key: "table", label: "表" },
    ],
    current: "cards",
  },
};

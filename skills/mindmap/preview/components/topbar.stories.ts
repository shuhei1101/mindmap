// トップバーのストーリー（部品設計『トップバー』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

const meta = {
  title: "Preview/Topbar",
  // ダークのときは、画面全体の色の組も切り替える（アプリが `data-theme` に持つ値と同じ）
  render: (args) => {
    document.documentElement.dataset["theme"] = args.theme;
    return MindmapPreview.topbar(args);
  },
  args: {
    title: "要件出しのスキル mindmap を設計する",
    tabs: [
      { key: "overview", label: "概要", icon: "home" },
      { key: "decisions", label: "検討事項", icon: "decision", count: 12 },
      { key: "tasks", label: "タスク", icon: "task", count: 8 },
      { key: "research", label: "調査", icon: "research", count: 3 },
      { key: "docs", label: "資料", icon: "doc", count: 5 },
      { key: "terms", label: "用語集", icon: "term", count: 9 },
      { key: "notes", label: "メモ", icon: "note", count: 4 },
      { key: "logs", label: "会話ログ", icon: "log", count: 20 },
    ],
    current: "overview",
    theme: "light",
    onNavigate: fn(),
    onSearch: fn(),
    onTheme: fn(),
  },
} satisfies Meta<MindmapPreview.TopbarProps>;

export default meta;

type Story = StoryObj<MindmapPreview.TopbarProps>;

/** 概要を開いている。開いている画面のタブに印の色の下線 */
export const Overview: Story = { args: { current: "overview" } };

/** つながりを開いている。つながりの入口だけを選んだ見た目にする */
export const Graph: Story = { args: { current: "graph" } };

/** 題名が長い。1 行で末尾を省略し、検索の入口とテーマの切り替えを押し出さない */
export const LongTitle: Story = {
  args: {
    title:
      "プレビューの画面（概要・検討事項・タスク・資料・つながり・詳細パネル）を見本に沿って作るための話し合いの記録",
  },
};

/** ダーク */
export const Dark: Story = { args: { theme: "dark" } };

/** 幅 390px。検索の入口を虫眼鏡だけにし、題名を隠す。タブは帯の中で横に送る */
export const Narrow: Story = {
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

// 記録の索引・関係する項目・検索。次の候補・ゴールまで・進み具合は build が計算した `derived` を使い、画面で計算し直さない。

namespace MindmapPreview {
  /** 項目の種類（`mindmap-data` のキー） */
  export type Kind = "decisions" | "tasks" | "research" | "docs" | "terms" | "notes" | "logs";

  /** 項目の種類の並び（ID の頭の文字の順と同じ） */
  export const KIND_KEYS: readonly Kind[] = [
    "decisions",
    "tasks",
    "research",
    "docs",
    "terms",
    "notes",
    "logs",
  ];

  /** 種類 → 画面に出す名前 */
  export const KIND_LABEL: Record<Kind, string> = {
    decisions: "検討事項",
    tasks: "タスク",
    research: "調査",
    docs: "資料",
    terms: "用語集",
    notes: "メモ",
    logs: "会話ログ",
  };

  /** ID の頭の文字 → 種類 */
  const KIND_OF_PREFIX: Record<string, Kind> = {
    D: "decisions",
    T: "tasks",
    R: "research",
    A: "docs",
    G: "terms",
    N: "notes",
    L: "logs",
  };

  /** 検討事項の状態の並び（画面で状態を並べるときの順） */
  export const DECISION_STATUSES: readonly string[] = [
    "要見直し",
    "未決定",
    "保留",
    "未整理",
    "決定済み",
    "対象外",
    "取り下げ",
  ];

  /** タスクの状態の並び */
  export const TASK_STATUSES: readonly string[] = ["未着手", "進行中", "保留", "完了", "中止"];

  /** 資料の状態の並び */
  export const DOC_STATUSES: readonly string[] = ["下書き", "確認中", "完成"];

  /** 検討事項の案 */
  export type Option = {
    key: string;
    content: string;
    pros?: string;
    cons?: string;
    note?: string;
    adopted?: boolean;
    reason?: string;
  };

  /** 7 種類の項目が持つキーをまとめた型（種類ごとに持つキーだけが入る） */
  export type Item = {
    id: string;
    title: string;
    target?: string;
    category?: string;
    phase?: string;
    tags?: string[];
    related?: string[];
    links?: { title: string; url: string }[];
    created: string;
    updated: string;
    status?: string;
    lead?: string;
    answer?: string;
    options?: Option[];
    weight?: string;
    parent?: string;
    depends_on?: string[];
    reason?: string;
    body?: string;
    sources?: string[];
    kind?: string;
    for?: string[];
    result?: string;
    question?: string;
    conclusion?: string;
    confidence?: string;
    angles?: string[];
    deliverable?: boolean;
    meaning?: string;
    aliases?: string[];
    avoid?: string[];
    content?: string;
    date?: string;
  };

  /** 設定（`mindmap.yaml`） */
  export type Settings = {
    summary: string;
    field: string;
    target_label: string;
    phases: string[];
    targets: { name: string; summary: string }[];
    categories: { name: string; target: string; summary: string }[];
    goal: { phase: string; summary: string; deliverables: { title: string; doc?: string }[] };
  };

  /** フェーズごと・カテゴリーごとの、決着した数と全体の数 */
  export type ProgressCell = { phase: string; settled: number; total: number };

  /** build が計算して埋め込んだ、画面に出す値 */
  export type Derived = {
    next: { id: string; title: string; phase: string | null; weight: string | null; followers: number }[];
    goal: {
      reached: boolean;
      goal_phase: string;
      phases: string[];
      remaining_decisions: { id: string; title: string; phase: string; status: string }[];
      remaining_deliverables: { title: string; doc: string | null }[];
      phase_progress: ProgressCell[];
    };
    progress: { category: string; cells: ProgressCell[]; settled: number; total: number }[];
  };

  /** 埋め込みのデータ（`mindmap-data` を `JSON.parse` した値） */
  export type MindmapData = Record<Kind, Item[]> & {
    settings: Settings;
    bodies: Record<string, string>;
    derived: Derived;
    built_at: string;
  };

  /** 記録の索引 */
  export type RecordIndex = {
    /** 埋め込みのデータそのもの */
    data: MindmapData;
    /** ID → 種類と項目 */
    byId: Map<string, { kind: Kind; item: Item }>;
    /** ID → その項目を `depends_on`・`for`・`related`・`sources` で指す項目の ID（ID の順） */
    referencedBy: Map<string, string[]>;
    /** 着手できる検討事項の ID（`derived.next` の ID） */
    readyIds: Set<string>;
  };

  /** 項目が別の項目を指すキー */
  const REFERENCE_KEYS = ["depends_on", "for", "related", "sources"] as const;

  /** ID を種類の順 → 連番の順に比べる */
  export function compareIds(a: string, b: string): number {
    const rank = (id: string) => KIND_KEYS.indexOf(KIND_OF_PREFIX[id.slice(0, 1)] ?? "logs");
    return rank(a) - rank(b) || Number(a.slice(2)) - Number(b.slice(2));
  }

  /** 埋め込みのデータから記録の索引を作る */
  export function buildIndex(data: MindmapData): RecordIndex {
    const byId = new Map<string, { kind: Kind; item: Item }>();
    for (const kind of KIND_KEYS) {
      for (const item of data[kind]) byId.set(item.id, { kind, item });
    }
    // 各項目が指す先ごとに、指した側の ID を足す（記録に無い ID もそのまま持つ）
    const referencedBy = new Map<string, string[]>();
    for (const { item } of byId.values()) {
      for (const key of REFERENCE_KEYS) {
        for (const target of item[key] ?? []) {
          const sources = referencedBy.get(target) ?? [];
          sources.push(item.id);
          referencedBy.set(target, sources);
        }
      }
    }
    for (const sources of referencedBy.values()) sources.sort(compareIds);
    return {
      data,
      byId,
      referencedBy,
      readyIds: new Set(data.derived.next.map((candidate) => candidate.id)),
    };
  }

  /** 詳細パネルに出す関係する項目（それぞれ ID の並び） */
  export type RelatedItems = {
    prerequisites: string[];
    successors: string[];
    tasks: string[];
    logs: string[];
    related: string[];
    referencedBy: string[];
  };

  /** 前提・後続・関連タスク・経緯・関連・参照している項目を返す */
  export function relatedItems({ id, index }: { id: string; index: RecordIndex }): RelatedItems {
    const entry = index.byId.get(id);
    const item = entry?.item;
    const referrers = index.referencedBy.get(id) ?? [];
    /** ID の項目が、キーで id を指しているか */
    const points = (referrer: string, key: "depends_on" | "for" | "related"): boolean =>
      (index.byId.get(referrer)?.item[key] ?? []).includes(id);
    const kindOf = (referrer: string): Kind | undefined => index.byId.get(referrer)?.kind;

    const successors = referrers.filter((referrer) => points(referrer, "depends_on"));
    const tasks = referrers.filter(
      (referrer) => kindOf(referrer) === "tasks" && points(referrer, "for"),
    );
    // 経緯: この項目を更新した会話ログと、この項目が経緯として指す会話ログ
    const incomingLogs = referrers.filter(
      (referrer) => kindOf(referrer) === "logs" && points(referrer, "related"),
    );
    const logs = [...new Set([...incomingLogs, ...(item?.sources ?? [])])].sort(compareIds);
    const related = item?.related ?? [];
    const shown = new Set([...successors, ...tasks, ...logs, ...related]);
    return {
      prerequisites: item?.depends_on ?? [],
      successors,
      tasks,
      logs,
      related,
      referencedBy: referrers.filter((referrer) => !shown.has(referrer)),
    };
  }

  /** 全体の検索の 1 件 */
  export type SearchHit = { id: string; kind: Kind; title: string };

  /** 項目の ID・タイトル・文字の値・本文を 1 つの文字列にする（小文字） */
  function searchableText(item: Item, bodies: Record<string, string>): string {
    const parts: string[] = [];
    for (const value of Object.values(item)) {
      if (typeof value === "string") parts.push(value);
      else if (Array.isArray(value)) {
        for (const element of value) if (typeof element === "string") parts.push(element);
      }
    }
    parts.push(bodies[item.body ?? ""] ?? "");
    return parts.join("\n").toLowerCase();
  }

  /** 空白で区切った語を全て含む項目を返す（大文字・小文字を区別しない） */
  export function searchItems({ query, index }: { query: string; index: RecordIndex }): SearchHit[] {
    const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    // 言葉が空なら何も探さない
    if (terms.length === 0) return [];
    const hits: SearchHit[] = [];
    for (const kind of KIND_KEYS) {
      const items = [...index.data[kind]].sort((a, b) => compareIds(a.id, b.id));
      for (const item of items) {
        const text = searchableText(item, index.data.bodies);
        if (terms.every((term) => text.includes(term))) {
          hits.push({ id: item.id, kind, title: item.title });
        }
      }
    }
    return hits;
  }

  /** ID の項目のタイトル。記録に無いときは「（記録にありません）」 */
  export function titleOf(index: RecordIndex, id: string): string {
    return index.byId.get(id)?.item.title ?? "（記録にありません）";
  }
}

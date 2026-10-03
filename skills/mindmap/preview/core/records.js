"use strict";
// 記録の索引・関係する項目・検索。次の候補・ゴールまで・進み具合は build が計算した `derived` を使い、画面で計算し直さない。
var MindmapPreview;
(function (MindmapPreview) {
    /** 項目の種類の並び（ID の頭の文字の順と同じ） */
    MindmapPreview.KIND_KEYS = [
        "decisions",
        "tasks",
        "research",
        "docs",
        "terms",
        "notes",
        "logs",
    ];
    /** 種類 → 画面に出す名前 */
    MindmapPreview.KIND_LABEL = {
        decisions: "検討事項",
        tasks: "タスク",
        research: "調査",
        docs: "資料",
        terms: "用語集",
        notes: "メモ",
        logs: "会話ログ",
    };
    /** ID の頭の文字 → 種類 */
    const KIND_OF_PREFIX = {
        D: "decisions",
        T: "tasks",
        R: "research",
        A: "docs",
        G: "terms",
        N: "notes",
        L: "logs",
    };
    /** 検討事項の状態の並び（画面で状態を並べるときの順） */
    MindmapPreview.DECISION_STATUSES = [
        "要見直し",
        "未決定",
        "保留",
        "未整理",
        "決定済み",
        "対象外",
        "取り下げ",
    ];
    /** タスクの状態の並び */
    MindmapPreview.TASK_STATUSES = ["未着手", "進行中", "保留", "完了", "中止"];
    /** 資料の状態の並び */
    MindmapPreview.DOC_STATUSES = ["下書き", "確認中", "完成"];
    /** 項目が別の項目を指すキー */
    const REFERENCE_KEYS = ["depends_on", "for", "related", "sources"];
    /** ID を種類の順 → 連番の順に比べる */
    function compareIds(a, b) {
        const rank = (id) => MindmapPreview.KIND_KEYS.indexOf(KIND_OF_PREFIX[id.slice(0, 1)] ?? "logs");
        return rank(a) - rank(b) || Number(a.slice(2)) - Number(b.slice(2));
    }
    MindmapPreview.compareIds = compareIds;
    /** 埋め込みのデータから記録の索引を作る */
    function buildIndex(data) {
        const byId = new Map();
        for (const kind of MindmapPreview.KIND_KEYS) {
            for (const item of data[kind])
                byId.set(item.id, { kind, item });
        }
        // 各項目が指す先ごとに、指した側の ID を足す（記録に無い ID もそのまま持つ）
        const referencedBy = new Map();
        for (const { item } of byId.values()) {
            for (const key of REFERENCE_KEYS) {
                for (const target of item[key] ?? []) {
                    const sources = referencedBy.get(target) ?? [];
                    sources.push(item.id);
                    referencedBy.set(target, sources);
                }
            }
        }
        for (const sources of referencedBy.values())
            sources.sort(compareIds);
        return {
            data,
            byId,
            referencedBy,
            readyIds: new Set(data.derived.next.map((candidate) => candidate.id)),
        };
    }
    MindmapPreview.buildIndex = buildIndex;
    /** 前提・後続・関連タスク・経緯・関連・参照している項目を返す */
    function relatedItems({ id, index }) {
        const entry = index.byId.get(id);
        const item = entry?.item;
        const referrers = index.referencedBy.get(id) ?? [];
        /** ID の項目が、キーで id を指しているか */
        const points = (referrer, key) => (index.byId.get(referrer)?.item[key] ?? []).includes(id);
        const kindOf = (referrer) => index.byId.get(referrer)?.kind;
        const successors = referrers.filter((referrer) => points(referrer, "depends_on"));
        const tasks = referrers.filter((referrer) => kindOf(referrer) === "tasks" && points(referrer, "for"));
        // 経緯: この項目を更新した会話ログと、この項目が経緯として指す会話ログ
        const incomingLogs = referrers.filter((referrer) => kindOf(referrer) === "logs" && points(referrer, "related"));
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
    MindmapPreview.relatedItems = relatedItems;
    /** 項目の ID・タイトル・文字の値・本文を 1 つの文字列にする（小文字） */
    function searchableText(item, bodies) {
        const parts = [];
        for (const value of Object.values(item)) {
            if (typeof value === "string")
                parts.push(value);
            else if (Array.isArray(value)) {
                for (const element of value)
                    if (typeof element === "string")
                        parts.push(element);
            }
        }
        parts.push(bodies[item.body ?? ""] ?? "");
        return parts.join("\n").toLowerCase();
    }
    /** 空白で区切った語を全て含む項目を返す（大文字・小文字を区別しない） */
    function searchItems({ query, index }) {
        const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
        // 言葉が空なら何も探さない
        if (terms.length === 0)
            return [];
        const hits = [];
        for (const kind of MindmapPreview.KIND_KEYS) {
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
    MindmapPreview.searchItems = searchItems;
    /** ID の項目のタイトル。記録に無いときは「（記録にありません）」 */
    function titleOf(index, id) {
        return index.byId.get(id)?.item.title ?? "（記録にありません）";
    }
    MindmapPreview.titleOf = titleOf;
})(MindmapPreview || (MindmapPreview = {}));

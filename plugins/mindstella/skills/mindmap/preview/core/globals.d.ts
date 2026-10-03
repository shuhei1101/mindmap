// 描画のライブラリ（雛形が CDN から読むグローバル）の型。npm の同じ版の型を割り当てる。出力しない。

/** Markdown を HTML に描く marked */
declare const marked: typeof import("marked").marked;

/** HTML を無害化する DOMPurify */
declare const DOMPurify: typeof import("dompurify").default;

/** マップの配置を計算する ELK（`new ELK().layout(...)` で使う） */
declare const ELK: typeof import("elkjs").default;

/** 図を SVG に描く mermaid */
declare const mermaid: typeof import("mermaid").default;

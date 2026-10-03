# mermaid-bundled.txt の集め直し

`mermaid-bundled.txt` は、`mermaid.min.js` が中に束ねた依存の、名前・版・ライセンスの名前と LICENSE・NOTICE の写し。
配る書き出し（`export`）がライセンスの表示に入れる。
mermaid の版（`package.json` と `template.html` の `<script src>`）を上げたら、次の手順で集め直す。

## 手順

リポジトリの直下で `npm ci` を済ませ、次のスクリプトを `collect.mjs` として置いて `node collect.mjs` を流す（流した後は `collect.mjs` を消す）。

スクリプトは、`node_modules/mermaid` の `package.json` の `dependencies` を、依存の依存まで `node_modules` を辿って集める。
同じ名前でも版が違うものは別々に写し、`@types/` の型定義も含める。
各パッケージフォルダの `LICENSE`・`NOTICE`・`COPYING` の名前のファイルを、名前・版の順に並べて `mermaid-bundled.txt` に書く。

```javascript
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";

// node_modules を上へ辿って、パッケージのフォルダを探す
const find = (name, from) => {
  for (let dir = from; ; dir = dirname(dir)) {
    const found = join(dir, "node_modules", name);
    if (existsSync(join(found, "package.json"))) return found;
    if (dirname(dir) === dir) throw new Error(`見つかりません: ${name}（${from}）`);
  }
};

// mermaid の dependencies を再帰して、フォルダごとに 1 回ずつ集める
const folders = new Set();
const walk = (folder) => {
  const { dependencies = {} } = JSON.parse(readFileSync(join(folder, "package.json"), "utf8"));
  for (const name of Object.keys(dependencies)) {
    const child = find(name, folder);
    if (!folders.has(child)) {
      folders.add(child);
      walk(child);
    }
  }
};
walk(resolve("node_modules/mermaid"));

// 名前・版の順に、名前・版・ライセンスの名前と、LICENSE・NOTICE の写しを並べる
const blocks = [...folders]
  .map((folder) => ({ folder, ...JSON.parse(readFileSync(join(folder, "package.json"), "utf8")) }))
  .sort((a, b) => a.name.localeCompare(b.name) || a.version.localeCompare(b.version))
  .map(({ folder, name, version, license }) => {
    const files = readdirSync(folder)
      .filter((file) => /^(licen[cs]e|notice|copying)(\.(md|txt))?$|^licen[cs]e-/i.test(file))
      .sort();
    const texts = files.map((file) => readFileSync(join(folder, file), "utf8").trim());
    return [`${name} ${version}`, `License: ${license ?? "（package.json に無い）"}`, "", ...texts].join("\n");
  });
writeFileSync("plugins/mindstella/skills/mindmap/preview/licenses/mermaid-bundled.txt", `${blocks.join("\n\n")}\n`);
console.log(`${blocks.length} packages`);
```

集め直した後は、`mermaid-bundled.txt` が `</script`・`<script` を含まないことを確かめる（含むと `export` が書き出さない）。

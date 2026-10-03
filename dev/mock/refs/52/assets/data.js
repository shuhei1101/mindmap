// 見本のデータ: mindmap スキル自身の設計の話し合いを、スキルの YAML の形で持つ
window.MINDMAP = {
  "workspace": {
    "field": "システム開発",
    "summary": "要件出しのスキル mindmap を設計する",
    "target_label": "システム",
    "stages": [
      "目的",
      "要件",
      "構成",
      "インターフェース",
      "コンテンツ"
    ],
    "goal": {
      "stage": "インターフェース",
      "summary": "フォルダ構成・YAML のスキーマ・steps・コマンドが決まり、作り始められる",
      "deliverables": [
        { "title": "YAML のスキーマ" },
        { "title": "スクリプトのコマンドと引数" },
        { "title": "進め方ガイドの中身" },
        { "title": "プレビューの画面とデザイン方針" }
      ]
    },
    "targets": [
      {
        "name": "mindmap",
        "summary": "話し合いを記録しながら形にするスキル"
      },
      {
        "name": "プレビュー",
        "summary": "検討事項とタスクを 1 枚で見る HTML"
      }
    ],
    "categories": [
      {
        "name": "分け方",
        "target": "mindmap",
        "summary": "対象・カテゴリー・フェーズ・タグ"
      },
      {
        "name": "データ構造",
        "target": "mindmap",
        "summary": "YAML の種類・キー・スキーマ"
      },
      {
        "name": "進め方",
        "target": "mindmap",
        "summary": "steps と 進め方ガイド"
      },
      {
        "name": "聞き方",
        "target": "mindmap",
        "summary": "質問の書式とラウンド"
      },
      {
        "name": "調査",
        "target": "mindmap",
        "summary": "サブエージェントと調べ方"
      },
      {
        "name": "配布",
        "target": "mindmap",
        "summary": "名前・依存・README"
      },
      {
        "name": "画面",
        "target": "プレビュー",
        "summary": "画面一覧と画面遷移"
      },
      {
        "name": "デザイン",
        "target": "プレビュー",
        "summary": "スタイルとデザイン方針"
      }
    ]
  },
  "decisions": [
    {
      "id": "D-001",
      "title": "何のためのスキルか",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "大",
      "lead": "抽象と具体を行き来する会話に付き合い、検討事項を持ち続けて形にする。",
      "answer": "話し合いを記録しながら、ゴールまで検討事項を育てる",
      "tags": [
        "コンセプト"
      ],
      "depends_on": [],
      "related": [
        "D-020"
      ],
      "sources": [
        "L-001"
      ],
      "updated": "2026-10-02",
      "category": "配布",
      "stage": "目的"
    },
    {
      "id": "D-002",
      "title": "他のスキル・外部の仕組みに依存させるか",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "大",
      "lead": "職場でも使うため、単体で動くかを決める。",
      "answer": "依存させない。調べ方の中身は references に写す",
      "tags": [
        "依存"
      ],
      "options": [
        {
          "key": "A",
          "content": "依存させない（中身を写す）",
          "pros": "単体で配れる",
          "cons": "写した分の保守が要る",
          "adopted": true,
          "reason": "職場でも使うため"
        },
        {
          "key": "B",
          "content": "既存の調査のスキルを呼ぶ",
          "pros": "重複しない",
          "cons": "他のスキルの変更に引きずられる",
          "adopted": false,
          "reason": "配れなくなる"
        }
      ],
      "depends_on": [],
      "related": [],
      "sources": [
        "L-002"
      ],
      "updated": "2026-10-02",
      "category": "配布",
      "stage": "目的"
    },
    {
      "id": "D-003",
      "title": "スキルの名前",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "小",
      "lead": "入力はマインドマップのように自由に飛び、記録は木で持つ。",
      "answer": "mindmap",
      "tags": [
        "命名"
      ],
      "options": [
        {
          "key": "A",
          "content": "kabeuchi",
          "pros": "通じやすい",
          "cons": "記録と木の面が出ない",
          "adopted": false,
          "reason": "記録の面が伝わらない"
        },
        {
          "key": "B",
          "content": "bonsai",
          "pros": "剪定と育て続けるが比喩に収まる",
          "cons": "意味が一度で伝わらない",
          "adopted": false,
          "reason": "ユーザーの好みで外れた"
        },
        {
          "key": "C",
          "content": "whiteboard",
          "pros": "書いて消せる",
          "cons": "木の面が出ない",
          "adopted": false,
          "reason": "木の面が出ない"
        },
        {
          "key": "D",
          "content": "mindmap",
          "pros": "自由に話し、自由に引ける",
          "cons": "一般名詞で埋もれやすい",
          "adopted": true,
          "reason": "attrs で自由に引ける仕組みと合う"
        }
      ],
      "depends_on": [],
      "related": [
        "D-011"
      ],
      "sources": [
        "L-005",
        "L-006"
      ],
      "updated": "2026-10-02",
      "category": "配布",
      "stage": "目的"
    },
    {
      "id": "D-004",
      "title": "分け方の軸",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "大",
      "lead": "aituber と文章の工場のように、複数のシステムを同じ会話で話しても混ざらないようにする。",
      "answer": "対象 > カテゴリー > フェーズ、ジャンルはタグ",
      "tags": [
        "軸"
      ],
      "options": [
        {
          "key": "A",
          "content": "対象 > カテゴリー > フェーズ",
          "pros": "システムをまたいでも混ざらない",
          "cons": "軸が 1 つ増える",
          "adopted": true,
          "reason": "境界の検討事項の置き場所が決まる"
        },
        {
          "key": "B",
          "content": "対象はタグにする",
          "pros": "軸が少ない",
          "cons": "境界の検討事項があいまい",
          "adopted": false,
          "reason": "境界の検討事項の置き場所があいまい"
        }
      ],
      "depends_on": [
        "D-001"
      ],
      "related": [
        "G-001",
        "G-002",
        "G-003"
      ],
      "sources": [
        "L-003",
        "L-004"
      ],
      "updated": "2026-10-02",
      "category": "分け方",
      "stage": "要件"
    },
    {
      "id": "D-005",
      "title": "システム開発のフェーズの切り方",
      "target": "mindmap",
      "status": "要見直し",
      "weight": "大",
      "lead": "ゴールをセットアップで選べるようにしたため、インターフェースより深いフェーズ（モジュール構成）を任意で足せる形に直す。",
      "answer": "目的 / 要件 / 構成 / インターフェース / コンテンツ",
      "tags": [
        "フェーズ"
      ],
      "depends_on": [
        "D-004",
        "D-020"
      ],
      "related": [
        "D-006",
        "D-007"
      ],
      "sources": [
        "L-003"
      ],
      "body": "D-005",
      "updated": "2026-10-02",
      "category": "分け方",
      "stage": "構成"
    },
    {
      "id": "D-006",
      "title": "システムが扱う中身のフェーズの名前",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "小",
      "lead": "キャラの設定やプロンプトの文面など、システムが扱うデータそのもののフェーズ。",
      "answer": "コンテンツ",
      "tags": [
        "命名"
      ],
      "options": [
        {
          "key": "A",
          "content": "コンテンツ",
          "pros": "一番通じる",
          "adopted": true,
          "reason": "通じやすい"
        },
        {
          "key": "B",
          "content": "素材",
          "pros": "短い",
          "cons": "画像・音声に寄る",
          "adopted": false,
          "reason": "意味が狭い"
        },
        {
          "key": "C",
          "content": "カテゴリー",
          "cons": "カテゴリーの軸とぶつかる",
          "adopted": false,
          "reason": "軸の名前と同じになる"
        }
      ],
      "depends_on": [
        "D-005"
      ],
      "related": [],
      "sources": [
        "L-004"
      ],
      "updated": "2026-10-02",
      "category": "分け方",
      "stage": "構成"
    },
    {
      "id": "D-007",
      "title": "インターフェースの線引き",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "中",
      "lead": "実行中のシステムの境界を、外から入る・外へ出るものをインターフェースとする。",
      "answer": "実行時に読むファイルの形は IF、文面はコンテンツ、呼ぶ順は構成",
      "tags": [
        "IF"
      ],
      "depends_on": [
        "D-005"
      ],
      "related": [],
      "sources": [
        "L-005"
      ],
      "body": "D-007",
      "updated": "2026-10-02",
      "category": "分け方",
      "stage": "構成"
    },
    {
      "id": "D-008",
      "title": "タスクの重み",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "中",
      "lead": "「次は何を話す？」に答えるとき、派生が多いものから提案する。",
      "answer": "手で付ける影響度（大・中・小）＋ 自動で数える後続の件数",
      "tags": [
        "優先度"
      ],
      "options": [
        {
          "key": "A",
          "content": "影響度＋後続の件数",
          "pros": "予感と依存の両方を見られる",
          "cons": "影響度を付ける判断が要る",
          "adopted": true,
          "reason": "未整理も数に入れられる"
        },
        {
          "key": "B",
          "content": "依存から数えるだけ",
          "pros": "手間が無い",
          "cons": "未整理が数に入らない",
          "adopted": false,
          "reason": "予感を拾えない"
        },
        {
          "key": "C",
          "content": "1〜5 の点数",
          "pros": "細かい",
          "cons": "付け方がぶれる",
          "adopted": false,
          "reason": "ぶれる"
        }
      ],
      "depends_on": [
        "D-009"
      ],
      "related": [],
      "sources": [
        "L-003"
      ],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "要件"
    },
    {
      "id": "D-009",
      "title": "問いを検討事項が持つか",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "大",
      "lead": "問いを検討事項とタスクの両方に置くと、同じ問いが 2 か所にできてずれる。",
      "answer": "問いは検討事項が持ち、タスクは決めるための作業だけ",
      "tags": [
        "YAML"
      ],
      "options": [
        {
          "key": "A",
          "content": "検討事項が問いを持つ",
          "pros": "1 つの問いが 1 か所",
          "cons": "状態の種類が増える",
          "adopted": true,
          "reason": "ずれない"
        },
        {
          "key": "B",
          "content": "話すタスクを別に持つ",
          "pros": "検討事項が単純",
          "cons": "問いと結果がずれる",
          "adopted": false,
          "reason": "二重管理になる"
        }
      ],
      "depends_on": [
        "D-004"
      ],
      "related": [],
      "sources": [
        "L-006"
      ],
      "updated": "2026-10-02",
      "category": "データ構造",
      "stage": "構成"
    },
    {
      "id": "D-010",
      "title": "メタデータの置き場所",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "中",
      "lead": "Markdown を外へ持ち出せるようにする。",
      "answer": "ルートの YAML が正本、Markdown は本文だけ",
      "tags": [
        "YAML",
        "Markdown"
      ],
      "options": [
        {
          "key": "A",
          "content": "Markdown の先頭（frontmatter）",
          "pros": "1 ファイルで完結",
          "cons": "持ち出すと余計なメタデータが付く",
          "adopted": false,
          "reason": "持ち運びにくい"
        },
        {
          "key": "B",
          "content": "ルートの YAML",
          "pros": "Markdown をそのまま持ち出せる",
          "cons": "改名時に YAML も直す",
          "adopted": true,
          "reason": "ずれは check で見つける"
        }
      ],
      "depends_on": [
        "D-009"
      ],
      "related": [],
      "sources": [
        "L-004"
      ],
      "updated": "2026-10-02",
      "category": "データ構造",
      "stage": "構成"
    },
    {
      "id": "D-011",
      "title": "キーの固定と例外",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "中",
      "lead": "分野ごとの項目（費用・懸念など）を、スクリプトを足さずに持つ。",
      "answer": "固定のキー＋自由な attrs。属性名の一覧を出すコマンドで揺れを防ぐ",
      "tags": [
        "YAML"
      ],
      "depends_on": [
        "D-009"
      ],
      "related": [
        "D-003"
      ],
      "sources": [
        "L-005"
      ],
      "updated": "2026-10-02",
      "category": "データ構造",
      "stage": "インターフェース"
    },
    {
      "id": "D-012",
      "title": "related の持ち方",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "小",
      "lead": "ID の頭の文字で種類が決まる。",
      "answer": "ID の配列。外の URL は links",
      "tags": [
        "YAML"
      ],
      "depends_on": [
        "D-009"
      ],
      "related": [],
      "sources": [
        "L-007"
      ],
      "updated": "2026-10-02",
      "category": "データ構造",
      "stage": "インターフェース"
    },
    {
      "id": "D-013",
      "title": "調べた結果の置き場所",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "中",
      "lead": "調べた結果は、終われば消えるタスクとは違い、後から何度も引く知識。",
      "answer": "research.yaml を足す",
      "tags": [
        "YAML"
      ],
      "depends_on": [
        "D-009"
      ],
      "related": [],
      "sources": [
        "L-007"
      ],
      "updated": "2026-10-02",
      "category": "調査",
      "stage": "構成"
    },
    {
      "id": "D-014",
      "title": "YAML スキーマの検証",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "中",
      "lead": "書き込む前に突き合わせ、AI が何を入れるかの手がかりにもする。",
      "answer": "jsonschema で突き合わせる",
      "tags": [
        "YAML",
        "依存"
      ],
      "depends_on": [
        "D-011"
      ],
      "related": [],
      "sources": [
        "L-007"
      ],
      "updated": "2026-10-02",
      "category": "データ構造",
      "stage": "構成"
    },
    {
      "id": "D-015",
      "title": "サブエージェントの起動ルール",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "中",
      "lead": "サブエージェントはトークンを多く使う。",
      "answer": "何を・どの観点で・何体かを出して確認を取る。ユーザーが自分から頼んだときだけ省く",
      "tags": [
        "サブエージェント"
      ],
      "depends_on": [
        "D-013"
      ],
      "related": [],
      "sources": [
        "L-006"
      ],
      "updated": "2026-10-02",
      "category": "調査",
      "stage": "要件"
    },
    {
      "id": "D-016",
      "title": "質問の書式",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "中",
      "lead": "1 ラウンドにまとめて聞くときの、1 問の書き方。",
      "answer": "タイトル → 冒頭の文 → 選択肢があるときだけ案の表と推奨",
      "tags": [
        "書式"
      ],
      "depends_on": [],
      "related": [
        "R-001"
      ],
      "sources": [
        "L-006",
        "L-007"
      ],
      "body": "D-016",
      "updated": "2026-10-02",
      "category": "聞き方",
      "stage": "インターフェース"
    },
    {
      "id": "D-017",
      "title": "脱線した質問を残すか",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "小",
      "lead": "「○○って何？」と聞いたときに調べた内容。",
      "answer": "言葉は用語集、それ以外はメモ。タスクにはしない",
      "tags": [
        "脱線"
      ],
      "depends_on": [],
      "related": [
        "N-001"
      ],
      "sources": [
        "L-005"
      ],
      "updated": "2026-10-02",
      "category": "聞き方",
      "stage": "要件"
    },
    {
      "id": "D-018",
      "title": "ワークスペースの入口",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "小",
      "lead": "次に同じフォルダを開いたとき、何から読ませるか。",
      "answer": "CLAUDE.md は作らず、status を 1 回流して状況を出す",
      "tags": [
        "再開"
      ],
      "depends_on": [],
      "related": [
        "D-033"
      ],
      "sources": [
        "L-005"
      ],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "構成"
    },
    {
      "id": "D-019",
      "title": "steps の一覧",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "大",
      "lead": "場面ごとの手順を steps に分け、SKILL.md は薄くする。",
      "answer": "セットアップ / 取り込み / ヒアリング / リサーチ / 方針転換 / プレビュー / ゴール判定",
      "tags": [
        "steps"
      ],
      "depends_on": [
        "D-018"
      ],
      "related": [
        "A-001",
        "A-003"
      ],
      "sources": [
        "L-006"
      ],
      "body": "D-019",
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "構成"
    },
    {
      "id": "D-020",
      "title": "ゴールをセットアップで決める",
      "target": "mindmap",
      "status": "決定済み",
      "weight": "大",
      "lead": "人によって、インターフェースまでで十分か、モジュール構成まで決めたいかが違う。",
      "answer": "進め方ガイドにゴールの候補を持たせ、セットアップで選ぶ。途中で変えてよい",
      "tags": [
        "ゴール"
      ],
      "depends_on": [
        "D-001"
      ],
      "related": [
        "D-005"
      ],
      "sources": [
        "L-007"
      ],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "要件"
    },
    {
      "id": "D-021",
      "title": "Markdown のレンダリング",
      "target": "プレビュー",
      "status": "決定済み",
      "weight": "小",
      "lead": "プレビューの中で本文を読めるようにする。",
      "answer": "CDN の marked と DOMPurify。版を固定して integrity を付ける",
      "tags": [
        "CDN",
        "依存"
      ],
      "options": [
        {
          "key": "A",
          "content": "CDN から読む",
          "pros": "依存が増えない",
          "cons": "ネットが要る",
          "adopted": true,
          "reason": "ネットはつながる"
        },
        {
          "key": "B",
          "content": "Python で変換して埋め込む",
          "pros": "オフラインで見られる",
          "cons": "pip の依存が増える",
          "adopted": false,
          "reason": "要らない"
        }
      ],
      "depends_on": [],
      "related": [
        "N-001",
        "N-002"
      ],
      "sources": [
        "L-004",
        "L-005"
      ],
      "updated": "2026-10-02",
      "category": "画面",
      "stage": "構成"
    },
    {
      "id": "D-022",
      "title": "デザインスタイル",
      "target": "プレビュー",
      "status": "未決定",
      "weight": "中",
      "lead": "自分と職場の人が使う、読むための社内ツール。3 案の見本を見比べて決める。",
      "tags": [
        "スタイル"
      ],
      "options": [
        {
          "key": "A",
          "content": "モダン",
          "pros": "標準で馴染む",
          "cons": "個性が出にくい"
        },
        {
          "key": "B",
          "content": "開発者ツール",
          "pros": "ID・状態の多い表と相性が良い",
          "cons": "開発者以外には硬い"
        },
        {
          "key": "C",
          "content": "エディトリアル × モダン",
          "pros": "本文が読みやすい",
          "cons": "表の密度が下がる"
        }
      ],
      "depends_on": [],
      "related": [
        "T-001"
      ],
      "sources": [
        "L-007"
      ],
      "updated": "2026-10-02",
      "category": "デザイン",
      "stage": "構成"
    },
    {
      "id": "D-023",
      "title": "画面一覧と画面遷移",
      "target": "プレビュー",
      "status": "未決定",
      "weight": "中",
      "lead": "HTML 1 ファイルの中で、タブ・詳細パネル・入れ子の表を切り替える。",
      "tags": [
        "遷移"
      ],
      "depends_on": [
        "D-022"
      ],
      "related": [
        "T-002"
      ],
      "sources": [
        "L-007"
      ],
      "updated": "2026-10-02",
      "category": "画面",
      "stage": "構成"
    },
    {
      "id": "D-024",
      "title": "システム開発の進め方ガイドの中身",
      "target": "mindmap",
      "status": "未決定",
      "weight": "大",
      "lead": "フェーズごとの観点・必ず調べるもの・ゴールの候補・引き渡しの形。",
      "tags": [
        "進め方ガイド"
      ],
      "depends_on": [
        "D-005",
        "D-019"
      ],
      "related": [],
      "sources": [],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "コンテンツ"
    },
    {
      "id": "D-025",
      "title": "調査の進め方ガイドの中身",
      "target": "mindmap",
      "status": "未決定",
      "weight": "中",
      "lead": "問い・観点（ユースケース・費用・懸念）・事実・評価・結論の並び。",
      "tags": [
        "進め方ガイド"
      ],
      "depends_on": [
        "D-019"
      ],
      "related": [],
      "sources": [],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "コンテンツ"
    },
    {
      "id": "D-026",
      "title": "資料作り・壁打ちの進め方ガイド",
      "target": "mindmap",
      "status": "未整理",
      "weight": "小",
      "lead": "使うときに足す。壁打ちは既定のフェーズを変えられるようにする。",
      "tags": [
        "進め方ガイド"
      ],
      "depends_on": [],
      "related": [],
      "sources": [],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "コンテンツ"
    },
    {
      "id": "D-027",
      "title": "steps の本文",
      "target": "mindmap",
      "status": "未決定",
      "weight": "大",
      "lead": "各フェーズで何をどの順に行うか。grilling の出し方を含める。",
      "tags": [
        "steps"
      ],
      "depends_on": [
        "D-019",
        "D-016"
      ],
      "related": [
        "R-001"
      ],
      "sources": [],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "コンテンツ"
    },
    {
      "id": "D-028",
      "title": "スクリプトのコマンドと引数",
      "target": "mindmap",
      "status": "未決定",
      "weight": "中",
      "lead": "check-env・init・status・find・show・add・update・adopt・impact・next・attrs・check・preview。",
      "tags": [
        "CLI"
      ],
      "depends_on": [
        "D-011",
        "D-014"
      ],
      "related": [],
      "sources": [],
      "updated": "2026-10-02",
      "category": "データ構造",
      "stage": "インターフェース"
    },
    {
      "id": "D-029",
      "title": "会話ログの本文の書き方",
      "target": "mindmap",
      "status": "未決定",
      "weight": "小",
      "lead": "要約と、残しておきたいユーザーの言葉。",
      "tags": [
        "ログ"
      ],
      "depends_on": [
        "D-010"
      ],
      "related": [],
      "sources": [],
      "updated": "2026-10-02",
      "category": "聞き方",
      "stage": "コンテンツ"
    },
    {
      "id": "D-030",
      "title": "入れ子の展開を残すか",
      "target": "プレビュー",
      "status": "決定済み",
      "weight": "小",
      "lead": "使ってみてから判断する。",
      "tags": [
        "入れ子"
      ],
      "depends_on": [
        "T-002"
      ],
      "related": [],
      "sources": [
        "L-007"
      ],
      "updated": "2026-10-02",
      "category": "画面",
      "stage": "構成",
      "answer": "入れ子の展開はやめ、詳細パネルだけで案を見る"
    },
    {
      "id": "D-031",
      "title": "aituber/tmp をこの形に移すか",
      "target": "mindmap",
      "status": "未整理",
      "weight": "中",
      "lead": "散らかった会話ログと検討事項を、スキルの形に移すかどうか。",
      "tags": [
        "移行"
      ],
      "depends_on": [],
      "related": [
        "T-007"
      ],
      "sources": [
        "L-001"
      ],
      "updated": "2026-10-02",
      "category": "配布",
      "stage": "目的"
    },
    {
      "id": "D-032",
      "title": "画面の配色とトークン",
      "target": "プレビュー",
      "status": "保留",
      "weight": "小",
      "lead": "採用したスタイルから、色・文字・角丸・影の決まりを書く。",
      "tags": [
        "デザイン方針"
      ],
      "depends_on": [
        "D-022"
      ],
      "related": [],
      "sources": [],
      "updated": "2026-10-02",
      "category": "デザイン",
      "stage": "コンテンツ"
    },
    {
      "id": "D-033",
      "title": "ワークスペースに CLAUDE.md を置く",
      "target": "mindmap",
      "status": "取り下げ",
      "weight": "小",
      "lead": "入口として CLAUDE.md を自動で作る案。",
      "answer": "status のスクリプトで足りるため廃止",
      "tags": [
        "再開"
      ],
      "depends_on": [],
      "related": [
        "D-018"
      ],
      "sources": [
        "L-005"
      ],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "構成"
    },
    {
      "id": "D-034",
      "title": "1 回で終わる相談（晩ご飯など）",
      "target": "mindmap",
      "status": "対象外",
      "weight": "小",
      "lead": "何回もの会話にまたがるもの、枝分かれするものを対象にする。",
      "reason": "記録の手間が見合わない",
      "tags": [
        "汎用化"
      ],
      "depends_on": [],
      "related": [],
      "sources": [
        "L-003"
      ],
      "updated": "2026-10-02",
      "category": "配布",
      "stage": "目的"
    },
    {
      "id": "D-035",
      "title": "画面と YAML の呼び名",
      "target": "mindmap",
      "category": "分け方",
      "stage": "インターフェース",
      "status": "決定済み",
      "weight": "中",
      "lead": "辞書に無い和語の造語をやめ、既存の製品・方法論で通じる語にそろえる。",
      "answer": "検討事項・未整理・フェーズ・カテゴリー・進め方ガイド・影響度・後続の件数・確度・調査・タイトル",
      "tags": [
        "用語"
      ],
      "depends_on": [
        "D-004"
      ],
      "related": [
        "G-002",
        "G-003",
        "G-004"
      ],
      "sources": [
        "L-007"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "D-036",
      "title": "最上位の軸の呼び名",
      "target": "mindmap",
      "category": "分け方",
      "stage": "要件",
      "status": "未決定",
      "weight": "中",
      "lead": "システム開発以外の話し合いでも通じる呼び名にする。",
      "tags": [
        "用語"
      ],
      "depends_on": [
        "D-035"
      ],
      "related": [],
      "sources": [],
      "updated": "2026-10-02",
      "options": [
        {
          "key": "A",
          "content": "進め方ガイドごとに呼び名を決める（システム・調査対象・資料・テーマ）",
          "pros": "分野ごとに一番通じる語になる",
          "cons": "画面の列名が分野で変わる"
        },
        {
          "key": "B",
          "content": "プロジェクトで固定",
          "pros": "どの分野でも同じ",
          "cons": "システム開発では粒度がずれる"
        }
      ]
    }
  ],
  "tasks": [
    {
      "id": "T-001",
      "title": "デザインスタイルの見本を 3 案作る",
      "kind": "作業",
      "status": "進行中",
      "target": "プレビュー",
      "for": [
        "D-022"
      ],
      "depends_on": [],
      "tags": [
        "モック"
      ],
      "updated": "2026-10-02",
      "category": "デザイン",
      "stage": "構成"
    },
    {
      "id": "T-002",
      "title": "プレビューのモックを作る（モダン）",
      "kind": "作業",
      "status": "進行中",
      "target": "プレビュー",
      "for": [
        "D-023",
        "D-030"
      ],
      "depends_on": [],
      "tags": [
        "モック"
      ],
      "updated": "2026-10-02",
      "category": "画面",
      "stage": "構成"
    },
    {
      "id": "T-003",
      "title": "システム開発の観点を集める（arc42・BABOK）",
      "kind": "調査",
      "status": "未着手",
      "target": "mindmap",
      "for": [
        "D-024"
      ],
      "depends_on": [],
      "tags": [
        "観点"
      ],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "コンテンツ"
    },
    {
      "id": "T-004",
      "title": "調査の進め方のベストプラクティスを調べる",
      "kind": "調査",
      "status": "未着手",
      "target": "mindmap",
      "for": [
        "D-025"
      ],
      "depends_on": [],
      "tags": [
        "観点"
      ],
      "updated": "2026-10-02",
      "category": "進め方",
      "stage": "コンテンツ"
    },
    {
      "id": "T-005",
      "title": "grilling と wayfinder を references に写す",
      "kind": "作業",
      "status": "中止",
      "target": "mindmap",
      "for": [
        "D-027"
      ],
      "depends_on": [
        "D-019"
      ],
      "tags": [
        "references"
      ],
      "updated": "2026-10-02",
      "category": "聞き方",
      "stage": "コンテンツ"
    },
    {
      "id": "T-006",
      "title": "スマホ幅でモックを確かめる",
      "kind": "検証",
      "status": "未着手",
      "target": "プレビュー",
      "for": [
        "D-023"
      ],
      "depends_on": [
        "T-002"
      ],
      "tags": [
        "Playwright"
      ],
      "updated": "2026-10-02",
      "category": "画面",
      "stage": "構成"
    },
    {
      "id": "T-007",
      "title": "aituber/tmp を移す",
      "kind": "作業",
      "status": "保留",
      "target": "mindmap",
      "for": [],
      "depends_on": [
        "D-031"
      ],
      "reason": "スキルが完成してから",
      "tags": [
        "移行"
      ],
      "updated": "2026-10-02",
      "category": "配布",
      "stage": "目的"
    },
    {
      "id": "T-008",
      "title": "UI の規約と計画画面の作りを読む",
      "kind": "調査",
      "status": "完了",
      "target": "プレビュー",
      "for": [
        "D-022",
        "D-023"
      ],
      "depends_on": [],
      "result": "R-004",
      "tags": [
        "UI"
      ],
      "updated": "2026-10-02",
      "category": "デザイン",
      "stage": "構成"
    }
  ],
  "research": [
    {
      "id": "R-001",
      "title": "Grill Me 系のスキル",
      "question": "聞き取りを繰り返して計画を詰めるスキルは、どう作られているか",
      "conclusion": "検討事項を木で持ち、前提が揃った問いを 1 ラウンドでまとめて推奨つきで聞く",
      "confidence": "高",
      "angles": [
        "聞き方",
        "状態の持ち方",
        "終わり方"
      ],
      "target": "mindmap",
      "tags": [
        "grilling"
      ],
      "links": [
        {
          "title": "mattpocock/skills",
          "url": "https://github.com/mattpocock/skills/"
        }
      ],
      "body": "R-001",
      "updated": "2026-10-02",
      "category": "聞き方",
      "stage": "構成"
    },
    {
      "id": "R-002",
      "title": "決定記録の書式",
      "question": "検討した案と採否をどう残すのが定石か",
      "conclusion": "MADR は検討した案を必須にし、状態に superseded を持つ",
      "confidence": "高",
      "angles": [
        "案の残し方",
        "状態"
      ],
      "target": "mindmap",
      "tags": [
        "ADR"
      ],
      "links": [
        {
          "title": "About MADR",
          "url": "https://adr.github.io/madr/"
        }
      ],
      "updated": "2026-10-02",
      "category": "データ構造",
      "stage": "構成"
    },
    {
      "id": "R-003",
      "title": "要件の分類",
      "question": "要件のフェーズはどう分けるのが定石か",
      "conclusion": "BABOK は business / stakeholder / solution / transition の 4 つ",
      "confidence": "中",
      "angles": [
        "フェーズ"
      ],
      "target": "mindmap",
      "tags": [
        "BABOK",
        "arc42"
      ],
      "links": [
        {
          "title": "arc42",
          "url": "https://arc42.org/overview/"
        }
      ],
      "updated": "2026-10-02",
      "category": "分け方",
      "stage": "構成"
    },
    {
      "id": "R-004",
      "title": "UI の規約と計画画面の作り",
      "question": "表・タブ・詳細パネルの置き方の決まりは何か",
      "conclusion": "タブに件数、列の絞り込みはチップ、詳細は非モーダルのサイドパネル、開閉は 1 段まで",
      "confidence": "高",
      "angles": [
        "画面の分け方",
        "表",
        "見た目"
      ],
      "target": "プレビュー",
      "tags": [
        "UI"
      ],
      "links": [],
      "updated": "2026-10-02",
      "category": "デザイン",
      "stage": "構成"
    }
  ],
  "terms": [
    {
      "id": "G-001",
      "title": "対象",
      "meaning": "検討事項の持ち主になるもの。ロジックツリーの一番上の枝",
      "aliases": [
        "システム"
      ],
      "avoid": [],
      "tags": [
        "軸"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "G-002",
      "title": "カテゴリー",
      "meaning": "対象の中の話題のまとまり（機能や関心ごと）",
      "aliases": [
        "領域"
      ],
      "avoid": [
        "ドメイン",
        "エリア"
      ],
      "tags": [
        "軸"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "G-003",
      "title": "フェーズ",
      "meaning": "どの深さの話か。並びは分野の進め方ガイドが決める",
      "aliases": [
        "レイヤー"
      ],
      "avoid": [
        "層",
        "段階"
      ],
      "tags": [
        "軸"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "G-004",
      "title": "未整理",
      "meaning": "まだ問いの形にならない予感。問いにできたら未決定へ上げる",
      "aliases": [],
      "avoid": [
        "気がかり",
        "霧"
      ],
      "tags": [
        "状態"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "G-005",
      "title": "進め方ガイド",
      "meaning": "分野ごとの進め方の手引き（フェーズ・観点・ゴール・引き渡しの形）",
      "aliases": [
        "手引き"
      ],
      "avoid": [
        "playbook（画面には出さない）"
      ],
      "tags": [
        "構成"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "G-006",
      "title": "ワークスペース",
      "meaning": "1 つの話し合いのフォルダ",
      "aliases": [],
      "avoid": [],
      "tags": [
        "構成"
      ],
      "updated": "2026-10-02"
    }
  ],
  "notes": [
    {
      "id": "N-001",
      "title": "CDN とは",
      "content": "ライブラリのファイルを各地のサーバーから配る仕組み。ブラウザが取ってくるだけで、こちらから送るものは無い",
      "tags": [
        "脱線"
      ],
      "related": [
        "D-021"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "N-002",
      "title": "integrity とは",
      "content": "読み込むファイルのハッシュ。合わないファイルはブラウザが実行しない",
      "tags": [
        "脱線"
      ],
      "related": [
        "D-021"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "N-003",
      "title": "計画画面にある表の部品",
      "content": "検索・列の絞り込み・並べ替え・ピン留め・列の出し入れ・条件のチップ・保存した条件・詳細パネル",
      "tags": [
        "UI"
      ],
      "related": [
        "R-004"
      ],
      "updated": "2026-10-02"
    }
  ],
  "logs": [
    {
      "id": "L-001",
      "title": "やりたいことと aituber の散らかり",
      "date": "2026-10-02",
      "related": [
        "D-001",
        "D-031"
      ],
      "body": "L-001",
      "updated": "2026-10-02"
    },
    {
      "id": "L-002",
      "title": "Grill Me と設計の段",
      "date": "2026-10-02",
      "related": [
        "D-002",
        "R-001"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "L-003",
      "title": "対象・重み・汎用化",
      "date": "2026-10-02",
      "related": [
        "D-004",
        "D-008",
        "D-034"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "L-004",
      "title": "中身の名前・CDN・メタデータ",
      "date": "2026-10-02",
      "related": [
        "D-006",
        "D-010",
        "D-021"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "L-005",
      "title": "インターフェースの線引きと名前",
      "date": "2026-10-02",
      "related": [
        "D-007",
        "D-011",
        "D-018"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "L-006",
      "title": "steps とリサーチの決まり",
      "date": "2026-10-02",
      "related": [
        "D-015",
        "D-019"
      ],
      "updated": "2026-10-02"
    },
    {
      "id": "L-007",
      "title": "スキーマ・プレビュー・ゴール",
      "date": "2026-10-02",
      "related": [
        "D-012",
        "D-013",
        "D-020",
        "D-022"
      ],
      "updated": "2026-10-02"
    }
  ],
  "bodies": {
    "D-005": "システム開発のフェーズの並び。\n\n| フェーズ | 決めること |\n| --- | --- |\n| 目的 | 目的・成功の基準・制約・スコープ |\n| 要件 | できること（ユースケース）・品質の目標・運用 |\n| 構成 | サブシステム・外部システム・ライブラリ・データの置き場所・主な処理の流れ |\n| インターフェース | 入出力の情報と型・DB のスキーマ・設定のキー・MCP / API |\n| コンテンツ | システムが扱う中身そのもの（キャラの設定・プロンプトの文面・ノウハウ） |\n\nゴールに「モジュール構成まで」を選んだときは、インターフェースの後にモジュール構成のフェーズを足す。",
    "D-007": "実行中のシステムの境界を、外から入る・外へ出るものをインターフェースとする。\n\n| 例 | フェーズ |\n| --- | --- |\n| 外部 API・MCP・画面の入力・DB | インターフェース |\n| 実行時に読むファイルの形（項目・差し込む値） | インターフェース |\n| 同じファイルの文面 | コンテンツ |\n| LLM・外部をどの順で呼ぶか | 構成 |\n| サブシステムの中の手順・クラスの分け方 | 対象外（話題に出たら構成に `内部` タグで記録） |",
    "D-016": "1 問の書き方。\n\n```\n### Q{番号} {タイトル}\n\n{冒頭の文: 何を決めるか、なぜ今か}\n\n| 案 | 内容 | メリット | デメリット | 備考 |\n| --- | --- | --- | --- | --- |\n| A | ... | ... | ... | - |\n\n推奨: A\n\n{理由}\n```\n\n- 選択肢が無い論点は、案の表の代わりにたたき台を出して「直すところ」を聞く\n- 選択肢にするかどうかは Claude が決める",
    "D-019": "| ステップ | 概要 |\n| --- | --- |\n| セットアップ | 依存の確認、フォルダの指定、新規なら分野・フェーズ・対象・カテゴリー・ゴールを決める。既存なら status を流して続きを推奨する |\n| 取り込み | 発言を振り分けて記録し、派生の検討事項・未整理・タスクを積む。保留と解除もここ |\n| ヒアリング | 前提が揃った未決定を影響度の順に選び、1 ラウンドにまとめて聞く |\n| リサーチ | 確認を取ってサブエージェントを起動し、結果を調査に書く |\n| 方針転換 | 採用する案を切り替え、影響をたどって要見直しにする |\n| プレビュー | HTML を作って開く |\n| ゴール判定 | ゴールに届いていれば検討事項を見せて確定をもらい、書き出す |",
    "R-001": "## 分かったこと\n\n- grilling: 検討事項を木として持ち、前提が決まった問い（frontier）を 1 ラウンドでまとめて番号つき・推奨つきで聞く。事実は自分で調べ、決めることだけを聞く\n- wayfinder: 地図は索引で、1 つの決定は 1 か所にだけ置く。まだ問いにならないものは Not yet specified に置く\n- domain-modeling: 用語集を会話の中で育て、曖昧な言葉をその場で正す\n\n## 取り入れたもの\n\n- ラウンドの出し方 → ヒアリング\n- 未整理（Not yet specified）→ 検討事項の状態\n- 用語集 → terms.yaml",
    "L-001": "## 話したこと\n\n- 最初の案出しは、普通の会話の方が得意。抽象と具体を行き来するため\n- aituber の要件決めが散らかり、何を進めているか分からなくなった\n- 会話ログ・フェーズごとの置き場所・ジャンル分け・タスクの依存を持ちたい\n\n## 残しておきたい言葉\n\n> それ一つで一気にボンって最後まで全部話し切ったら、だいたい形が決まってる",
    "A-001": "ユーザーとの会話から、YAML の正本とプレビューまでの構成。\n\n```mermaid\nflowchart LR\n  U([ユーザー]) -->|発言| S[mindmap スキル]\n  S -->|steps を読む| P[steps/]\n  S -->|コマンド| C[scripts/]\n  C -->|読み書き| Y[(YAML の正本)]\n  C -->|書き出す| H[preview.html]\n  S -->|確認を取って起動| R[リサーチのサブエージェント]\n  R -->|結果| Y\n  H -->|見る| U\n```",
    "A-002": "```\n{ワークスペース}/\n  mindmap.yaml        設定（分野・フェーズ・対象とカテゴリー・ゴール）\n  decisions.yaml      検討事項\n  tasks.yaml          タスク\n  research.yaml       調査\n  docs.yaml           資料\n  terms.yaml          用語集\n  notes.yaml          メモ\n  logs.yaml           会話ログ\n  docs/               本文の Markdown\n  handoff/            ゴール判定で書き出す資料\n  preview.html        プレビュー\n```",
    "A-003": "```mermaid\nsequenceDiagram\n  actor U as ユーザー\n  participant S as mindmap\n  participant Y as YAML\n  U->>S: 発言\n  S->>Y: 近い検討事項を検索\n  S->>Y: 記録・派生の検討事項を追加\n  S->>U: 変わったところと次の問い\n```"
  },
  "docs": [
    {
      "id": "A-001",
      "deliverable": true,
      "title": "mindmap スキルの構成図",
      "status": "完成",
      "kind": "図",
      "target": "mindmap",
      "category": "進め方",
      "stage": "構成",
      "tags": [
        "構成図"
      ],
      "related": [
        "D-019",
        "D-009"
      ],
      "body": "A-001",
      "updated": "2026-10-02"
    },
    {
      "id": "A-002",
      "deliverable": true,
      "title": "ワークスペースのフォルダ構成",
      "status": "確認中",
      "kind": "文書",
      "target": "mindmap",
      "category": "データ構造",
      "stage": "構成",
      "tags": [
        "フォルダ"
      ],
      "related": [
        "D-010",
        "D-013"
      ],
      "body": "A-002",
      "updated": "2026-10-02"
    },
    {
      "id": "A-003",
      "title": "1 回の発言を取り込む流れ",
      "status": "下書き",
      "kind": "図",
      "target": "mindmap",
      "category": "進め方",
      "stage": "構成",
      "tags": [
        "フロー"
      ],
      "related": [
        "D-019",
        "D-008"
      ],
      "body": "A-003",
      "updated": "2026-10-02"
    }
  ]
};

// 資料のボードの見本のデータ: 21 の見本に、下書きの列に成果物とそれ以外が並ぶ資料と、長い題・タグの無い資料を足す
(() => {
  const M = window.MINDMAP;
  M.bodies["A-004"] = "メモ書きの本文";
  M.bodies["A-005"] = "## 目的\n\n検討事項から決まったことを、受け取る人へ渡す形にまとめる。\n\n| 節 | 中身 |\n| --- | --- |\n| 概要 | 何を作るか |\n| 決めたこと | 採用した案と理由 |";
  M.docs.push(
    {
      "id": "A-004",
      "title": "プレビューの資料の画面で、状態の列のボードに切り替えたときにカードへ出す項目と、列の中の並び順についての覚え書き",
      "status": "下書き",
      "kind": "メモ書き",
      "target": "mindmap",
      "category": "進め方",
      "stage": "構成",
      "related": ["D-019"],
      "body": "A-004",
      "updated": "2026-10-03"
    },
    {
      "id": "A-005",
      "deliverable": true,
      "title": "要件の仕様書",
      "status": "下書き",
      "kind": "仕様書",
      "target": "mindmap",
      "category": "データ構造",
      "stage": "要件",
      "tags": ["仕様", "受け渡し", "ゴール判定"],
      "related": ["D-010"],
      "body": "A-005",
      "updated": "2026-10-03"
    }
  );
})();

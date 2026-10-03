"use strict";
// つながり。全種類の項目を、関連（依存・関連・根拠・進めるタスク）でつないで 3D で描く。ライブラリを使わず、平たい円をキャンバスへ透視で描く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 項目が別の項目を指すキー → 線の種類 */
    const LINK_KEYS = [
        ["depends_on", "depends"],
        ["for", "for"],
        ["sources", "source"],
        ["related", "related"],
    ];
    /** 表示する種類の項目を玉に、関連を線にして返す（両端のどちらかが非表示か記録に無い線は含めない） */
    function buildGraph({ index, shownKinds, }) {
        const nodes = [];
        for (const [id, { kind }] of index.byId)
            if (shownKinds.has(kind))
                nodes.push({ id, kind });
        const shown = new Set(nodes.map((node) => node.id));
        const links = [];
        const seen = new Set();
        for (const { id: source } of nodes) {
            const item = index.byId.get(source)?.item;
            if (item === undefined)
                continue;
            for (const [key, type] of LINK_KEYS) {
                for (const target of item[key] ?? []) {
                    const identity = `${type}|${source}|${target}`;
                    // 自分自身へ・非表示や記録に無い項目へ・同じ線の重なりは作らない
                    if (source === target || !shown.has(target) || seen.has(identity))
                        continue;
                    seen.add(identity);
                    links.push({ source, target, type });
                }
            }
        }
        return { nodes, links };
    }
    MindmapPreview.buildGraph = buildGraph;
    /** 線の種類ごとの見た目（実線・点線・破線・一点鎖線） */
    const LINK_DASH = {
        depends: [],
        related: [1.5, 3],
        source: [6, 4],
        for: [10, 3, 2, 3],
    };
    /** 項目の種類 → 色のトークン */
    const KIND_COLOR_VAR = {
        decisions: "--k-dec",
        tasks: "--k-task",
        research: "--k-res",
        docs: "--k-doc",
        terms: "--k-term",
        notes: "--k-note",
        logs: "--k-log",
    };
    /** 文字の書体（太さつき）。倍率は描くときにかけるので、10px で持つ */
    const FONT_NORMAL = '400 10px "JetBrains Mono", "Noto Sans JP", monospace';
    const FONT_BOLD = '500 10px "JetBrains Mono", "Noto Sans JP", monospace';
    /** 玉の上の文字を画像に描くときの、元の大きさに対する倍率 */
    const LABEL_RESOLUTION = 4;
    /** 文字の画像の高さ（10px の文字に対する px） */
    const LABEL_HEIGHT = 14;
    /** 寄せる先: 乗せた玉との距離の 1 割だけ近づいたところ（残す割合） */
    const PULL_KEEP = 0.9;
    /** 毎コマ、目標へ寄せる割合 */
    const PULL_EASE = 0.03;
    /** 透視の基準の長さ */
    const FOCAL = 700;
    /** 操作が止まってから自動で回り始めるまでの時間（ms） */
    const IDLE_BEFORE_ROTATE_MS = 2500;
    /** 自動の回転の速さ（毎コマの角度） */
    const AUTO_ROTATE_STEP = 0.00018;
    /** 色をトークンから引く */
    function readColors() {
        const style = getComputedStyle(document.documentElement);
        const read = (name) => style.getPropertyValue(name).trim();
        return {
            kind: Object.fromEntries(Object.entries(KIND_COLOR_VAR).map(([kind, name]) => [kind, read(name)])),
            label: read("--g-label"),
            line: read("--g-line"),
            dot: read("--g-dot"),
            ring: read("--accent"),
        };
    }
    /** 玉を球面上に黄金角の螺旋で散らして置き、線の数から半径を決める */
    function placeBalls(index, graph) {
        const balls = graph.nodes.map((node, position, all) => {
            const t = (position + 0.5) / all.length;
            const phi = Math.acos(1 - 2 * t);
            const theta = Math.PI * (1 + Math.sqrt(5)) * position;
            const title = index.byId.get(node.id)?.item.title ?? node.id;
            const x = 120 * Math.sin(phi) * Math.cos(theta);
            const y = 120 * Math.cos(phi);
            const z = 120 * Math.sin(phi) * Math.sin(theta);
            return {
                ...node,
                x,
                y,
                z,
                title,
                label: title.length > 22 ? `${title.slice(0, 21)}…` : title,
                degree: 0,
                radius: 4,
                home: { x, y, z },
                fade: 1,
            };
        });
        const byId = new Map(balls.map((ball) => [ball.id, ball]));
        for (const link of graph.links) {
            const from = byId.get(link.source);
            const to = byId.get(link.target);
            if (from !== undefined)
                from.degree += 1;
            if (to !== undefined)
                to.degree += 1;
        }
        for (const ball of balls)
            ball.radius = 4 + Math.sqrt(ball.degree) * 2.2;
        return balls;
    }
    /** 互いに離れ、線でつながったものは引き合い、中心へ寄る力を、玉が落ち着くまで繰り返して位置を整える */
    function settle(balls, links) {
        // 玉が多いほど繰り返しを減らす（総当たりの計算が増えるため）
        const steps = Math.max(40, Math.min(260, Math.floor(120000 / Math.max(1, balls.length))));
        const velocity = new Map(balls.map((ball) => [ball.id, { x: 0, y: 0, z: 0 }]));
        let alpha = 1;
        for (let step = 0; step < steps; step += 1) {
            for (let i = 0; i < balls.length; i += 1) {
                for (let j = i + 1; j < balls.length; j += 1) {
                    const a = balls[i];
                    const b = balls[j];
                    const dx = a.x - b.x;
                    const dy = a.y - b.y;
                    const dz = a.z - b.z;
                    const force = (4400 / (dx * dx + dy * dy + dz * dz + 1)) * alpha;
                    const va = velocity.get(a.id);
                    const vb = velocity.get(b.id);
                    va.x += dx * force;
                    va.y += dy * force;
                    va.z += dz * force;
                    vb.x -= dx * force;
                    vb.y -= dy * force;
                    vb.z -= dz * force;
                }
            }
            for (const link of links) {
                const want = link.type === "depends" ? 84 : link.type === "related" ? 140 : 110;
                const dx = link.t.x - link.s.x;
                const dy = link.t.y - link.s.y;
                const dz = link.t.z - link.s.z;
                const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
                const pull = ((distance - want) / distance) * 0.03 * alpha;
                const vs = velocity.get(link.s.id);
                const vt = velocity.get(link.t.id);
                vs.x += dx * pull;
                vs.y += dy * pull;
                vs.z += dz * pull;
                vt.x -= dx * pull;
                vt.y -= dy * pull;
                vt.z -= dz * pull;
            }
            for (const ball of balls) {
                const v = velocity.get(ball.id);
                v.x -= ball.x * 0.012 * alpha;
                v.y -= ball.y * 0.012 * alpha;
                v.z -= ball.z * 0.012 * alpha;
                v.x *= 0.9;
                v.y *= 0.9;
                v.z *= 0.9;
                ball.x += v.x * 0.28;
                ball.y += v.y * 0.28;
                ball.z += v.z * 0.28;
            }
            alpha *= 0.994;
        }
        // 整えた位置を、注目が外れたときに戻る位置として覚える
        for (const ball of balls)
            ball.home = { x: ball.x, y: ball.y, z: ball.z };
    }
    /** 画面の外へ出る前に描き続ける余白を足した、画面の中か */
    function onScreen(x, y, width, height, margin) {
        return x > -margin && y > -margin && x < width + margin && y < height + margin;
    }
    /** 開いているつながりの画面（外から玉を選ぶ・色を変えるために覚える） */
    let live = null;
    /** 詳細パネルで開いた項目を、つながりの画面でも選んだ状態にする（画面を開いていなければ何もしない） */
    function selectGraphItem(id) {
        live?.select(id);
    }
    MindmapPreview.selectGraphItem = selectGraphItem;
    /** つながりの画面を返す。`selected` は最初に選んでおく項目 */
    function graphScreen({ index, on, selected = null, }) {
        // ===== 状態 =====
        const shownKinds = new Set(MindmapPreview.KIND_KEYS);
        const canvas = MindmapPreview.h({ tag: "canvas", attrs: { id: "graph-canvas", class: "g3-wrap", role: "img", "aria-label": "すべての項目のつながり" } });
        const kindToggles = MindmapPreview.h({ tag: "div", attrs: { class: "legend", role: "group", "aria-label": "表示する種類" } });
        // 表示する種類が 1 つも無いときに、枠の中央に出す文
        const emptyNotice = MindmapPreview.h({ tag: "p", attrs: { class: "empty map-empty", hidden: shownKinds.size > 0 }, children: ["表示する種類の項目はありません"] });
        const root = MindmapPreview.h({
            tag: "div",
            attrs: { class: "screen graph" },
            children: [
                MindmapPreview.h({ tag: "div", attrs: { class: "map-tools" }, children: [kindToggles] }),
                MindmapPreview.h({ tag: "div", attrs: { class: "map-frame space" }, children: [emptyNotice, canvas] }),
            ],
        });
        const labelCache = new Map();
        let colors = readColors();
        let balls = [];
        let ballById = new Map();
        let links = [];
        // 回転は「目標」と「今」を分け、今を目標へ毎コマ少しずつ寄せる（動き出しも止まり際もなめらかにする）
        const camera = {
            yaw: 0.6,
            pitch: -0.25,
            yawTarget: 0.6,
            pitchTarget: -0.25,
            yawSpeed: 0,
            pitchSpeed: 0,
            distance: 520,
            distanceTarget: 520,
            fit: 520,
            center: { x: 0, y: 0, z: 0 },
            centerTarget: { x: 0, y: 0, z: 0 },
        };
        let focus = selected;
        let hover = null;
        let current = selected;
        let lastInput = 0;
        let birth = performance.now();
        let projected = new Map();
        let width = 0;
        let height = 0;
        let dpr = 1;
        /** 玉・太さ・色ごとに、文字を 1 回だけ画像に描いて取っておく */
        const labelImage = (ball, bold, color) => {
            const key = `${ball.id}|${bold}|${color}`;
            const cached = labelCache.get(key);
            if (cached !== undefined)
                return cached;
            const font = (bold ? FONT_BOLD : FONT_NORMAL).replace("10px", `${10 * LABEL_RESOLUTION}px`);
            const image = document.createElement("canvas");
            const measure = image.getContext("2d");
            measure.font = font;
            measure.letterSpacing = `${0.8 * LABEL_RESOLUTION}px`;
            image.width = Math.ceil(measure.measureText(ball.label).width) + 4;
            image.height = LABEL_HEIGHT * LABEL_RESOLUTION;
            const context = image.getContext("2d");
            context.font = font;
            context.letterSpacing = `${0.8 * LABEL_RESOLUTION}px`;
            context.fillStyle = color;
            context.textAlign = "center";
            context.textBaseline = "bottom";
            context.fillText(ball.label, image.width / 2, image.height);
            labelCache.set(key, image);
            return image;
        };
        /** 玉と線を作り直す（表示する種類が変わったとき） */
        const rebuild = () => {
            emptyNotice.hidden = shownKinds.size > 0;
            const graph = buildGraph({ index, shownKinds });
            balls = placeBalls(index, graph);
            ballById = new Map(balls.map((ball) => [ball.id, ball]));
            links = graph.links.flatMap((link) => {
                const s = ballById.get(link.source);
                const t = ballById.get(link.target);
                return s === undefined || t === undefined ? [] : [{ s, t, type: link.type }];
            });
            settle(balls, links);
            // 全体が枠に収まる距離（外れた玉に引っぱられないよう、近い順に 9 割目の玉までの半径を使う）
            const radii = balls.map((ball) => Math.hypot(ball.x, ball.y, ball.z)).sort((a, b) => a - b);
            const reach = Math.max(40, radii[Math.floor(radii.length * 0.9)] ?? 40);
            const box = Math.max(1, Math.min(canvas.clientWidth || 600, canvas.clientHeight || 460));
            camera.fit = ((FOCAL * reach) / (box * 0.42) + reach * 0.4) * 0.72;
            camera.distance = camera.distanceTarget = camera.fit;
            camera.center = { x: 0, y: 0, z: 0 };
            camera.centerTarget = { x: 0, y: 0, z: 0 };
            birth = performance.now();
            select(current);
        };
        /** 項目の種類ごとの表示 / 非表示の切り替え（右端にまとめて切り替える箱） */
        const drawToggles = () => {
            kindToggles.replaceChildren(...MindmapPreview.KIND_KEYS.map((kind) => MindmapPreview.h({
                tag: "label",
                children: [
                    MindmapPreview.h({
                        tag: "input",
                        attrs: {
                            type: "checkbox",
                            value: kind,
                            "data-act": "gkind",
                            checked: shownKinds.has(kind),
                            "aria-label": MindmapPreview.KIND_LABEL[kind],
                            onchange: (event) => {
                                if (event.target.checked)
                                    shownKinds.add(kind);
                                else
                                    shownKinds.delete(kind);
                                drawToggles();
                                rebuild();
                            },
                        },
                    }),
                    MindmapPreview.h({ tag: "span", attrs: { class: "kdot", style: `background:var(${KIND_COLOR_VAR[kind]})` } }),
                    MindmapPreview.KIND_LABEL[kind],
                    MindmapPreview.h({ tag: "span", attrs: { class: "n" }, children: [index.data[kind].length] }),
                ],
            })), MindmapPreview.toggleAllBox({
                label: "すべての種類を表示",
                shown: shownKinds,
                all: [...MindmapPreview.KIND_KEYS],
                onChange: (next) => {
                    shownKinds.clear();
                    for (const kind of next)
                        shownKinds.add(kind);
                    drawToggles();
                    rebuild();
                },
            }));
        };
        /** 項目を選ぶ（その玉へゆっくり寄る）。選ぶのをやめたら、全体を見る位置へ戻す */
        const select = (id) => {
            current = id;
            const ball = id === null ? undefined : ballById.get(id);
            focus = ball?.id ?? hover;
            camera.distanceTarget = ball === undefined ? camera.fit : camera.fit * 0.38;
            if (ball === undefined)
                camera.centerTarget = { x: 0, y: 0, z: 0 };
        };
        // ===== 投影 =====
        /** 玉の位置を画面に透視で投影する */
        const project = (point) => {
            const cx = point.x - camera.center.x;
            const cy = point.y - camera.center.y;
            const cz = point.z - camera.center.z;
            const cosYaw = Math.cos(camera.yaw);
            const sinYaw = Math.sin(camera.yaw);
            const cosPitch = Math.cos(camera.pitch);
            const sinPitch = Math.sin(camera.pitch);
            const x1 = cx * cosYaw - cz * sinYaw;
            const z1 = cx * sinYaw + cz * cosYaw;
            const y1 = cy * cosPitch - z1 * sinPitch;
            const z2 = cy * sinPitch + z1 * cosPitch;
            const f = FOCAL / (z2 + camera.distance);
            return { sx: width / 2 + x1 * f, sy: height / 2 + y1 * f, f, z: z2 };
        };
        /** 画面のずれを、今の向きで世界の座標のずれに戻す */
        const screenToWorld = (dx, dy) => {
            const cosYaw = Math.cos(camera.yaw);
            const sinYaw = Math.sin(camera.yaw);
            const cosPitch = Math.cos(camera.pitch);
            const sinPitch = Math.sin(camera.pitch);
            const y = dy * cosPitch;
            const z1 = -dy * sinPitch;
            return { x: dx * cosYaw + z1 * sinYaw, y, z: -dx * sinYaw + z1 * cosYaw };
        };
        /** 全体が収まる距離で見たときの倍率（玉と文字の大きさの基準） */
        const baseScale = () => FOCAL / camera.fit;
        const radiusOf = (ball, scale) => ball.radius * 1.05 * (scale / baseScale());
        /** 画面の点にある、いちばん手前の玉 */
        const hitTest = (x, y) => {
            let best = null;
            let bestDepth = Number.POSITIVE_INFINITY;
            for (const ball of balls) {
                const p = projected.get(ball.id);
                if (p === undefined || p.z + camera.distance <= 10)
                    continue;
                const reach = Math.max(8, radiusOf(ball, p.f)) + 4;
                if (Math.hypot(p.sx - x, p.sy - y) < reach && p.z < bestDepth) {
                    best = ball;
                    bestDepth = p.z;
                }
            }
            return best;
        };
        // ===== 操作 =====
        let drag = null;
        let moved = 0;
        canvas.addEventListener("pointerdown", (event) => {
            drag = { x: event.clientX, y: event.clientY, time: performance.now() };
            moved = 0;
            canvas.setPointerCapture(event.pointerId);
            lastInput = performance.now();
            camera.yawSpeed = camera.pitchSpeed = 0;
        });
        canvas.addEventListener("pointermove", (event) => {
            const rect = canvas.getBoundingClientRect();
            if (drag !== null) {
                const dx = event.clientX - drag.x;
                const dy = event.clientY - drag.y;
                const now = performance.now();
                const dt = Math.max(8, now - drag.time);
                moved += Math.abs(dx) + Math.abs(dy);
                camera.yawTarget += dx * 0.0032;
                camera.pitchTarget = Math.max(-1.3, Math.min(1.3, camera.pitchTarget + dy * 0.0032));
                camera.yawSpeed = dx * 0.0032 * (16 / dt);
                camera.pitchSpeed = dy * 0.0032 * (16 / dt);
                drag = { x: event.clientX, y: event.clientY, time: now };
                lastInput = now;
                return;
            }
            const target = hitTest(event.clientX - rect.left, event.clientY - rect.top);
            const id = target?.id ?? null;
            if (id !== hover) {
                hover = id;
                if (current === null)
                    focus = id;
            }
            canvas.style.cursor = id === null ? "grab" : "pointer";
        });
        canvas.addEventListener("pointerleave", () => {
            if (drag === null && hover !== null) {
                hover = null;
                if (current === null)
                    focus = null;
            }
        });
        canvas.addEventListener("pointerup", (event) => {
            const rect = canvas.getBoundingClientRect();
            // ほとんど動かさずに離した: 玉を押した
            if (drag !== null && moved < 5) {
                const target = hitTest(event.clientX - rect.left, event.clientY - rect.top);
                if (target !== null) {
                    select(target.id);
                    on.open(target.id);
                }
            }
            // 止めてから離したときは滑らせない
            if (drag !== null && performance.now() - drag.time > 80)
                camera.yawSpeed = camera.pitchSpeed = 0;
            drag = null;
        });
        // ホイール: マウスのある位置へ向かって寄る・離れる（距離も中心も目標へなめらかに寄せる）
        canvas.addEventListener("wheel", (event) => {
            event.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const mx = event.clientX - rect.left - width / 2;
            const my = event.clientY - rect.top - height / 2;
            const old = camera.distanceTarget;
            const next = Math.max(camera.fit * 0.15, Math.min(camera.fit * 2.5, old * Math.exp(event.deltaY * 0.0016)));
            if (current === null) {
                const f = FOCAL / old;
                const shift = screenToWorld((mx / f) * (1 - next / old), (my / f) * (1 - next / old));
                camera.centerTarget = {
                    x: camera.centerTarget.x + shift.x,
                    y: camera.centerTarget.y + shift.y,
                    z: camera.centerTarget.z + shift.z,
                };
            }
            camera.distanceTarget = next;
            lastInput = performance.now();
            // 中心は群れの中に収め、全体まで離れたら戻す
            const limit = camera.fit * 0.35;
            const length = Math.hypot(camera.centerTarget.x, camera.centerTarget.y, camera.centerTarget.z);
            if (length > limit) {
                camera.centerTarget = {
                    x: (camera.centerTarget.x * limit) / length,
                    y: (camera.centerTarget.y * limit) / length,
                    z: (camera.centerTarget.z * limit) / length,
                };
            }
            if (next >= camera.fit * 0.95 && current === null)
                camera.centerTarget = { x: 0, y: 0, z: 0 };
        }, { passive: false });
        // 背景のダブルクリックで、全体を見る位置へ戻す
        canvas.addEventListener("dblclick", () => {
            if (current !== null)
                return;
            camera.centerTarget = { x: 0, y: 0, z: 0 };
            camera.distanceTarget = camera.fit;
        });
        // ===== 毎コマの描き =====
        const resize = () => {
            dpr = Math.min(2, window.devicePixelRatio || 1);
            width = canvas.clientWidth;
            height = canvas.clientHeight;
            canvas.width = width * dpr;
            canvas.height = height * dpr;
        };
        new ResizeObserver(resize).observe(canvas);
        const context = canvas.getContext("2d");
        /** 注目している玉につながる玉を、注目している玉の近くへゆっくり寄せる。注目が外れると元の位置へ戻す */
        const pullNear = () => {
            const focused = focus === null ? undefined : ballById.get(focus);
            const near = new Set();
            if (focused !== undefined) {
                for (const link of links) {
                    if (link.s.id === focused.id)
                        near.add(link.t.id);
                    if (link.t.id === focused.id)
                        near.add(link.s.id);
                }
            }
            for (const ball of balls) {
                const home = ball.home;
                const pivot = focused?.home;
                const goal = pivot !== undefined && near.has(ball.id)
                    ? {
                        x: pivot.x + (home.x - pivot.x) * PULL_KEEP,
                        y: pivot.y + (home.y - pivot.y) * PULL_KEEP,
                        z: pivot.z + (home.z - pivot.z) * PULL_KEEP,
                    }
                    : home;
                ball.x += (goal.x - ball.x) * PULL_EASE;
                ball.y += (goal.y - ball.y) * PULL_EASE;
                ball.z += (goal.z - ball.z) * PULL_EASE;
            }
        };
        const frame = (now) => {
            // 画面から外れたら止める
            if (!canvas.isConnected) {
                if (live !== null && live.select === select)
                    live = null;
                return;
            }
            requestAnimationFrame(frame);
            if (document.hidden || width === 0)
                return;
            pullNear();
            // 離した後の滑りと、何もしていないときのごくゆっくりした自動の回転
            if (drag === null) {
                camera.yawTarget += camera.yawSpeed;
                camera.pitchTarget = Math.max(-1.3, Math.min(1.3, camera.pitchTarget + camera.pitchSpeed));
                camera.yawSpeed *= 0.955;
                camera.pitchSpeed *= 0.93;
                if (now - lastInput > IDLE_BEFORE_ROTATE_MS && hover === null)
                    camera.yawTarget += AUTO_ROTATE_STEP;
            }
            camera.yaw += (camera.yawTarget - camera.yaw) * 0.07;
            camera.pitch += (camera.pitchTarget - camera.pitch) * 0.07;
            const selectedBall = current === null ? undefined : ballById.get(current);
            if (selectedBall !== undefined) {
                camera.centerTarget = { x: selectedBall.x, y: selectedBall.y, z: selectedBall.z };
            }
            camera.center.x += (camera.centerTarget.x - camera.center.x) * 0.025;
            camera.center.y += (camera.centerTarget.y - camera.center.y) * 0.025;
            camera.center.z += (camera.centerTarget.z - camera.center.z) * 0.025;
            camera.distance += (camera.distanceTarget - camera.distance) * 0.04;
            // 開いたときは中心から広がる
            const born = Math.min(1, (now - birth) / 1400);
            const ease = 1 - (1 - born) ** 3;
            const focused = focus !== null && ballById.has(focus) ? focus : null;
            const near = new Set(focused === null ? [] : [focused]);
            if (focused !== null) {
                for (const link of links) {
                    if (link.s.id === focused)
                        near.add(link.t.id);
                    if (link.t.id === focused)
                        near.add(link.s.id);
                }
            }
            const baseK = baseScale();
            context.setTransform(dpr, 0, 0, dpr, 0, 0);
            context.clearRect(0, 0, width, height);
            projected = new Map(balls.map((ball) => [
                ball.id,
                project({
                    x: ball.x * ease + camera.center.x * (1 - ease),
                    y: ball.y * ease + camera.center.y * (1 - ease),
                    z: ball.z * ease + camera.center.z * (1 - ease),
                }),
            ]));
            // つながる玉どうしを、ごく薄い線で結ぶ（遠いほど薄い）。画面の外の線は描かない
            context.lineWidth = 0.9;
            context.strokeStyle = colors.line;
            for (const link of links) {
                const a = projected.get(link.s.id);
                const b = projected.get(link.t.id);
                if (a === undefined || b === undefined)
                    continue;
                if (a.z + camera.distance <= 10 || b.z + camera.distance <= 10)
                    continue;
                if ((a.sx < 0 && b.sx < 0) || (a.sx > width && b.sx > width) || (a.sy < 0 && b.sy < 0) || (a.sy > height && b.sy > height))
                    continue;
                const depth = Math.max(0, Math.min(1, 1.25 - ((a.z + b.z) / 2 + camera.distance) / (camera.distance * 2.2)));
                context.setLineDash(LINK_DASH[link.type]);
                context.globalAlpha = 0.32 * depth * Math.min(link.s.fade, link.t.fade);
                context.beginPath();
                context.moveTo(a.sx, a.sy);
                context.lineTo(b.sx, b.sy);
                context.stroke();
            }
            // 注目している項目とつながる線と、そこを流れる小さな玉（注目している項目から外へ、ゆっくり）
            if (focused !== null) {
                const from = projected.get(focused);
                for (const link of links) {
                    if (link.s.id !== focused && link.t.id !== focused)
                        continue;
                    const to = projected.get(link.s.id === focused ? link.t.id : link.s.id);
                    if (from === undefined || to === undefined)
                        continue;
                    if (from.z + camera.distance <= 10 || to.z + camera.distance <= 10)
                        continue;
                    context.globalAlpha = 1;
                    context.strokeStyle = colors.line;
                    context.lineWidth = 1.3;
                    context.setLineDash(LINK_DASH[link.type]);
                    context.beginPath();
                    context.moveTo(from.sx, from.sy);
                    context.lineTo(to.sx, to.sy);
                    context.stroke();
                    context.setLineDash([]);
                    for (const offset of [0, 0.5]) {
                        const t = (now / 4200 + offset + (link.s.id.length % 7) * 0.13) % 1;
                        context.globalAlpha = 0.9 * Math.sin(Math.PI * t);
                        context.fillStyle = colors.dot;
                        context.beginPath();
                        context.arc(from.sx + (to.sx - from.sx) * t, from.sy + (to.sy - from.sy) * t, 1.8, 0, Math.PI * 2);
                        context.fill();
                    }
                }
            }
            context.setLineDash([]);
            // 奥から順に描く。遠いほど小さく薄く、注目しているときはつながらないものを沈める
            const order = [...balls].sort((a, b) => (projected.get(b.id)?.z ?? 0) - (projected.get(a.id)?.z ?? 0));
            for (const ball of order) {
                const p = projected.get(ball.id);
                if (p === undefined || p.z + camera.distance <= 10)
                    continue;
                const r0 = radiusOf(ball, p.f);
                // 画面の外の玉は描かない
                if (!onScreen(p.sx, p.sy, width, height, r0 + 40) || r0 > Math.max(width, height))
                    continue;
                const depth = Math.max(0.15, Math.min(1, 1.25 - (p.z + camera.distance) / (camera.distance * 2.2)));
                ball.fade += ((focused !== null && !near.has(ball.id) ? 0.18 : 1) - ball.fade) * 0.03;
                const radius = Math.max(1.2, r0 * ease);
                // 手前に来すぎた玉は薄くして、奥を隠さないようにする
                const close = Math.min(1, Math.max(0, ((p.z + camera.distance) / camera.distance - 0.08) / 0.2));
                if (close <= 0.02)
                    continue;
                context.globalAlpha = (0.35 + 0.55 * depth) * ball.fade * close;
                context.fillStyle = colors.kind[ball.kind];
                context.beginPath();
                context.arc(p.sx, p.sy, radius, 0, Math.PI * 2);
                context.fill();
                const marked = ball.id === current || ball.id === hover;
                if (marked) {
                    context.globalAlpha = 0.9;
                    context.strokeStyle = colors.ring;
                    context.lineWidth = 1.5;
                    context.beginPath();
                    context.arc(p.sx, p.sy, radius + 4, 0, Math.PI * 2);
                    context.stroke();
                }
                // 名前: 玉と同じ倍率で大きさが変わる（玉の幅に英字 6 文字ほど）。いつもは薄く、注目している項目とつながる項目ははっきり出す
                const strong = near.has(ball.id) || ball.id === hover;
                const scale = p.f / baseK;
                const fontSize = 4.6 * scale;
                const alpha = (strong ? 0.85 : 0.42 * ball.fade) * depth ** 1.4 * Math.max(0, Math.min(1, (fontSize - 3.5) / 2.5));
                if (alpha > 0.03 && ease > 0.9 && onScreen(p.sx, p.sy - radius, width, height, 400)) {
                    const color = ball.id === current ? colors.ring : colors.label;
                    // 毎コマ文字を作らず、画像に倍率をかけて置く
                    const image = labelImage(ball, marked, color);
                    const k = (dpr * fontSize) / 10 / LABEL_RESOLUTION;
                    context.globalAlpha = alpha * close;
                    context.setTransform(k, 0, 0, k, dpr * p.sx, dpr * (p.sy - radius - 3 * scale));
                    context.drawImage(image, -image.width / 2, -image.height);
                    context.setTransform(dpr, 0, 0, dpr, 0, 0);
                }
            }
            context.globalAlpha = 1;
        };
        // ===== 起動 =====
        drawToggles();
        // 文字の書体が読み込まれたら、取っておいた文字の画像を作り直す
        document.fonts?.addEventListener("loadingdone", () => labelCache.clear());
        // テーマが変わったら、色を読み直す
        const refreshColors = () => {
            colors = readColors();
            labelCache.clear();
        };
        new MutationObserver(refreshColors).observe(document.documentElement, {
            attributes: true,
            attributeFilter: ["data-theme"],
        });
        live = { select, refreshColors };
        // 枠の大きさが決まってから玉を置き、描き始める
        const start = new ResizeObserver(() => {
            if (canvas.clientWidth === 0)
                return;
            start.disconnect();
            resize();
            rebuild();
            requestAnimationFrame(frame);
        });
        start.observe(canvas);
        return root;
    }
    MindmapPreview.graphScreen = graphScreen;
})(MindmapPreview || (MindmapPreview = {}));

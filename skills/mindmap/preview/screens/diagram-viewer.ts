// 図の拡大。ホイールで拡大・縮小し、背景のドラッグで動かす。図の文字は選んでコピーできる（文字の上のドラッグは選択に任せる）。

namespace MindmapPreview {
  /** 図の拡大の引数 */
  export type DiagramViewerProps = {
    /** 描いた図 */
    svg: SVGElement;
    on: {
      /** 閉じる（開いた元の詳細パネルか詳細の全画面の本文に戻る） */
      close: () => void;
    };
  };

  /** 拡大率の範囲と、ボタン 1 回の倍率 */
  const SCALE_MIN = 0.2;
  const SCALE_MAX = 6;
  const BUTTON_FACTOR = 1.25;
  const WHEEL_FACTOR = 1.12;

  /** 開いたときに図の周りに空ける余白（px） */
  const FIT_MARGIN = 64;

  /** 開いたときの拡大率の上限 */
  const FIT_MAX_SCALE = 3;

  /** 図の拡大の中身（道具の行と、図を置く窓）を返す。モーダルか全画面の中に入れて使う */
  export function diagramViewer({ svg, on }: DiagramViewerProps): HTMLElement {
    const stage = h("div", { class: "v-stage" });
    const canvas = h("div", { class: "v-canvas" }, stage);
    const percent = h("span", { class: "v-pct mono" }, "100%");
    const view = { scale: 1, x: 0, y: 0 };
    /** 位置と拡大率を図に当てる */
    const apply = (): void => {
      stage.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.scale})`;
      percent.textContent = `${Math.round(view.scale * 100)}%`;
    };
    /** 窓の中心を保って拡大率を変える */
    const zoomAt = (factor: number, originX: number, originY: number): void => {
      const next = Math.max(SCALE_MIN, Math.min(SCALE_MAX, view.scale * factor));
      view.x = originX - (originX - view.x) * (next / view.scale);
      view.y = originY - (originY - view.y) * (next / view.scale);
      view.scale = next;
      apply();
    };
    const centerZoom = (factor: number): void => {
      const box = canvas.getBoundingClientRect();
      zoomAt(factor, box.width / 2, box.height / 2);
    };

    // 図の写しを置く（文字を選べるよう、写しの大きさは元の viewBox に合わせる）
    const copy = svg.cloneNode(true) as SVGElement;
    const viewBox = (svg as SVGSVGElement).viewBox.baseVal;
    copy.removeAttribute("style");
    copy.setAttribute("width", String(viewBox.width));
    copy.setAttribute("height", String(viewBox.height));
    stage.append(copy);

    canvas.addEventListener(
      "wheel",
      (event) => {
        event.preventDefault();
        const box = canvas.getBoundingClientRect();
        zoomAt(event.deltaY < 0 ? WHEEL_FACTOR : 1 / WHEEL_FACTOR, event.clientX - box.left, event.clientY - box.top);
      },
      { passive: false },
    );
    // 背景のドラッグで動かす（図の文字・ボタンの上は選択やクリックに任せる）
    let drag: { x: number; y: number } | null = null;
    canvas.addEventListener("pointerdown", (event) => {
      if ((event.target as Element).closest("button, text, foreignObject, .nodeLabel, .edgeLabel, .label")) return;
      event.preventDefault();
      drag = { x: event.clientX - view.x, y: event.clientY - view.y };
      canvas.classList.add("dragging");
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
      if (drag === null) return;
      view.x = event.clientX - drag.x;
      view.y = event.clientY - drag.y;
      apply();
    });
    const release = (): void => {
      drag = null;
      canvas.classList.remove("dragging");
    };
    canvas.addEventListener("pointerup", release);
    canvas.addEventListener("pointercancel", release);

    const root = h(
      "div",
      { class: "viewer-body" },
      h(
        "div",
        { class: "v-bar" },
        h("button", { class: "icon-btn", type: "button", "aria-label": "縮小", onclick: () => centerZoom(1 / BUTTON_FACTOR) }, "−"),
        percent,
        h("button", { class: "icon-btn", type: "button", "aria-label": "拡大", onclick: () => centerZoom(BUTTON_FACTOR) }, "＋"),
        h("span", { class: "spacer" }),
        h("button", { class: "btn ghost", type: "button", "data-act": "diagram-close", onclick: on.close }, icon("back"), "本文へ戻る"),
      ),
      canvas,
    );
    // 開いたときは、窓に収まる大きさで中央に置く（窓の大きさが決まってから）
    let placed = false;
    new ResizeObserver(() => {
      if (placed || canvas.clientWidth === 0) return;
      placed = true;
      const box = canvas.getBoundingClientRect();
      const size = copy.getBoundingClientRect();
      view.scale = Math.min(FIT_MAX_SCALE, (box.width - FIT_MARGIN) / size.width, (box.height - FIT_MARGIN) / size.height);
      view.x = (box.width - size.width * view.scale) / 2;
      view.y = (box.height - size.height * view.scale) / 2;
      apply();
    }).observe(canvas);
    apply();
    return root;
  }
}

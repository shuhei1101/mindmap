"""PoC の stream-json の出力から、成功条件の判定に使う欄を抜き出す。"""
import json
import sys
from pathlib import Path

MARKERS = ["SETUP-SKILL-MARKER-7341", "SESSION-SKILL-MARKER-5820", "SHARED-REFERENCE-MARKER-9157", "python_ok"]


def summarize(path: Path) -> dict:
    init = {}
    tools = []
    result = {}
    text = path.read_text()
    for line in text.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            init = ev
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    tools.append(c.get("name"))
        if ev.get("type") == "result":
            result = ev
    return {
        "case": path.stem,
        "mindmap_commands": sorted(c for c in init.get("slash_commands", []) if c.startswith("mindmap:")),
        "tool_uses": tools,
        "permission_denials": [d.get("tool_name") for d in result.get("permission_denials", [])],
        "markers": {m: (m in text) for m in MARKERS},
        "plugin_root_lines": sorted({l.strip() for l in text.replace("\\n", "\n").splitlines() if "PLUGIN_ROOT=" in l and "${" not in l}),
        "is_error": result.get("is_error"),
    }


for p in sorted(Path(sys.argv[1]).glob("*.jsonl")):
    print(json.dumps(summarize(p), ensure_ascii=False))

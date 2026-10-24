"""
ComfyUI 自定义节点：中文描述 -> 英文风格串

安装
-----
1. 把本文件复制到  ComfyUI/custom_nodes/
   （或建子目录  ComfyUI/custom_nodes/prompt_style_hint/ 并把本文件放进去）
2. 先启动服务（另开一个终端）：
      <项目根>/... <项目根>/... --port 8848
3. 重启 ComfyUI，在节点菜单里搜索 "中文 风格" 或 "Style Hint"

节点
----
* 中文风格提示 (Style Hint)      -> 输出可直接接 CLIPTextEncode 的英文风格串
* 中文提示词检索 (Prompt Search)  -> 输出检索到的完整英文提示词

依赖
----
零依赖。只用 Python 标准库 urllib，ComfyUI 环境不需要装任何东西。
"""

import json
import urllib.error
import urllib.request

SERVICE = "http://127.0.0.1:8848"


def _post(path, payload, timeout=10):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        SERVICE + path, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"连不上风格服务 {SERVICE}：{e}\n"
            f"请先启动： <项目根>/... <项目根>/... --port 8848"
        )
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"风格服务出错：{e}")


class StyleHint:
    """中文描述 -> 英文风格串（含导演名 + 风格标签）"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "中文描述": ("STRING", {"multiline": True,
                                       "default": "霓虹夜色，慢门，暧昧的感觉"}),
                "候选数": ("INT", {"default": 1, "min": 1, "max": 5, "step": 1}),
                "追加到": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("风格串", "调试信息")
    FUNCTION = "run"
    CATEGORY = "中文 风格"

    def run(self, 中文描述, 候选数, 追加到):
        res = _post("/style-hint", {"query": 中文描述, "topk": 候选数})
        items = res.get("results") or []
        if not items:
            return ("", "无结果")

        picks = [it["style_string"] for it in items[:候选数]]
        text = "，".join(picks) if len(picks) > 1 else picks[0]
        if 追加到 and 追加到.strip():
            text = text + ", " + 追加到.strip()

        dbg = "\n".join(
            f"{i+1}. {it['director']} / {it['director_zh']} "
            f"[{it['facet']}] score={it['score']}"
            for i, it in enumerate(items)
        )
        return (text, dbg)


class PromptSearch:
    """中文描述 -> 检索到的完整英文提示词"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "中文描述": ("STRING", {"multiline": True,
                                       "default": "一个杯子就让人紧张起来那种感觉"}),
                "候选数": ("INT", {"default": 1, "min": 1, "max": 5, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("提示词", "调试信息")
    FUNCTION = "run"
    CATEGORY = "中文 风格"

    def run(self, 中文描述, 候选数):
        res = _post("/search", {"query": 中文描述, "topk": 候选数})
        items = res.get("results") or []
        if not items:
            return ("", "无结果")

        text = items[0]["prompt"]
        if 候选数 > 1:
            text = "\n\n".join(f"[{i+1}] {it['prompt']}" for i, it in enumerate(items[:候选数]))

        dbg = "\n".join(
            f"{i+1}. {it['doc_id']} {it['director']} [{it['facet']}] score={it['score']}"
            for i, it in enumerate(items)
        )
        return (text, dbg)


NODE_CLASS_MAPPINGS = {
    "PromptStyleHint": StyleHint,
    "PromptSearch": PromptSearch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptStyleHint": "中文风格提示 (Style Hint)",
    "PromptSearch": "中文提示词检索 (Prompt Search)",
}

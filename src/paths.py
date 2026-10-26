"""
路径的唯一真相：从节点读默认值

为什么需要这个
--------------
`serve_style.py` / `smoke_test.py` / `gen_format_samples.py` /
`audit_prompt_fill.py` / `calibrate_floors.py` 各自写死了索引文件名。
节点换到 subjects_v12 / crafts_v6 / materials_v11 之后，它们还指着 v4/v3/v4。

后果不是报错，是**悄悄给出不同结果**——服务、冒烟、样例、审计四套东西，
和部署中的节点用的根本不是同一个库。这比崩掉更难发现。

所以：所有脚本都从这里取路径，一处改、处处跟上。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))

import local_style_hint as N  # noqa: E402

_R = N.LocalStyleHint.INPUT_TYPES()["required"]


def _d(key):
    return _R[key][1]["default"]


DEFAULTS = {
    "model": _d("模型目录"),
    "corpus": _d("语料文件"),
    "subjects": _d("题材文件"),
    "crafts": _d("工艺文件"),
    "materials": _d("材质文件"),
}

if __name__ == "__main__":
    for k, v in DEFAULTS.items():
        print(f"  {k:<10} {os.path.basename(v)}")

"""
修节拍匹配的三处

① 「抱着纸箱跑」命中了「拥抱」的节拍，输出成"手臂收紧、两个人的头靠近"——
   抱着东西和拥抱是两件事。改：拥抱只认 拥抱/相拥/抱住，不再认"抱着"；
   而且跑/走/奔这类位移动词优先于任何"持物"节拍。
② 空镜没有节拍，退回占位符。补一条：环境继续动，人不再出现。
③ 四镜风格不统一 —— 这是调用方式的问题，在生成脚本里用同一个风格名。
"""
import json
import os

ROOT = r"F:\llm"
BEAT = os.path.join(ROOT, "data", "raw", "beat_ref.json")

d = json.load(open(BEAT, encoding="utf-8"))

# ① 拥抱不再吃「抱着」
if "拥抱" in d:
    kw = [k for k in d["拥抱"]["kw"] if k != "抱着"]
    if "抱着" not in kw:
        d["拥抱"]["kw"] = kw

# ② 空镜节拍
if "空镜" not in d:
    d["空镜"] = {
        "kw": ["空镜", "人不入画", "只剩", "留白收"],
        "mid": "环境继续动：雨还在落，水还在流，有东西在轻微晃",
        "end": "画面停住，全程没有任何人进入画框",
    }

# ③ 位移优先：加一个优先级字段，匹配时长词的先赢
d["_priority"] = ["跑", "走", "打", "对峙", "空镜", "变", "看", "拿", "坐",
                  "开门", "等", "喊", "拥抱"]

json.dump(d, open(BEAT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("  拥抱 kw:", d["拥抱"]["kw"])
print("  空镜:", d["空镜"]["mid"][:24])
print("  优先级:", d["_priority"][:5], "...")

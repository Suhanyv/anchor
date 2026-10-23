"""
语言句式模板：**训练集和评测集必须严格不相交**

为什么单独成一个模块
--------------------
第一版三语评测犯了个错：eval_3lang 的日文评测句式 T_JA
和 build_ja_queries 的训练句式是**同一批**。
-> 那 93.1% 是「见过的句式」，不是「没见过的说法」。
和最早那次模板坍缩（119 条 query 两两余弦 0.9385）是同一类问题。

规则
----
- TRAIN_*：只用于生成训练 query
- EVAL_* ：只用于评测，**任何一条都不得出现在训练里**
- 模块末尾有自检：两组之间不能有重合字符串
"""

# ============================ 训练用（build_mlq.py 消费） ============================
TRAIN_ZH = [
    "{kw} 那种感觉",
    "{kw} 要怎么描述",
    "想找{kw}这种",
    "{kw} 的风格叫什么",
    "{kw} 的提示词怎么写",
    "给我点{kw}的灵感",
]

TRAIN_JA = [
    "{kw} な感じがほしい",
    "{kw} ってどう表現する",
    "{kw} っぽい雰囲気",
    "{kw} のスタイルは何て言う",
    "{kw} の映像を作りたい",
    "{kw} を英語でどう言う",
]

# ============================ 评测用（只用于 eval_3lang.py） ============================
# 刻意用不同的语气和句法，确保训练时没见过
EVAL_ZH = [
    "有没有{kw}的参考",
    "{kw}，越具体越好",
    "{kw} 对应的英文标签",
    "我要{kw}，给我关键词",
]

EVAL_JA = [
    "{kw} の参考はありますか",
    "{kw}、もっと具体的に",
    "{kw} に対応する英語のタグ",
    "{kw} がほしい、キーワードを",
]

# 英文那组用 style_tags 填，句式也隔离
EVAL_EN = [
    "any reference for {kw}",
    "{kw}, be more specific",
    "what is the english tag for {kw}",
    "I want {kw}, give me keywords",
]

# ============================ 韩语 ============================
TRAIN_KO = [
    "{kw} 느낌으로",
    "{kw} 어떻게 표현해?",
    "{kw} 분위기",
    "{kw} 스타일 뭐라고 해?",
    "{kw} 로 만들고 싶어",
    "{kw} 영어로 어떻게 말해?",
]

EVAL_KO = [
    "{kw} 참고 자료 있어?",
    "{kw} 더 구체적으로",
    "{kw} 에 해당하는 영어 태그",
    "{kw} 주세요, 키워드로",
]

# ============================ 德语 ============================
TRAIN_DE = [
    "{kw}, so eine Stimmung",
    "wie beschreibt man {kw}",
    "ich will {kw} als Stimmung",
    "wie heisst {kw} auf Englisch",
    "gib mir {kw} als Gefuehl",
    "{kw} im Bild",
]

EVAL_DE = [
    "gibt es Referenzen fuer {kw}",
    "{kw}, konkreter bitte",
    "welcher englische Tag steht fuer {kw}",
    "ich will {kw}, gib mir Stichwoerter",
]


def _check_no_overlap():
    """训练句式与评测句式不得有任何一条相同"""
    a = set(TRAIN_ZH) | set(TRAIN_JA) | set(TRAIN_KO) | set(TRAIN_DE)
    b = set(EVAL_ZH) | set(EVAL_JA) | set(EVAL_KO) | set(EVAL_DE)
    same = a & b
    assert not same, f"训练与评测句式重叠: {same}"
    # 还要检查「实质相同」：去掉 kw 占位符与标点后比较
    import re

    def norm(s):
        s = s.replace("{kw}", "")
        return re.sub(r"[\s，。、？！,.?!]", "", s)

    na = {norm(x) for x in a}
    nb = {norm(x) for x in b}
    assert not (na & nb), f"训练与评测句式规范化后重叠: {na & nb}"
    return len(a), len(b)


if __name__ == "__main__":
    nt, ne = _check_no_overlap()
    print(f"训练句式 {nt} 条 / 评测句式 {ne} 条，零重叠 ✅")
    print("\n训练 ZH:", TRAIN_ZH)
    print("训练 JA:", TRAIN_JA)
    print("\n评测 ZH:", EVAL_ZH)
    print("评测 JA:", EVAL_JA)
    print("\n### TEMPLATES_OK")

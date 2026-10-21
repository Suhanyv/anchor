"""
P0：人名别名归一化。

问题（v3 实测）：模型无法把中文音译名映射到英文原名
     "斯科塞斯"   -> "Martin Scorsese"   ❌  name 类 query Recall@10 仅 5%（低于随机）
     "深焦、仰拍" -> "deep focus"         ✅  style 类 38%

策略：追加而非替换
     "像斯科塞斯那样的画面" -> "像斯科塞斯(Martin Scorsese)那样的画面"
   保留原语义，只在旁边架桥。能用查表解决的不用训练解决。

覆盖：大陆译名 / 港台译名 / 繁体 / 简称
"""
import json
import os
import re

ROOT = r"F:\llm"
CORPUS = os.path.join(ROOT, "data", "raw", "prompt_director.jsonl")
QUERIES = os.path.join(ROOT, "data", "raw", "query_director.jsonl")
TABLE = os.path.join(ROOT, "data", "raw", "alias_table.json")
NORM_OUT = os.path.join(ROOT, "data", "raw", "query_director_norm.jsonl")

# 港台/繁体/简称等额外变体（键为语料里的英文名）
VARIANTS = {
    "Stanley Kubrick": ["寇比力克", "库柏力克", "史丹利库柏力克"],
    "Martin Scorsese": ["史柯西斯", "马丁史柯西斯", "史高西斯"],
    "Denis Villeneuve": ["维勒纳夫", "丹尼维勒纳夫", "丹尼斯维伦纽瓦"],
    "Christopher Nolan": ["诺蓝", "克里斯多福诺兰"],
    "Steven Spielberg": ["史蒂芬史匹柏", "斯皮尔柏格"],
    "Quentin Tarantino": ["昆丁塔伦提诺", "塔伦提诺", "昆汀塔伦蒂诺"],
    "David Lynch": ["林奇", "大卫林区", "林区"],
    "Wes Anderson": ["魏斯安德森", "安德森"],
    "Wong Kar-wai": ["王家衛", "墨镜王", "王墨镜"],
    "Akira Kurosawa": ["黑澤明", "黑泽明"],
    "Hayao Miyazaki": ["宮崎駿", "宫崎峻"],
    "Bong Joon-ho": ["奉俊昊", "奉俊浩"],
    "Park Chan-wook": ["朴贊郁", "朴赞旭"],
    "Alfred Hitchcock": ["希區考克", "希区考克", "希治阁"],
    "Orson Welles": ["奥森威尔斯", "奥逊威尔斯"],
    "Federico Fellini": ["费里尼", "费德里柯费里尼"],
    "Ingmar Bergman": ["英格玛柏格曼", "柏格曼", "伯格曼"],
    "Andrei Tarkovsky": ["塔可夫斯基", "塔尔科夫斯基", "塔科夫斯基"],
    "Jean-Luc Godard": ["高达", "高达尔", "戈达尔"],
    "Francois Truffaut": ["楚浮", "特吕福"],
    "Ridley Scott": ["雷利史考特", "雷德利史考特"],
    "David Fincher": ["大卫芬奇", "芬奇"],
    "James Cameron": ["詹姆斯柯麦隆", "卡麦隆"],
    "Tim Burton": ["提姆波顿"],
    "Pedro Almodovar": ["阿莫多瓦", "阿尔莫多瓦"],
    "Guillermo del Toro": ["戴托罗", "德尔托罗", "陀螺"],
    "Alejandro Gonzalez Inarritu": ["伊纳利图", "阿利安卓岗札雷伊纳利图"],
    "Alfonso Cuaron": ["卡隆", "阿方索库隆"],
    "Zhang Yimou": ["張藝謀"],
    "Chen Kaige": ["陳凱歌"],
    "Jia Zhangke": ["賈樟柯"],
    "Ang Lee": ["李安"],
    "Edward Yang": ["楊德昌"],
    "Hou Hsiao-hsien": ["侯孝賢"],
    "Tsai Ming-liang": ["蔡明亮"],
    "John Woo": ["吳宇森", "吴宇森"],
    "Tsui Hark": ["徐克", "徐文光"],
    "Stephen Chow": ["周星馳", "星爷"],
    "Hirokazu Kore-eda": ["是枝裕和"],
    "Makoto Shinkai": ["新海誠"],
    "Takeshi Kitano": ["北野武", "彼得武"],
    "Takashi Miike": ["三池崇史"],
    "Kim Ki-duk": ["金基德"],
    "Lee Chang-dong": ["李滄東", "李昌东"],
    "Satyajit Ray": ["萨雅吉雷", "萨蒂亚吉特雷伊"],
    "Abbas Kiarostami": ["基阿鲁斯塔米", "阿巴斯奇亚罗斯塔米"],
    "Werner Herzog": ["荷索", "韦纳荷索"],
    "Rainer Werner Fassbinder": ["法斯班德", "法斯宾德"],
    "Wim Wenders": ["文温德斯", "温德斯"],
    "Michael Haneke": ["汉内克", "麦可汉内克"],
    "Lars von Trier": ["拉斯冯提尔", "冯提尔"],
    "Krzysztof Kieslowski": ["奇士劳斯基", "基斯洛夫斯基"],
    "Fritz Lang": ["佛列兹朗", "弗里兹朗"],
    "F. W. Murnau": ["穆瑙", "茂瑙"],
    "Carl Theodor Dreyer": ["德莱叶", "德雷叶"],
    "Robert Bresson": ["布烈松", "布莱松"],
    "Jean Renoir": ["雷诺瓦", "尚雷诺"],
    "Agnes Varda": ["华达", "安妮华达"],
    "Jacques Tati": ["贾克大蒂", "塔蒂"],
    "Claire Denis": ["克莱尔德尼"],
    "Pedro Almodóvar": ["阿莫多瓦"],
    "Spike Lee": ["史派克李"],
    "Michael Mann": ["麦可曼恩"],
    "Sidney Lumet": ["薛尼卢梅"],
    "Brian De Palma": ["布莱恩狄帕玛", "狄帕玛"],
    "George Miller": ["乔治米勒"],
    "Terrence Malick": ["泰伦斯马力克", "马利克"],
    "Paul Thomas Anderson": ["保罗汤玛斯安德森", "PTA"],
    "Coen Brothers": ["柯恩兄弟", "高安兄弟"],
    "Sofia Coppola": ["苏菲亚柯波拉"],
    "Ari Aster": ["艾瑞艾斯特"],
    "Robert Eggers": ["罗伯艾格斯"],
    "Jordan Peele": ["乔丹皮尔"],
    "Greta Gerwig": ["葛莉塔洁薇"],
    "Darren Aronofsky": ["戴伦阿洛诺夫斯基"],
    "David Cronenberg": ["大卫柯能堡", "柯能堡"],
    "John Carpenter": ["约翰卡本特"],
    "Clint Eastwood": ["克林伊斯威特", "东木"],
    "Sam Peckinpah": ["佩金帕", "山姆毕京柏"],
    "Woody Allen": ["伍迪艾伦", "活地亚伦"],
    "Francis Ford Coppola": ["柯波拉", "法兰西斯柯波拉"],
    "Sergei Eisenstein": ["爱森斯坦", "艾森斯坦"],
    "Aleksandr Sokurov": ["苏古诺夫", "索库洛夫"],
    "Andrzej Wajda": ["华依达", "瓦伊达"],
    "Yorgos Lanthimos": ["尤格蓝西莫", "兰西莫"],
    "Luis Bunuel": ["布纽尔", "布努埃尔"],
    "Paolo Sorrentino": ["索伦提诺"],
    "Michael Haneke": ["汉内克"],
    "Thomas Vinterberg": ["凡提柏格"],
    "Ken Loach": ["肯洛区"],
    "Derek Jarman": ["德瑞克贾曼"],
    "Nicolas Roeg": ["尼可拉斯罗吉"],
    "Peter Greenaway": ["彼得格林纳威"],
    "Terry Gilliam": ["泰瑞吉兰", "吉列姆"],
    "Yasujiro Ozu": ["小津安二郎", "小津"],
    "Kenji Mizoguchi": ["溝口健二", "沟口健二"],
    "Masaki Kobayashi": ["小林正樹", "小林正树"],
    "Hideaki Anno": ["庵野秀明"],
    "Fernando Meirelles": ["梅瑞尔斯"],
    "Glauber Rocha": ["格劳贝尔罗沙"],
    "Walter Salles": ["华特萨勒斯"],
    "Carlos Reygadas": ["雷加达斯"],
    "Alejandro Jodorowsky": ["尤杜洛斯基", "佐杜洛斯基"],
    "Lucrecia Martel": ["露柯希亚马泰"],
    "Ousmane Sembene": ["塞姆班", "桑贝内"],
    "Djibril Diop Mambety": ["吉布里尔迪奥普曼贝蒂"],
    "Youssef Chahine": ["夏因", "约瑟夫夏欣"],
    "Nuri Bilge Ceylan": ["锡兰", "努瑞贝其锡兰"],
    "Asghar Farhadi": ["法哈蒂", "阿斯哈法哈蒂"],
    "Jafar Panahi": ["潘纳希", "帕纳希"],
    "Mohsen Makhmalbaf": ["马克马巴夫"],
    "Apichatpong Weerasethakul": ["阿比查邦", "阿彼察邦韦拉斯哈古"],
    "Michelangelo Antonioni": ["安东尼奥尼", "米开朗基罗安东尼奥尼"],
    "Pier Paolo Pasolini": ["帕索里尼", "巴索里尼"],
    "Luchino Visconti": ["维斯康提", "维斯康蒂"],
    "Vittorio De Sica": ["狄西嘉", "德西卡"],
    "Roberto Rossellini": ["罗塞里尼", "罗西里尼"],
    "Alain Resnais": ["雷奈", "雷乃"],
    "Eric Rohmer": ["侯麦", "侯默"],
    "Claude Chabrol": ["夏布洛"],
    "Jean-Pierre Melville": ["梅尔维尔", "尚皮耶梅尔维尔"],
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def build_table():
    corpus = load(CORPUS)
    pairs = {}
    for d in corpus:
        pairs[d["director"]] = d["director_zh"]

    table = {}
    for en, zh in pairs.items():
        names = {zh}
        # 去掉中点/间隔号的写法
        names.add(zh.replace("·", ""))
        names.add(zh.replace("·", " "))
        if zh.startswith(("大卫", "马丁", "史丹利")):
            names.add(zh[2:])
        for v in VARIANTS.get(en, []):
            names.add(v)
        names = {n.strip() for n in names if len(n.strip()) >= 2}
        table[en] = sorted(names, key=len, reverse=True)

    with open(TABLE, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=2)
    n_alias = sum(len(v) for v in table.values())
    print(f"alias table: {len(table)} directors, {n_alias} aliases -> {TABLE}")
    return table


def normalize(text, table):
    """找出所有命中的人名，非重叠、长名优先，在首次出现处追加英文名。"""
    cands = []
    for en, aliases in table.items():
        for a in aliases:
            for m in re.finditer(re.escape(a), text):
                cands.append((m.start(), m.end(), a, en))
    # 长名优先，再按位置
    cands.sort(key=lambda x: (-(x[1] - x[0]), x[0]))

    taken, chosen = [], []
    for s, e, a, en in cands:
        if any(not (e <= ts or s >= te) for ts, te in taken):
            continue
        taken.append((s, e))
        chosen.append((s, e, en))

    if not chosen:
        return text, []

    chosen.sort()
    out, cur = [], 0
    for s, e, en in chosen:
        out.append(text[cur:s])
        out.append(text[s:e])
        # 若后面紧跟括号就不重复追加
        if not text[e:e + 1] == "(":
            out.append(f"({en})")
        cur = e
    out.append(text[cur:])
    return "".join(out), sorted({en for _, _, en in chosen})


def main():
    table = build_table()
    queries = load(QUERIES)
    out, hit, miss = [], 0, []
    for q in queries:
        new, matched = normalize(q["query"], table)
        if matched:
            hit += 1
        elif q["query_kind"] == "name":
            miss.append(q["query"])
        r = dict(q)
        r["query_orig"] = q["query"]
        r["query"] = new
        r["alias_matched"] = matched
        out.append(r)

    with open(NORM_OUT, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"normalized queries -> {NORM_OUT}")
    print(f"命中别名的 query: {hit}/{len(queries)} ({hit/len(queries):.1%})")
    if miss:
        print(f"name 类仍未命中 {len(miss)} 条，例: {miss[:3]}")
    print("\n样例：")
    shown = 0
    for r in out:
        if r["alias_matched"] and shown < 6:
            print(f"  [{r['query_kind']:<5}] {r['query_orig']}")
            print(f"        -> {r['query']}")
            shown += 1
    print("\n### ALIAS_DONE")


if __name__ == "__main__":
    main()

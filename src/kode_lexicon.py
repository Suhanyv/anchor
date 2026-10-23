"""
中 → 韩 / 德 风格词对照表（第一批：高频词 + 东方影像，约 110 个）

为什么先做这批
-------------
corpus_v14 有 401 个风格关键词，但频次分布很不均：
约 95 个词出现 ≥6 次（覆盖大多数导演的 base 面），其余多为长尾。
先用高频批训练一版，测量收益，再决定要不要补全 401 —— 避免又白做一轮。

与日语的差别
------------
日语那次是「先测后补」：49.1% -> 89.7%。这次已有基线（韩 40% / 德 50%），
补完后同样用 eval_kode.py 测量，可直接与基线对比。

翻译原则（同 ja_lexicon）
------------------------
1. 用目标语言使用者真的会打的词，不用词典直译
2. 性格/气质词译成形容表达（克制 -> zurückhaltend / 절제된）
3. 意境词保留意象（苍茫 / 空旷 -> leer / 텅 빈）
"""

KO = {
    # ---- 构图 / 摄影 ----
    "对称": "대칭", "几何": "기하학적", "长镜": "롱테이크", "长镜头": "롱테이크",
    "深焦": "딥 포커스", "高对比": "고대비", "精准构图": "정확한 구도",
    "手持": "핸드헬드", "窥视": "훔쳐보기", "剪影": "실루엣", "镜像": "거울상",
    "横向": "가로", "极简": "미니멀", "留白": "여백", "一角": "한쪽 모서리",
    "半边": "반쪽", "贴着边角": "가장자리에 붙은", "元素极少": "요소 극소",
    "公路": "도로", "街景": "거리 풍경",
    # ---- 光 ----
    "自然光": "자연광", "日光": "햇빛", "烛光": "촛불", "暖光": "따뜻한 빛",
    "冷光": "차가운 빛", "逆光": "역광", "烈日": "뙤약볕",
    # ---- 色彩 ----
    "黑白": "흑백", "黑白新写实": "흑백 네오리얼리즘", "红绿": "빨강과 초록",
    "大红": "진홍", "冷蓝": "차가운 파랑", "冷灰": "차가운 회색", "冷峻": "냉철한",
    "高饱和": "고채도", "哑色": "무딘 색", "金调": "금빛 톤", "秋色": "가을색",
    "灰绿": "회록", "暖金": "따뜻한 금색",
    # ---- 风格 / 流派 ----
    "巴洛克": "바로크", "表现主义": "표현주의", "纪实": "다큐멘터리",
    "写实": "사실적", "超现实": "초현실", "荒诞": "부조리", "拼贴": "콜라주",
    "碎片": "파편", "现代性": "현대성", "象征": "상징", "寓言": "우화",
    "情节剧": "멜로드라마", "造作": "인위적", "粗粝": "거친", "考究": "정교한",
    # ---- 情绪 ----
    "克制": "절제된", "冷面": "무표정", "诡异": "기이한", "静默": "정적",
    "空旷": "텅 빈", "孤独": "고독", "疏离": "소외", "衰败": "쇠락",
    "黄昏": "황혼", "平凡": "평범", "破碎": "부서진", "末世": "종말",
    "宏大": "웅장한", "巨构": "거대 구조", "朴素": "소박한", "抒情": "서정적",
    "仪式": "의식", "梦境": "꿈속", "灵性": "영성", "人文": "휴머니즘",
    "感官": "관능적", "沉思": "명상", "历史感": "역사감", "家庭": "가족",
    "日常": "일상", "自然": "자연", "雨夜": "비 오는 밤", "尘土": "먼지",
    "冷峻村庄": "차가운 마을", "战后废墟": "전후 폐허", "中产": "중산층",
    "废墟": "폐허", "雨": "비", "雾": "안개", "水": "물", "群像": "군상",
    # ---- 东方影像 ----
    "水墨": "수묵", "青绿": "청록", "矿物色": "광물 안료", "金线": "금실",
    "雾江": "안개 강", "孤舟": "외로운 배", "远山": "먼 산", "年画": "연화",
    "木版": "목판", "民俗": "민속", "皮影": "그림자극", "透光": "빛이 새어듦",
    "笔触": "붓터치", "山雾": "산안개", "飘": "나부끼는", "院体": "원체화",
    "工细": "정밀", "绢本": "견본", "工笔": "공필", "重彩": "중채",
    "白描": "백묘", "手卷": "두루마리", "长卷": "긴 두루마리",
}

DE = {
    # ---- 构图 / 摄影 ----
    "对称": "Symmetrie", "几何": "geometrisch", "长镜": "lange Einstellung",
    "长镜头": "lange Einstellung", "深焦": "Tiefenschärfe",
    "高对比": "hoher Kontrast", "精准构图": "präzise Komposition",
    "手持": "Handkamera", "窥视": "heimliches Beobachten",
    "剪影": "Silhouette", "镜像": "Spiegelbild", "横向": "Querformat",
    "极简": "minimalistisch", "留白": "Leerraum", "一角": "eine Ecke",
    "半边": "eine Hälfte", "贴着边角": "am Bildrand", "元素极少": "minimale Elemente",
    "公路": "Landstraße", "街景": "Straßenszene",
    # ---- 光 ----
    "自然光": "natürliches Licht", "日光": "Tageslicht", "烛光": "Kerzenlicht",
    "暖光": "warmes Licht", "冷光": "kaltes Licht", "逆光": "Gegenlicht",
    "烈日": "gleißende Sonne",
    # ---- 色彩 ----
    "黑白": "Schwarzweiß", "黑白新写实": "Schwarzweiß-Neorealismus",
    "红绿": "Rot und Grün", "大红": "leuchtendes Rot", "冷蓝": "kaltes Blau",
    "冷灰": "kaltes Grau", "冷峻": "kühl", "高饱和": "hohe Sättigung",
    "哑色": "gedämpfte Farbe", "金调": "Goldton", "秋色": "Herbstfarben",
    "灰绿": "Graugrün", "暖金": "warmes Gold",
    # ---- 风格 / 流派 ----
    "巴洛克": "Barock", "表现主义": "Expressionismus", "纪实": "dokumentarisch",
    "写实": "realistisch", "超现实": "surreal", "荒诞": "absurd",
    "拼贴": "Collage", "碎片": "Fragmente", "现代性": "Modernität",
    "象征": "Symbol", "寓言": "Fabel", "情节剧": "Melodram",
    "造作": "künstlich", "粗粝": "rau", "考究": "sorgfältig",
    # ---- 情绪 ----
    "克制": "zurückhaltend", "冷面": "ausdruckslos", "诡异": "unheimlich",
    "静默": "Stille", "空旷": "leer", "孤独": "Einsamkeit",
    "疏离": "Entfremdung", "衰败": "Verfall", "黄昏": "Dämmerung",
    "平凡": "gewöhnlich", "破碎": "zerbrochen", "末世": "Endzeit",
    "宏大": "monumental", "巨构": "Großstruktur", "朴素": "schlicht",
    "抒情": "lyrisch", "仪式": "Ritual", "梦境": "Traum",
    "灵性": "Spiritualität", "人文": "humanistisch", "感官": "sinnlich",
    "沉思": "kontemplativ", "历史感": "Historizität", "家庭": "Familie",
    "日常": "Alltag", "自然": "Natur", "雨夜": "Regennacht",
    "尘土": "Staub", "冷峻村庄": "kühles Dorf", "战后废墟": "Nachkriegsruinen",
    "中产": "Mittelschicht", "废墟": "Ruine", "雨": "Regen", "雾": "Nebel",
    "水": "Wasser", "群像": "Ensemble",
    # ---- 东方影像 ----
    "水墨": "Tuschemalerei", "青绿": "Blau-Grün-Landschaft",
    "矿物色": "Mineralpigmente", "金线": "Goldlinien", "雾江": "nebliger Fluss",
    "孤舟": "einsames Boot", "远山": "ferne Berge", "年画": "Neujahrsbild",
    "木版": "Holzschnitt", "民俗": "Volkskunst", "皮影": "Schattenspiel",
    "透光": "durchscheinend", "笔触": "Pinselstrich", "山雾": "Bergnebel",
    "飘": "schwebend", "院体": "Akademiemalerei", "工细": "fein gearbeitet",
    "绢本": "auf Seide", "工笔": "Gongbi", "重彩": "deckende Farben",
    "白描": "Weißzeichnung", "手卷": "Handrolle", "长卷": "lange Rolle",
}

assert set(KO) == set(DE), f"韩德键不一致: {set(KO) ^ set(DE)}"

if __name__ == "__main__":
    print(f"韩语 {len(KO)} 词 / 德语 {len(DE)} 词，键完全一致 ✅")
    print("\n样例：")
    for k in ("对称", "长镜", "留白", "雾江", "水墨", "皮影"):
        print(f"  {k:<6} {KO[k]:<14} {DE[k]}")
    print("\n### KODE_LEXICON_OK")

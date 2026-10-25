"""
动物批次：动物本体（题材）+ 动物质感（材质）

为什么这批重要
--------------
库里此前**一条动物都没有**。而"猫在窗台上""一只狗跑过"这类请求一定会来。
而且用户那个电影的设定里就有"鲸鱼女孩"——鲸也不在库里。

写法
----
动物的描述不写百科特征，写**可被拍到的状态**：
    不写 "猫是小型猫科动物"
    写   "一只猫坐着，重心压实，尾巴和身体各自在动"

因为提示词里有用的是后者：姿势、重心、朝向、动作独立性。

材质补的是画面上真正看到的：毛、羽、鳞、湿毛、兽眼、甲壳。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "comfyui"))
RAW = os.path.join(ROOT, "data", "raw")

SUBJECTS = [
    ("Cat", "猫", "a cat seated with its weight settled, the tail moving on its own",
     ["猫", "猫科", "尾巴", "坐"],
     ["a cat seated, weight settled, the tail moving independently of the body",
      "a cat crouched low before a step, shoulders gathered",
      "a cat lying with one paw over its face, the ear still tracking sound"]),
    ("Dog", "狗", "a dog standing with weight on the front feet, ears turning before the head",
     ["狗", "犬", "耳朵", "站"],
     ["a dog standing, weight forward, ears turning before the head does",
      "a dog running with all four feet off the ground for one frame",
      "a dog sitting, one ear folded back, tongue out, breathing hard"]),
    ("Bird", "鸟", "a small bird perched, the head turning in short separate jerks",
     ["鸟", "雀", "羽毛", "栖"],
     ["a small bird perched, the head turning in short separate jerks",
      "a bird taking off, wings still folded at the first frame",
      "a bird standing in shallow water, one leg lifted and held"]),
    ("Fish", "鱼", "fish holding against a current, the fins making small corrections",
     ["鱼", "鱼群", "鳍", "水"],
     ["fish holding against a current, fins correcting all the time",
      "a shoal turning as one, no individual leading",
      "a fish close to the surface, the back breaking the water line"]),
    ("Horse", "马", "a horse standing with one hind leg resting, the coat shifting over the ribs",
     ["马", "鬃毛", "马蹄", "骑"],
     ["a horse standing, one hind leg resting, the coat moving over the ribs",
      "a horse at a canter, the mane lifting with the stride",
      "a horse's head down, breath visible in cold air"]),
    ("Deer", "鹿", "a deer stopped mid-step, head up, both ears forward",
     ["鹿", "鹿角", "警觉", "停"],
     ["a deer stopped mid-step, head up, both ears forward",
      "a deer at the edge of trees, only the head and neck visible",
      "a deer turning away, the white underside of the tail showing"]),
    ("Snake", "蛇", "a snake crossing dry ground, the body curving without limbs",
     ["蛇", "鳞", "爬行", "缠绕"],
     ["a snake crossing dry ground, the body curving without limbs",
      "a snake coiled, only the head moving, tongue testing the air",
      "snake scales catching light along each overlapping edge"]),
    ("Bear", "熊", "a bear on all fours, the shoulder standing higher than the head",
     ["熊", "野兽", "爪", "庞大"],
     ["a bear on all fours, the shoulder higher than the head",
      "a bear standing up, weight shifting, front paws hanging",
      "a bear in water, only the head and hump above the surface"]),
    ("Rabbit", "兔", "a rabbit crouched with ears back, absolutely still",
     ["兔", "兔子", "耳朵", "蹲"],
     ["a rabbit crouched, ears back, absolutely still",
      "a rabbit in motion, the hind legs folded and released in one beat",
      "a rabbit's nose moving while nothing else does"]),
    ("Whale", "鲸", "a whale's back breaking the surface, water sheeting off it",
     ["鲸", "鲸鱼", "背", "海"],
     ["a whale's back breaking the surface, water sheeting off the skin",
      "a whale's tail lifting clear before the body follows it down",
      "a whale passing under the boat, the shape read through the water"]),
    ("Octopus", "章鱼", "an octopus with arms curling and uncurling, the skin changing texture",
     ["章鱼", "触手", "吸盘", "变色"],
     ["an octopus with arms curling and uncurling, the skin going from smooth to peaked",
      "an octopus changing colour across the body in a wave",
      "suckers running in two rows down the inside of each arm"]),
    ("Butterfly", "蝴蝶", "a butterfly settled with the wings opening and closing slowly",
     ["蝴蝶", "翅膀", "鳞粉", "停"],
     ["a butterfly settled, wings opening and closing slowly",
      "a butterfly in flight, the path irregular and the wings never still",
      "wing scales catching colour only at a shallow angle"]),
    ("Bee", "蜜蜂", "a bee working a flower, the pollen baskets loaded",
     ["蜜蜂", "花粉", "蜂", "花"],
     ["a bee working a flower, the pollen baskets visibly loaded",
      "a bee hovering, the body held still while the wings blur",
      "bees entering a hive mouth in a continuous line"]),
    ("Spider", "蜘蛛", "a spider at the centre of a web, one leg testing a strand",
     ["蜘蛛", "蛛网", "腿", "丝"],
     ["a spider at the centre of a web, one leg testing a strand",
      "a web catching light only where the silk faces the source",
      "a spider wrapping something, the legs working in alternation"]),
]

MATERIALS = [
    ("Fur", "毛皮", "fur catching light along the guard hairs with the undercoat matte",
     ["毛皮", "绒毛", "毛", "皮毛"],
     ["guard hairs catching light while the undercoat stays matte",
      "fur parting along the spine where the animal has been touched",
      "short dense fur with no individual hairs readable at all"]),
    ("Feathers", "羽毛", "feathers overlapping in rows, the shafts catching a thin highlight",
     ["羽毛", "羽", "翎", "鸟羽"],
     ["feathers overlapping in rows, each shaft a thin line of highlight",
      "a single feather bent, the barbs still holding together",
      "down at the base of the plumage, matte and structureless"]),
    ("Scales", "鳞片", "overlapping scales each catching a line of light along its free edge",
     ["鳞片", "鳞", "鱼鳞", "甲"],
     ["overlapping scales, every free edge a line of light",
      "scales going from bright silver to dark as the body turns",
      "a scale lifted at one corner, the skin beneath paler"]),
    ("Wet Fur", "湿毛", "wet fur clumped into points, water running off the tips",
     ["湿毛", "淋湿", "水", "贴住"],
     ["wet fur clumped into points, the body reading much smaller",
      "water running off the tips and dropping clear",
      "wet fur drying in patches, some clumped and some lifted"]),
    ("Animal Eye", "兽眼", "an eye with a hard wet highlight, the rim dark and thin",
     ["眼睛", "兽眼", "瞳孔", "眼神"],
     ["an eye with a hard wet highlight and a thin dark rim",
      "a horizontal pupil narrowing while the lid does not move",
      "the eye reflecting the light source as a small square"]),
    ("Shell", "甲壳", "a hard carapace with a seam down the middle, matte where worn",
     ["甲壳", "壳", "硬壳", "背甲"],
     ["a hard carapace with a seam down the middle, matte where handled",
      "the shell polished to a dull shine on the high points only",
      "shell plates meeting along a line, each one slightly different"]),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def name_keys(sample):
    return (next(k for k in sample if k.endswith("_en")),
            next(k for k in sample if k.endswith("_zh")))


def build(src, out, entries, kind, prefix, extra_type=None):
    rows = load(src)
    k_en, k_zh = name_keys(rows[0])
    n = len(rows)
    added = []
    for en, zh, phrase, kw, variants in entries:
        for v in variants:
            n += 1
            row = {"doc_id": f"{prefix}{n:04d}", "kind": kind,
                   k_en: en, k_zh: zh, "phrase": phrase, "kw_zh": kw,
                   "description": v, "text_semantic": f"{v}，{zh}，{'、'.join(kw)}"}
            if extra_type and "type" in rows[0]:
                row["type"] = extra_type
            added.append(row)
    with open(out, "w", encoding="utf-8") as f:
        for r in rows + added:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {os.path.basename(out):<20} {len(rows)} -> {len(rows)+len(added)}"
          f"  (+{len(added)} / {len(entries)} 项)")


def main():
    print("=== 动物批次 ===")
    build(os.path.join(RAW, "subjects_v9.jsonl"), os.path.join(RAW, "subjects_v10.jsonl"),
          SUBJECTS, "subject", "s", extra_type="object")
    build(os.path.join(RAW, "materials_v9.jsonl"), os.path.join(RAW, "materials_v10.jsonl"),
          MATERIALS, "material", "m")
    print("\n### KB_ANIMALS_DONE")


if __name__ == "__main__":
    main()

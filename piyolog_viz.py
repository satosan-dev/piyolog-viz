#!/usr/bin/env python3
"""ぴよログデータ解析・可視化スクリプト"""

import re
import json
import calendar
from pathlib import Path
from datetime import datetime, timedelta, date as date_type

# ===== 設定ファイルの読み込み =====
CONFIG_PATH = Path(__file__).parent / "config.json"
if not CONFIG_PATH.exists():
    raise FileNotFoundError(
        "config.json が見つかりません。config.json.example をコピーして設定してください。\n"
        "  cp config.json.example config.json"
    )
with open(CONFIG_PATH, encoding="utf-8") as _f:
    _config = json.load(_f)

BIRTH_DATE     = datetime.strptime(_config["birth_date"], "%Y-%m-%d").date()
BABY_NAME      = _config.get("baby_name", "赤ちゃん")
OUTPUT_FILENAME = _config.get("output_filename", "piyolog_viz.html")

# ファイルマッピング
DATA_DIR = Path(__file__).parent / "data"

# dataフォルダ内の ぴよログ_YYYY-MM.txt を自動検出
def find_files():
    files = {}
    for f in sorted(DATA_DIR.glob("ぴよログ_*.txt")):
        m = re.match(r"ぴよログ_(\d{4})-(\d{2})\.txt", f.name)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
            label = f"{year}年{month}月"
            files[label] = str(f)
    return files

FILES = find_files()

def parse_piyolog(filepath):
    """ぴよログテキストを解析してデータを返す"""
    records = {}
    current_date = None

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # 日付ブロックで分割
    day_blocks = re.split(r"----------", content)

    for block in day_blocks:
        block = block.strip()
        if not block:
            continue

        # 日付行を探す
        date_match = re.search(r"(\d{4}/\d{1,2}/\d{1,2})", block)
        if not date_match:
            continue

        raw_date_str = date_match.group(1)
        try:
            date = datetime.strptime(raw_date_str, "%Y/%m/%d").date()
        except ValueError:
            continue

        date_str = date.strftime("%Y/%m/%d")  # ゼロパディングで正規化

        rec = {"date": date_str, "height": None, "weight": None, "head": None, "chest": None,
               "sleep_min": None, "milk_ml": None, "pee": None, "poo": None,
               "breastfeed_left": None, "breastfeed_right": None, "notes": []}

        # 身長
        m = re.search(r"身長\s+([\d.]+)cm", block)
        if m: rec["height"] = float(m.group(1))

        # 体重
        m = re.search(r"体重\s+([\d.]+)g", block)
        if m: rec["weight"] = float(m.group(1))
        m = re.search(r"体重\s+([\d.]+)kg", block)
        if m: rec["weight"] = float(m.group(1)) * 1000

        # 頭囲
        m = re.search(r"頭囲\s+([\d.]+)cm", block)
        if m: rec["head"] = float(m.group(1))

        # 胸囲
        m = re.search(r"胸囲\s+([\d.]+)cm", block)
        if m: rec["chest"] = float(m.group(1))

        # 睡眠合計（時間分）
        m = re.search(r"睡眠合計\s+(\d+)時間(\d+)分", block)
        if m: rec["sleep_min"] = int(m.group(1)) * 60 + int(m.group(2))

        # ミルク合計
        m = re.search(r"ミルク合計\s+\d+回\s+(\d+)ml", block)
        if m: rec["milk_ml"] = int(m.group(1))

        # おしっこ
        m = re.search(r"おしっこ合計\s+(\d+)回", block)
        if m: rec["pee"] = int(m.group(1))

        # うんち
        m = re.search(r"うんち合計\s+(\d+)回", block)
        if m: rec["poo"] = int(m.group(1))

        # 母乳合計（左右分）
        m = re.search(r"母乳合計\s+左\s+(\d+)分\s*/\s*右\s+(\d+)分", block)
        if m:
            rec["breastfeed_left"] = int(m.group(1))
            rec["breastfeed_right"] = int(m.group(2))

        # メモ（日次サマリー下のフリーテキスト）
        lines = block.split("\n")
        for line in lines:
            line = line.strip()
            if line and not re.match(r"[\d:/\(\)ちか\s月日\u6bcd\u4e73\u30df\u30eb\u30af\u7761\u7720\u304a\u3057\u3063\u3053\u3046\u3093\u3061\u5408\u8a08\u5de6\u53f3]", line):
                if len(line) > 5 and not re.match(r"^\d{2}:\d{2}", line) and "【ぴよログ】" not in line:
                    rec["notes"].append(line)

        records[date_str] = rec

    return records

# 全データ読み込み
all_records = {}
for month, filepath in FILES.items():
    p = Path(filepath)
    if p.exists():
        records = parse_piyolog(filepath)
        all_records.update(records)
        print(f"  {month}: {len(records)}日分読み込み")
    else:
        print(f"  {month}: ファイルが見つかりません ({filepath})")

# 日付順にソート
sorted_dates = sorted(all_records.keys())
print(f"\n総日数: {len(sorted_dates)}日")

# データ抽出
dates = sorted_dates
heights = [(d, all_records[d]["height"]) for d in dates if all_records[d]["height"]]
weights = [(d, all_records[d]["weight"]) for d in dates if all_records[d]["weight"]]
sleeps  = [(d, all_records[d]["sleep_min"]) for d in dates if all_records[d]["sleep_min"] is not None]
milks   = [(d, all_records[d]["milk_ml"]) for d in dates if all_records[d]["milk_ml"] is not None]
pees    = [(d, all_records[d]["pee"]) for d in dates if all_records[d]["pee"] is not None]
poos    = [(d, all_records[d]["poo"]) for d in dates if all_records[d]["poo"] is not None]

# 母乳合計（左+右）
bf = [(d, (all_records[d]["breastfeed_left"] or 0) + (all_records[d]["breastfeed_right"] or 0))
      for d in dates
      if all_records[d]["breastfeed_left"] is not None or all_records[d]["breastfeed_right"] is not None]

# 最後のうんち記録日
last_poo_date_str = None
for d in sorted(all_records.keys(), reverse=True):
    if all_records[d].get('poo') and all_records[d]['poo'] > 0:
        last_poo_date_str = d
        break

if last_poo_date_str:
    last_poo_dt = datetime.strptime(last_poo_date_str, '%Y/%m/%d').date()
    days_since_poo = (date_type.today() - last_poo_dt).days
    if days_since_poo == 0:
        poo_status = "今日した！"
        poo_color = "#4caf50"
    elif days_since_poo == 1:
        poo_status = "昨日"
        poo_color = "#8bc34a"
    elif days_since_poo <= 2:
        poo_status = f"{days_since_poo}日前"
        poo_color = "#ff9800"
    else:
        poo_status = f"{days_since_poo}日前 ⚠️"
        poo_color = "#e53935"
else:
    days_since_poo = None
    poo_status = "記録なし"
    poo_color = "#aaa"

print(f"身長記録: {len(heights)}件")
print(f"体重記録: {len(weights)}件")
print(f"睡眠記録: {len(sleeps)}件")

# ===== 離乳食マップ =====

RYUNYU_DATA_PATH = Path(__file__).parent / "ryunyu_foods.json"

# 特定原材料（表示色を強調する8品目）
ALLERGEN_TOP8 = {"卵", "乳", "小麦", "そば", "落花生", "えび", "かに", "くるみ"}

FOOD_ALIASES = {
    "10倍がゆ": "白米・おかゆ", "10倍粥": "白米・おかゆ",
    "七倍がゆ": "白米・おかゆ", "七倍粥": "白米・おかゆ",
    "おかゆ": "白米・おかゆ", "白米": "白米・おかゆ",
    "人参": "にんじん", "にんじんペースト": "にんじん",
    "ほうれん草": "ほうれんそう", "ほうれんそうペースト": "ほうれんそう",
    "さつまいもペースト": "さつまいも",
}

# 食材マスター（ステージ > カテゴリ > 食材名: アレルゲン）
# ※ タブ0はゴックン期+モグモグ期の2列表示、タブ1以降は単独表示
FOOD_MASTER = {
    "ゴックン期（5〜6ヶ月）": {
        "🍚 穀類": {
            "白米・おかゆ": None, "米粉": None,
            "食パン": "小麦", "うどん": "小麦", "そうめん": "小麦",
        },
        "🍠 いも類": {
            "じゃがいも": None, "さつまいも": None, "片栗粉": None,
        },
        "🥕 野菜": {
            "にんじん": None, "かぼちゃ": None, "玉ねぎ": None,
            "キャベツ": None, "ほうれんそう": None, "小松菜": None,
            "ブロッコリー": None, "トマト": None, "大根": None, "カブ": None,
        },
        "🍓 果物": {
            "りんご": None, "みかん": None, "もも": "もも",
            "バナナ": "バナナ", "いちご": None, "すいか": None, "メロン": None,
        },
        "🐟 魚介": {
            "しらす": None, "たら": None, "かれい": None, "ひらめ": None,
        },
        "🥚 卵": {
            "卵黄": "卵",
        },
        "🫘 豆腐・豆類": {
            "豆腐": "大豆", "きな粉": "大豆", "大豆": "大豆",
            "白いんげん豆": None, "金時豆": None,
        },
        "🥛 乳製品": {
            "調整粉乳": "乳", "ヨーグルト": "乳",
        },
        "🍵 だし・調味料": {
            "昆布だし": None, "かつおだし": None, "麦茶": None,
        },
    },
    "モグモグ期（7〜8ヶ月）": {
        "🍚 穀類": {
            "マカロニ": "小麦", "パスタ": "小麦", "オートミール": None,
        },
        "🍠 いも類": {
            "里芋": None,
        },
        "🥕 野菜": {
            "なす": None, "アスパラ": None, "ズッキーニ": None,
            "とうもろこし": None, "レタス": None, "ピーマン": None,
            "おくら": None, "さやいんげん": None,
        },
        "🍓 果物": {
            "ぶどう": None, "梨": None,
        },
        "🐟 魚介": {
            "さけ": None, "ツナ水煮": None,
            "まぐろ（赤身）": None, "さわら": None,
        },
        "🍗 肉": {
            "鶏ささみ": "鶏肉", "鶏むね肉": "鶏肉", "鶏ひき肉": "鶏肉",
        },
        "🥚 卵": {
            "全卵": "卵",
        },
        "🫘 豆腐・豆類": {
            "納豆": "大豆", "厚揚げ": "大豆", "小豆": "大豆",
        },
        "🥛 乳製品": {
            "プレーンヨーグルト": "乳", "カッテージチーズ": "乳",
        },
    },
    "カミカミ期（9〜11ヶ月）": {
        "🍚 穀類": {
            "軟飯": None, "麩": "小麦", "フレンチトースト": "卵・小麦・乳",
        },
        "🍠 いも類": {
            "こんにゃく": None,
        },
        "🥕 野菜": {
            "ごぼう": None, "れんこん": None, "もやし": None,
            "白菜": None, "カリフラワー": None, "セロリ": None,
        },
        "🌿 海草・きのこ": {
            "のり": None, "わかめ": None,
            "しいたけ": None, "しめじ": None, "まいたけ": None,
        },
        "🐟 魚介": {
            "ぶり": None, "あじ": None,
            "さば": "さば", "えび（加熱）": "えび",
        },
        "🍗 肉": {
            "鶏もも肉": "鶏肉", "牛ひき肉": "牛肉",
            "豚ひき肉": "豚肉", "レバー": "鶏肉",
        },
        "🥛 乳製品": {
            "牛乳（料理用）": "乳", "プロセスチーズ": "乳",
        },
        "🍵 だし・調味料": {
            "醤油（少量）": "小麦・大豆", "みりん（少量）": None,
            "みそ汁": "大豆・小麦", "バター": "乳",
        },
    },
    "パクパク期（12〜18ヶ月）": {
        "🍚 穀類": {
            "普通飯": None, "ロールパン": "小麦・乳・卵",
        },
        "🥕 野菜": {
            "ゴーヤ": None, "にら": None,
        },
        "🍓 果物": {
            "キウイ": None, "プルーン": None,
        },
        "🐟 魚介": {
            "さんま": None, "まぐろ（脂身少）": None,
            "いわし": "いわし", "あさり": "貝類",
        },
        "🍗 肉": {
            "豚薄切り": "豚肉", "牛薄切り": "牛肉",
            "ハム": "豚肉", "ウインナー": "豚肉",
        },
        "🥛 乳製品": {
            "牛乳（飲用）": "乳", "アイスクリーム": "乳・卵",
        },
        "🍵 調味料": {
            "ケチャップ": None, "マヨネーズ": "卵", "中濃ソース": None,
        },
        "⚠️ 要注意食材": {
            "ピーナッツ（ペースト）": "落花生", "そば": "そば",
        },
    },
}


def load_ryunyu_data():
    """食材導入記録をJSONから読み込み、ぴよログのエントリも追記する"""
    introduced = {}
    if RYUNYU_DATA_PATH.exists():
        with open(RYUNYU_DATA_PATH, encoding="utf-8") as f:
            introduced = json.load(f).get("introduced", {})

    # マスター全食材名セット（ぴよログとのマッチング用）
    all_food_names = set()
    for stage_data in FOOD_MASTER.values():
        for cat_data in stage_data.values():
            all_food_names.update(cat_data.keys())

    # ぴよログの「離乳食 食材名」エントリを解析
    for filepath in FILES.values():
        p = Path(filepath)
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            content = f.read()
        for block in re.split(r"----------", content):
            date_match = re.search(r"(\d{4}/\d{1,2}/\d{1,2})", block)
            if not date_match:
                continue
            try:
                date_str = datetime.strptime(date_match.group(1), '%Y/%m/%d').strftime('%Y/%m/%d')
            except ValueError:
                continue
            for line in block.split("\n"):
                if not re.match(r"\d{2}:\d{2}\s+離乳食", line):
                    continue
                m = re.match(r"\d{2}:\d{2}\s+離乳食\s*(.*)", line)
                if not m:
                    continue
                for part in re.split(r"[・、,，\s　]+", m.group(1).strip()):
                    part = part.strip()
                    part = FOOD_ALIASES.get(part, part)
                    if part in all_food_names and part not in introduced:
                        introduced[part] = {"date": date_str, "reaction": ""}
    return introduced


def get_current_stage():
    """月齢からステージキーを返す"""
    today = date_type.today()
    age = (today.year - BIRTH_DATE.year) * 12 + (today.month - BIRTH_DATE.month)
    if today.day < BIRTH_DATE.day:
        age -= 1
    if age < 7:   return "ゴックン期（5〜6ヶ月）"
    if age < 9:   return "モグモグ期（7〜8ヶ月）"
    if age < 12:  return "カミカミ期（9〜11ヶ月）"
    return "パクパク期（12〜18ヶ月）"


def get_suggestions(introduced, stage, derived=None, n=5):
    """現ステージの未導入食材からカテゴリ多様に n 件返す"""
    if derived is None:
        derived = set()
    stage_data = FOOD_MASTER.get(stage, {})
    non_al, al = [], []
    for cat, foods in stage_data.items():
        for food, allergen in foods.items():
            if food not in introduced and food not in derived:
                bucket = al if allergen else non_al
                bucket.append({"food": food, "cat": cat, "allergen": allergen})
    diverse, seen = [], set()
    for item in non_al + al:
        if item["cat"] not in seen:
            diverse.append(item)
            seen.add(item["cat"])
        if len(diverse) >= n:
            break
    for item in non_al + al:
        if item not in diverse:
            diverse.append(item)
        if len(diverse) >= n:
            break
    return diverse[:n]


def _allergen_class(allergen):
    if not allergen:
        return ""
    return "fm-al-top" if any(a.strip() in ALLERGEN_TOP8 for a in allergen.split("・")) else "fm-al-sub"


def get_derived_ok(introduced):
    """導入済み食材のアレルゲンから『準じてOK』な未導入食材を返す"""
    # マスター全体から導入済み食材のアレルゲンを収集 → クリア済みセット
    cleared = set()
    for stage_data in FOOD_MASTER.values():
        for cat_data in stage_data.values():
            for food, allergen in cat_data.items():
                if food in introduced and allergen:
                    for a in allergen.split("・"):
                        cleared.add(a.strip())

    # 未導入のうち、全アレルゲンがクリア済みの食材を返す
    derived = set()
    for stage_data in FOOD_MASTER.values():
        for cat_data in stage_data.values():
            for food, allergen in cat_data.items():
                if food in introduced or not allergen:
                    continue
                if {a.strip() for a in allergen.split("・")}.issubset(cleared):
                    derived.add(food)
    return derived


def _chips_html(cats, introduced, derived=None):
    """カテゴリ辞書からチップHTMLを生成する"""
    if derived is None:
        derived = set()
    html = ""
    for cat, foods in cats.items():
        html += f'<div class="fm-cat"><div class="fm-cat-label">{cat}</div><div class="fm-chips">'
        for food, allergen in foods.items():
            info = introduced.get(food)
            if info:
                state = "fm-eaten"
                tip   = f"📅 {info['date']}"
                if info.get("reaction"):
                    tip += f"  {info['reaction']}"
                if allergen:
                    tip += f"  ⚠️ {allergen}"
            elif food in derived:
                state = "fm-derived"
                tip   = f"準OK（アレルゲン導入済み）"
                if allergen:
                    tip += f"  ⚠️ {allergen}"
            else:
                state = "fm-new"
                tip   = "未導入"
                if allergen:
                    tip += f"  ⚠️ {allergen}"
            alcls = _allergen_class(allergen)
            html += f'<span class="fm-chip {state} {alcls}" data-tip="{tip}">{food}</span>'
        html += "</div></div>"
    return html


def parse_day_events(block):
    """1日分のブロックからイベントリストを返す"""
    events = []
    for line in block.split('\n'):
        line = line.strip()
        m = re.match(r'(\d{2}):(\d{2})\s+(.*)', line)
        if not m:
            continue
        h, mi, content = int(m.group(1)), int(m.group(2)), m.group(3).strip()
        t = h * 60 + mi
        if re.search(r'いってきます|登園', content):
            events.append({'t': t, 'type': 'hoiku_start'})
        elif re.search(r'ただいま|降園|お迎え', content):
            events.append({'t': t, 'type': 'hoiku_end'})
        elif re.search(r'寝る', content) and 'お風呂' not in content:
            events.append({'t': t, 'type': 'sleep_start'})
        elif re.search(r'起きる', content):
            events.append({'t': t, 'type': 'sleep_end'})
        elif re.search(r'おしっこ', content):
            events.append({'t': t, 'type': 'pee'})
        elif re.search(r'うんち', content):
            qty_map = {'多め': 3, '多い': 3, 'ふつう': 2, '普通': 2, '少し': 1, '少量': 1, '少ない': 1}
            qty = 2
            for k, v in qty_map.items():
                if k in content:
                    qty = v
                    break
            events.append({'t': t, 'type': 'poo', 'qty': qty})
        elif re.search(r'ミルク\s+\d', content):
            ml_m = re.search(r'(\d+)ml', content)
            events.append({'t': t, 'type': 'milk', 'ml': int(ml_m.group(1)) if ml_m else 0})
        elif re.search(r'母乳', content):
            lm = re.search(r'左\s*(\d+)分', content)
            rm = re.search(r'右\s*(\d+)分', content)
            total = (int(lm.group(1)) if lm else 0) + (int(rm.group(1)) if rm else 0)
            events.append({'t': t, 'type': 'breast', 'min': total})
        elif re.search(r'離乳食', content):
            events.append({'t': t, 'type': 'food'})
    return events


def get_all_timeline_data():
    """全期間のタイムラインデータを返す"""
    all_blocks = {}
    for filepath in FILES.values():
        p = Path(filepath)
        if not p.exists():
            continue
        with open(p, encoding='utf-8') as f:
            content = f.read()
        for block in re.split(r'----------', content):
            date_m = re.search(r'(\d{4}/\d{1,2}/\d{1,2})', block)
            if date_m:
                try:
                    norm = datetime.strptime(date_m.group(1), '%Y/%m/%d').strftime('%Y/%m/%d')
                except ValueError:
                    continue
                all_blocks[norm] = block

    all_dates = sorted(all_blocks.keys())
    result = {}
    for date_str in all_dates:
        evts = parse_day_events(all_blocks[date_str])
        evts.sort(key=lambda x: x['t'])
        sleeps, sleep_start = [], None
        if evts and evts[0]['type'] == 'sleep_end':
            sleep_start = 0
        for e in evts:
            if e['type'] == 'sleep_start':
                sleep_start = e['t']
            elif e['type'] == 'sleep_end':
                if sleep_start is not None:
                    sleeps.append([sleep_start, e['t']])
                    sleep_start = None
        if sleep_start is not None:
            sleeps.append([sleep_start, 1440])
        # 保育園帯
        hoiku = []
        hoiku_start = None
        for e in evts:
            if e['type'] == 'hoiku_start':
                hoiku_start = e['t']
            elif e['type'] == 'hoiku_end' and hoiku_start is not None:
                hoiku.append([hoiku_start, e['t']])
                hoiku_start = None
        result[date_str] = {
            'sleeps': sleeps,
            'hoiku': hoiku,
            'events': [e for e in evts if e['type'] not in ('sleep_start', 'sleep_end', 'hoiku_start', 'hoiku_end')]
        }
    return result, all_dates


WEEKDAY_JA = ['月','火','水','木','金','土','日']

def build_timeline_html(timeline_data, all_dates):
    """全期間タイムラインのHTMLを生成する（JSページネーション付き）"""
    all_rows_html = ''
    for date_str in all_dates:
        d = datetime.strptime(date_str, '%Y/%m/%d')
        label = f"{d.month}/{d.day}({WEEKDAY_JA[d.weekday()]})"
        day = timeline_data.get(date_str, {'sleeps': [], 'events': []})

        bar_inner = ''
        # 夜間帯（0〜7時、19〜24時）を薄グレー背景
        bar_inner += '<div class="tl-night" style="left:0%;width:29.17%"></div>'
        bar_inner += '<div class="tl-night" style="left:79.17%;width:20.83%"></div>'
        # 睡眠ブロック
        for s, e_end in day['sleeps']:
            left  = s / 1440 * 100
            width = max((e_end - s) / 1440 * 100, 0.3)
            bar_inner += f'<div class="tl-sleep" style="left:{left:.2f}%;width:{width:.2f}%"></div>'
        # 保育園帯（黄色半透明）
        for hs, he in day.get('hoiku', []):
            left  = hs / 1440 * 100
            width = (he - hs) / 1440 * 100
            h_s, m_s = divmod(hs, 60)
            h_e, m_e = divmod(he, 60)
            bar_inner += (f'<div class="tl-hoiku" style="left:{left:.2f}%;width:{width:.2f}%" '
                          f'data-tip="🏫 保育園 {h_s:02d}:{m_s:02d}〜{h_e:02d}:{m_e:02d}"></div>')
        # イベントドット
        for evt in day['events']:
            pct = evt['t'] / 1440 * 100
            cls = f"tl-{evt['type']}"
            h, mi = divmod(evt['t'], 60)
            extra_style = ''
            if evt['type'] == 'breast':
                mins = evt.get('min', 0)
                tip = f"{h:02d}:{mi:02d} 授乳 {mins}分"
                sz = min(max(5 + mins * 0.43, 5), 18)
                extra_style = f'width:{sz:.0f}px;height:{sz:.0f}px;'
            elif evt['type'] == 'milk':
                ml = evt.get('ml', 0)
                tip = f"{h:02d}:{mi:02d} ミルク {ml}ml"
                sz = min(max(5 + ml / 17, 5), 18)
                extra_style = f'width:{sz:.0f}px;height:{sz:.0f}px;'
            elif evt['type'] == 'food':
                tip = f"{h:02d}:{mi:02d} 離乳食"
            elif evt['type'] == 'pee':
                tip = f"{h:02d}:{mi:02d} おしっこ"
            else:
                qty = evt.get('qty', 2)
                qty_label = {1: '少し', 2: '普通', 3: '多め'}.get(qty, '普通')
                tip = f"{h:02d}:{mi:02d} うんち（{qty_label}）"
                sz_poo = {1: 8, 2: 14, 3: 20}.get(qty, 14)
                extra_style = f'width:{sz_poo}px;height:{sz_poo}px;'
            bar_inner += (f'<div class="{cls} tl-dot" '
                          f'style="left:{pct:.2f}%;{extra_style}" data-tip="{tip}"></div>')

        all_rows_html += (
            f'<div class="tl-row" data-date="{date_str}">'
            f'<div class="tl-label">{label}</div>'
            f'<div class="tl-bar-wrap"><div class="tl-bar">{bar_inner}</div></div>'
            f'</div>\n'
        )

    # 時刻ヘッダー（6時間刻み + 7時・19時強調）
    hour_marks = ''.join(
        f'<div class="tl-hour" style="left:{h/24*100:.2f}%">{h}</div>'
        for h in range(0, 25, 6)
    )

    return f"""
<div class="card" style="grid-column:1/-1">
  <h2>📅 日々のタイムライン</h2>
  <div class="tl-legend">
    <span><span class="tl-legend-sleep"></span>睡眠</span>
    <span><span class="tl-hoiku-legend"></span>保育園</span>
    <span><span class="tl-dot tl-breast tl-legend-dot"></span>授乳（大きさ＝時間）</span>
    <span><span class="tl-dot tl-milk   tl-legend-dot"></span>ミルク（大きさ＝量）</span>
    <span><span class="tl-dot tl-food   tl-legend-dot"></span>離乳食</span>
    <span><span class="tl-dot tl-pee    tl-legend-dot"></span>おしっこ</span>
    <span><span class="tl-dot tl-poo    tl-legend-dot"></span>うんち</span>
  </div>
  <div class="tl-nav">
    <button class="tl-btn" id="tl-prev">◀ 前の7日間</button>
    <span class="tl-nav-info" id="tl-nav-info"></span>
    <button class="tl-btn" id="tl-next">次の7日間 ▶</button>
  </div>
  <div class="tl-wrap">
    <div class="tl-hours-row">
      <div class="tl-label"></div>
      <div class="tl-bar-wrap"><div class="tl-bar tl-hours">{hour_marks}</div></div>
    </div>
    <div id="tl-rows">{all_rows_html}</div>
  </div>
</div>
"""


def build_food_map_html(introduced, stage):
    """離乳食マップの HTML ブロックを生成する"""
    derived    = get_derived_ok(introduced)
    stage_keys = list(FOOD_MASTER.keys())
    gok, mog   = stage_keys[0], stage_keys[1]

    # タブ（3つ: ゴックン+モグモグ / カミカミ / パクパク）
    tab_labels = ["ゴックン期 + モグモグ期", stage_keys[2], stage_keys[3]]
    active_tab = 0 if stage in (gok, mog) else (1 if stage == stage_keys[2] else 2)
    tabs = "".join(
        f'<button class="fm-tab{"  fm-tab-on" if i == active_tab else ""}" '
        f'onclick="fmSwitch({i})">{label}</button>'
        for i, label in enumerate(tab_labels)
    )

    # タブ0: ゴックン+モグモグ 2列
    gok_cls = "fm-col-on" if stage == gok else "fm-col-dim"
    mog_cls = "fm-col-on" if stage == mog else "fm-col-dim"
    tab0 = f"""<div id="fm-g0" style="display:{'block' if active_tab==0 else 'none'}">
  <div class="fm-combined">
    <div class="{gok_cls}">
      <div class="fm-col-hd">{gok}</div>
      {_chips_html(FOOD_MASTER[gok], introduced, derived)}
    </div>
    <div class="{mog_cls}">
      <div class="fm-col-hd">{mog}</div>
      {_chips_html(FOOD_MASTER[mog], introduced, derived)}
    </div>
  </div>
</div>"""

    # タブ1・2: 単独グリッド（display:grid で表示）
    tab1 = (f'<div id="fm-g1" class="fm-grid" '
            f'style="display:{"grid" if active_tab==1 else "none"}">'
            f'{_chips_html(FOOD_MASTER[stage_keys[2]], introduced, derived)}</div>')
    tab2 = (f'<div id="fm-g2" class="fm-grid" '
            f'style="display:{"grid" if active_tab==2 else "none"}">'
            f'{_chips_html(FOOD_MASTER[stage_keys[3]], introduced, derived)}</div>')

    # サジェスト
    sugs = get_suggestions(introduced, stage, derived=derived)
    sug_html = "".join(
        f'<div class="fm-sug {_allergen_class(s["allergen"])}">'
        f'<b>{s["food"]}</b>'
        f'<small>{s["cat"]}{"　⚠️ " + s["allergen"] if s["allergen"] else ""}</small>'
        f'</div>'
        for s in sugs
    )

    return f"""
<div class="card" style="grid-column:1/-1">
  <h2>🥄 離乳食マップ</h2>
  <div class="fm-header">
    <div class="fm-badges">
      <span class="fm-badge">現在: <b>{stage}</b></span>
      <span class="fm-badge">食べた食材: <b>{len(introduced)} 品目</b></span>
    </div>
    <div class="fm-legend">
      <span class="fm-chip fm-eaten">食べた</span>
      <span class="fm-chip fm-derived">準OK</span>
      <span class="fm-chip fm-new">未導入</span>
      <span class="fm-legend-sep"></span>
      <span class="fm-chip fm-new fm-al-top">赤枠</span><span class="fm-legend-note">特定アレルゲン8品目</span>
      <span class="fm-chip fm-new fm-al-sub">橙枠</span><span class="fm-legend-note">準ずるアレルゲン</span>
    </div>
  </div>
  <div class="fm-tabs">{tabs}</div>
  {tab0}{tab1}{tab2}
  <div class="fm-next">
    <h3>💡 次におすすめの食材（{stage}・未導入から）</h3>
    <div class="fm-sug-row">{sug_html}</div>
  </div>
</div>
"""


# 離乳食データ読み込み
ryunyu_introduced = load_ryunyu_data()
ryunyu_stage      = get_current_stage()
food_map_html     = build_food_map_html(ryunyu_introduced, ryunyu_stage)
print(f"離乳食記録: {len(ryunyu_introduced)}品目 / 現在ステージ: {ryunyu_stage}")

timeline_data, timeline_all_dates = get_all_timeline_data()
timeline_html = build_timeline_html(timeline_data, timeline_all_dates)

# ===== HTMLの生成 =====
def to_chart_data(pairs):
    # date-fns アダプター対応のためISOフォーマット（YYYY-MM-DD）で出力
    return {"labels": [p[0].replace('/', '-') for p in pairs], "data": [p[1] for p in pairs]}

# 1回あたり平均授乳時間
bf_per_session_pairs = []
for date_str in timeline_all_dates:
    day = timeline_data[date_str]
    breast_evts = [e for e in day['events'] if e['type'] == 'breast' and e.get('min', 0) > 0]
    if breast_evts:
        avg = sum(e['min'] for e in breast_evts) / len(breast_evts)
        bf_per_session_pairs.append((date_str, round(avg, 1)))

def _gen_milestones(birth_date, months=18):
    """生年月日からマイルストーン辞書を自動生成する"""
    result = {}
    for m in range(1, months + 1):
        total = birth_date.month - 1 + m
        year  = birth_date.year + total // 12
        month = total % 12 + 1
        day   = min(birth_date.day, calendar.monthrange(year, month)[1])
        result[f"{year}/{month:02d}/{day:02d}"] = f"{m}ヶ月"
    return result

MILESTONE_DATES = _gen_milestones(BIRTH_DATE)

# マイルストーン日付を実データの最近傍日付にマッピング（category scaleで正確に表示するため）
def _nearest_date(target_str, date_list):
    if not date_list:
        return target_str
    target = datetime.strptime(target_str, '%Y/%m/%d').date()
    return min(date_list, key=lambda d: abs(datetime.strptime(d, '%Y/%m/%d').date() - target))

MILESTONE_LABELS = {
    _nearest_date(ms_date, sorted_dates): ms_label
    for ms_date, ms_label in MILESTONE_DATES.items()
    if sorted_dates and datetime.strptime(ms_date, '%Y/%m/%d').date() <= datetime.strptime(sorted_dates[-1], '%Y/%m/%d').date()
}

# 動的サブタイトル
if sorted_dates:
    _fd = datetime.strptime(sorted_dates[0], '%Y/%m/%d')
    _ld = datetime.strptime(sorted_dates[-1], '%Y/%m/%d')
    _age_days = (_ld.date() - BIRTH_DATE).days
    _age_mo = (_ld.year - BIRTH_DATE.year) * 12 + (_ld.month - BIRTH_DATE.month)
    subtitle_text = f"{_fd.year}年{_fd.month}月〜{_ld.year}年{_ld.month}月（生後{_age_mo}ヶ月）"
else:
    subtitle_text = ""

chart_data = {
    "heights": to_chart_data(heights),
    "weights": to_chart_data([(d, w/1000) for d, w in weights]),  # kg変換
    "sleeps":  to_chart_data([(d, s/60) for d, s in sleeps]),      # 時間変換
    "milks":   to_chart_data(milks),
    "pees":    to_chart_data(pees),
    "poos":    to_chart_data(poos),
    "bf":      to_chart_data(bf),
    "bf_session": to_chart_data(bf_per_session_pairs),
}

html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{BABY_NAME} 成長記録</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3/dist/chartjs-plugin-annotation.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Hiragino Sans', sans-serif; background: #fdf6f0; color: #333; }}
  h1 {{ text-align: center; padding: 24px; color: #e07070; font-size: 1.6rem; }}
  .subtitle {{ text-align: center; color: #999; margin-bottom: 24px; font-size: 0.9rem; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; padding: 0 24px 40px; max-width: 1200px; margin: 0 auto; }}
  .card {{ background: white; border-radius: 16px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
  .card h2 {{ font-size: 1rem; color: #666; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #fde; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }}
  .stat {{ background: #fff5f5; border-radius: 10px; padding: 10px 16px; }}
  .stat .label {{ font-size: 0.75rem; color: #999; }}
  .stat .value {{ font-size: 1.4rem; font-weight: bold; color: #e07070; }}
  @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}

  /* 離乳食マップ */
  .fm-header  {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:14px; }}
  .fm-badges  {{ display:flex; gap:10px; flex-wrap:wrap; }}
  .fm-badge   {{ background:#fff5f5; border-radius:8px; padding:6px 12px; font-size:.88rem; }}
  .fm-legend  {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; font-size:.8rem; }}
  .fm-tabs    {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px; border-bottom:2px solid #fde; padding-bottom:10px; }}
  .fm-tab     {{ padding:5px 15px; border-radius:20px; border:2px solid #fde; background:white; cursor:pointer; font-size:.82rem; color:#aaa; }}
  .fm-tab-on,.fm-tab:hover {{ background:#e07070; color:white; border-color:#e07070; }}
  /* 2列レイアウト（ゴックン+モグモグ） */
  .fm-combined {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px; }}
  .fm-col-hd  {{ text-align:center; font-weight:bold; font-size:.88rem; padding:6px 12px; border-radius:8px; margin-bottom:12px; }}
  .fm-col-on  .fm-col-hd {{ background:#e07070; color:white; }}
  .fm-col-dim .fm-col-hd {{ background:#f0f0f0; color:#aaa; }}
  .fm-col-dim .fm-chip   {{ opacity:.45; }}
  /* 単独グリッド */
  .fm-grid   {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:14px; margin-bottom:20px; }}
  .fm-cat    {{ background:#fdf6f0; border-radius:12px; padding:12px; }}
  .fm-cat-label {{ font-size:.82rem; font-weight:bold; color:#888; margin-bottom:8px; }}
  .fm-chips  {{ display:flex; flex-wrap:wrap; gap:5px; }}
  /* チップ基本 */
  .fm-chip {{ position:relative; display:inline-block; padding:3px 10px; border-radius:20px; font-size:.78rem; cursor:default; background:white; color:#333; border:1.5px solid #e8e8e8; transition:transform .1s; }}
  .fm-chip:hover {{ transform:scale(1.08); }}
  /* 食べた：緑背景・緑文字・ボールド */
  .fm-eaten  {{ background:#e8f5e9; color:#2e7d32; font-weight:bold; border-color:#a5d6a7; }}
  /* 準OK：薄緑背景・薄緑文字・ボールドなし */
  .fm-derived {{ background:#f1f8e9; color:#9ccc65; border-color:#dcedc8; }}
  /* アレルゲン：枠色のみ（背景・文字色は状態に従う） */
  .fm-al-top {{ border:2px solid #e53935 !important; }}
  .fm-al-sub {{ border:2px solid #fb8c00 !important; }}
  /* サジェスト */
  .fm-next    {{ background:#f0f8ff; border-radius:12px; padding:14px; margin-top:4px; }}
  .fm-next h3 {{ font-size:.9rem; color:#666; margin-bottom:10px; }}
  .fm-sug-row {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:10px; }}
  .fm-sug     {{ background:white; border-radius:10px; padding:10px 14px; border:2px solid #e3f2fd; display:flex; flex-direction:column; gap:3px; }}
  .fm-sug b   {{ font-size:.95rem; color:#333; }}
  .fm-sug small {{ font-size:.75rem; color:#999; }}
  .fm-sug.fm-al-top {{ border-color:#e53935; }}
  .fm-sug.fm-al-sub {{ border-color:#fb8c00; }}
  .fm-legend-sep  {{ width:1px; background:#eee; margin:0 4px; align-self:stretch; }}
  .fm-legend-note {{ font-size:.75rem; color:#888; margin-right:8px; }}
  @media(max-width:600px) {{ .fm-combined {{ grid-template-columns:1fr; }} }}

  /* タイムライン */
  .tl-legend {{ display:flex; gap:16px; flex-wrap:wrap; font-size:.8rem; color:#555; margin-bottom:14px; align-items:center; }}
  .tl-legend-sleep {{ display:inline-block; width:24px; height:10px; background:#b3d9ff; border-radius:3px; vertical-align:middle; margin-right:4px; }}
  .tl-legend-dot {{ position:static !important; transform:none !important; margin-right:4px; vertical-align:middle; }}
  .tl-wrap {{ overflow-x:hidden; }}
  .tl-hours-row, .tl-row {{ display:flex; align-items:center; margin-bottom:6px; }}
  .tl-label {{ width:60px; flex-shrink:0; font-size:.8rem; color:#666; text-align:right; padding-right:10px; }}
  .tl-bar-wrap {{ flex:1; overflow:hidden; border-radius:5px; }}
  .tl-bar {{ position:relative; width:100%; height:28px; background:#f5f5f5; }}
  .tl-sleep {{ position:absolute; top:4px; bottom:4px; background:#b3d9ff; border-radius:3px; pointer-events:none; z-index:2; }}
  .tl-dot {{ position:absolute; width:10px; height:10px; border-radius:50%; top:50%; transform:translateY(-50%) translateX(-50%); cursor:default; z-index:3; }}
  .tl-breast {{ background:#f48fb1; border:1.5px solid #e91e8c44; }}
  .tl-milk   {{ background:#ffb300; border:1.5px solid #e65c0044; }}
  .tl-food   {{ background:#a5d6a7; border:1.5px solid #388e3c44; width:10px; height:10px; border-radius:2px; }}
  .tl-pee    {{ background:#e3f2fd; border:1.5px solid #90caf9; width:8px; height:8px; }}
  .tl-poo    {{ background:#d7ccc8; border:1.5px solid #8d6e63; width:8px; height:8px; }}
  .tl-hours {{ height:20px; background:transparent; }}
  .tl-hour {{ position:absolute; font-size:.65rem; color:#aaa; transform:translateX(-50%); top:2px; }}
  .tl-vline {{ position:absolute; top:0; bottom:0; width:1px; background:#e8e8e8; pointer-events:none; }}
  .tl-vline-em {{ background:rgba(80,80,200,0.18); width:1.5px; }}
  .tl-hour-em {{ color:#6060c0; font-weight:bold; font-size:.7rem; }}
  .tl-nav {{ display:flex; align-items:center; gap:12px; margin-bottom:12px; flex-wrap:wrap; }}
  .tl-btn {{ padding:5px 14px; border-radius:20px; border:1.5px solid #b0b8e0; background:white; cursor:pointer; font-size:.82rem; color:#555; }}
  .tl-btn:hover {{ background:#6060c0; color:white; border-color:#6060c0; }}
  .tl-btn:disabled {{ opacity:.35; cursor:default; }}
  .tl-nav-info {{ font-size:.82rem; color:#888; }}
  .tl-night {{ position:absolute; top:0; bottom:0; background:rgba(0,0,40,0.055); border-radius:2px; pointer-events:none; z-index:0; }}
  .tl-hoiku {{ position:absolute; top:0; bottom:0; background:rgba(255,180,50,0.22); border-radius:2px; pointer-events:all; cursor:default; z-index:1; }}
  .tl-hoiku-legend {{ display:inline-block; width:24px; height:10px; background:rgba(255,180,50,0.3); border-radius:2px; vertical-align:middle; margin-right:4px; }}
</style>
</head>
<body>
<div id="fm-tip" style="display:none;position:fixed;background:rgba(40,40,40,.92);color:#fff;padding:5px 10px;border-radius:7px;font-size:.75rem;z-index:9999;pointer-events:none;box-shadow:0 2px 8px rgba(0,0,0,.3);max-width:260px;line-height:1.5;"></div>
<h1>🌸 {BABY_NAME} の成長記録</h1>
<p class="subtitle">{subtitle_text}</p>
<div style="text-align:center;margin-bottom:20px">
  <button id="refresh-btn" onclick="doRefresh()" style="padding:7px 20px;border-radius:20px;border:1.5px solid #e07070;background:white;color:#e07070;cursor:pointer;font-size:.85rem;">🔄 最新データに更新</button>
</div>

<div class="grid">

  <!-- タイムライン -->
  {timeline_html}

  <!-- 離乳食マップ -->
  {food_map_html}

  <!-- 身長 -->
  <div class="card">
    <h2>📏 身長の推移 (cm)</h2>
    {"" if not heights else f'<div class="stats"><div class="stat"><div class="label">生後最初</div><div class="value">{heights[0][1]}cm</div></div><div class="stat"><div class="label">最新</div><div class="value">{heights[-1][1]}cm</div></div><div class="stat"><div class="label">増加</div><div class="value">+{heights[-1][1]-heights[0][1]:.1f}cm</div></div></div>'}
    <canvas id="heightChart"></canvas>
  </div>

  <!-- 体重 -->
  <div class="card">
    <h2>⚖️ 体重の推移 (kg)</h2>
    {"" if not weights else f'<div class="stats"><div class="stat"><div class="label">生後最初</div><div class="value">{weights[0][1]/1000:.2f}kg</div></div><div class="stat"><div class="label">最新</div><div class="value">{weights[-1][1]/1000:.2f}kg</div></div><div class="stat"><div class="label">増加</div><div class="value">+{(weights[-1][1]-weights[0][1])/1000:.2f}kg</div></div></div>'}
    <canvas id="weightChart"></canvas>
  </div>

  <!-- うんち最終記録 -->
  <div class="card">
    <h2>💩 うんち最終記録</h2>
    <div class="stats">
      <div class="stat" style="border-left:4px solid {poo_color}">
        <div class="label">最後のうんち</div>
        <div class="value" style="color:{poo_color}">{poo_status}</div>
      </div>
      <div class="stat">
        <div class="label">記録日</div>
        <div class="value" style="font-size:1rem">{last_poo_date_str or '—'}</div>
      </div>
    </div>
    <canvas id="pooChart"></canvas>
  </div>

  <!-- おしっこ回数 -->
  <div class="card">
    <h2>💧 おしっこ回数 (回/日)</h2>
    <canvas id="peeChart"></canvas>
  </div>

  <!-- 母乳時間 -->
  <div class="card">
    <h2>🍼 母乳時間の推移 (分/日)</h2>
    <canvas id="bfChart"></canvas>
  </div>

  <!-- 睡眠 -->
  <div class="card">
    <h2>😴 睡眠時間の推移 (時間/日)</h2>
    <canvas id="sleepChart"></canvas>
  </div>

</div>

<script>
const chartData = {json.dumps(chart_data, ensure_ascii=False)};

const milestones = {json.dumps(MILESTONE_DATES, ensure_ascii=False)};

// 各チャートのラベルセットから各マイルストーンの最近傍ラベルを求め、重複時は縦にずらす
function buildAnnotations(labels) {{
  const ann = {{}};
  if (!labels || !labels.length) return ann;
  const lastDate = new Date(labels[labels.length-1].replace(/\//g, '-'));
  const sorted = Object.entries(milestones).sort(([a],[b]) => a.localeCompare(b));
  sorted.forEach(([date, msLabel], i) => {{
    const target = new Date(date.replace(/\//g, '-'));
    if (target - lastDate > 20 * 86400000) return;  // 未来マイルストーンはスキップ
    // time scaleなのでtimestampで直接指定
    ann['ms_' + date] = {{
      type: 'line',
      scaleID: 'x',
      value: target.getTime(),
      borderColor: 'rgba(224,112,112,0.45)',
      borderWidth: 1.5,
      borderDash: [4, 3],
      label: {{
        display: true,
        content: msLabel,
        font: {{ size: 10 }},
        color: '#e07070',
        position: 'start',
        yAdjust: -(4 + (i % 4) * 14),
        backgroundColor: 'rgba(255,255,255,0.9)',
        padding: {{ x: 3, y: 1 }},
      }}
    }};
  }});
  return ann;
}}

const commonOptions = {{
  responsive: true,
  plugins: {{ legend: {{ display: false }} }},
  scales: {{
    x: {{
      type: 'time',
      time: {{
        unit: 'month',
        tooltipFormat: 'yyyy/MM/dd',
        displayFormats: {{ month: 'M月' }},
      }},
      ticks: {{ maxRotation: 0 }},
      grid: {{ color: '#f0f0f0' }}
    }},
    y: {{ grid: {{ color: '#f0f0f0' }} }}
  }}
}};

function makeChart(id, labels, data, color, type='line', yLabel='') {{
  const ctx = document.getElementById(id);
  if (!ctx || !labels.length) return;
  new Chart(ctx, {{
    type,
    data: {{
      labels,
      datasets: [{{
        data,
        borderColor: color,
        backgroundColor: type === 'bar' ? color + '88' : color + '22',
        fill: type === 'line',
        tension: 0.3,
        pointRadius: type === 'line' ? 3 : 0,
        borderWidth: 2,
      }}]
    }},
    options: {{
      ...commonOptions,
      plugins: {{
        ...commonOptions.plugins,
        annotation: {{ annotations: buildAnnotations(labels) }}
      }}
    }}
  }});
}}

makeChart('heightChart', chartData.heights.labels, chartData.heights.data, '#e07070');
makeChart('weightChart', chartData.weights.labels, chartData.weights.data, '#70a0e0');
makeChart('pooChart',    chartData.poos.labels,    chartData.poos.data,    '#8d6e63', 'bar');
makeChart('peeChart',    chartData.pees.labels,    chartData.pees.data,    '#70b0e0');
makeChart('bfChart',     chartData.bf.labels,      chartData.bf.data,      '#e090c0');
makeChart('sleepChart',  chartData.sleeps.labels,  chartData.sleeps.data,  '#70c070');

function fmSwitch(idx) {{
  const displays = ['block', 'grid', 'grid'];
  for (let i = 0; i < 3; i++) {{
    const el = document.getElementById('fm-g' + i);
    if (el) el.style.display = i === idx ? displays[i] : 'none';
  }}
  document.querySelectorAll('.fm-tab').forEach((el, i) => {{
    el.classList.toggle('fm-tab-on', i === idx);
  }});
}}

(function() {{
  const tip = document.getElementById('fm-tip');
  document.querySelectorAll('[data-tip]').forEach(el => {{
    el.addEventListener('mouseenter', e => {{
      tip.textContent = el.dataset.tip;
      tip.style.display = 'block';
    }});
    el.addEventListener('mousemove', e => {{
      const m = 12, w = tip.offsetWidth, h = tip.offsetHeight;
      let x = e.clientX + m, y = e.clientY - h - m;
      if (x + w > window.innerWidth - m) x = e.clientX - w - m;
      if (y < m) y = e.clientY + m;
      tip.style.left = x + 'px';
      tip.style.top  = y + 'px';
    }});
    el.addEventListener('mouseleave', () => {{ tip.style.display = 'none'; }});
  }});
}})();

// タイムライン ページネーション
(function() {{
  const PAGE = 7;
  const allDates = {json.dumps(timeline_all_dates)};
  let offset = 0;

  function render() {{
    const total = allDates.length;
    const endIdx = total - offset;
    const startIdx = Math.max(0, endIdx - PAGE);
    const vis = new Set(allDates.slice(startIdx, endIdx));
    document.querySelectorAll('#tl-rows .tl-row').forEach(row => {{
      row.style.display = vis.has(row.dataset.date) ? 'flex' : 'none';
    }});
    const info = document.getElementById('tl-nav-info');
    if (info) info.textContent = `${{startIdx + 1}}〜${{Math.min(endIdx, total)}} 日目 / 全${{total}}日`;
    const prev = document.getElementById('tl-prev');
    const next = document.getElementById('tl-next');
    if (prev) prev.disabled = offset >= allDates.length - PAGE;
    if (next) next.disabled = offset === 0;
  }}

  const prev = document.getElementById('tl-prev');
  const next = document.getElementById('tl-next');
  if (prev) prev.addEventListener('click', () => {{ offset = Math.min(offset + PAGE, allDates.length - PAGE); render(); }});
  if (next) next.addEventListener('click', () => {{ offset = Math.max(offset - PAGE, 0); render(); }});

  render();
}})();

function doRefresh() {{
  const btn = document.getElementById('refresh-btn');
  if (btn) {{ btn.textContent = '⏳ 更新中...'; btn.disabled = true; }}
  fetch('/refresh').then(r => r.text()).then(() => location.reload()).catch(() => location.reload());
}}

// サーバーモード時のみ: /version をポーリングして変更があれば自動リロード
(function() {{
  let lastVer = null;
  function checkVersion() {{
    fetch('/version').then(r => r.text()).then(v => {{
      if (lastVer && v !== lastVer) location.reload();
      lastVer = v;
    }}).catch(() => {{}});
  }}
  setInterval(checkVersion, 5000);
}})();
</script>
</body>
</html>
"""

output_path = str(Path(__file__).parent / OUTPUT_FILENAME)
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ HTMLファイル生成完了: {output_path}")

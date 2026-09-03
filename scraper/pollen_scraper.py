"""
東京都保健医療局「東京都アレルギー情報navi.」から花粉飛散データを取得し、JSONに変換するスクリプト。

出典: https://www.hokeniryo1.metro.tokyo.lg.jp/allergy/pollen/
このサイトにAPI・CORSは無いため、HTMLを解析して自前でJSON化する。
東京都公式サイトのコンテンツは「私的使用のための複製」が著作権法上認められており、
本スクリプトは家庭内タブレット表示という私的利用の範囲内での利用を想定している
(再配布・商用利用はしないこと)。

観測地点: 杉並(埼玉県朝霞市に最も近い観測点。朝霞市役所からの直線距離 約11.5km。
東京都の12観測点の中で最も近い。埼玉県さいたま市も公式データを公開しているが
画像(グラフ)形式のみでスクレイピング不可のため対象外。朝霞市自体・埼玉県内に
構造化データを公開している観測点は無い)

スギ・ヒノキの飛散シーズン(1〜5月)は「スギ・ヒノキ合計」ページの日別データを、
それ以外の時期は「夏から秋の花粉」ページの週別サマリーを使う
(サイト側の構成がシーズンで分かれているため)。
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

JST = timezone(timedelta(hours=9))

CEDAR_HINOKI_URL = "https://www.hokeniryo1.metro.tokyo.lg.jp/allergy/pollen/data/total.html"
HERBACEOUS_URL = "https://www.hokeniryo1.metro.tokyo.lg.jp/allergy/pollen/data/herbaceous.html"

LOCATION = "杉並"

# スギ・ヒノキ飛散シーズンの月(このサイトでは主にこの期間のみ日別データが更新される)
CEDAR_HINOKI_SEASON_MONTHS = {1, 2, 3, 4, 5}

# 日別花粉数(個/cm²/日)の目安レベル(環境省・日本気象協会等で広く使われる区分の簡易版)
LEVEL_THRESHOLDS = [
    (10, "少ない"),
    (30, "やや多い"),
    (50, "多い"),
    (100, "非常に多い"),
]


def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def parse_cedar_hinoki(html: str) -> dict | None:
    """スギ・ヒノキ合計ページから、指定地点の最新の日別観測値を取り出す。"""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table")
    if len(tables) < 2:
        return None

    daily_table = tables[1]
    header_rows = daily_table.select("thead tr")
    if len(header_rows) < 2:
        return None

    locations = [c.get_text(strip=True) for c in header_rows[0].find_all(["th", "td"])][2:]
    if LOCATION not in locations:
        return None
    loc_index = locations.index(LOCATION)  # 3列(スギ/ヒノキ/合計)ずつ並んでいる
    col_start = 2 + loc_index * 3  # 先頭2列は 日付・曜日

    body_rows = daily_table.select("tbody tr")
    for row in reversed(body_rows):
        cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if len(cells) <= col_start + 2:
            continue
        date_str, weekday = cells[0], cells[1]
        sugi, hinoki, total = cells[col_start:col_start + 3]
        try:
            total_val = float(total)
        except ValueError:
            continue
        return {
            "season": "cedar_hinoki",
            "period": f"{date_str}({weekday})",
            "values": {"スギ": float(sugi), "ヒノキ": float(hinoki)},
            "total": total_val,
            "unit": "個/cm²/日",
        }
    return None


def parse_herbaceous(html: str) -> dict | None:
    """夏から秋の花粉ページの「全地点最新飛散値」サマリーから、指定地点の最新値を取り出す。"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("#hisan table")
    if table is None:
        return None

    header_cells = [c.get_text(strip=True) for c in table.select("thead tr")[0].find_all(["th", "td"])]
    category_names = header_cells[2:]  # スギ, ヒノキ, イネ科, ブタクサ属, ヨモギ属, カナムグラ

    for row in table.select("tbody tr"):
        cells = row.find_all(["th", "td"])
        texts = [c.get_text(strip=True) for c in cells]
        if not texts or texts[0] != LOCATION:
            continue
        period = texts[1]
        values = {}
        for name, val in zip(category_names, texts[2:]):
            try:
                values[name] = float(val)
            except ValueError:
                values[name] = None
        total_val = sum(v for v in values.values() if v is not None)
        return {
            "season": "herbaceous",
            "period": period,
            "values": values,
            "total": round(total_val, 1),
            "unit": "個/cm²(観測期間合計、週1回更新)",
        }
    return None


def level_for(total_val: float, season: str) -> str | None:
    # 日別値(スギ・ヒノキ)のみレベル判定する。週間集計値は基準が異なるため判定しない。
    if season != "cedar_hinoki":
        return None
    for threshold, label in LEVEL_THRESHOLDS:
        if total_val < threshold:
            return label
    return "極めて多い"


def build_pollen_data() -> dict:
    now = datetime.now(JST)
    result = None

    if now.month in CEDAR_HINOKI_SEASON_MONTHS:
        result = parse_cedar_hinoki(fetch_html(CEDAR_HINOKI_URL))
    if result is None:
        result = parse_herbaceous(fetch_html(HERBACEOUS_URL))

    if result is None:
        return {
            "available": False,
            "reason": "データ取得失敗",
            "updatedAt": now.isoformat(),
        }

    return {
        "available": True,
        "location": LOCATION,
        "season": result["season"],
        "period": result["period"],
        "values": result["values"],
        "total": result["total"],
        "unit": result["unit"],
        "level": level_for(result["total"], result["season"]),
        "updatedAt": now.isoformat(),
        "source": "東京都保健医療局 東京都アレルギー情報navi.",
        "sourceUrl": "https://www.hokeniryo1.metro.tokyo.lg.jp/allergy/pollen/",
    }


def main() -> None:
    data = build_pollen_data()
    out_path = Path(__file__).resolve().parent.parent / "data" / "pollen.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

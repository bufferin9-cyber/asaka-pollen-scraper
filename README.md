# 花粉情報スクレイパー

[[../2026-09_タブレット家族ダッシュボード]] の花粉カード用に、東京都保健医療局
「東京都アレルギー情報navi.」のページを定期的に解析してJSON化するリポジトリ。
GitHub Actionsで定期実行し、`data/pollen.json` を自動更新する。

## 目的・概要

- ダッシュボード本体(Googleカレンダーの実IDなど個人情報を含む)とは別リポジトリに分離し、
  こちらは花粉データのみを扱う(公開しても個人情報が漏れない構成)
- ダッシュボード側は `https://raw.githubusercontent.com/<owner>/<repo>/main/data/pollen.json`
  を直接fetchする。外部の`https://`URLになるため、`file://`でダッシュボードを開いても
  ローカルファイルのfetch制限に引っかからず正常に取得できる

対象地点は「杉並」(埼玉県朝霞市に最も近い観測点、直線距離約11.5km)。
観測データの出典・私的利用の範囲についての注意点は `scraper/pollen_scraper.py` の
docstringを参照。

## 構成

```
scraper/
└── pollen_scraper.py      # スクレイピング・JSON化本体
data/
└── pollen.json             # 出力(GitHub Actionsが自動更新)
.github/workflows/
└── update-pollen.yml        # 1日2回(07:13, 15:13 JST)自動実行
requirements.txt
```

## ローカルでのテスト方法

```bash
pip install -r requirements.txt
python scraper/pollen_scraper.py
```

## 運用メモ

- 東京都側のページ構成が変わるとスクレイパーが壊れる可能性がある。
  GitHub Actionsが失敗した場合は登録メールアドレスに通知が届くので、
  それに気づいたら `scraper/pollen_scraper.py` の解析ロジックを見直すこと
- スギ・ヒノキ花粉(1〜5月)は日別データ、それ以外の時期はイネ科・ブタクサ属等の
  週間サマリーデータを使用する設計(対象サイトの構成がシーズンで分かれているため)

## 進捗

- 2026-09-03: 初版作成。[[../2026-09_タブレット家族ダッシュボード]] から花粉部分を分離独立

# ICSO 投稿パッケージメモ

## 現在のファイル

- 日本語原稿ソース: `papers/ICSO/main.typ`
- 英語投稿候補ソース: `papers/ICSO/main_en.typ`
- SPIE風Typstテンプレート: `papers/ICSO/template.typ`
- 日本語PDF: `papers/ICSO/main.pdf`
- 英語投稿候補PDF: `papers/ICSO/main_en.pdf`
- 図フォルダ: `papers/ICSO/figure/`
- 結果要約:
  - `results/icso/femap_los_summary.csv`
  - `results/icso/pat_performance_summary.csv`

## 注意

現在の `main.typ` は、SPIE A4 sample PDF / Word template の主要条件を参考にしたTypst原稿である。

ただし、SPIE公式のTypstテンプレートではないため、最終提出前には公式Word/PDF sampleと見比べる。フォーマット面で不安が残る場合は、本文をSPIE Word A4 templateへ移植して最終PDFを作る。

`main_en.typ` は `main.typ` の数値・論理・主張を保持した英語投稿候補である。最終アップロード時は、paper number を取得後に公式指定の `PaperNumber_FamilyName.pdf` 形式へファイル名を変更する。

## ビルド手順

図と数値要約を再生成する。

```powershell
python scripts/generate_icso_results.py
```

SPIE風Typst PDFを作る。

```powershell
typst compile --root . papers/ICSO/main.typ papers/ICSO/main.pdf
typst compile --root . papers/ICSO/main_en.typ papers/ICSO/main_en.pdf
```

## 投稿メタデータ案

Title:

Hierarchical prediction and feedforward correction of time-varying thermal line-of-sight bias for coarse acquisition in satellite optical communications

Authors:

Hideki Takamoto, Kazuki Takashima, Yuki Kusano, Satoshi Ikari, Ryu Funase

Keywords:

- Optical communication
- Pointing, acquisition, and tracking
- Thermal deformation
- Line-of-sight bias
- Feedforward correction

## Abstractの正本

- 日本語: `papers/ICSO/main.typ` の `abstract`
- 英語: `papers/ICSO/main_en.typ` の `abstract`

英語abstractは226語で、日本語版と同じ21ケース、16係数モデル、nested leave-one-case-out評価、PAT捕捉結果、代表2ケースの残差Fourier更新を含む。

## 最終提出前チェック

- SPIE A4 sample PDFと見比べて、余白・1カラム・title/authors/abstract/keywords/section headingの体裁を確認した。
- header / footer / page number が入っていないことを確認した。
- フォーマットに不安がある場合は、SPIE Word A4 templateへ移植した。
- 著者順と所属を確認した。
- ページ数、ファイルサイズ、参考文献形式を確認した。
- 図表番号と本文参照が一致している。
- 本文中の数値が再生成されたCSVと一致している。
- PDFを開いてレイアウト崩れがない。
- 投稿締切時刻とタイムゾーンを確認した。
- 投稿完了メールまたはスクリーンショットを保存した。

## 現時点の限界として書くこと

- 同一箱型構造の数値解析に限定され、地上試験を含まない。
- 被覆・軌道条件で残差が増える場合があり、連続発熱量は二値フラグでは十分に表現できない。
- 非熱誤差とスキャンは簡略モデルであり、点間移動、整定、確率的検出を考慮しない。
- 残差Fourier更新は代表2ケース・密サンプルでの予備評価である。

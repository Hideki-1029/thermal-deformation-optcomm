# scripts/

リポジトリ直下から実行する前提のユーティリティです。

```bash
# リポジトリルートで
python scripts/<script>.py [options]
```

---

## `export_case_matrix.py`

**役割:** 人手編集の `cases/case_matrix.xlsx` を CSV に書き出す。

```bash
python scripts/export_case_matrix.py
# 任意: --input --output --sheet
```

既定出力: `cases/case_matrix.csv`

---

## `export_orbit_catalog.py`

**役割:** 人手編集の `cases/orbit_catalog.xlsx` を CSV に書き出す。

```bash
python scripts/export_orbit_catalog.py
# 任意: --input --output --sheet
```

既定出力: `cases/orbit_catalog.csv`

---

## `export_case_inputs.py`

**役割:** 上記2つをまとめて実行（case matrix + orbit catalog）。

```bash
python scripts/export_case_inputs.py
```

---

## `build_lightweight_dataset.py`

**役割:** case / orbit / TD symbols / Femap LOS・温度 CSV を結合し、軽量 LoS モデル用データセットを作る。

```bash
python scripts/build_lightweight_dataset.py
# 任意: --case-matrix --orbit-catalog --symbol-dir --femap-result-dir
#       --output-dir --train-ratio --val-ratio --seed
```

既定出力: `results/pat_acquisition/lightweight_dataset/`

---

## `extract_mapper_temperature_probe.py`

**役割:** Thermal Desktop → Femap mapper 出力から、代表ノード（または probe set）の温度履歴を抽出する。

```bash
# 単一パネル代表点
python scripts/extract_mapper_temperature_probe.py --mapper-dir <path> --panel PANEL_PX

# probe set（cases/temperature_probe_sets.yaml）
python scripts/extract_mapper_temperature_probe.py --mapper-dir <path> --probe-set default_surface_9points
```

既定の `--mapper-dir` はローカル Femap パス。環境に合わせて指定する。

---

## `generate_icso_results.py`

**役割:** ICSO 論文用に Femap LoS 要約と PAT 性能比較の CSV / 図を生成する。

```bash
python scripts/generate_icso_results.py
```

出力: `results/icso/` および `papers/ICSO/figure/`  
（前提となる結果 CSV・PAT スクリプトが存在すること）

---

## PDF メモ読み（推奨フロー）

1. `pdf_to_png.py` … ページ画像（gitignore、図の確認用）
2. `png_to_md.py` … PNG を OCR して Markdown 化（Print-to-PDF 向け）
3. 普段は MD を読む。図欠落・文字化けのページだけ PNG を開く

（テキスト層がある PDF なら `pdf_to_md.py` でも可。`google_doc/` の Print-to-PDF は空になりやすい）

```bash
python scripts/pdf_to_png.py docs/research_notes/google_doc
python scripts/png_to_md.py  docs/research_notes/google_doc/PNG/260712_JANUS研究
```

---

## `pdf_to_png.py`

**役割:** PDF をページ単位の PNG にラスタライズする（Print-to-PDF などテキスト層なし向け）。出力は gitignore（`**/PNG/`）。

依存: `pip install pymupdf`

```bash
# フォルダ内の全 PDF → <folder>/PNG/<pdf名>/page_001.png ...
python scripts/pdf_to_png.py docs/research_notes/google_doc

# 単一 PDF → <親>/PNG/<pdf名>/
python scripts/pdf_to_png.py path/to/notes.pdf

# DPI 変更（既定は 300）
python scripts/pdf_to_png.py docs/research_notes/google_doc --dpi 144
```

---

## `png_to_md.py`

**役割:** `PNG/<名前>/page_*.png` を Tesseract OCR し、`MD/<名前>/content.md` を書く。

依存:
- `pip install pytesseract pillow`
- Tesseract OCR（`winget install --id UB-Mannheim.TesseractOCR -e`）
- 日本語データ `jpn.traineddata`（未導入なら `%LOCALAPPDATA%\tesseract-ocr\tessdata\` に配置）

```bash
# 1ドキュメント
python scripts/png_to_md.py docs/research_notes/google_doc/PNG/260712_JANUS研究

# PNG/ 配下すべて
python scripts/png_to_md.py docs/research_notes/google_doc/PNG

# 親フォルダ（中の PNG/ を見る）
python scripts/png_to_md.py docs/research_notes/google_doc
```

---

## `pdf_to_md.py`

**役割:** PDF からネイティブテキストを抽出し Markdown 化。文字が少ない／無いページは PNG へのリンクを付ける。

依存: `pip install pymupdf`  
任意: `--ocr`（PDF ページ直接 OCR。PNG 経由なら `png_to_md.py` の方がわかりやすい）

```bash
python scripts/pdf_to_md.py docs/research_notes/google_doc
python scripts/pdf_to_md.py docs/research_notes/google_doc --ocr
python scripts/pdf_to_md.py docs/research_notes/google_doc --link-png always
```

`MD/` は再生成可能だが軽いので、gitignore せずコミットしてもよい。

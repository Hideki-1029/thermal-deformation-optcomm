# ICSO `main.typ` 初稿レビュー

- 対象: `papers/icso/main.typ`
- レビュー日: 2026-08-17
- 対象範囲: 題名、abstract、論文構成、モデル検証、PAT評価、残差更新、投稿形式
- 判定: **Major revision before English translation**

## 総評

研究の芯は明確である。「熱構造解析 → 低次元予測 → PAT性能」という流れと、主張の適用範囲を同一衛星構造・同一STT/LCT配置に限定している点はよい。

一方、英訳へ進む前に修正すべき重要な不整合がある。特に、非支配軸の扱い、leave-one-case-out評価の範囲、static-bias baselineとの比較を揃えないと、「固定10係数」「未知ケースへの予測」「2成分熱残差8.5 µrad」「PAT性能」の関係が曖昧になる。

## 最優先の指摘

### 1. 非支配軸の扱いが本文と実装で異なる→実装を変更。非支配軸にb_caseのみ採用

本文は、非支配軸をモデル化せず、scan centerにも加えないゼロ補正としている。

- `papers/icso/main.typ:313`

一方、実装では評価対象ケースの先頭1軌道から求めた非支配軸の平均値を補正に使っている。

- `src/pat_acquisition/models/sunface_deltaT_bcase_los/model.py:272-300`
- 特に `model.py:297-300`

```python
static_bias = np.mean(y_all[train_mask], axis=0)
pred = np.tile(static_bias, (len(case_df), 1))
axis_idx = 0 if dominant_axis == "x" else 1
pred[:, axis_idx] = b_urad + a_urad_per_c * x_all[:, 0]
```

このため、現在のPAT結果は固定10係数の階層モデルだけによる結果ではなく、評価ケース固有の非支配軸static biasも使用した結果である。

#### 推奨対応

本文の主張を優先し、非支配軸をゼロ補正にしてPATを再計算する。その上で以下を再確認する。

- 2成分平均熱残差 8.5 µrad
- 熱のみの平均捕捉時間 0.10 s
- 非熱込みの平均捕捉時間 4.75 s
- 捕捉成功率 100 %

もし非支配軸static biasを残す場合は、モデルを「固定10係数＋ケース内校正値」と記述し、未知ケース評価という表現を弱める必要がある。

（高本）

- 現状の本文の通りに、非支配軸をゼロ補正にすると、DCバイアス成分は大きいのでこれが補正できず全体の捕捉時間が悪化（支配軸の追従の効果が半減）
- かといって非支配軸を今の設定のままstatic biasで補正すると、Kimi K3指摘にあったような、「ケース内static biasは初回捕捉前に得られない」というのに反する
  - これが本当なのか知りたい！！
  - 例えば、事前の熱解析で支配軸のa,bを決めてしまうなら、その熱解析で非支配軸のstatic biasを決めてしまうのも同じではある気がする★
  - これ普通に今の実装のまま（非支配軸はstatic bias）じゃだめなの？？★
- 非支配軸についても、同じようにaΔT + b_caseを適用するのは重いのだろうか？
- 



### 2. 「学習に用いなかったケース」は少し強すぎる→実装を変更。aもLOCOする（これはnested LOCOで対応済）

現在leave-one-case-outされているのはLevel-2のケースバイアス $b$ だけである。

- `src/pat_acquisition/models/sunface_deltaT_bcase_los/model.py:156-161`
  - 共有感度 $a_{\mathrm{shared}}$ は全ケースの $a_{\mathrm{emp}}$ の中央値から算出される。
- `model.py:197-217`
  - leave-one-case-outは $b$ のみ。
- 非支配軸平均には評価ケース自身の先頭1軌道が使われる。

したがって、abstractの「学習に用いなかったケースに対しても」という表現は、完全に未知のケースを意味するには強い。

#### 推奨対応

完全な未知ケース評価を主張する場合は、評価ケースを次のすべてから除くnested leave-one-case-outにする。

1. $a_{\mathrm{shared}}$ の算出
2. Level-2の $b$ 回帰
3. 非支配軸の補正値
4. その他のケース固有パラメータ

現状の評価を維持する場合は、次のように限定して記述する。

> ケースバイアスをleave-one-case-outで推定し、各ケースの後続軌道で時系列予測誤差を評価した。

（高本）

- これはつまり、aを算出する際にもLOCOをすべきということかな？
  - 符号が一致していれば可能
  - aはケース横断で同じ値になるので、そこまで難しくならないはず
  - aをLOCOしても、結果も大きく変わらないはず



### 3. Static-bias baselineを本文の比較表に出すべき→なし。今の方針のまま「staticは表に出さない」で行く。

現在の結果ファイルでは、熱誤差のみの17ケース平均は次の通りである。


| 補正方式            | 平均捕捉時間  |
| --------------- | ------- |
| 補正なし            | 12.07 s |
| ケース内static bias | 0.272 s |
| 階層モデル           | 0.10 s  |
| 熱真値             | 0.10 s  |


根拠:

- `results/pat_acquisition/sunface_deltaT_bcase_los_model/pat/summary.csv`

しかし、本文のPAT比較表ではstatic biasが省かれている。

- `papers/icso/main.typ:399-414`

この比較だけでは、12.1 sから0.10 sへの改善のうち、DCバイアス除去と時変モデル $a\Delta T$ の寄与を分離できない。また、`main.typ:474` の「staticな補正では1 mrad級の時変成分が残る」という説明は、現在のstatic-bias結果と整合しにくい。

#### 推奨するアブレーション

1. 補正なし
2. 単一の地上校正値／固定バイアス
3. 太陽面別 $b_0$
4. 太陽面＋発熱による階層 $b$
5. $a\Delta T$ のみ
6. 階層 $b + a\Delta T$
7. 熱真値

これにより、「条件依存DCの予測」と「軌道内時変成分の追従」がそれぞれどの程度PAT性能に効くかを説明できる。

（高本）

- Kimi K3的には、static biasの補正が実際の運用では現実的に不可能との指摘があった
  - ケース内static biasは初回捕捉前に得られないオラクル？
- しかし、よく考えると、今の階層モデルのaとb（それに伴う係数）も、事前の熱構造解析で出力するものなので、static biasもある程度妥当ではある？
  - 特に、非熱誤差込の捕捉に対する評価であれば、あり得る話ではある？
- 実際の運用において、aとbってどうやって決めるんだっけ？
- あと、やはりなぜstatic biasの結果がここまでよくなってしまうかが気になる。
  - 結構時変成分が大きい場合もあるんだけどね。



### 4. PAT指標の定義を明記する必要がある→いったん記述無し



#### 捕捉失敗は平均時間から除外されている

捕捉失敗時の捕捉時間はNaNとなり、平均は `np.nanmean` で計算される。

- `src/pat_acquisition/pat_acquisition_simulator.py:120-134`

したがって、非熱誤差込みの16.3 sは「成功試行に条件付けた平均捕捉時間」である。本文・表・abstractで明記する必要がある。

可能であれば、次のいずれかも併記する。

- 失敗を72.9 sで打ち切った全試行平均
- 成功率と成功時平均の組
- survival analysis／time-to-acquisitionの分布



#### 単一の乱数seed→いったん実装・記述無し

非熱誤差評価は単一seedの一実現である。98.3 %から100 %という成功率差を主要結果にするなら、複数seedのensembleと信頼区間が欲しい。

#### 走査中のLOSを固定している

各時刻を独立な捕捉機会として評価し、最大72.9 sの走査中も初期指向誤差を固定している。熱LOS、軌道LOS、姿勢誤差が走査中に変化しない仮定を、スキャンモデルの制約として明記する。

（高本）

- これはどういう意味？走査の時間軸と軌道・熱の変化の時間軸は異なるのだから、この仮定は妥当では？
  - 姿勢誤差に関してはその変化の周波数的に、走査中でも変化させるべきな気はする



#### 実際の外周は±1560 µrad→いったん記述変更なし

実装は次で外周のリング数を決めている。

```python
n = int(max_range_urad // step_urad)
```

$1600 // 120 = 13$ なので、走査点の最大座標は $13 \times 120 = 1560$ µradである。

- `src/pat_acquisition/pat_acquisition_simulator.py:25-41`

表の「±1600 µrad、27×27、729点」は、厳密には「設定上限1600 µrad、実点列±1560 µrad」と記載するのが正確である。

### 5. 残差更新は現段階では予備評価→題名から残差更新を外す。

残差Fourier更新には次の有利な前提がある。

- 代表2ケースのみ
- 60.5 s刻みの密な全時刻サンプルを使用
- 捕捉失敗点の残差も学習に使用
- TLE誤差を周期写像しているため、周回間の再現性が高い
  - （高本）これはおっしゃる通りだな。
- 実運用の疎な通信機会を模擬していない

本文はこれらを `main.typ:464` で適切に認めている。一方、題名とabstractでは残差更新が主結果と同等に見える。

また、abstractは「ケースバイアスの逐次更新とFourier更新を組み合わせた」と読めるが、本文表では逐次 $\delta b$ とresidual Fourierは別方式として比較されている。Fourier級数の定数項がDCを吸収する構成なら、その役割を明示し、両手法を同時に適用したという表現は避ける。

#### 選択肢

- 残差更新を題名から外し、本文では「preliminary extension」とする。
- あるいは全ケース、複数seed、疎サンプル、成功点のみで再評価して主貢献に引き上げる。



## 題名レビュー→題名を"Hierarchical Prediction and Feedforward Correction of Time-Varying Thermal Line-of-Sight Bias for Coarse Acquisition in Satellite Optical Communications"に変更



### 現在の題名

> Feedforward Correction and On-Orbit Residual Update of Time-Varying Thermal Line-of-Sight Bias for Coarse Acquisition in Satellite Optical Communications

内容は表しているが長く、代表2ケースの残差更新が主貢献と同格に見える。

### 第一候補

> Hierarchical Prediction and Feedforward Correction of Thermal Line-of-Sight Bias for Coarse Acquisition in Satellite Optical Communications

階層モデルとPATへの接続という、本稿で最も検証が厚い部分を前面に出せる。

### 採択abstractとの二層構成を残す候補

> Feedforward and Residual-Based Correction of Thermal Line-of-Sight Bias for Coarse Acquisition in Satellite Optical Communications

`On-Orbit`を外すことで、軌道上データで実証済みという誤読を避けられる。

### 投稿メタデータとの整合

提出済みabstractと現在のfull paperで題名が異なる。

- 提出済み: `Feedforward and Adaptive Correction of Time-Varying Thermal Bias for Coarse Acquisition in Optical Communication Systems`
- 現在: `Feedforward Correction and On-Orbit Residual Update ...`

参照:

- `papers/icso/icso_abstract.md`
- `papers/icso/submission_package.md`
- `papers/icso/main.typ:73`

投稿システム上で題名変更が可能か確認し、最終的に全ファイルを同期する。

## Abstractレビュー→短縮案採用。



### 現状

- 1,169文字
- PDFの第1ページの大半を占める
- 数値と副次的な残差更新まで盛り込み、主メッセージが分散している
- 「未知ケース」「熱LOS 5.5 µrad」など、評価指標の限定が省略されている
- 非熱込みの平均捕捉時間が成功試行に条件付けられていることが書かれていない

保存されているSPIEテンプレートでは、abstractは1段落、250 words以下とされている。

- `papers/icso/SPIE_template/ProcSPIETemplate_A4.docx`



### 短縮案

以下は、現時点の数値を使った暫定案である。非支配軸を修正してPATを再実行した後、数値を確定する。

> 衛星光通信の粗捕捉では、光フィードバック取得前の熱変形由来指向バイアスが走査時間を増大させる。本研究では、衛星バスの熱変形によるスターセンサ基準と光通信端末光軸の相対LOSを温度・運用情報から予測し、走査中心へfeedforward補正する手法を提案する。LEO箱型衛星の熱構造解析により、太陽指向面、内部発熱、表面特性、軌道条件を変えた21ケースのLOS時系列を生成した。支配軸LOSを太陽面—反対面温度差に対する面別感度と運用状態依存バイアスで表した結果、ケースバイアスをleave-one-case-outで推定した後続軌道のRMSEは平均5.5 µradとなり、生LOSの支配軸RMS中央値615 µradを大幅に下回った。標準COLD・標準表面の17ケースを用いた矩形走査では、熱誤差のみの平均捕捉時間を12.1 sから0.10 sへ短縮した。合成非熱誤差を含む条件では、成功試行の平均捕捉時間を16.3 sから4.75 sへ短縮し、成功率を98.3 %から100 %へ改善した。代表2ケースの予備評価では、前周回の観測残差を次周回へ適用するFourier更新が、feedforward後の周期残差をさらに低減した。



### Abstractで明確にする指標

- 615 µrad: 支配軸の生RMS中央値
- 5.5 µrad: 支配軸の後続軌道test RMSE平均
- leave-one-case-out: 現状はLevel-2のケースバイアス $b$ に適用
- 16.3 s / 4.75 s: 捕捉成功試行に条件付けた平均
- 0.10 s: 予測が熱真値と同精度という意味ではなく、現在の検出半径・走査刻みで性能が飽和した値



## 解析・再現性に関する追加推奨



### 熱構造解析

次の情報を本文または表に追加したい。

- 熱解析の初期温度
  - （高本）20℃に設定している
- 周期定常への収束判定
  - （高本）TDの機能を使用。明確な設定は覚えてないので、web上に情報ないなら書かなくていいや
- 3軌道のうち第1軌道に初期過渡が含まれるか
  - （高本）含まれない。定常になってからの値を用いている
- 熱メッシュと構造メッシュの規模
  - （高本）これはrepoのどこかに情報があったはず。熱が数十～百オーダー、構造が3万点だった気がする
- 温度マッピング方法
  - （高本）TDのmapper機能を使用しmapを出力、これをFemapに取り込んだ
- メッシュ収束確認
  - （高本）これはなんだ？
- 最小拘束の具体的な拘束自由度
  - （高本）拘束点は基準点のSTTの取付位置近くにおいて、3-2-1拘束をかけている
- STT/LCT取付面の回転抽出方法
  - （高本）これは本文に記載している？STT, LCTの回転角自体はFemapから直接出る
- 単一節点回転か、取付面の平均／平面fitか
  - （高本）STT, LCTの重心の回転。これは本文に書いてあるはず
- 構造基準温度23.9 °Cと地上アライメント校正状態の関係
  - （高本）これは特に検討していない

★ これは追加が簡単なので、表とかで書きたいかも。

### オンボード実装性

$\Delta T$を軌道上で得る方法を明確にする。

- 温度センサ位置
- パネル中心温度を実測するか、熱推定器から得るか
- センサ精度
- 量子化
- 時間遅れ
- センサ故障時の扱い

共有感度が約30 µrad/°Cなので、温度差誤差1 °Cが約30 µradのLOS誤差になる。簡単な温度ノイズ感度を追加すると実用性を説明しやすい。

（高本）

- パネル中心温度を温度センサで取得する。一般的な熱電対の温度計測精度は、0.1℃程度なので、今回のモデルにおいても問題はないはず



## 表現・数式上の指摘



### 発熱係数の適用面

実装では発熱フラグの係数をMY/PYでのみ有効にしている。

- `src/pat_acquisition/models/sunface_deltaT_bcase_los/features.py:49-80`

一方、本文の式

$$
b_{\mathrm{case}} \approx b_0(\mathrm{sun}) + c_{\mathrm{prop}} I_{\mathrm{prop}} + c_{\mathrm{pcdu}} I_{\mathrm{pcdu}}
$$

は全太陽面で発熱係数が有効に見える。MY/PYだけでゲーティングするなら、式または直後の説明で明示する。

### 半電力ケース

`main.typ:366` の「発熱フラグが離散的なためLevel-2の外挿」という表現は、厳密には外挿というより、連続発熱量を二値フラグで表したことによるモデル仕様誤差である。

候補表現:

> 半電力状態をON/OFFの二値フラグで表したため、全電力ONと同じ入力として扱われ、連続発熱量を表現できないことによるバイアスが生じた。



### 用語

論文向けには内部実装名の `bcase` を減らし、次のいずれかへ統一する。

- hierarchical bias model
- hierarchical $b_{\mathrm{case}}$ model
- hierarchical temperature-difference model

`feedforward`、`FF`、`scan center`、`coarse acquisition`、`DC`、`Level-2`についても初出で定義し、以後の表記を統一する。

（高本）

- これはおっしゃる通りで、内部実装名をそのまま使っている箇所があるので、論文用に直したい。



## 参考文献・誤記→採用



### Rüddenklau文献

`papers/icso/bibliography.bib:79-86` の著者名は `Riiddenklau` ではなく `Rüddenklau`。

また、ページは1810--1819。

- DOI: `10.2514/1.G009261`
- TU Wien書誌情報: [https://repositum.tuwien.at/handle/20.500.12708/228429](https://repositum.tuwien.at/handle/20.500.12708/228429)



### Zhang/Cheng文献

`papers/icso/bibliography.bib:89-97` は第一著者 Zhang Ping が欠落している。

正しい著者順:

1. Zhang Ping
2. Cheng Fei
3. Guan Zhe
4. He Wenzheng
5. Han Yidan

追加すべきDOI:

- `10.12347/j.ycyk.20241217006`
- 雑誌公式ページ: [https://www.spacejournal.cn/hwyjggc/en/article/id/ycyk_20241217006](https://www.spacejournal.cn/hwyjggc/en/article/id/ycyk_20241217006)

この修正後、本文の `Cheng et al.` も `Zhang et al.` に変更する。

### 誤記

- `papers/icso/main.typ:152` の「建鏡への影響」は「リンク確立への影響」などに修正する。
- `papers/icso/main.typ:237` の「軌道 模擬」は不要な空白を削除する。
- 数字と単位、LOS前後、PAT前後の空白を最終的に統一する。



## 投稿形式

ローカルで `typst compile` は成功し、PDFは20ページだった。公開されているICSO 2026の主な条件は次の通り。

- 最低6ページ
- header/footerなし
- PDF提出
- ファイル名は `Paper Number#_FamilyName`

公式ページ:

- [https://atpi.eventsair.com/icso-2026/author-instructions](https://atpi.eventsair.com/icso-2026/author-instructions)

現在の20ページは公開条件上の違反ではない。ただし、図表ブロックが18個あり、序論・関連研究・考察・結論で新規性と限界の説明が繰り返されている。英語化するとさらに長くなる可能性がある。

### 圧縮候補

- 関連研究の俯瞰表とJANUS比較表を統合する。
- 序論の研究質問、貢献、適用範囲を短縮する。
- 残差更新を「preliminary extension」の1節へ圧縮する。
- 議論と結論で繰り返している数値を減らす。
- ケース行列の詳細は必要に応じて補足資料へ移す。



### 所属

SPIEテンプレートに合わせて、所属にstreet addressとpostal codeを追加する。

候補:

> Department of Aeronautics and Astronautics, The University of Tokyo, 7-3-1 Hongo, Bunkyo-ku, Tokyo 113-8656, Japan



## 修正の推奨順序

1. 非支配軸を本文と実装で統一する。→  実装を変える
2. 完全LOOCVにするか、主張をLevel-2 $b$ のLOOCVへ限定する。→ 完全LOOCVにする
3. PATを再実行して主要数値を確定する。
4. Static-biasおよび各モデル成分のアブレーションを追加する。
5. 捕捉失敗を含む指標と複数seed評価を追加する。
6. 題名で残差更新をどの程度押し出すか決める。→ いう通り、今の残差更新はかなり理想的なものなので、題名を残差更新の主張を抑えたものにする。
7. Abstractを250 words以下相当へ短縮する。
8. 熱構造解析・温度観測・校正基準の説明を追加する。
9. 参考文献と誤記を修正する。
10. 英語化とSPIE形式の最終調整を行う。

問題が起きた。→ 

主要な仕様変更は動作しました。ただし重要な結果が出ています。非支配軸をゼロ補正にすると、PX/MXではその軸に約0.7 mradのDC成分が残るため、熱のみの平均捕捉時間は従来の0.10 sではなく約2.73 sになります。これは以前の0.10 sが評価ケース先頭軌道の非支配軸平均を暗黙利用していた影響です。

---



## 2026-08-18 対応完了メモ（非支配軸 Level-2 化 + 完全 nested LOO）



### 決定

非支配軸はゼロ補正でもケース内 static bias でもなく、**Level-2（太陽面ダミー＋発熱フラグ）で DC バイアスを事前予測**する形に実装を変更した。支配軸の `a, b` を事前の熱解析で決めるのと同じ正当性で、非支配軸の DC も同じ解析から決められる、という高本の指摘（上記★）に基づく。

### 実装

- `model.py`:
  - `estimate_case_deltaT_params` が非支配軸の学習区間平均 `b_nd_emp_urad` も返す。
  - `run_bcase_pipeline` が非支配軸用の第2の Level-2 を学習し、LOO では支配軸 b・非支配軸 b・共有感度 a を**すべて除外ケースなしで再学習**する nested LOO（`b_nd_pred_loo_urad`, `a_shared_loo_urad_per_c` 列を追加）。
  - `predict_bcase_xy` は `b_nd_urad` を必須引数にし、非支配軸 = その定数。ケース内 static bias の利用を廃止。
  - `resolve_operational_params` で 3 パラメータを一括解決（4 ランナー共通）。
- **発熱フラグのゲーティングが非支配軸では逆**（重要）: 発熱機器は ±Y 面にあり、その影響は y 軸 LOS に出る。支配軸 Level-2 は MY/PY ゲート、非支配軸 Level-2 は **MX/PX ゲート**（`BCaseConfig.nd_heat_faces`）。これを MY/PY のままにすると nd LOO RMSE が 54 µrad に悪化する（MX/PX ゲートで 3.1 µrad）。当初 predict 側が config.heat_faces を見るバグで一時 92 µrad となり、fit/predict の heat_faces 不一致として修正済み。
- 静的バイアス補正アームを PAT 評価から削除（`pat_common.BCASE_MODEL_NAMES` から除去）。



### 再実行後の数値（validate + PAT 再実行済み）

- Level-2 係数: 支配軸は不変。非支配軸 b0 = MX −594 / MY +16.6 / PX −596 / PY +25.1 µrad、c_prop = −131, c_pcdu = +22.1 µrad。
- b の LOO RMSE: 支配軸 3.8 µrad（不変）、**非支配軸 3.1 µrad（max 5.3）**。
- 固定パラメータ: 10 → **16 係数**（a 4 + b0 4×2 + c 2×2）。
- PAT（17 ケース、LOO）: 熱のみ 12.1 s → 0.10 s（不変）、非熱込み 16.3 s / 98.3% → **4.74 s / 100%**（旧 4.75）。補正後の平均熱残差（2 成分合成）8.5 → **9.0 µrad**。非熱込みの平均初期誤差 422 → 421 µrad。PY 系の補正なし 37.5–39.5 s → 37.3–39.5 s。
- §8（cases 13/16、17 ケース LOO fit）: FF 1.63→1.64 s、FF+残差 Fourier 0.78→0.79 s、Case 16 FF 1.56→1.55 s、δb の周1以降 1.32→1.35 s。直接 Fourier 側は不変（39.5 s 初周など）。
- `main.typ` に反映済み（§6 モデル定義・係数表・LOO 記述、§7 表と本文、§8 表と本文、§9、abstract、模式図の「固定16係数」）。



### 残課題（レビュー推奨順序との対応）

- 項目1（非支配軸の本文と実装の統一）→ **完了**
- 項目2（完全 LOOCV）→ **完了**（nested LOO にした）
- 項目3（PAT 再実行）→ **完了**
- 項目4（Static-bias / 成分アブレーション）→ static bias は削除済み。**実現可能成分のアブレーション（b0 のみ / +フラグ / +aΔT / フル）は未着手**
- 項目5（失敗込み指標・複数 seed）→ 未着手
- ページ数は 20 → 21 ページに微増（§6 の記述追加）。圧縮候補の検討が必要。


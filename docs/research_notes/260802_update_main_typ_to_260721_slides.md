# 260802 Update `main.typ` to 260721 Slides

- 作成日：2026-08-02
- 対象：`papers/icso/main.typ`
- 主な基準資料：`papers/seminar/20260721_optcommrg_takamoto_v3_issl.pptx`
- 目的：2026年7月21日時点の研究成果と、その後の議論・文献調査を基準に、ICSO full paperを全面改稿するための章立てと説明順を固定する。
- このノートの範囲：章構成、各章の役割、主要主張、図表候補、執筆順を整理する。本文の書き換えはまだ行わない。

## 0. 結論

現行の`main.typ`は部分修正ではなく、説明順を含めた全面改稿を行う。

論文の中心的な主張は、単純な温度差―LOS一次式の新規性ではない。次の一連の接続を主な貢献とする。

> 複数の軌道・姿勢・発熱・表面条件に対する熱構造解析から、衛星バス上で離隔したSTT–LCT間のfar-field相対LOSを生成し、その支配成分を少数温度・運用情報による階層モデルへ圧縮し、光通信粗捕捉のscan-center補正と捕捉性能まで接続した。

論文の説明順は、次の因果関係に従う。

```text
粗捕捉時の運用上の問題
→ 補正対象を予測可能な熱成分に限定
→ 衛星モデルと熱構造解析
→ STT–LCT far-field相対LOSの定義
→ ケース横断解析で得た観察
→ 階層型温度差モデル
→ ケース内・ケース間の検証
→ scan-center feedforward補正
→ 熱のみ／非熱込みPAT評価
→ JANUS等との差分、限界、Adaptiveへの帰結
```



## 1. 改稿時の基本方針



### 1.1 日本語で詳細に書く

- 初稿は日本語で作成する。
- 句読点は「、」「。」へ統一する。
- ページ数はいったん制限せず、定義、条件、評価方法を省略しない。
- 英訳時に削れるよう、各段落は主張、根拠、結果、解釈、限界を分けて書く。



### 1.2 観察結果からモデルを導く

階層モデルを最初から仮定したようには書かない。まず熱構造解析から次を観察し、その結果としてモデルを導入する。

1. 温度場と熱LOSが同じ軌道周期で変化する。
2. 太陽指向面によって支配軸と符号が系統的に変化する。
3. 同一太陽指向面では、面間温度差に対するLOS感度が比較的安定する。
4. 発熱、被覆、軌道・熱履歴によって、ケース間の平均オフセットが変化する。
5. 局所温度時系列を追加すると、面間温度差との共線性と低SNRにより係数が不安定になる。

この観察を受けて、軌道内時変を`a ΔT(t)`、ケース間差を`b_case`として分ける。


★ ここの流れを論文に残すか迷う。今回ページ上限は特にないので、研究で気づいた流れをそのまま論文に起こすのが自然ではある？まあ、基本方針はやはり解析の結果をみて気づいたことを書くのがよさそう

### 1.3 Adaptiveを主たる定量結果としない

- 現時点の定量結果は物理ベースfeedforward補正である。
- `a_sunface`は地上解析・熱真空試験で事前固定する候補とする。
- `b_case`と未モデル化された低周波DCを、将来の軌道上更新候補とする。
- 熱LOSと軌道予測誤差は同じ軌道周期帯を持つため、単純な低周波抽出で両者を分離できるとは主張しない。
- Adaptive推定器の実装・定量評価は、実施しない限り今後課題として扱う。


★ ここちょっと頑張りたい。adaptiveを一通り完成させてから論文執筆したいかも。







### 1.4 主張の適用範囲を明示する

- 同一の箱型衛星基本構造、同一STT/LCT配置、同一LOS定義における条件横断性を評価した研究である。
- 別衛星構造、別配置、実機、飛行環境への普遍的な汎化は主張しない。
- 共有感度`a_sunface`の値そのものは、評価した構造と配置に依存する。
- 移植可能性を主張する対象は、`ΔT`による軌道内成分と`b_case`によるケース間成分を分離するモデル構造である。



## 2. 推奨章立て



## 2.1 Introduction



### この章の役割

光通信粗捕捉におけるscan-center errorの問題を示し、熱変形を「予測可能な初期指向誤差成分」として扱う理由を説明する。研究の目的、研究質問、貢献、適用範囲を固定する。

### 説明順

1. 衛星光通信では狭いビームによりPATが重要となる。
2. 粗捕捉前には安定した光フィードバックを利用できない。
3. 軌道、姿勢、アライメント、熱変形等を含む初期指向誤差が探索領域を広げる。
4. 熱変形は軌道、太陽指向面、表面特性、発熱状態と関係するため、事前予測できる可能性がある。
5. 本研究は全指向誤差を除去せず、予測可能な熱LOSをscan centerからfeedforwardで差し引く。
6. 既存研究と未解決点を短く示す。
7. 本稿の研究質問と貢献を提示する。



### 研究質問

- 衛星バス上で離隔したSTT–LCT間の熱変形LOSは、少数の温度・運用情報で予測できるか。
- 太陽面、発熱、表面特性、軌道条件をまたいで、共有可能な低次元モデルを構成できるか。
- 予測熱LOSを粗捕捉のscan centerへ反映すると、熱のみ、および非熱誤差が共存する条件で捕捉性能を改善できるか。



### 貢献の候補

1. Thermal DesktopとFemap/Nastranを用いて、複数条件におけるSTT-relative far-field LOS時系列を生成した。
2. 軌道内時変とケース間DCを分離する階層型温度差モデルを構築し、leave-one-case-outで条件横断性を評価した。
3. 予測LOSを光通信粗捕捉シミュレータへ接続し、捕捉時間と成功率への効果を評価した。



### 入れないもの

- 階層モデルの詳細式。
- 全係数と全結果。
- Adaptive更新式の詳細。



## 2.2 Previous Research and Positioning



### この章の役割

熱変形LOS、光通信粗捕捉、温度情報を用いたLOS補正の先行研究を整理し、本研究の差分を式形ではなく対象システム、入力、出力、評価目的で示す。

### 先行研究の分類

1. 光通信PATと初期指向誤差。
  - Kaushal and Kaddoum。
  - TBIRD。
  - body-pointing feedforward compensation。
2. 衛星バス熱変形と光通信捕捉。
  - Shi et al.によるSTT/LCT配置・構造最適化と捕捉時間。
3. 地球観測系の熱変形LOS補正。
  - Hu et al.のGEO時系列補正。
  - Li et al.のLEO観測条件とデータ駆動補正。
4. JANUSのSTOP解析と地上試験。
  - 2019年STOP解析。
  - 2021年大気中地上試験。



### JANUS 2019 STOP解析で書く内容

- ESATAN-TMS、NASTRAN、ZEMAXを接続したSTOP解析である。
- JANUS Optical Head Unit内部のLOS変化を対象とする。
- 光学要素個別の変形より、Opto-Mechanical Structure全体の回転がLOSを支配した。
- Optical WallとBaffle Wallの温度差とLOSの比例関係を導いた。
- `LoS ≈ α ΔT_walls`と、その予測不確かさを構成した。
- 校正時と科学観測時のLOS差としてAKEを扱い、共通バイアスを差し引く。
- ミッション条件と設計が固定されたJUICE/JANUSを対象とする。



### JANUS 2021地上試験で書く内容

- OHU STMを大気中で段階加熱した。
- Optical Cubeの回転をTheodoliteで測定した。
- `K ≈ 7.2 µrad/°C`を不確かさ付きで同定した。
- 実測温度分布を入力したSTOP FEMと地上試験結果が不確かさ範囲内で整合した。
- 実機ではOptical WallとBaffle Wallの2個のPT1000からLOSとAKEを推定する構成である。
- Flight ConfigurationのEnd-to-End光学試験ではなく、支配構造モードと比例係数の構造レベル検証である。



### JANUSと本研究の差分


| 観点   | JANUS                       | 本研究                      |
| ---- | --------------------------- | ------------------------ |
| 対象   | 単一光学ヘッド内部                   | 衛星バス上で離隔したSTT–LCT間       |
| 補正量  | 校正時からのLOS/AKE変化             | 粗捕捉開始時のscan-center error |
| 温度入力 | Optical Wall–Baffle Wall温度差 | 太陽面–反対面パネル温度差と運用フラグ      |
| モデル  | 原点通過の比例モデル                  | `a ΔT + b_case`の階層モデル    |
| 条件   | 固定ミッションの代表4熱ケース             | 太陽面、発熱、被覆、軌道を含む21ケース     |
| 評価出力 | LOS/AKEと不確かさ                | LOS残差、捕捉時間、捕捉成功率         |
| 検証   | STOP解析と地上試験                 | 現時点では数値解析                |




### 新規性の書き方

温度差とLOSの一次関係自体を新規性としない。次を差分とする。

- JANUSで示された低次元温度勾配モデルの考え方を、衛星バス上のSTT–LCT相対LOSへ適用したこと。
- 条件間で変わるDC成分を、太陽面と発熱状態から階層的に予測したこと。
- 予測LOSを光通信粗捕捉のscan centerへ接続し、捕捉性能で評価したこと。



## 2.3 Problem Formulation and LOS Definition



### この章の役割

補正対象、座標系、LOS定義、scan-center補正式を固定する。後続章で「LOS」の意味が変化しないようにする。

### 書く内容

1. STTを衛星姿勢基準とする。
2. LCTの外向きboresightを通信光軸とする。
3. 遠方通信へ直接寄与するのは、STT基準で見たLCT光軸の相対回転である。
4. STT/LCT代表点間の並進から算出されるcenterline tiltは、構造診断量として保持するが、far-field PAT LOSには加えない。
5. 熱LOS真値を次のように定義する。

```text
θ_thermal,true(t) = θ_LCT,rot(t) − θ_STT,rot(t)
```

1. scan-center補正と残差を定義する。

```text
θ_scan(t) = θ_nominal(t) − θ_hat_thermal(t)

e_scan(t) = e_nonthermal(t)
          + θ_thermal,true(t)
          − θ_hat_thermal(t)
```



### 図候補

- STT、LCT、代表基準面と光軸の模式図。
- far-field相対回転とcenterline tiltの比較図。
- 熱成分だけをscan centerから差し引く問題設定図。



## 2.4 Spacecraft and Thermo-Structural Analysis Model



### この章の役割

熱LOS時系列が、どのモデル、入力、解析手順から得られたかを再現可能な粒度で説明する。

### 2.4.1 Spacecraft configuration

- 箱型衛星バスの寸法。
- パネル厚、材料。
- STT、LCT、PROP、PCDUの配置。
- LCT boresightと各面のMX、MY、PX、PY、MZ、PZ表記。
- 実衛星の完全再現ではなく、小型衛星を模した代表モデルであること。



### 2.4.2 Thermal Desktop analysis

- 軌道高度、LTAN、周期、日照・食条件。
- 解析時間、軌道数、サンプリング。
- 太陽指向面。
- 表面熱光学特性。
- 各機器の発熱量と発熱モード。
- TDからパネル・節点温度時系列を出力すること。



### 2.4.3 Femap/Nastran thermoelastic analysis

- TD温度場を構造モデルへマッピングする方法。
- 材料物性、CTE、Young率、Poisson比、基準温度。
- 拘束条件。
- 節点並進・回転6成分を出力すること。
- Femapはプリ・ポスト環境、Nastranは構造ソルバーとして表記を整理する。



### 2.4.4 LOS post-processing

- STTとLCTの代表節点・基準面。
- 座標変換。
- far-field LOSのx、y成分。
- 支配軸の決定方法。



### 図表候補

- 衛星モデルと機器配置。
- TD → Nastran → LOS後処理の解析フロー。
- TD条件表。
- Femap/Nastran条件表。
- 内部発熱量と配置の表。



## 2.5 Case Matrix and Observed Thermal-LOS Characteristics



### この章の役割

モデル化前に、何を変化させ、何を固定し、熱LOSにどのような規則性が現れたかを示す。

### ケース設計

- 評価ケース数は21ケース。
- 太陽指向面：MX、MY、PX、PY。
- 発熱モード：STT/LCT、+PROP、+PCDU、ALL。
- PROP半電力ケース。
- 表面特性：0.5、Black、Alodine。
- 軌道・熱環境：LTAN06/COLD、HOT、LTAN18 Sentinel-1 proxy等。
- 固定条件：基本構造、STT/LCT配置、材料、LOS定義。



### 代表結果から示す観察

1. 温度場とfar-field LOSが軌道周期で変化する。
2. MY/PYではy軸、MX/PXではx軸が支配的となる。
3. 太陽面によって感度の符号が変わる。
4. 熱LOSの大きさは、MYで約150–260 µrad、PX/MXで約0.6–0.9 mrad、PYで約1.2 mradに達する。
5. 発熱、被覆、軌道条件は平均オフセットと一部の波形残差へ影響する。



### この章からモデル章への接続

```text
軌道内で連続的に変化する成分
→ 太陽面–反対面の温度差で説明する。

ケースごとに変化する平均成分
→ 太陽面、発熱、被覆、軌道条件に関係するケースDCとして分離する。
```



### 図表候補

- 全21ケースのcase matrix。
- 代表MYケースの各面温度時系列とfar-field LOS。
- 太陽面ごとの支配軸と生LOSオーダーの表。



## 2.6 Hierarchical Temperature-Difference Model



### この章の役割

観察結果を、軌道上で利用可能な少数入力・固定少数係数のモデルへ落とし込む。

### 2.6.1 Modeling requirement

- TD/Femap/Nastranをオンボードで実行しない。
- 少数温度センサと既知の運用情報だけを用いる。
- scan-center補正量を直接出力する。
- 係数を物理的・運用的に解釈できるようにする。



### 2.6.2 Level 1：軌道内時変

```text
ΔT(t) = T_sunface(t) − T_opposite(t)

θ_dom(t) = b_case + a_sunface ΔT(t) + ε(t)
```

- `θ_dom(t)`：太陽指向面から定まる支配軸の熱LOS。
- `a_sunface`：同一太陽指向面の複数ケースで共有する温度感度。
- `b_case`：各ケースの平均的なLOSオフセット。
- `ε(t)`：モデル化されない軌道内残差。



### 2.6.3 Level 2：ケース間DC

```text
b_case = b0_sunface
       + c_PROP I_PROP
       + c_PCDU I_PCDU
       + η_case
```

- `b0_sunface`：太陽面ごとの基準DC。
- `I_PROP`、`I_PCDU`：定常発熱モードを示すフラグ。
- `η_case`：被覆、軌道条件、過渡等を含む未モデル化ケース差。



### 2.6.4 モデル選択の根拠

- 局所機器温度時系列を追加したモデルも検討した。
- `corr(ΔT, T_PCDU) ≈ 0.995`程度の強い共線性があった。
- 局所温度変動の標準偏差は約0.1°Cと小さかった。
- 係数が巨大化し、ケース間で不安定になった。
- 効いていた発熱効果は、軌道内追加波形よりケース平均DCとして安定していた。



### 現行Level-2の限界

- `c_PROP`、`c_PCDU`は太陽面によらない第一版の係数である。
- 発熱量を連続値として扱っていない。
- 軌道途中のON/OFF過渡を扱っていない。
- HOT/COLD、被覆を明示的なLevel-2入力にしていない。
- 定常運用モードに対する近似として位置づける。



### 図候補

- Level 1とLevel 2の階層モデル模式図。
- 局所温度特徴追加が不安定になる理由の模式図または補足表。



## 2.7 Parameter Identification and Cross-Case Validation



### この章の役割

学習データ、test区間、共有感度の決め方、LOO評価を結果より先に説明する。

### 学習・検証手順

1. 各ケースの先頭1軌道を学習区間とする。
2. ケースごとにLevel 1をfitし、`a_emp`と`b_emp`を求める。
3. 同一太陽面の`a_emp`の中央値を`a_shared`とする。
4. 後続2軌道で`a_shared`による時系列予測を評価する。
5. 全ケースの`b_emp`を用いてLevel 2をfitする。
6. 1ケースを除外してLevel 2を再学習し、除外ケースの`b_pred`を予測する。
7. ケースDCのLOO誤差と、最終LOS時系列のLOO test RMSEを分けて報告する。



### 報告する最新結果



#### 共有感度


| Sun face | `a_shared` [µrad/°C] |
| -------- | -------------------- |
| MX       | +30.6                |
| MY       | +28.6                |
| PX       | −28.1                |
| PY       | −28.7                |




#### Level-2係数


| Feature  | Coefficient [µrad] |
| -------- | ------------------ |
| `b0_MX`  | +15.7              |
| `b0_MY`  | +2.8               |
| `b0_PX`  | −12.0              |
| `b0_PY`  | −24.0              |
| `c_PROP` | −22.9              |
| `c_PCDU` | −10.2              |




#### 誤差指標

- Level-2 in-sample RMSE：約3.1 µrad。
- Level-2 leave-one-case-out RMSE：約3.8 µrad。
- 最終`b_pred,LOO + a_shared ΔT`の平均test RMSE：約5.5 µrad。
- median raw thermal LOS RMS：約615 µrad。
- 標準ケースでは数µrad、PROP半電力ケースでは約15 µradの残差。



### 結果の解釈

- 感度の絶対値が約28–31 µrad/°Cにまとまったことは、同一基本構造内で共有係数を使える可能性を示す。
- 3.8 µradはケースDC予測のみの誤差である。
- 5.5 µradはケースDC誤差と軌道内残差を含む最終時系列予測誤差である。
- raw RMSとprediction RMSEは異なる統計量であるため、オーダー比較であることを明記する。



### 図候補

- `a_emp`の太陽面別分布。
- `b_emp`対`b_pred`のin-sample/LOO比較。
- 標準case 05と半電力case 22の時系列。
- raw thermal LOSと最終LOO test RMSEの比較。
- Black、half-power、LTAN18の難しいケース。



## 2.8 Coarse-Acquisition Simulation



### この章の役割

LOS予測誤差を、粗捕捉の捕捉成否と捕捉時間へ変換する評価方法を定義する。

### 2.8.1 Signal flow

```text
熱LOS真値
− モデル予測熱LOS
+ 軌道、姿勢、アライメント、ドリフト等の非熱誤差
= scan-center residual
→ rectangular spiral scan
→ acquisition success / time
```



### 2.8.2 Scan model


| Parameter         | Value       |
| ----------------- | ----------- |
| Scan range        | ±1600 µrad  |
| Grid spacing      | 40 µrad     |
| Detection radius  | 25 µrad     |
| Dwell time        | 0.1 s/point |
| Total scan points | 6561        |
| Maximum scan time | 656.1 s     |




### 捕捉判定

- 真の指向誤差が検出半径内に入った最初の走査点を捕捉時刻とする。
- 最大走査範囲・時間を超えた場合は失敗とする。
- 平均捕捉時間は成功試行に条件付けられた統計量であることを明記する。



### 簡略化

- 点間のslewとsettlingを考慮しない。
- 受光強度の確率変動を考慮しない。
- 各走査点を独立な捕捉機会として扱う。
- 走査中の対象方向変化を簡略化する。
- 特定LCTの実装を再現した捕捉モデルではなく、残差の相対比較を行うための簡略モデルである。



### 比較モデル

最低限、次を比較する。

1. No thermal correction。
2. Static bias correction。
3. Hierarchical `b_case + a ΔT` correction。
4. Thermal-truth correction。実装可能手法ではなく理想上限。

追加候補。

1. JANUS-inspired proportional baseline。校正基準を明示した原点通過`a ΔT`。
2. Fourier baseline。
3. Temperature-feature Ridge baseline。



## 2.9 Nonthermal Error Model



### この章の役割

熱モデル単体の能力評価と、非熱誤差が共存するPAT主評価を分ける。

### 非熱誤差の構成

```text
e_nonthermal = e_orbit
             + e_alignment
             + e_attitude
             + e_drift
```



### 軌道予測誤差

- Sentinel-1の最新TLEをSGP4で伝播する。
- AUX_POEORBを高精度軌道暦の参照値とする。
- 位置誤差をリンクLOS横断面へ射影する。
- STT/body x–yへ変換し、熱LOSと同じ2成分で加算する。
- partnerとリンク幾何を太陽面ごとに定義する。
- 既存のlegacy基底に現れた成分不連続を物理的LOSジャンプとして解釈しない。



### その他の非熱誤差

- Alignment：温度勾配とは独立な取付・組立・衝撃由来の準静的誤差。
- Attitude：簡略化された広帯域姿勢誤差。
- Drift：低周波の未モデル化変動。
- 特定衛星の誤差バジェット再現ではなく、GNSS非搭載LEO小型衛星の共存シナリオであることを明記する。



### 周波数帯の解釈

- 熱LOSと軌道予測誤差は、ともに軌道周期およびその近傍の周波数成分を持つ。
- 単純な「低周波＝熱」という観測分離は困難である。
- だからこそ、温度と運用状態を用いた事前feedforwardに意味がある。



## 2.10 PAT Results



### この章の役割

熱モデルの能力評価と、非熱共存下のシステム評価を分けて示す。

### 2.10.1 Thermal-only evaluation


| Model                 | Success | Mean acquisition time | Mean thermal residual |
| --------------------- | ------- | --------------------- | --------------------- |
| No correction         | 95.9%   | 124.6 s               | 667 µrad              |
| Static bias           | 99.3%   | 4.78 s                | 108 µrad              |
| Hierarchical `b_case` | 100%    | 0.116 s               | 8.8 µrad              |
| Thermal truth         | 100%    | 0.100 s               | 0 µrad                |


解釈。

- Thermal-onlyは軽量モデルが熱成分を除去する能力を見る理想条件である。
- static biasでも大きく改善するが、軌道内の時変成分が残る。
- 階層モデルは平均オフセットと軌道内変動の両方を補正し、thermal-truth上限に近づく。



### 2.10.2 Thermal plus nonthermal evaluation


| Model                    | Success | Mean acquisition time | Median acquisition time |
| ------------------------ | ------- | --------------------- | ----------------------- |
| No thermal correction    | 94.0%   | 156.9 s               | 150.3 s                 |
| Hierarchical feedforward | 97.1%   | 59.6 s                | 36.2 s                  |


主張。

- 本簡略走査条件では、平均捕捉時間が約62%短縮した。
- 捕捉成功率は3.1 percentage points改善した。
- 熱補正後は非熱誤差、特に軌道予測誤差が残差を支配する。
- 熱補正ですべての指向誤差を除去したのではなく、熱由来の探索負荷を非熱誤差床まで低減したと解釈する。



### 2.10.3 Case dependence

- PYのように熱LOSが約1.2 mradと大きい場合、改善幅が大きい。
- MYのように熱LOSと軌道誤差が同程度の場合、改善は中程度となる。
- PXでは熱補正後も軌道誤差が大きく残る。
- LTAN18 MYのように熱LOSがほぼDCの場合、staticとの差は小さくなる。
- 改善幅は熱バイアスの大きさだけでなく、リンク幾何と非熱誤差の大きさに依存する。



### 図表候補

- PAT評価フロー。
- Thermal-onlyの比較棒グラフ。
- Nonthermal込みの捕捉時間・成功率比較。
- 代表MY/PYケースの時系列と捕捉時間。
- ケースファミリごとの解釈表。



## 2.11 Discussion



### 2.11.1 研究質問への回答

- 面間温度差により、支配軸熱LOSの軌道内変動を数µradから十数µradの残差で予測できた。
- 同一基本構造内では、太陽面ごとの共有感度がケース横断で安定した。
- ケースDCは太陽面と発熱フラグで一定程度予測できた。
- 非熱誤差が共存しても、熱が大きいケースでは捕捉負荷を低減できた。



### 2.11.2 JANUSとの関係

- JANUSは、温度勾配からLOSを予測する物理ベース軽量モデルが、実機光学ヘッドと地上試験で成立することを示した先行例である。
- 本研究は、その考え方を衛星バス上のSTT–LCT相対LOSと光通信粗捕捉へ展開する。
- JANUSの原点通過モデルは校正状態からのLOS変化を扱う。本研究の`b_case`は、未校正のケース差または運用状態依存DCを明示的に扱う。
- JANUSには地上検証があるため、本研究が実験的妥当性で優れているとは主張しない。



### 2.11.3 Adaptiveへの帰結

- `a_sunface`はケース横断で安定しており、地上で固定する候補である。
- `b_case`は発熱、被覆、軌道・熱履歴で変わるため、運用テーブルまたは軌道上更新候補である。
- 捕捉後残差をすべて熱DCとして吸収すると、軌道誤差やアライメント誤差を誤学習する可能性がある。
- 更新には、同一運用モードの複数パス平均、軌道誤差の別状態推定、更新量制約が必要である。
- 本稿では設計指針までとし、推定器の実装は今後課題とする。



### 2.11.4 Limitations

1. 箱型代表衛星モデルであり、実機構造ではない。
2. 別衛星構造、別STT/LCT配置への汎化は未評価。
3. 支配軸を主対象とし、非支配軸の詳細モデル化は未完。
4. `c_PROP`、`c_PCDU`の太陽面依存を未検証。
5. 発熱量の連続値と軌道途中ON/OFF過渡を未評価。
6. HOT/COLD、被覆条件の完全なLevel-2一般化は未完。
7. TD/Femap/Nastranモデルの実験検証は未実施。
8. PAT走査モデルはslew、settling、受光確率等を簡略化している。
9. 非熱誤差は特定衛星の完全な誤差バジェットではない。
10. Adaptive補正は未実装・未評価。



## 2.12 Conclusion



### この章で答えること

- 何を解析したか。
- どのモデルを構築したか。
- どの範囲で有効だったか。
- PAT性能へどの程度つながったか。
- 何が未解決か。



### 入れる最新数値

- 21ケース。
- 共有感度の絶対値は約28–31 µrad/°C。
- ケースDCのLOO RMSEは約3.8 µrad。
- 最終LOS時系列の平均LOO test RMSEは約5.5 µrad。
- Thermal-onlyで124.6 sから0.116 s。
- Nonthermal込みで156.9 sから59.6 s、成功率94.0%から97.1%。



### 書き方の注意

- thermal-truthは実装可能手法ではなく理想上限とする。
- 捕捉時間は簡略走査モデルの条件付き結果とする。
- 別構造・実機への一般化を結論で拡大しない。
- Adaptiveが完成したようには書かない。



## 3. 図表の暫定構成

ページ数を制限しない初稿では、次の図表を候補とする。英訳・投稿版で統合または削減する。

### Figure 1：研究の問題設定

```text
日照・食／内部発熱
→ 温度場
→ STT–LCT相対LOS
→ scan-center error
→ feedforward補正
```

PowerPointのスクリーンショットではなく、Typstで再作図する。

### Figure 2：地上解析と軌道上運用の全体フロー

```text
Orbit/attitude/heat/coating
→ Thermal Desktop
→ Nastran thermoelastic response
→ STT–LCT LOS
→ lightweight model
→ PAT scan center
```

Typstで再作図し、必要ならTD/Femapの小画像を配置する。

### Figure 3：衛星モデルと機器配置

- TDモデル。
- Femapモデル。
- STT、LCT、PROP、PCDU位置。
- boresight。



### Table 1：TD/Femap/Nastran解析条件



### Table 2：内部発熱条件



### Figure 4：LOS定義

- STT基準面。
- LCT基準面。
- far-field相対回転。
- centerline tiltを含めない理由。



### Table 3：21ケースのcase matrix



### Figure 5：代表ケースの温度場とfar-field LOS

- MYケースの各面温度。
- 同ケースのx、y far-field LOS。



### Figure 6：階層モデル

- Level 1とLevel 2を一図にまとめる。



### Figure 7：共有感度

- `a_emp`の太陽面別分布。
- `a_shared`の値。



### Figure 8：Level-2ケースDC予測

- `b_emp`対`b_pred`。
- in-sampleとLOOを並べる。
- 係数表を併記する。



### Figure 9：代表時系列

- 標準case 05。
- 半電力case 22。



### Figure 10：全ケースのraw LOSと予測残差

- raw RMSとtest RMSEが異なる統計量であることを明記する。
- 可能なら同一統計量で再作図する。



### Figure 11：PAT評価フローとスキャン条件

- 残差計算。
- rectangular spiral。
- 成功判定。



### Figure 12：Thermal-only PAT結果



### Figure 13：Nonthermal込みPAT結果



### Figure 14：ケース依存性

- MY/PY代表ケース、またはケースファミリ表。



### Figure 15：難しいケース

- Black。
- half-power。
- LTAN18。

本文に入らない場合はAppendixへ移す。

## 4. 現行`main.typ`から削除・置換するもの



### 削除または全面置換

- 17ケースに基づくすべての数値。
- Level-2 LOO RMSE 2.3 µradという記述。
- 非熱込み171.0 s → 21.8 sという旧結果。
- 旧Level-2係数。
- 旧PAT比較図。
- 現在の簡略な熱構造解析説明。
- JANUSを2021年地上試験だけで説明する関連研究節。



### 残せる考え方

- far-field STT-relative LOSを採用する理由。
- `ΔT`による軌道内時変と`b_case`によるケース間DCの分離。
- thermal-onlyとnonthermal込みを分ける評価方針。
- Adaptiveを後段として位置づける考え方。
- 別構造への一般化を主張しない姿勢。



## 5. 執筆の推奨順序

全面改稿は次の単位で進める。

### Step 1：論文骨格の固定

- このノートの章立てを確認する。
- タイトルにAdaptiveを残すか決める。
- 本文で使う主結果と限界を固定する。



### Step 2：IntroductionとPrevious Research

- JANUS 2019/2021を追加する。
- Shi、Hu、Li、TBIRD、feedforward研究との位置づけを整理する。
- Contributionを固定する。



### Step 3：Problem FormulationからCase Matrix

- 衛星モデル、解析条件、LOS定義を詳細化する。
- 21ケースを正式な評価集合として定義する。
- 観察結果からモデルへつなぐ。



### Step 4：ModelとValidation

- Level 1、Level 2、学習区間、test区間、LOOを記述する。
- 3.8 µradと5.5 µradを分けて報告する。
- 難しいケースとモデル選択理由を含める。



### Step 5：PATとNonthermal

- 残差式、スキャン条件、成功判定を定義する。
- 最新の21ケース結果へ更新する。
- 軌道誤差の座標系とリンク幾何を明記する。



### Step 6：DiscussionとConclusion

- JANUSとの差分を再確認する。
- Adaptive更新対象を結果から導く。
- Limitationsを主張と対応させる。



### Step 7：Abstractとタイトル

- 全本文が固まった後で書く。
- 数値は本文・図表・Conclusionと機械的に照合する。
- 英訳は日本語版の論理と数値が確定してから行う。



## 6. 改稿前に判断が必要な事項

1. タイトルに`Adaptive Correction`を残すか。
2. JANUS-inspired proportional baselineを追加解析するか。
3. Fourier baselineを本文に入れるか。
4. `c_PROP/c_PCDU`のsun×heat交互作用を追加解析するか。
5. 現行の21ケースすべてを主結果へ含めるか、標準ケース群とchallenge casesを分けるか。
6. 軌道予測誤差の詳細図を本文に置くか、Appendixへ置くか。
7. PAT結果をmean acquisition timeだけでなく、成功率、median、p95までどこまで示すか。
8. `raw RMS`対`test RMSE`図をそのまま使うか、同一統計量で再作図するか。
9. Adaptiveについて、概念説明だけにするか、簡単な更新式まで示すか。



## 7. 参照する研究ノート

- `docs/research_notes/260715_icso_paper_outline.md`
- `docs/research_notes/260718_orbit_prediction_error_assumptions.md`
- `docs/research_notes/260718_pat_error_budget_frequency.md`
- `docs/research_notes/260721_rg_slide_retrospective_and_paper_narrative.md`
- `docs/research_notes/260722_optcomm_rg_feedback_response_plan.md`
- `docs/research_notes/260723_review_icso_paper.md`
- `docs/research_notes/260724_JANUS_STOP_review.md`
- `docs/research_notes/260725_JANUS_GROUND_TEST.md`
- `docs/research_notes/google_doc/MD/260711_モデル先行研究/content.md`
- `docs/research_notes/google_doc/MD/260712_JANUS研究/content.md`
- `docs/research_notes/google_doc/MD/260717_Adaptiveモデル/content.md`
- `docs/research_notes/google_doc/MD/260720_光RG発表/content.md`



## 8. 次の作業

この章立てを確認後、まずIntroductionとPrevious Researchを日本語で全面改稿する。その際、JANUS 2019 STOP解析の参考文献を`bibliography.bib`へ追加し、2021年地上試験の著者情報を完全な形へ修正する。
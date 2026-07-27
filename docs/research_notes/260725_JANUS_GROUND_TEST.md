# 260725 JANUS Ground Test Review

- 作成: 2026-07-25
- 目的: 2026/7/25 JANUS STOP解析に対する答え合わせ的な論文。地上で大気下で試験した場合の式の正しさを評価する。in Barcelonaへの飛行機
- 主な入力:
  - `docs/literature/JANUS_Optical_Head_Line_of_Sight_Temperature_dependence_Characterization_and_Validation_by_on_ground_test.pdf`


---
## 1. 論文読み -Turella, JANUS Ground Test -

### Abstract
- ミッション的にLOSの精度に対する要求が高い
- JANUSのLOSは熱環境で変わりうる
- JANUSの温度場を変えうる要素は、
  - 軌道姿勢の変更
  - 宇宙機のマヌーバ
  - サイエンスペイロードの内部発熱（heat dissipationってなに？★）
- STOP解析を実施し、光学要素の並進移動・回転を出力
- 結果、LOSの値・uncertaintyとOHUの構造の温度勾配の間に線形関係があることを発見
- この関係性を、実際に地上大気試験で示した
- 試験で得た係数を用いることで、OHUの温度センサの値を読むことで、LOSの予測と（不確定さの？）評価をリアルタイムかつindirectに行うことができる。


### 1. INTRODUCTION
- JUICEミッションは、3つのGalelian moonを探査する
- Ganymedeに行くSpace Craftは初めてになる予定
- ミッションの目的：
  - 惑星構成の必要条件
  - 生命の発現
- JANUSはカメラ
- JANUSはJovian 大気調査とGanymedeのLibrationの計測が目的
- OHUのLOSの知識と特徴づけが非常に重要
- STOP解析とそのverificationがこの論文のメイン


### 2. LOS CHARACTERIZATION WITH IN-AIR TEST
- Opto Mechanical Structure；OMS に注目した試験をする
  - → LOSにおいてメインのcontributer。Baffle Wall とOptical Wallの間の温度差
- [2] 論文：JANUS STOP解析 によると、
  - LOS = LOS_Y
- OMS以外の全ての要素のLOSに対する寄与が無視できるほど小さいことは既知とする（これは前回のSTOP解析でわかったこと）
- TESTはOHUのSTMを用いて行われた
  - Focal Plane ModuleとFilter Wheel ModuleのSTMが入っている
  - ハーネスや宇宙機のpurging lineは入ってない←purging lineってなに？★
- FPMのDetectorやPCBのひずみ、FWM Filterの回転・ひずみは考慮しない

#### A.Concept

# 算法层说明

`algorithm` 是 BusMind 的候选线路评分算法层，负责离线数据集构建、伪标签生成、模型训练评估，以及向后端提供统一的候选路线打分入口。

## 目录结构

```text
algorithm/
  dataset/   # 离线训练数据、伪标签和数据构建脚本
  model/     # 线性、XGBoost、TabPFN 评分模型及评估脚本
  routing/   # 候选路线搜索图逻辑，后端和离线构建共用
```

## 工作链路

1. `routing/` 和后端数据共同生成候选公交路线。
2. `dataset/scripts/build_features.py` 把候选路线整理为 `features/features.csv`。
3. `build_rule_pseudo_labels.py` 和 `build_llm_pseudo_labels.py` 生成伪标签。
4. `model/*/train.py` 使用融合标签训练候选线路评分模型。
5. `model/evaluation/compare.py` 对比 Linear、XGBoost 和 TabPFN。
6. 后端通过 `algorithm.model.predictor.predict_recommendation` 调用当前配置的模型。

## 常用命令

构建数据与标签：

```powershell
python .\algorithm\dataset\scripts\build_features.py --groups 1000
python .\algorithm\dataset\scripts\summarize_features.py
python .\algorithm\dataset\scripts\build_rule_pseudo_labels.py
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py fuse
```

训练和对比模型：

```powershell
python .\algorithm\model\linear_scoring\train.py
python .\algorithm\model\xgboost_scoring\train.py
python .\algorithm\model\tabpfn_scoring\train.py --max-train-rows 1000
python .\algorithm\model\evaluation\compare.py --plot-curves
```

切换后端默认模型：

```powershell
$env:BUSMIND_SCORING_MODEL="xgboost"
```

可选值包括 `linear`、`xgboost` 和 `tabpfn`。当前建议默认使用 `xgboost`。

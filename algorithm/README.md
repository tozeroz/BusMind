# 算法层说明

`algorithm` 是 BusMind 的候选线路评分算法层，负责把候选公交路线转成可训练数据、生成伪标签、训练评分模型，并向后端提供统一的打分入口。

## 目录结构

```text
algorithm/
  dataset/   # 离线训练数据、伪标签和数据构建脚本
  model/     # 候选线路评分模型、训练脚本和评估工具
  routing/   # 公交路线图搜索逻辑，后端和离线数据构建共用
```

## 工作链路

1. `routing/` 根据公交网络生成候选路线。
2. `dataset/scripts/build_features.py` 把候选路线整理成 `dataset/features/features.csv`。
3. `dataset/scripts/build_rule_pseudo_labels.py` 生成规则伪标签。
4. `dataset/scripts/build_llm_pseudo_labels.py` 生成、调用、聚合并融合 LLM-assisted 伪标签。
5. `model/*/train.py` 使用融合标签训练候选线路评分模型。
6. `model/evaluation/compare.py` 对比 Linear、XGBoost 和 TabPFN 的效果。
7. 后端通过 `algorithm.model.predictor.predict_recommendation` 调用当前配置的评分模型。

## 模型输出

候选线路评分模型统一输出六个分数：

```text
time_score
comfort_score
walk_score
transfer_score
reliability_score
recommend_score
```

其中前五个是路线级子评分，`recommend_score` 会结合用户偏好权重生成。

## 常用命令

构建训练数据：

```powershell
python .\algorithm\dataset\scripts\build_features.py --groups 1000
python .\algorithm\dataset\scripts\summarize_features.py
python .\algorithm\dataset\scripts\build_rule_pseudo_labels.py
```

生成并融合 LLM 伪标签：

```powershell
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py split-requests --shards 5
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py merge-responses
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py aggregate
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py fuse
```

训练模型：

```powershell
python .\algorithm\model\linear_scoring\train.py
python .\algorithm\model\xgboost_scoring\train.py
python .\algorithm\model\tabpfn_scoring\train.py --max-train-rows 1000
```

对比模型并生成曲线图：

```powershell
python .\algorithm\model\evaluation\compare.py --plot-curves
```

切换后端默认模型：

```powershell
$env:BUSMIND_SCORING_MODEL="xgboost"
```

可选值包括 `linear`、`xgboost` 和 `tabpfn`。当前建议默认使用 `xgboost`。

## 相关文档

- `algorithm/dataset/README.md`：数据集目录、伪标签和执行流程。
- `algorithm/model/README.md`：模型目录、训练命令和评估指标。

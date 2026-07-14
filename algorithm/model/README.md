# 模型目录说明

`algorithm/model` 保存候选线路评分模型、统一接口、训练脚本和评估工具。三个模型都读取同一份 `algorithm/dataset/features/features.csv` 和 `algorithm/dataset/labels/rule_llm_fused_pseudo_labels.csv`。

## 目录结构

```text
algorithm/model/
  base.py
  contracts.py
  preprocessing.py
  register.py
  predictor.py
  linear_scoring/
  xgboost_scoring/
  tabpfn_scoring/
  evaluation/
  utils/
```

## 模块职责

- `contracts.py`：定义后端与算法之间的请求、特征和评分结构。
- `preprocessing.py`：把后端业务字段转换为模型使用的 12 维数值特征。
- `register.py`：根据 `BUSMIND_SCORING_MODEL` 选择具体模型。
- `predictor.py`：后端调用的统一预测入口。
- `linear_scoring/`：轻量可解释 baseline。
- `xgboost_scoring/`：结构化特征强基线，当前推荐作为默认模型。
- `tabpfn_scoring/`：小数据集表格学习实验方案。
- `evaluation/`：统一评估三个模型，并生成指标和曲线图。

## 训练命令

```powershell
python .\algorithm\model\linear_scoring\train.py
python .\algorithm\model\xgboost_scoring\train.py
python .\algorithm\model\tabpfn_scoring\train.py --max-train-rows 1000
```

训练产物保存在各模型自己的 `artifacts/` 目录中，并随仓库提交，便于后端直接联调。

## 模型对比

```powershell
python .\algorithm\model\evaluation\compare.py --plot-curves
```

输出位于：

```text
algorithm/model/evaluation/artifacts/
```

主要指标包括：

- `macro_rmse`：五个子评分 RMSE 的平均值。
- `recommend_score_rmse`：综合推荐分的 RMSE。
- `top1_agreement`：同一候选组内模型第一名是否与标签第一名一致。
- `ndcg_at_5`：候选组前 5 条路线排序质量。

## 后端模型切换

```powershell
$env:BUSMIND_SCORING_MODEL="xgboost"
```

可选值：

```text
linear
xgboost
tabpfn
```

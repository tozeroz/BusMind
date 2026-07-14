# 算法数据集目录

`algorithm/dataset` 保存候选线路评分模型的离线训练数据和数据构建脚本。它的目标是把 `data/processed` 中的公交网络、实时到站、历史客流和路况数据整理成与后端 `routes[]` 字段对齐的数据集。

## 目录结构

```text
algorithm/dataset/
  features/
    features.csv
    feature-summary.md
  labels/
    rule_pseudo_labels.csv
    llm_pseudo_labels.csv
    rule_llm_fused_pseudo_labels.csv
  llm/
    llm_pseudo_label_requests.jsonl
    llm_pseudo_label_responses.jsonl
    shards/
  scripts/
    data.py
    feature_contract.py
    paths.py
    build_features.py
    summarize_features.py
    build_rule_pseudo_labels.py
    build_llm_pseudo_labels.py
```

## 目录职责

- `features/`：保存候选路线冻结特征。`features.csv` 是模型训练入口，`feature-summary.md` 是数据质量摘要。
- `labels/`：保存伪标签。规则标签、LLM 聚合标签和融合标签都按 `candidate_group_id + route_id` 对齐。
- `llm/`：保存发给 DeepSeek 的请求、响应和多人并行标注分片。
- `scripts/`：保存数据读取、字段契约、路径定义和构建脚本。

## 核心脚本

| 脚本 | 作用 |
|---|---|
| `scripts/data.py` | 读取 raw / processed 数据，并提供客流、拥堵等查表能力 |
| `scripts/feature_contract.py` | 定义 `features.csv` 冻结字段，并把业务字段转为模型输入 |
| `scripts/paths.py` | 集中管理 dataset 产物路径 |
| `scripts/build_features.py` | 构建候选路线冻结特征 |
| `scripts/summarize_features.py` | 生成 `features/feature-summary.md` |
| `scripts/build_rule_pseudo_labels.py` | 生成规则伪标签 |
| `scripts/build_llm_pseudo_labels.py` | 生成、调用、聚合并融合 LLM 伪标签 |

## 执行顺序

构建特征与规则伪标签：

```powershell
python .\algorithm\dataset\scripts\build_features.py --groups 1000
python .\algorithm\dataset\scripts\summarize_features.py
python .\algorithm\dataset\scripts\build_rule_pseudo_labels.py
```

生成 LLM-assisted 伪标签：

```powershell
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py generate-prompts --seed-count 3
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py call-deepseek
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py aggregate
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py fuse
```

多人并行调用 DeepSeek 时，先拆分请求：

```powershell
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py split-requests --shards 5
```

每个人只处理自己的分片，例如第 1 份：

```powershell
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py call-deepseek `
  --requests .\algorithm\dataset\llm\shards\llm_pseudo_label_requests_part_01_of_05.jsonl `
  --output .\algorithm\dataset\llm\shards\llm_pseudo_label_responses_part_01_of_05.jsonl
```

收齐响应后：

```powershell
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py merge-responses
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py aggregate
python .\algorithm\dataset\scripts\build_llm_pseudo_labels.py fuse
```

## 数据字段口径

`features.csv` 只保存与后端候选路线 payload 对齐的业务字段，以及离线训练管理字段。模型内部的 12 维数值特征由 `algorithm/model/preprocessing.py` 统一生成，不直接写入 `features.csv`。

主要训练标签是：

```text
time_score
comfort_score
walk_score
transfer_score
reliability_score
recommend_score
```

其中前五个是路线级子评分，`recommend_score` 会结合用户偏好权重生成。

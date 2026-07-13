> 核心判断：当前候选线路评分模型面对的是缺少真实用户选择、点击和满意度标签的数据集，因此需要先构造可靠的伪标签，再训练下游评分模型。本方法将规则伪标签与大模型辅助标注结合，利用 `Roll the dice & look before you leap: Going beyond the creative limits of next-token prediction` 中的 seed-conditioning 思路，把大模型输出的随机性转化为标签一致性和置信度评估

# 一、问题背景

当前候选线路评分模型的输入是候选路线的结构化特征，训练目标是输出路线体验评分：

```text
12 维路线特征
    ↓
time_score
comfort_score
walk_score
transfer_score
reliability_score
recommend_score
```

但当前阶段缺少真实监督信号，例如：

- 用户实际选择了哪条路线
- 用户是否点击某条候选线路推荐结果
- 用户是否满意推荐结果
- 用户是否取消、改选或重复查询

因此，这不是一个可以直接使用真实标签训练的标准监督学习问题，而是一个**无真实标签数据集下的弱监督伪标签构造问题**

# 二、原有规则伪标签方法

原方案主要依赖业务规则生成伪标签：

```text
features.csv
    ↓
规则评分函数
    ↓
pseudo_labels.csv
```

规则方法的优势是：

- 可解释，能说明每个分数来自哪些业务字段
- 稳定，同一输入一定得到同一标签
- 可复现，适合作为第一版 baseline
- 成本低，不依赖外部大模型调用

但它也有明显局限：

| **问题** | **说明** |
|---|---|
| 人工权重僵硬 | 时间、舒适、步行、换乘、可靠性之间的权重主要来自经验 |
| 边界样本硬切 | 分数接近的候选路线可能因为阈值被强行拉开 |
| 鲁棒性不足 | 模型容易只学习规则表面，而不是更一般的出行偏好 |
| 缺少模糊判断 | 真实用户可能在等待、拥挤、少走路之间做复杂权衡 |
| 难以表达不确定性 | 单一规则输出只有一个标签，不知道这个标签是否可靠 |

因此，纯规则伪标签适合打通训练链路，但不一定适合作为最终高质量训练目标

# 三、为什么引入大模型

引入大模型的目的不是让它直接替代规则，而是将它作为**教师模型**或**辅助标注器**

大模型在大规模语料中学习过大量关于出行体验的常识，例如：

- 等待时间过长会降低时间效率
- 拥挤和高客流会降低舒适度
- 步行距离和换乘次数会影响用户接受度
- 不同用户对“最快”“舒适”“少走路”“少换乘”的取舍不同
- 数据缺失或来源不稳定会降低推荐可信度

因此，大模型可以为伪标签提供比手写规则更柔性的判断。这个过程可以理解为一种弱监督下的知识蒸馏：

```text
无真实标签数据
    ↓
规则标签 + 大模型辅助标签
    ↓
融合后的伪标签
    ↓
XGBoost / TabPFN / 当前候选线路评分模型
```

更准确地说，该方法属于：

```text
LLM-assisted pseudo-labeling
规则与大模型辅助的弱监督伪标签学习
```

# 四、`Roll the dice & look before you leap` 带来的新思路

论文 `Roll the dice & look before you leap: Going beyond the creative limits of next-token prediction` 研究的是大模型在开放式生成任务中的随机性、多样性和 next-token prediction 局限

它的核心观点包括：

- 标准 next-token prediction 容易只学习局部 token 关系，难以学习需要提前规划的全局结构
- 许多复杂生成任务需要先形成隐含计划，再输出最终结果
- 只在输出端通过 temperature 制造随机性，可能导致不稳定或思路混杂
- 在输入端加入随机 seed，即 seed-conditioning，可以让模型在同一任务约束下产生多样但相对连贯的输出

seed-conditioning 的形式可以理解为：

```text
[SEED: A7F3] + 同一个评分任务
[SEED: K91Q] + 同一个评分任务
[SEED: M42D] + 同一个评分任务
```

seed 本身不提供答案，只作为输入扰动，让大模型在同一评分准则下形成不同视角的判断

# 五、如何迁移到伪标签构造

借鉴 seed-conditioning，不应只让大模型对一条路线单次打分，而是让大模型在多个 seed 下重复标注同一组候选路线：

```text
同一 candidate_group_id
同一批候选路线
同一套评分标准
不同 seed-conditioned prompt
    ↓
多组五维评分
    ↓
聚合评分 + 一致性评估
```

大模型输出建议限制为：

```text
time_score
comfort_score
walk_score
transfer_score
reliability_score
reason
confidence
```

`recommend_score` 不建议由大模型直接生成，而应由系统根据用户偏好权重计算：

```text
recommend_score = preference_weights · five_scores
```

这样可以避免大模型破坏推荐分的可控性和一致性

# 六、随机性如何转化为鲁棒性

这里的关键不是“让大模型越随机越好”，而是把随机性用于**不确定性估计**

多个 seed 输出接近，说明该样本标签稳定：

```text
seed_1: time_score = 84
seed_2: time_score = 86
seed_3: time_score = 85
```

多个 seed 输出分歧大，说明该样本判断模糊：

```text
seed_1: comfort_score = 82
seed_2: comfort_score = 61
seed_3: comfort_score = 74
```

因此可以定义：

```text
最终标签 = 多 seed 输出的 median / trimmed mean
标签置信度 = 1 - 多 seed 输出方差
```

训练时可以按置信度加权：

| **标签类型** | **训练权重建议** |
|---|---|
| 高置信规则标签 | `1.0` |
| 高一致性 LLM 标签 | `0.8 ~ 1.0` |
| 规则与 LLM 基本一致的融合标签 | `0.8` |
| LLM 分歧较大的标签 | `0.3 ~ 0.5` |
| 规则与 LLM 冲突严重的标签 | 降权或进入人工复核 |

# 七、与纯规则标签的对比

| **维度** | **纯规则伪标签** | **LLM-assisted pseudo-labeling** |
|---|---|---|
| 标签来源 | 人工规则函数 | 规则约束 + 大模型语义先验 |
| 输出方式 | 单次确定性输出 | 多 seed 多次输出后聚合 |
| 稳定性 | 很高 | 需要聚合和方差控制 |
| 柔性 | 较弱 | 较强 |
| 可解释性 | 强 | 需要 prompt 约束和 reason 字段 |
| 不确定性 | 难以表达 | 可用多 seed 分歧衡量 |
| 成本 | 低 | 较高 |
| 适合阶段 | baseline 和硬约束 | 标签增强和鲁棒训练 |

两者不是替代关系，而是互补关系：

```text
规则标签
    提供基础方向和硬约束

LLM 多 seed 标签
    提供语义先验、多视角判断和不确定性估计
```

# 八、推荐的整体流程

推荐采用下面的伪标签生成链路：

```text
features.csv
    ↓
规则伪标签
    ↓
LLM 多 seed 伪标签
    ↓
一致性评估
    ↓
规则标签与 LLM 标签融合
    ↓
training_targets.csv
    ↓
当前模型 / XGBoost / TabPFN 对比训练
```

其中 `training_targets.csv` 建议保存：

```text
candidate_group_id
route_id
time_score
comfort_score
walk_score
transfer_score
reliability_score
rule_score_source
llm_score_median
llm_score_variance
label_confidence
sample_weight
```

# 九、方法定位

该方案可以总结为：

> 面向无真实监督信号的候选线路评分数据集，项目采用规则与大模型辅助的弱监督伪标签学习方法。规则标签提供基础约束，大模型提供语义先验和更柔性的出行体验判断。`Roll the dice & look before you leap: Going beyond the creative limits of next-token prediction` 中的 seed-conditioning 思路启发我们，通过不同随机 seed 在输入端诱导大模型产生多组独立标注结果，再根据多次输出的一致性进行标签聚合和置信度评估。这样可以构造出比单一规则更稳健的伪标签，为后续 XGBoost 或 TabPFN 等回归模型提供更高质量的训练目标

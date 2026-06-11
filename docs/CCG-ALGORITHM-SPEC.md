# 认知冲突图谱算法技术规格书 (CCG Algorithm Spec)

> 版本: 1.0.0
> 日期: 2026-05-31
> 作者: 乔迈
> 状态: MVP开发中

---

## 一、核心定位

**CCG（Cognitive Conflict Graph）** —— 认知冲突图谱算法

核心命题：思维能力的本质，不是"拥有多少正确的知识"，而是对自身认知状态的觉察与调控能力。

算法目标（只做三件事）：
1. **推断**：学生此刻相信什么？
2. **检测**：他相信的这些东西之间，有矛盾吗？
3. **暴露**：如何让他自己看见这个矛盾？

---

## 二、数据结构

### 2.1 信念节点 (Belief)

```python
class Belief:
    id: str                          # 唯一标识
    proposition: str                 # 信念的命题表述
    type: BeliefType                 # 信念类型
    confidence: float                # 置信度 [0, 1]
    source: str                      # 来源追溯
    timestamp: datetime              # 首次建立时间
    last_activated: datetime         # 最近激活时间
    activation_count: int            # 激活总次数
    stability: float                 # 稳定性 [0, 1]
    emotional_tag: EmotionalTag      # 情感标记

class BeliefType(Enum):
    CONCEPT = "concept"              # 概念性信念
    PROCEDURE = "procedure"          # 程序性信念
    HEURISTIC = "heuristic"          # 启发式信念
    PRESUPPOSITION = "presupposition" # 前提性信念

class EmotionalTag(Enum):
    NEUTRAL = "neutral"              # 中性
    ATTACHED = "attached"            # 有情感依附
    INSECURE = "insecure"            # 不自信
```

### 2.2 信念关系边 (BeliefRelation)

```python
class BeliefRelation:
    source_id: str                   # 源信念ID
    target_id: str                   # 目标信念ID
    type: RelationType               # 关系类型
    strength: float                  # 关系强度 [0, 1]
    detected_by: str                 # 检测方式

class RelationType(Enum):
    IMPLIES = "implies"              # 蕴含
    CONTRADICTS = "contradicts"      # 矛盾
    PREREQUISITE = "prerequisite"    # 前置条件
    GENERALIZES = "generalizes"      # 泛化
    EXEMPLIFIES = "exemplifies"      # 具体化
    ASSOCIATES = "associates"        # 关联
```

### 2.3 冲突记录 (Conflict)

```python
class Conflict:
    id: str
    belief_a_id: str                 # 冲突方A
    belief_b_id: str                 # 冲突方B
    type: ConflictType               # 冲突类型
    severity: float                  # 严重度 [0, 1]
    teaching_value: float            # 教学价值 [0, 1]
    status: ConflictStatus           # 状态
    history: list                    # 处理历史

class ConflictType(Enum):
    LOGICAL = "logical"              # 逻辑矛盾
    BOUNDARY = "boundary"            # 边界矛盾
    CONFIDENCE = "confidence"        # 置信度矛盾
    PATH_DEPENDENCY = "path_dependency" # 路径依赖矛盾

class ConflictStatus(Enum):
    ACTIVE = "active"                # 活跃，未被觉察
    EXPOSED = "exposed"              # 已暴露，处理中
    RESOLVED = "resolved"            # 已修正
    RESOLVED_AI_ASSISTED = "resolved_ai" # AI引导下修正
    ABANDONED = "abandoned"          # 放弃处理
    RECURRING = "recurring"          # 复现
```

---

## 三、核心算法流程

```
学生输入
    ↓
┌─────────────────────────────────────┐
│ 模块1：信念提取与置信度校准        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 模块2：认知图谱更新                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 模块3：冲突检测与排序              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 模块4：追问决策与生成              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 模块5：学生应答处理与图谱再更新    │
└─────────────────────────────────────┘
    ↓
  闭环循环
```

### 3.1 模块1：信念提取与置信度校准

**输入**：学生当前回答文本
**输出**：结构化信念列表

**算法**：
1. 语言层提取（LLM）：
   - 表层：明确表达的命题
   - 中层：隐含的前提假设
   - 深层：思维习惯

2. 置信度校准：
   ```
   confidence = 0.5 × linguistic_certainty + 0.3 × behavioral_consistency + 0.2 × historical_stability
   ```

### 3.2 模块2：认知图谱更新

**输入**：新提取的信念列表、现有图谱
**输出**：更新后的图谱

**算法**：
1. 语义匹配（相似度 > 0.9 → 同一信念）
2. 关系推理（逻辑蕴含/矛盾）
3. 稳定性更新
4. 触发冲突检测

### 3.3 模块3：冲突检测与排序

**检测规则**：
- 规则1：逻辑矛盾（A蕴含P，B蕴含¬P）
- 规则2：边界矛盾（条件X下成立，错误应用于条件Y）
- 规则3：置信度矛盾（同时持有A和¬A）
- 规则4：路径依赖矛盾（推理路径前提互斥）

**排序公式**：
```
Priority(C) = Severity(C) × TeachingValue(C) × StudentReadiness(C) × Novelty(C)
```

### 3.4 模块4：追问生成

**追问类型**：
1. 引导发现型
2. 反例挑战型
3. 边界探索型
4. 路径对比型
5. 拆解引导型

**生成约束**：
- 长度 < 20字
- 不直接给答案
- 不评判
- 不先肯定再否定

### 3.5 模块5：应答处理

**思维流同步**：
- 学生思考时，AI静默监听
- 暂停超过15秒，才考虑追问
- 根据图谱状态决定是否追问

---

## 四、特殊场景处理

| 场景 | 处理策略 |
|------|----------|
| 逻辑自洽但方法非标准 | 不生成冲突，记录为解法变体 |
| 完全无思路 | 切换到"锚点建立模式" |
| 高挫败状态 | 暂停冲突暴露，切换到"肯定+存档"模式 |
| 冲突复现 | 升级优先级，追问更直接 |

---

## 五、MVP范围（7天）

### 第1天：项目框架 + 信念存储
- [ ] FastAPI项目结构
- [ ] Belief/Conflict数据模型
- [ ] NetworkX图结构
- [ ] SQLite持久化

### 第2天：信念提取模块
- [ ] LLM Prompt设计（准高一版本）
- [ ] 结构化输出解析
- [ ] 置信度校准算法

### 第3天：冲突检测（逻辑矛盾）
- [ ] 逻辑矛盾检测规则
- [ ] 冲突排序算法
- [ ] 冲突状态管理

### 第4天：追问生成模块
- [ ] 追问类型决策
- [ ] LLM追问生成Prompt
- [ ] 约束条件检查

### 第5天：对话管理 + API
- [ ] 对话状态机
- [ ] RESTful API设计
- [ ] WebSocket实时通信

### 第6天：前端框架
- [ ] React Native项目初始化
- [ ] 对话界面UI
- [ ] 语音输入集成

### 第7天：集成测试 + 调优
- [ ] 端到端测试
- [ ] 边界case测试
- [ ] 性能调优

---

## 六、技术栈

| 层级 | 选型 | 版本 |
|------|------|------|
| 前端 | React Native | 0.73+ |
| 后端 | Python FastAPI | 0.110+ |
| 图结构 | NetworkX | 3.2+ |
| 持久化 | SQLite | 3.45+ |
| LLM | Qwen-7B + GPT-4o-mini | - |
| 语音 | 科大讯飞API | - |

---

## 七、API设计

### 对话接口

```
POST /api/chat/message
{
    "session_id": "xxx",
    "student_input": "我觉得x=3",
    "context": {
        "grade": "high_school",
        "subject": "math"
    }
}

Response:
{
    "ai_response": "为什么你觉得x=3？",
    "belief_extracted": [...],
    "conflicts_detected": [...],
    "thinking_time_allowed": 15
}
```

### 认知图谱接口

```
GET /api/graph/{session_id}
{
    "beliefs": [...],
    "relations": [...],
    "conflicts": [...]
}
```

---

## 八、质量指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| 信念提取准确率 | > 80% | 人工标注前50次 |
| 冲突检测召回率 | > 70% | 人工验证 |
| 追问相关性 | > 75% | 学生反馈 |
| 响应时间 | < 2秒 | 自动监控 |

---

## 九、后续迭代（V2）

1. 小学版本适配
2. 行为层提取（画布操作）
3. 边界矛盾+路径依赖矛盾检测
4. 情感标记系统
5. 冲突复现检测
6. 多元宇宙界面可视化

---

*文档结束*

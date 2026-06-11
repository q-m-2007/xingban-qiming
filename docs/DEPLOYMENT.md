# 星伴·启明 CCG追问引擎 部署文档

> 版本: 1.0.0
> 日期: 2026-06-01
> 算法: CCG (Cognitive Conflict Graph)

---

## 一、项目概述

星伴·启明是一个基于认知冲突图谱（CCG）的AI追问引擎，通过检测学生信念体系中的矛盾，引导学生自己发现答案。

### 核心特性

- **信念提取**：从学生输入中提取表层、中层、深层信念
- **冲突检测**：检测逻辑矛盾、边界矛盾、置信度矛盾、路径依赖矛盾
- **追问生成**：根据冲突类型生成引导性追问
- **思维流同步**：学生思考时AI静默监听

---

## 二、快速开始

### 2.1 环境要求

- Python 3.11+
- 2GB+ 内存
- 1GB+ 磁盘空间

### 2.2 安装步骤

```bash
# 1. 克隆项目
cd /home/ubuntu/xingban-qiming

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install networkx pydantic fastapi uvicorn httpx pytest

# 4. 创建数据目录
mkdir -p data

# 5. 运行测试
python -m pytest tests/ -v

# 6. 启动服务
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2.3 使用启动脚本

```bash
chmod +x start.sh
./start.sh
```

---

## 三、API接口

### 3.1 对话接口

#### POST /api/chat/message
发送学生消息，获取AI追问响应

**请求体：**
```json
{
    "session_id": "xxx",  // 可选，首次为空
    "student_input": "我觉得x=3",
    "context": {
        "grade": "high_school",
        "subject": "math"
    }
}
```

**响应：**
```json
{
    "session_id": "xxx",
    "ai_response": "为什么你觉得x=3？",
    "question_type": "guide_discovery",
    "beliefs_extracted": [...],
    "conflicts_detected": [...],
    "thinking_time_allowed": 15,
    "state": "active"
}
```

### 3.2 图谱接口

#### GET /api/chat/{session_id}/graph
获取会话的认知图谱

#### GET /api/chat/{session_id}/statistics
获取会话统计信息

#### GET /api/graph/{session_id}/beliefs
获取信念列表

#### GET /api/graph/{session_id}/conflicts
获取冲突列表

### 3.3 会话管理

#### GET /api/sessions
列出所有会话

#### DELETE /api/sessions/{session_id}
删除会话

### 3.4 健康检查

#### GET /api/health
返回服务状态

---

## 四、算法说明

### 4.1 CCG算法流程

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

### 4.2 冲突类型

| 类型 | 说明 | 检测规则 |
|------|------|----------|
| LOGICAL | 逻辑矛盾 | A蕴含P，B蕴含¬P |
| BOUNDARY | 边界矛盾 | 条件X下成立，错误应用于条件Y |
| CONFIDENCE | 置信度矛盾 | 同时持有A和¬A，且两者置信度均>0.5 |
| PATH_DEPENDENCY | 路径依赖矛盾 | 推理路径前提互斥 |

### 4.3 追问类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| GUIDE_DISCOVERY | 引导发现型 | 通用场景 |
| COUNTEREXAMPLE | 反例挑战型 | 逻辑矛盾 |
| BOUNDARY_EXPLORE | 边界探索型 | 边界矛盾 |
| PATH_COMPARE | 路径对比型 | 路径依赖 |
| DECOMPOSE | 拆解引导型 | 高认知负荷 |

---

## 五、项目结构

```
xingban-qiming/
├── backend/                    # 后端代码
│   └── app/
│       ├── api/               # API接口
│       │   └── chat.py
│       ├── engine/            # 核心引擎
│       │   ├── belief_extractor.py
│       │   ├── conflict_detector.py
│       │   ├── conversation_manager.py
│       │   ├── llm_client.py
│       │   └── question_generator.py
│       ├── graph/             # 图结构
│       │   └── cognitive_graph.py
│       ├── models/            # 数据模型
│       │   ├── ccg_models.py
│       │   └── schemas.py
│       ├── storage/           # 持久化
│       │   └── sqlite_store.py
│       └── main.py            # 主应用
├── frontend/                  # 前端代码
│   └── index.html
├── tests/                     # 测试代码
│   ├── test_day1.py
│   ├── test_day2.py
│   ├── test_day3.py
│   ├── test_day4.py
│   └── test_day5.py
├── docs/                      # 文档
│   ├── CCG-ALGORITHM-SPEC.md
│   ├── 7DAY-DEV-PLAN.md
│   └── DEPLOYMENT.md
├── data/                      # 数据目录
├── start.sh                   # 启动脚本
└── README.md                  # 项目说明
```

---

## 六、测试

### 6.1 运行所有测试

```bash
python -m pytest tests/ -v
```

### 6.2 运行特定测试

```bash
# Day 1测试：数据模型+图结构+持久化
python -m pytest tests/test_day1.py -v

# Day 2测试：信念提取
python -m pytest tests/test_day2.py -v

# Day 3测试：冲突检测
python -m pytest tests/test_day3.py -v

# Day 4测试：追问生成
python -m pytest tests/test_day4.py -v

# Day 5测试：对话管理+API
python -m pytest tests/test_day5.py -v
```

---

## 七、配置

### 7.1 LLM配置

在环境变量中配置LLM API：

```bash
# OpenAI兼容接口
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"

# 通义千问
export DASHSCOPE_API_KEY="your-api-key"
```

### 7.2 数据库配置

默认使用SQLite，数据库文件位于 `data/ccg.db`

### 7.3 服务配置

默认服务配置：
- 主机：0.0.0.0
- 端口：8000
- 调试模式：开启

---

## 八、监控

### 8.1 健康检查

```bash
curl http://localhost:8000/api/health
```

### 8.2 日志

服务日志输出到标准输出，包含：
- 请求日志
- 错误日志
- 性能日志

### 8.3 统计

通过API获取统计信息：
- `/api/chat/{session_id}/statistics`
- `/api/sessions`

---

## 九、故障排除

### 9.1 常见问题

**问题：ModuleNotFoundError**
```bash
# 解决：安装依赖
pip install networkx pydantic fastapi uvicorn httpx
```

**问题：端口被占用**
```bash
# 解决：更换端口
uvicorn app.main:app --port 8001
```

**问题：LLM调用失败**
```bash
# 解决：检查API Key配置
echo $OPENAI_API_KEY
```

### 9.2 日志调试

```bash
# 启用详细日志
uvicorn app.main:app --log-level debug
```

---

## 十、后续计划

### V2版本
1. 小学版本适配
2. 行为层提取（画布操作）
3. 边界矛盾+路径依赖矛盾检测
4. 情感标记系统
5. 冲突复现检测
6. 多元宇宙界面可视化

### V3版本
1. React Native移动端
2. 语音交互
3. 多模态输入
4. 个性化学习路径

---

*文档结束*

# 星伴·启明 AI教学引擎

基于统一教学管道的个性化AI教学系统（融合13条铁律）

## 算法架构

### 七层管道

```
学生输入
  ↓
第0层 守门层（<1ms）：沉默决策 + 思考边界 + 输入检查
  ↓
第1层 感知层（<10ms）：三级匹配 + 规则信念提取 + 情绪检测
  ↓
第2层 验证层（<5ms）：误解验证 + 边界校验 + 前置检查
  ↓
第3层 推理层（<10ms）：认知图谱 + 冲突检测 + 冲突排序
  ↓
第4层 个性化层（<5ms）：难度调节 + 节奏控制 + 惯性检测
  ↓
第5层 决策层（<5ms）：统一决策 + 模板生成 + 边界检查
  ↓
第6层 执行层（异步）：结果记录 + 效果追踪 + 可解释性报告
  ↓
第7层 进化层（后台）：画像更新 + 误解演化 + 知识库扩展 + 策略优化 + 老化检测 + 过拟合防护
```

### 十三条铁律

| 类别 | 铁律 | 核心模块 |
|------|------|---------|
| **性能** | P1响应快 | 三级匹配+模板库 |
| | P2逻辑准 | 知识图谱推导 |
| | P3定位准 | 三重定位 |
| | P4自进化 | 三层进化机制 |
| | P5存储优 | 分层+增量 |
| | P6可扩展 | 自动扩展知识库 |
| **教育** | E1不替思考 | ThinkingBoundary |
| | E2服从节奏 | PacingController |
| | E3不优化短期 | 独立解决率权重0.4 |
| | E4防过拟合 | 3次证据才确认 |
| | E5沉默权 | 5种沉默条件 |
| | E6老化检测 | 知识库保质期 |
| | E7可解释性 | 每个决策有报告 |

## 部署

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 创建.env文件
cp .env.example .env
# 编辑 .env 设置 LLM_API_KEY

# 启动服务
uvicorn main:app --reload
```

### Docker部署

```bash
# 设置环境变量
export LLM_API_KEY=your_api_key

# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 云服务器部署

```bash
# 克隆代码
git clone <your-repo-url>
cd xingban-qiming

# 设置环境变量
cp .env.example .env
# 编辑 .env 设置 LLM_API_KEY

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

## API接口

### V3统一管道（推荐）

```bash
# 聊天接口
curl -X POST https://qiming.xinxunai.com.cn/api/v3/chat/message \
  -H "Content-Type: application/json" \
  -d '{"student_id": "test", "message": "什么是因数", "topic": "factor"}'

# 学生诊断
curl https://qiming.xinxunai.com.cn/api/v3/student/test/diagnosis

# 健康检查
curl https://qiming.xinxunai.com.cn/api/v3/health
```

## 文件结构

```
xingban-qiming/
├── main.py              # FastAPI主应用
├── llm_client.py        # LLM客户端
├── api/                 # API接口
│   ├── v3_chat.py       # V3统一管道接口
│   ├── chat.py          # V1兼容接口
│   └── v2_chat.py       # V2兼容接口
├── pipeline/            # 统一教学管道
│   ├── models.py        # 数据模型
│   ├── gate.py          # 守门层
│   ├── perception.py    # 感知层
│   ├── validation.py    # 验证层
│   ├── reasoning.py     # 推理层
│   ├── personalization.py # 个性化层
│   ├── decision.py      # 决策层
│   ├── execution.py     # 执行层
│   ├── evolution.py     # 进化层
│   └── pipeline.py      # 管道编排器
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── deploy.sh
└── README.md
```

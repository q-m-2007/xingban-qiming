# 星伴·启明 AI教学引擎

> **v1.0.0** | 2026-06-11 | [GitHub](https://github.com/q-m-2007/xingban-qiming)

基于统一教学管道的个性化AI教学系统（融合13条铁律）

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-06-11 | 首发版本：统一教学管道 + 前端网站 + LLM集成 |

## 在线体验

- 网站：http://124.220.62.96
- 域名：xingban.xinxunai.com.cn（待解析）

## 功能特性

- **首页**：产品介绍、功能展示
- **登录/注册**：用户认证
- **AI对话**：接入DeepSeek LLM的数学辅导
- **学习诊断**：15维认知画像报告

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
git clone https://github.com/q-m-2007/xingban-qiming.git
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
curl -X POST http://124.220.62.96/api/v3/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"message": "什么是因数"}'

# 学生诊断
curl http://124.220.62.96/api/v3/student/diagnosis \
  -H "Authorization: Bearer your_token"

# 健康检查
curl http://124.220.62.96/api/v3/health
```

## 文件结构

```
xingban-qiming/
├── main.py              # FastAPI主应用
├── llm_client.py        # LLM客户端
├── database.py          # 数据库模块
├── auth.py              # 认证模块
├── api/                 # API接口
│   ├── auth.py          # 认证API
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
├── static/              # 前端文件
│   ├── index.html       # 首页
│   ├── chat.html        # 对话页
│   ├── login.html       # 登录页
│   ├── register.html    # 注册页
│   ├── diagnosis.html   # 诊断页
│   ├── css/style.css    # 样式
│   └── js/app.js        # 逻辑
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── deploy.sh
└── README.md
```

## 技术栈

- **前端**：HTML/CSS/JS，苹果科技风格
- **后端**：FastAPI + SQLite
- **算法**：七层统一教学管道（13条铁律）
- **AI**：DeepSeek LLM
- **部署**：Docker + Nginx

## 服务器信息

- IP：124.220.62.96
- 用户：ubuntu
- Docker容器：xingban-qiming
- 端口：8080（内部）→ 80（Nginx）

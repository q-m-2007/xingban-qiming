# 星伴·启明 CCG算法 7天开发计划

> 开始时间: 2026-06-01
> 目标: 7天完成MVP，老大测试
> 汇报: 每天晚上8点自动汇报到微信

---

## Day 1 (6/1): 项目框架 + 信念存储

### 任务清单
- [ ] 1.1 重构FastAPI项目结构
- [ ] 1.2 实现Belief/Conflict数据模型
- [ ] 1.3 实现NetworkX图结构封装
- [ ] 1.4 实现SQLite持久化层
- [ ] 1.5 编写单元测试

### 预期产出
- `/backend/app/models/belief.py` - 信念数据模型
- `/backend/app/models/conflict.py` - 冲突数据模型
- `/backend/app/graph/cognitive_graph.py` - 认知图谱核心
- `/backend/app/storage/sqlite_store.py` - 持久化层
- `/backend/tests/test_models.py` - 单元测试

### 验收标准
- 数据模型能正确序列化/反序列化
- 图结构能增删改查节点和边
- SQLite能正确持久化和恢复图谱

---

## Day 2 (6/2): 信念提取模块

### 任务清单
- [ ] 2.1 设计信念提取Prompt（准高一版本）
- [ ] 2.2 实现LLM调用封装
- [ ] 2.3 实现结构化输出解析
- [ ] 2.4 实现置信度校准算法
- [ ] 2.5 编写测试用例

### 预期产出
- `/backend/app/engine/belief_extractor.py` - 信念提取器
- `/backend/app/engine/confidence_calibrator.py` - 置信度校准
- `/backend/app/utils/llm_client.py` - LLM调用封装
- `/backend/app/prompts/belief_extraction.txt` - 提取Prompt
- `/backend/tests/test_belief_extraction.py` - 测试

### 验收标准
- 能从学生回答中提取表层/中层/深层信念
- 置信度计算正确
- LLM调用有重试和兜底机制

---

## Day 3 (6/3): 冲突检测模块

### 任务清单
- [ ] 3.1 实现逻辑矛盾检测规则
- [ ] 3.2 实现冲突严重度计算
- [ ] 3.3 实现教学价值计算
- [ ] 3.4 实现学生就绪度计算
- [ ] 3.5 实现冲突排序算法
- [ ] 3.6 编写测试用例

### 预期产出
- `/backend/app/engine/conflict_detector.py` - 冲突检测器
- `/backend/app/engine/conflict_ranker.py` - 冲突排序
- `/backend/app/prompts/conflict_analysis.txt` - 分析Prompt
- `/backend/tests/test_conflict_detection.py` - 测试

### 验收标准
- 能检测出逻辑矛盾
- 排序算法输出合理的优先级
- 冲突状态正确流转

---

## Day 4 (6/4): 追问生成模块

### 任务清单
- [ ] 4.1 实现追问类型决策逻辑
- [ ] 4.2 设计追问生成Prompt
- [ ] 4.3 实现追问生成器
- [ ] 4.4 实现约束条件检查
- [ ] 4.5 编写测试用例

### 预期产出
- `/backend/app/engine/question_generator.py` - 追问生成器
- `/backend/app/engine/question_type_decider.py` - 类型决策
- `/backend/app/prompts/question_generation.txt` - 生成Prompt
- `/backend/tests/test_question_generation.py` - 测试

### 验收标准
- 能根据冲突类型生成合适的追问
- 追问符合约束条件（<20字、不评判等）
- 追问风格适合准高一学生

---

## Day 5 (6/5): 对话管理 + API

### 任务清单
- [ ] 5.1 实现对话状态机
- [ ] 5.2 实现会话管理
- [ ] 5.3 设计RESTful API
- [ ] 5.4 实现WebSocket实时通信
- [ ] 5.5 编写API文档

### 预期产出
- `/backend/app/engine/conversation_manager.py` - 对话管理器
- `/backend/app/api/chat.py` - 对话API
- `/backend/app/api/graph.py` - 图谱API
- `/backend/app/websocket/handler.py` - WebSocket处理
- `/backend/docs/API.md` - API文档

### 验收标准
- 能进行完整的对话流程
- API响应正确且快速
- WebSocket能实时推送

---

## Day 6 (6/6): 前端框架

### 任务清单
- [ ] 6.1 React Native项目初始化
- [ ] 6.2 对话界面UI设计
- [ ] 6.3 实现消息列表
- [ ] 6.4 实现输入组件
- [ ] 6.5 集成语音输入API

### 预期产出
- `/mobile/` - React Native项目
- `/mobile/src/screens/ChatScreen.tsx` - 对话界面
- `/mobile/src/components/MessageList.tsx` - 消息列表
- `/mobile/src/components/InputBar.tsx` - 输入组件
- `/mobile/src/services/speech.ts` - 语音服务

### 验收标准
- 界面美观，交互流畅
- 能发送和接收消息
- 语音输入能正确识别

---

## Day 7 (6/7): 集成测试 + 调优

### 任务清单
- [ ] 7.1 端到端测试
- [ ] 7.2 边界case测试
- [ ] 7.3 性能测试
- [ ] 7.4 Bug修复
- [ ] 7.5 部署准备

### 预期产出
- `/backend/tests/test_e2e.py` - 端到端测试
- `/backend/tests/test_edge_cases.py` - 边界测试
- `/docs/TEST-REPORT.md` - 测试报告
- `/docs/DEPLOYMENT.md` - 部署文档

### 验收标准
- 所有测试通过
- 响应时间 < 2秒
- 准备好给老大测试

---

## 每日汇报模板

```
📊 星伴·启明开发进度汇报

日期: YYYY-MM-DD
今日完成: X/Y 任务
整体进度: XX%

✅ 已完成:
- 任务1
- 任务2

⏳ 进行中:
- 任务3

❌ 遇到问题:
- 问题描述

📋 明日计划:
- 任务4
- 任务5

💡 备注:
- 其他说明
```

---

*计划结束*

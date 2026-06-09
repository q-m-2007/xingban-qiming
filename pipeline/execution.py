"""
第6层：执行层（Execution Layer）
职责：结果记录 + 效果追踪 + 可解释性报告
铁律：E7可解释性 + P5存储优化
"""

from typing import Dict, List, Optional
from datetime import datetime
from .models import (
    ExecutionResult, PipelineContext, DecisionResult,
    InquiryType, StudentState
)


class OutcomeRecorder:
    """结果记录器（P5存储优化）"""

    def __init__(self):
        self.records: List[Dict] = []

    def record(self, context: PipelineContext,
               decision: DecisionResult,
               final_response: str) -> Dict:
        """记录教学结果"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "student_id": context.student_id,
            "topic": context.topic,
            "student_input": context.student_input,
            "response": final_response,
            "inquiry_type": decision.inquiry_type.value,
            "state": context.reasoning.state.value if context.reasoning else "unknown",
            "emotion": context.perception.emotion if context.perception else "neutral",
            "difficulty": context.personalization.difficulty_level if context.personalization else 0.5,
            "layer_times": context.layer_times,
        }

        # P5：只保留最近100条记录
        self.records.append(record)
        if len(self.records) > 100:
            self.records = self.records[-100:]

        return record


class DecisionExplainer:
    """决策解释器（E7可解释性）"""

    def generate_report(self, context: PipelineContext,
                        decision: DecisionResult) -> str:
        """生成可解释性报告"""
        parts = []

        # 1. 输入分析
        parts.append("【输入分析】")
        parts.append(f"  学生输入：{context.student_input[:50]}...")
        if context.perception:
            parts.append(f"  情绪状态：{context.perception.emotion}")
            parts.append(f"  匹配话题：{context.perception.match.topic}")
            parts.append(f"  匹配置信度：{context.perception.match.confidence:.0%}")

        # 2. 验证结果
        if context.validation:
            parts.append("\n【验证结果】")
            parts.append(f"  前置知识：{'满足' if context.validation.prerequisite_ok else '不满足'}")
            if context.validation.misconceptions:
                parts.append(f"  误解数量：{len(context.validation.misconceptions)}")
                for mis in context.validation.misconceptions:
                    parts.append(f"    - {mis.content}")

        # 3. 推理结果
        if context.reasoning:
            parts.append("\n【推理结果】")
            parts.append(f"  学生状态：{context.reasoning.state.value}")
            if context.reasoning.top_conflict:
                parts.append(f"  主要冲突：{context.reasoning.top_conflict.description}")
                parts.append(f"  冲突优先级：{context.reasoning.top_conflict.priority:.2f}")

        # 4. 个性化决策
        if context.personalization:
            parts.append("\n【个性化】")
            parts.append(f"  难度级别：{context.personalization.difficulty_level:.0%}")
            if context.personalization.pacing.should_wait:
                parts.append(f"  节奏控制：等待{context.personalization.pacing.wait_seconds}秒")
                parts.append(f"  原因：{context.personalization.pacing.reason}")
            if context.personalization.inertia_detected:
                parts.append(f"  惯性检测：{context.personalization.inertia_method}")

        # 5. 最终决策
        parts.append("\n【最终决策】")
        parts.append(f"  追问类型：{decision.inquiry_type.value}")
        parts.append(f"  决策置信度：{decision.confidence:.0%}")
        parts.append(f"  思考边界：{'通过' if not decision.thinking_injected else '已注入我也不会'}")
        parts.append(f"  回复内容：{decision.response_text[:80]}...")

        # 6. 性能统计
        parts.append("\n【性能统计】")
        total_time = sum(context.layer_times.values())
        parts.append(f"  总耗时：{total_time:.1f}ms")
        for layer, time_ms in context.layer_times.items():
            parts.append(f"  {layer}：{time_ms:.1f}ms")

        return "\n".join(parts)


class ExecutionLayer:
    """执行层主类"""

    def __init__(self):
        self.recorder = OutcomeRecorder()
        self.explainer = DecisionExplainer()

    def process(self, context: PipelineContext) -> ExecutionResult:
        """处理执行层逻辑"""
        decision = context.decision

        # 1. 生成最终回复
        final_response = decision.response_text if decision else ""

        # 2. 生成可解释性报告（E7）
        explanation = self.explainer.generate_report(context, decision)

        # 3. 记录结果（P5存储优化）
        self.recorder.record(context, decision, final_response)

        return ExecutionResult(
            final_response=final_response,
            explanation=explanation,
        )

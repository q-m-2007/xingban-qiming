"""
CCG信念提取器 v2
统一提取新信念 + 识别被取代的旧信念

核心算法：
1. 将学生输入 + 已有活跃信念一起送入LLM
2. LLM同时输出：新提取的信念 + 被取代的旧信念索引
3. 被取代的旧信念自动降级，相关冲突自动resolved
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..models.ccg_models import (
    Belief, BeliefType, EmotionalTag
)
from ..engine.llm_client import generate_structured


# ── 统一提取Prompt ────────────────────────────────────────────


EXTRACTION_PROMPT_V2 = """你是一位专业的数学教育AI助手，正在分析学生的数学思维演变。

## 学生最新输入
"{student_input}"

## 学生之前持有的信念（按置信度排序）
{existing_beliefs_text}

## 上下文
- 学段：{grade}
- 学科：{subject}

## 任务

请完成两个任务：

### 任务1：从最新输入中提取信念
提取表层（明确表达）、中层（隐含前提）、深层（思维习惯）三层信念。

### 任务2：判断旧信念是否被新输入修正
对比学生的新输入和之前的信念，判断哪些旧信念已经被学生自己修正或推翻。
判断标准：
- 新输入明确否定了旧信念（如从"解是x=2"变为"解是x=2和x=3"）
- 新输入展示了更完整的理解，使旧信念变得不准确
- 新输入的结论与旧信念矛盾

注意：如果新输入只是在旧信念基础上补充细节（而非修正），不要标记为superseded。

请返回JSON格式：
{{
    "new_beliefs": [
        {{
            "proposition": "信念表述",
            "layer": "表层/中层/深层",
            "type": "concept/procedure/heuristic/presupposition",
            "confidence": 0.0到1.0,
            "emotional_tag": "neutral/attached/insecure",
            "reasoning": "提取理由"
        }}
    ],
    "superseded_indices": [0, 2]
}}

superseded_indices 是被取代的旧信念在上面列表中的索引（从0开始）。如果没有旧信念被取代，返回空数组。"""


# ── 输出Schema ────────────────────────────────────────────


EXTRACTION_SCHEMA_V2 = {
    "new_beliefs": [
        {
            "proposition": "string",
            "layer": "string",
            "type": "string",
            "confidence": "float",
            "emotional_tag": "string",
            "reasoning": "string"
        }
    ],
    "superseded_indices": ["integer"]
}


# ── 信念提取器 v2 ────────────────────────────────────────────


class BeliefExtractorV2:
    """
    信念提取器 v2
    统一处理新信念提取和旧信念淘汰
    """

    def __init__(self):
        pass

    async def extract_and_update(
        self,
        student_input: str,
        existing_beliefs: List[Belief],
        grade: str = "high_school",
        subject: str = "math",
        question_context: str = ""
    ) -> Tuple[List[Belief], List[str]]:
        """
        统一提取：返回 (新信念列表, 被取代的旧信念ID列表)

        Args:
            student_input: 学生最新输入
            existing_beliefs: 当前活跃的旧信念列表
            grade: 学段
            subject: 学科
            question_context: 题目上下文

        Returns:
            (new_beliefs, superseded_belief_ids)
        """
        # 构建已有信念文本
        if existing_beliefs:
            belief_lines = []
            for i, b in enumerate(existing_beliefs):
                belief_lines.append(
                    f"[{i}] {b.proposition}（置信度:{b.confidence}，类型:{b.type.value}）"
                )
            existing_text = "\n".join(belief_lines)
        else:
            existing_text = "（无历史信念，这是第一轮对话）"

        # 构建prompt
        prompt = EXTRACTION_PROMPT_V2.format(
            student_input=student_input,
            existing_beliefs_text=existing_text,
            grade=grade,
            subject=subject
        )

        try:
            result = await generate_structured(prompt, EXTRACTION_SCHEMA_V2)

            # 解析新信念
            new_beliefs = []
            for item in result.get("new_beliefs", []):
                belief = self._parse_belief(item)
                if belief:
                    new_beliefs.append(belief)

            # 解析被取代的旧信念
            superseded_ids = []
            for idx in result.get("superseded_indices", []):
                if isinstance(idx, int) and 0 <= idx < len(existing_beliefs):
                    superseded_ids.append(existing_beliefs[idx].id)

            return new_beliefs, superseded_ids

        except Exception as e:
            print(f"信念提取v2失败: {e}")
            # 降级：规则提取 + 无淘汰
            fallback_beliefs = self._fallback_extraction(student_input)
            return fallback_beliefs, []

    def _parse_belief(self, data: Dict[str, Any]) -> Optional[Belief]:
        """解析单个信念"""
        try:
            proposition = data.get("proposition", "").strip()
            if not proposition:
                return None

            # 信念类型
            type_map = {
                "concept": BeliefType.CONCEPT,
                "procedure": BeliefType.PROCEDURE,
                "heuristic": BeliefType.HEURISTIC,
                "presupposition": BeliefType.PRESUPPOSITION
            }
            belief_type = type_map.get(
                data.get("type", "concept").lower(),
                BeliefType.CONCEPT
            )

            # 置信度
            confidence = max(0, min(1, float(data.get("confidence", 0.5))))

            # 情感标记
            emotion_map = {
                "neutral": EmotionalTag.NEUTRAL,
                "attached": EmotionalTag.ATTACHED,
                "insecure": EmotionalTag.INSECURE
            }
            emotional_tag = emotion_map.get(
                data.get("emotional_tag", "neutral").lower(),
                EmotionalTag.NEUTRAL
            )

            return Belief(
                proposition=proposition,
                type=belief_type,
                confidence=confidence,
                source="llm_extraction",
                emotional_tag=emotional_tag,
                metadata={
                    "layer": data.get("layer", "unknown"),
                    "reasoning": data.get("reasoning", "")
                }
            )

        except Exception as e:
            print(f"解析信念失败: {e}")
            return None

    def _fallback_extraction(self, student_input: str) -> List[Belief]:
        """规则降级提取"""
        beliefs = []
        patterns = [
            r'([a-zA-Z])\s*=\s*(\d+)',
            r'答案是\s*(\d+)',
            r'等于\s*(\d+)',
            r'应该是\s*(\d+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, student_input)
            for match in matches:
                if isinstance(match, tuple):
                    proposition = f"{match[0]}={match[1]}" if len(match) == 2 else match[0]
                else:
                    proposition = f"答案是{match}"

                beliefs.append(Belief(
                    proposition=proposition,
                    type=BeliefType.CONCEPT,
                    confidence=0.6,
                    source="rule_extraction",
                    emotional_tag=EmotionalTag.NEUTRAL,
                    metadata={"layer": "表层", "method": "fallback"}
                ))

        if not beliefs and student_input.strip():
            beliefs.append(Belief(
                proposition=student_input.strip()[:50],
                type=BeliefType.CONCEPT,
                confidence=0.4,
                source="fallback",
                emotional_tag=EmotionalTag.NEUTRAL,
                metadata={"layer": "表层", "method": "fallback_generic"}
            ))

        return beliefs

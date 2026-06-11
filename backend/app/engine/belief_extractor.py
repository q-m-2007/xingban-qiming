"""
CCG信念提取器
从学生输入中提取信念（表层、中层、深层）
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.ccg_models import (
    Belief, BeliefType, EmotionalTag
)
from ..engine.llm_client import generate_structured


# ── Prompt模板 ────────────────────────────────────────────────


BELIEF_EXTRACTION_PROMPT = """你是一位专业的数学教育AI助手，正在分析学生的数学思维。

学生输入："{student_input}"

上下文信息：
- 学段：{grade}
- 学科：{subject}
- 当前题目：{question_context}

请从学生的回答中提取以下三个层次的信念：

1. **表层信念**：学生明确表达的数学命题
   - 例如："x=3"、"答案是5"

2. **中层信念**：学生回答中隐含的前提假设
   - 例如："我以为可以直接移过去"、"我觉得这道题应该用加法"

3. **深层信念**：学生回答背后反映的思维习惯
   - 例如："我习惯先算右边再算左边"、"看到最大值就想到顶点"

对于每个信念，请判断：
- 信念类型（concept/procedure/heuristic/presupposition）
- 置信度（0-1，根据学生语气判断）
- 情感标记（neutral/attached/insecure）

请返回JSON格式，包含提取的信念列表。"""


# ── 输出Schema ────────────────────────────────────────────────


BELIEF_SCHEMA = {
    "beliefs": [
        {
            "proposition": "string - 信念的命题表述",
            "layer": "string - 表层/中层/深层",
            "type": "string - concept/procedure/heuristic/presupposition",
            "confidence": "float - 0到1之间的置信度",
            "emotional_tag": "string - neutral/attached/insecure",
            "reasoning": "string - 提取这个信念的理由"
        }
    ]
}


# ── 信念提取器 ────────────────────────────────────────────────


class BeliefExtractor:
    """
    信念提取器
    从学生输入中提取结构化信念
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    async def extract_beliefs(
        self,
        student_input: str,
        grade: str = "high_school",
        subject: str = "math",
        question_context: str = ""
    ) -> List[Belief]:
        """
        从学生输入中提取信念
        
        Args:
            student_input: 学生的输入文本
            grade: 学段（high_school/primary_school）
            subject: 学科
            question_context: 当前题目上下文
            
        Returns:
            提取的信念列表
        """
        # 构建prompt
        prompt = BELIEF_EXTRACTION_PROMPT.format(
            student_input=student_input,
            grade=grade,
            subject=subject,
            question_context=question_context or "无特定题目"
        )
        
        try:
            # 调用LLM提取
            result = await generate_structured(prompt, BELIEF_SCHEMA)
            
            # 解析结果
            beliefs = []
            for belief_data in result.get("beliefs", []):
                belief = self._parse_belief(belief_data)
                if belief:
                    beliefs.append(belief)
            
            return beliefs
            
        except Exception as e:
            print(f"信念提取失败: {e}")
            # 降级：使用规则提取
            return self._fallback_extraction(student_input)
    
    def _parse_belief(self, data: Dict[str, Any]) -> Optional[Belief]:
        """解析单个信念数据"""
        try:
            # 验证必填字段
            proposition = data.get("proposition", "").strip()
            if not proposition:
                return None
            
            # 解析信念类型
            belief_type_str = data.get("type", "concept").lower()
            belief_type_map = {
                "concept": BeliefType.CONCEPT,
                "procedure": BeliefType.PROCEDURE,
                "heuristic": BeliefType.HEURISTIC,
                "presupposition": BeliefType.PRESUPPOSITION
            }
            belief_type = belief_type_map.get(belief_type_str, BeliefType.CONCEPT)
            
            # 解析置信度
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0, min(1, confidence))
            
            # 解析情感标记
            emotional_tag_str = data.get("emotional_tag", "neutral").lower()
            emotional_tag_map = {
                "neutral": EmotionalTag.NEUTRAL,
                "attached": EmotionalTag.ATTACHED,
                "insecure": EmotionalTag.INSECURE
            }
            emotional_tag = emotional_tag_map.get(emotional_tag_str, EmotionalTag.NEUTRAL)
            
            # 创建信念对象
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
        """
        降级提取（规则引擎）
        当LLM调用失败时使用
        """
        beliefs = []
        
        # 简单规则：提取"X=Y"格式的命题
        import re
        
        # 匹配 "x=3"、"答案是5" 等模式
        patterns = [
            r'([a-zA-Z])\s*=\s*(\d+)',  # x=3
            r'答案是\s*(\d+)',  # 答案是5
            r'等于\s*(\d+)',  # 等于5
            r'应该是\s*(\d+)',  # 应该是5
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
        
        # 如果没有提取到任何信念，创建一个通用信念
        if not beliefs and student_input.strip():
            beliefs.append(Belief(
                proposition=student_input.strip()[:50],  # 截取前50字符
                type=BeliefType.CONCEPT,
                confidence=0.4,
                source="fallback",
                emotional_tag=EmotionalTag.NEUTRAL,
                metadata={"layer": "表层", "method": "fallback_generic"}
            ))
        
        return beliefs


# ── 置信度校准器 ────────────────────────────────────────────────


class ConfidenceCalibrator:
    """
    置信度校准器
    综合多个信号计算信念的置信度
    """
    
    # 权重配置
    WEIGHTS = {
        "linguistic_certainty": 0.5,
        "behavioral_consistency": 0.3,
        "historical_stability": 0.2
    }
    
    @staticmethod
    def calibrate(
        belief: Belief,
        linguistic_certainty: Optional[float] = None,
        behavioral_consistency: Optional[float] = None,
        historical_stability: Optional[float] = None
    ) -> float:
        """
        校准置信度
        
        Args:
            belief: 原始信念
            linguistic_certainty: 语言确信度（从语气推断）
            behavioral_consistency: 行为一致性（说和做是否一致）
            historical_stability: 历史稳定性（该信念在历史中是否稳定出现）
            
        Returns:
            校准后的置信度
        """
        # 默认值
        linguistic = linguistic_certainty if linguistic_certainty is not None else belief.confidence
        behavioral = behavioral_consistency if behavioral_consistency is not None else 0.5
        historical = historical_stability if historical_stability is not None else 0.5
        
        # 加权计算
        calibrated = (
            ConfidenceCalibrator.WEIGHTS["linguistic_certainty"] * linguistic +
            ConfidenceCalibrator.WEIGHTS["behavioral_consistency"] * behavioral +
            ConfidenceCalibrator.WEIGHTS["historical_stability"] * historical
        )
        
        return max(0, min(1, calibrated))
    
    @staticmethod
    def infer_linguistic_certainty(text: str) -> float:
        """
        从文本推断语言确信度
        
        高确信（0.8+）：肯定句、确定性词汇
        中确信（0.5-0.7）：一般陈述
        低确信（<0.5）：犹豫、不确定词汇
        """
        text_lower = text.lower()
        
        # 高确信词汇
        high_confidence_words = [
            "肯定", "一定", "确定", "绝对是", "肯定是",
            "我确定", "我肯定", "毫无疑问", "肯定是"
        ]
        
        # 低确信词汇
        low_confidence_words = [
            "可能", "也许", "大概", "不确定", "不太确定",
            "我猜", "应该是", "可能是", "也许吧", "不知道"
        ]
        
        # 检查高确信
        for word in high_confidence_words:
            if word in text_lower:
                return 0.9
        
        # 检查低确信
        for word in low_confidence_words:
            if word in text_lower:
                return 0.3
        
        # 默认中等确信
        return 0.6

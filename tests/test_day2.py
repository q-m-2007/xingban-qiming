"""
Day 2 单元测试：信念提取模块
"""

import pytest
import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.models.ccg_models import Belief, BeliefType, EmotionalTag
from app.engine.belief_extractor import BeliefExtractor, ConfidenceCalibrator


# ── 信念提取器测试 ────────────────────────────────────────────────


class TestBeliefExtractor:
    """测试信念提取器"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.extractor = BeliefExtractor()
    
    def test_fallback_extraction_equation(self):
        """测试降级提取：方程"""
        beliefs = self.extractor._fallback_extraction("x=3")
        
        assert len(beliefs) >= 1
        assert any("x=3" in b.proposition for b in beliefs)
        assert all(b.source == "rule_extraction" for b in beliefs)
    
    def test_fallback_extraction_answer(self):
        """测试降级提取：答案"""
        beliefs = self.extractor._fallback_extraction("答案是5")
        
        assert len(beliefs) >= 1
        assert any("5" in b.proposition for b in beliefs)
    
    def test_fallback_extraction_generic(self):
        """测试降级提取：通用输入"""
        beliefs = self.extractor._fallback_extraction("我觉得这道题很难")
        
        assert len(beliefs) == 1
        assert beliefs[0].source == "fallback"
        assert beliefs[0].confidence == 0.4
    
    def test_parse_belief_valid(self):
        """测试解析有效信念数据"""
        data = {
            "proposition": "x等于3",
            "layer": "表层",
            "type": "concept",
            "confidence": 0.8,
            "emotional_tag": "neutral",
            "reasoning": "学生明确说了x=3"
        }
        
        belief = self.extractor._parse_belief(data)
        
        assert belief is not None
        assert belief.proposition == "x等于3"
        assert belief.type == BeliefType.CONCEPT
        assert belief.confidence == 0.8
        assert belief.emotional_tag == EmotionalTag.NEUTRAL
        assert belief.metadata["layer"] == "表层"
    
    def test_parse_belief_missing_proposition(self):
        """测试解析缺少命题的信念"""
        data = {
            "type": "concept",
            "confidence": 0.8
        }
        
        belief = self.extractor._parse_belief(data)
        
        assert belief is None
    
    def test_parse_belief_invalid_type(self):
        """测试解析无效类型"""
        data = {
            "proposition": "测试",
            "type": "invalid_type",
            "confidence": 0.5
        }
        
        belief = self.extractor._parse_belief(data)
        
        assert belief is not None
        assert belief.type == BeliefType.CONCEPT  # 默认值
    
    def test_parse_belief_confidence_clamping(self):
        """测试置信度范围限制"""
        data = {
            "proposition": "测试",
            "type": "concept",
            "confidence": 1.5  # 超出范围
        }
        
        belief = self.extractor._parse_belief(data)
        
        assert belief is not None
        assert belief.confidence == 1.0  # 被限制到1.0
        
        data["confidence"] = -0.5
        belief = self.extractor._parse_belief(data)
        assert belief.confidence == 0.0  # 被限制到0.0


# ── 置信度校准器测试 ────────────────────────────────────────────────


class TestConfidenceCalibrator:
    """测试置信度校准器"""
    
    def test_calibrate_default(self):
        """测试默认校准"""
        belief = Belief(
            proposition="测试",
            type=BeliefType.CONCEPT,
            confidence=0.6
        )
        
        calibrated = ConfidenceCalibrator.calibrate(belief)
        
        # 默认值：0.5*0.6 + 0.3*0.5 + 0.2*0.5 = 0.3 + 0.15 + 0.1 = 0.55
        assert abs(calibrated - 0.55) < 0.01
    
    def test_calibrate_with_values(self):
        """测试带参数校准"""
        belief = Belief(
            proposition="测试",
            type=BeliefType.CONCEPT,
            confidence=0.8
        )
        
        calibrated = ConfidenceCalibrator.calibrate(
            belief,
            linguistic_certainty=0.9,
            behavioral_consistency=0.7,
            historical_stability=0.6
        )
        
        # 0.5*0.9 + 0.3*0.7 + 0.2*0.6 = 0.45 + 0.21 + 0.12 = 0.78
        assert abs(calibrated - 0.78) < 0.01
    
    def test_calibrate_clamping(self):
        """测试校准结果范围"""
        belief = Belief(
            proposition="测试",
            type=BeliefType.CONCEPT,
            confidence=0.5
        )
        
        # 所有值都为1.0
        calibrated = ConfidenceCalibrator.calibrate(
            belief,
            linguistic_certainty=1.0,
            behavioral_consistency=1.0,
            historical_stability=1.0
        )
        
        assert calibrated == 1.0
        
        # 所有值都为0.0
        calibrated = ConfidenceCalibrator.calibrate(
            belief,
            linguistic_certainty=0.0,
            behavioral_consistency=0.0,
            historical_stability=0.0
        )
        
        assert calibrated == 0.0
    
    def test_infer_linguistic_certainty_high(self):
        """测试推断高确信度"""
        text = "我确定x等于3"
        certainty = ConfidenceCalibrator.infer_linguistic_certainty(text)
        
        assert certainty >= 0.8
    
    def test_infer_linguistic_certainty_low(self):
        """测试推断低确信度"""
        text = "可能是5吧"
        certainty = ConfidenceCalibrator.infer_linguistic_certainty(text)
        
        assert certainty <= 0.4
    
    def test_infer_linguistic_certainty_medium(self):
        """测试推断中等确信度"""
        text = "x等于3"
        certainty = ConfidenceCalibrator.infer_linguistic_certainty(text)
        
        assert 0.4 <= certainty <= 0.7


# ── 运行测试 ────────────────────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
CPPA 教学效果反馈闭环
记录每次教学的完整过程和结果，用于优化算法
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json


@dataclass
class TeachingRecord:
    """一次完整的教学记录"""
    record_id: str
    student_id: str
    problem_id: str
    topic: str

    # 教学前状态
    profile_snapshot: Dict          # 教学前的画像快照
    strategy_used: str              # 使用的教学策略
    method_recommended: str         # 推荐的解法

    # 教学过程
    total_rounds: int               # 总对话轮次
    stuck_rounds: int               # 卡壳轮次
    hints_given: int                # 给了几个提示
    analogy_used: bool              # 是否用了类比讲解
    concept_rebuild_used: bool      # 是否用了概念重建

    # 教学结果
    student_actual_method: str      # 学生实际用的方法
    success: bool                   # 是否成功
    time_spent: float               # 耗时（秒）
    verification_level: int         # 三阶验证通过了几阶（0-3）
    transfer_success: bool          # 变式题是否成功

    # 学生反馈
    student_satisfaction: str       # 'confident' | 'ok' | 'confused' | 'frustrated'

    # 元信息
    timestamp: str = ''
    notes: str = ''

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class TeachingRecordStore:
    """教学记录存储"""

    def __init__(self):
        self.records: List[TeachingRecord] = []

    def add_record(self, record: TeachingRecord):
        """添加教学记录"""
        self.records.append(record)

    def get_student_records(self, student_id: str) -> List[TeachingRecord]:
        """获取某学生的所有教学记录"""
        return [r for r in self.records if r.student_id == student_id]

    def get_topic_records(self, topic: str) -> List[TeachingRecord]:
        """获取某知识点的所有教学记录"""
        return [r for r in self.records if r.topic == topic]

    def get_strategy_effectiveness(self) -> Dict[str, Dict]:
        """分析各教学策略的效果"""
        strategy_stats = {}

        for record in self.records:
            s = record.strategy_used
            if s not in strategy_stats:
                strategy_stats[s] = {
                    'total': 0, 'success': 0,
                    'avg_time': 0, 'avg_verification': 0,
                    'transfer_success': 0,
                }
            stats = strategy_stats[s]
            stats['total'] += 1
            if record.success:
                stats['success'] += 1
            stats['avg_time'] += record.time_spent
            stats['avg_verification'] += record.verification_level
            if record.transfer_success:
                stats['transfer_success'] += 1

        # 计算平均值
        for s, stats in strategy_stats.items():
            total = stats['total']
            if total > 0:
                stats['success_rate'] = stats['success'] / total
                stats['avg_time'] /= total
                stats['avg_verification'] /= total
                stats['transfer_rate'] = stats['transfer_success'] / total

        return strategy_stats

    def get_method_effectiveness(self) -> Dict[str, Dict]:
        """分析各解法的教学效果"""
        method_stats = {}

        for record in self.records:
            m = record.method_recommended
            if m not in method_stats:
                method_stats[m] = {
                    'total': 0, 'success': 0,
                    'avg_time': 0, 'avg_verification': 0,
                }
            stats = method_stats[m]
            stats['total'] += 1
            if record.success:
                stats['success'] += 1
            stats['avg_time'] += record.time_spent
            stats['avg_verification'] += record.verification_level

        for m, stats in method_stats.items():
            total = stats['total']
            if total > 0:
                stats['success_rate'] = stats['success'] / total
                stats['avg_time'] /= total
                stats['avg_verification'] /= total

        return method_stats

    def generate_report(self, student_id: Optional[str] = None) -> str:
        """生成教学效果报告"""
        records = self.get_student_records(student_id) if student_id else self.records

        if not records:
            return "暂无教学记录"

        lines = ["═══ 教学效果报告 ═══\n"]

        if student_id:
            lines.append(f"学生：{student_id}")
        lines.append(f"总记录：{len(records)}次\n")

        # 策略效果
        strategy_stats = self.get_strategy_effectiveness()
        lines.append("【教学策略效果】")
        strategy_names = {
            'A_guided': '追问引导',
            'B_hint': '提示+追问',
            'C_analogy': '类比讲解',
            'D_concept': '概念重建',
            'E_comfort': '安抚降级',
            'F_inertia': '惯性突破',
        }
        for s, stats in strategy_stats.items():
            name = strategy_names.get(s, s)
            lines.append(f"  {name}: {stats['total']}次, "
                        f"成功率{stats.get('success_rate', 0):.0%}, "
                        f"平均耗时{stats.get('avg_time', 0):.0f}秒")

        # 解法效果
        method_stats = self.get_method_effectiveness()
        lines.append("\n【解法教学效果】")
        for m, stats in method_stats.items():
            lines.append(f"  {m}: {stats['total']}次, "
                        f"成功率{stats.get('success_rate', 0):.0%}")

        # 趋势分析
        if len(records) >= 10:
            recent_5 = records[-5:]
            prev_5 = records[-10:-5]
            recent_acc = sum(1 for r in recent_5 if r.success) / 5
            prev_acc = sum(1 for r in prev_5 if r.success) / 5
            if recent_acc > prev_acc + 0.1:
                trend = "📈 进步中"
            elif recent_acc < prev_acc - 0.1:
                trend = "📉 需要关注"
            else:
                trend = "➡️ 稳定"
            lines.append(f"\n【趋势】{trend}")
            lines.append(f"  最近5次成功率：{recent_acc:.0%}")
            lines.append(f"  之前5次成功率：{prev_acc:.0%}")

        return '\n'.join(lines)

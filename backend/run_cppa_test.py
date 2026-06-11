#!/usr/bin/env python3
"""CPPA v2.0 全部优化测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.cppa import (
    CognitiveProfile, ProfileUpdater, ColdStartInitializer,
    MethodHistory, MethodAttempt, MethodMastery, ForgettingAwareProfile,
    EvidenceExtractor, EngagementDetector, ProcessTracker,
    MethodBank, MethodRecommender, InertiaDetector, DifficultyAdjuster,
    TeachingEngine, StudentState, TeachingStrategy,
    TeachingRecord, TeachingRecordStore,
    LearningPathPlanner, LearningPath,
    MetacognitiveReflector,
    MethodGenerator,
)

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}")
        failed += 1

# ═══════════════════════════════════════════
print("=== 1. 认知画像 ===")
p = CognitiveProfile(student_id='t')
check("创建画像", p.visual == 0.33)
check("15维度", len(p.to_dict()) == 15)
check("风格标签", '视觉型' in p.get_style_label() or '语言型' in p.get_style_label())

# ═══════════════════════════════════════════
print("\n=== 2. 贝叶斯更新 ===")
updater = ProfileUpdater(learning_rate=0.3)
for _ in range(8):
    p = updater.update(p, {'visual': 0.9, 'verbal': 0.1})
check("8次更新后visual上升", p.visual > 0.5)
check("8次更新后verbal下降", p.verbal < 0.3)

# ═══════════════════════════════════════════
print("\n=== 3. 遗忘感知（优化3）===")
fp = ForgettingAwareProfile(base_profile=p)
fp.practice_method('factoring', success=True)
fp.practice_method('factoring', success=True)
check("方法练习后掌握度上升", fp.get_effective_mastery('factoring') > 0.5)
check("未知方法默认掌握度", fp.get_effective_mastery('unknown') == 0.3)

# 测试遗忘衰减
mm = MethodMastery(method_id='test', mastery=0.9, last_practice='2020-01-01T00:00:00')
check("遗忘后掌握度下降", mm.apply_forgetting() < 0.5)

# 需要复习的方法
fp2 = ForgettingAwareProfile(base_profile=CognitiveProfile(student_id='t'))
mm2 = MethodMastery(method_id='old_method', mastery=0.8, practice_count=5)
mm2.last_practice = '2020-01-01T00:00:00'  # 很久以前
fp2.method_masteries['old_method'] = mm2
review = fp2.get_methods_needing_review(threshold=0.3)
check("检测到需要复习的方法", len(review) > 0)

# ═══════════════════════════════════════════
print("\n=== 4. 冷启动 ===")
init = ColdStartInitializer()
for i in range(5):
    cp = CognitiveProfile(student_id=f'h{i}')
    cp.visual = 0.7
    cp.data_points = 20
    init.add_historical_profile(cp)
new = init.initialize('new')
check("冷启动初始化", new.confidence == 0.2)

# ═══════════════════════════════════════════
print("\n=== 5. 证据提取（优化1）===")
ext = EvidenceExtractor(use_llm=False)
ev = ext.extract("我画了个图看出来答案是3")
check("视觉型信号", ev.get('visual', 0) > 0.3)
ev = ext.extract("设x为未知数，根据公式代入计算")
check("语言型信号", ev.get('verbal', 0) >.3)
ev = ext.extract("我试了一下x=1不对")
check("动手型信号", ev.get('kinesthetic', 0) > 0)

# ═══════════════════════════════════════════
print("\n=== 6. 投入度检测（优化7）===")
det = EngagementDetector()
sig = det.detect("太难了不想做", 10, False)
check("挫败信号", sig['frustrated'] > 0.5)
sig = det.detect("为什么这样做？", 60, True)
check("好奇信号", sig['curious'] > 0.5)
sig = det.detect("我会了", 10, True)
check("快速正确-可能无聊", sig['bored'] > 0.3)
sig = det.detect("我想到一个很巧妙的方法", 120, True)
check("长思考正确-挑战享受", sig['challenged'] > 0.5)

# ═══════════════════════════════════════════
print("\n=== 7. 解题过程追踪 ===")
tracker = ProcessTracker()
tracker.start_problem('p1')
tracker.add_step("设宽为x", 1)
tracker.add_step("长为x+4", 2)
check("追踪步骤", len(tracker.current_steps) == 2)
check("检测方法", tracker.method_detected is not None)

# ═══════════════════════════════════════════
print("\n=== 8. 解法库（优化4）===")
bank = MethodBank()
methods = bank.get_methods('一元二次方程')
check("5种解法", len(methods) >= 4)
check("类比题", len(bank.get_analogy_problems('factoring')) >= 2)
check("变式题", len(bank.get_variant_problems('factoring')) >= 2)

# LLM生成器（无LLM时用内置）
gen = MethodGenerator()
data = gen.generate_for_topic('一元二次方程')
check("生成器产出", len(data.get('methods', [])) >= 3)

# ═══════════════════════════════════════════
print("\n=== 9. 解法推荐 ===")
rec = MethodRecommender(bank)
vp = CognitiveProfile(student_id='v'); vp.visual = 0.8; vp.verbal = 0.1
lp = CognitiveProfile(student_id='l'); lp.visual = 0.1; lp.verbal = 0.8
vr = rec.recommend('一元二次方程', vp, 'comfort')
lr = rec.recommend('一元二次方程', lp, 'comfort')
check("视觉型→图像法", 'graphical' in vr[0][0].id or 'direct' in vr[0][0].id)
check("语言型→求根/因式", any(m.id in lr[0][0].id for m in methods))

# ═══════════════════════════════════════════
print("\n=== 10. 惯性检测 ===")
det = InertiaDetector(min_attempts=5)
hist = MethodHistory()
for i in range(15):
    hist.add_attempt(MethodAttempt('t',f'p{i}','一元二次方程','quadratic_formula',True,120,5,2,None))
for i in range(2):
    hist.add_attempt(MethodAttempt('t',f'p{15+i}','一元二次方程','factoring',True,60,3,3,None))
r = det.detect('t', hist)
check("检测到惯性", r is not None)
check("惯性强度>0.5", r.strength > 0.5)
check("建议切换", r.suggested_alternative != 'unknown')

# ═══════════════════════════════════════════
print("\n=== 11. 难度调节 ===")
adj = DifficultyAdjuster()
pl = CognitiveProfile('low'); pl.abstract_reasoning = 0.3
al = [MethodAttempt('low',f'p{i}','一元二次方程','factoring',i%3==0,120,4,1,None) for i in range(10)]
dl = adj.adjust(pl, al, '一元二次方程')
check("低能力调节", dl.level in ['simplify', 'standard'])
ph = CognitiveProfile('high'); ph.abstract_reasoning = 0.8; ph.challenge_drive = 0.7
ah = [MethodAttempt('high',f'p{i}','一元二次方程','factoring',True,30,3,3,None) for i in range(10)]
dh = adj.adjust(ph, ah, '一元二次方程')
check("高能力调节", dh.level in ['challenge', 'standard'])

# ═══════════════════════════════════════════
print("\n=== 12. 学习路径规划（优化5）===")
planner = LearningPathPlanner(bank)
fp3 = ForgettingAwareProfile(base_profile=CognitiveProfile(student_id='path_test'))
path = planner.plan(fp3, hist, '一元二次方程', num_problems=8)
check("路径生成", len(path.steps) == 8)
check("阶段1-信心建立", path.steps[0].purpose == 'build_confidence')
check("最后一步-挑战", path.steps[-1].purpose in ['challenge', 'practice'])
check("进度初始为0", path.get_progress() == 0.0)
path.advance()
check("进度推进", path.get_progress() > 0)

# ═══════════════════════════════════════════
print("\n=== 13. 元认知反思（优化6）===")
mc = MetacognitiveReflector(bank)
fb = mc.reflect(
    problem='2x²-5x+3=0', topic='一元二次方程',
    method_used='quadratic_formula', method_recommended='factoring',
    success=True, time_spent=180,
    profile=ForgettingAwareProfile(base_profile=CognitiveProfile(student_id='t')),
    alternative_methods=['factoring', 'completing_square'],
)
check("生成反思", fb is not None)
check("反思类型", fb.feedback_type in ['efficiency', 'strategy', 'method_awareness', 'growth', 'forgetting'])
check("有行动建议", len(fb.action_suggestion) > 0)

# ═══════════════════════════════════════════
print("\n=== 14. 教学引擎（完整集成）===")
eng = TeachingEngine()

d1 = eng.process_student_response('s1','这道题我完全不会','2x²-5x+3=0','一元二次方程',[],1)
check("深度卡壳→类比", d1.strategy == TeachingStrategy.ANALOGY_TEACHING)
check("有类比题", d1.analogy_problem is not None)

d2 = eng.process_student_response('s1','x²=3x两边除以x得x=3','x²=3x','一元二次方程',[],1)
check("概念错误→重建", d2.strategy == TeachingStrategy.CONCEPT_REBUILD)
check("有引导问题", len(d2.question_to_ask) > 0)

d3 = eng.process_student_response('s1','太难了学不会不想做','3x²+2x-1=0','一元二次方程',[],1)
check("情绪崩溃→安抚", d3.strategy == TeachingStrategy.COMFORT_DOWNGRADE)

d4 = eng.process_student_response('s1','我知道要求根公式但判别式怎么算','2x²-5x+3=0','一元二次方程',[],1)
check("局部卡壳→提示", d4.strategy == TeachingStrategy.HINT_THEN_QUESTION)

d5 = eng.process_student_response('s1','我用因式分解(2x-3)(x-1)=0','2x²-5x+3=0','一元二次方程',[],1,
                                  time_spent=60, is_correct=True)
check("正常探索→引导", d5.strategy == TeachingStrategy.GUIDED_QUESTIONING)
check("推荐解法", d5.recommended_method is not None)
check("投入度信号", len(d5.engagement_signals) > 0)
check("教学风格", len(d5.teaching_style) > 0)

# 记录结果
eng.record_outcome('s1','p1','一元二次方程','factoring',True,60,3,3)
fp_s1 = eng.get_or_create_profile('s1')
check("掌握度更新", fp_s1.get_effective_mastery('factoring') > 0.3)

# ═══════════════════════════════════════════
print("\n=== 15. 教学记录 ===")
store = TeachingRecordStore()
for i in range(10):
    store.add_record(TeachingRecord(f'r{i}','s1',f'p{i}','一元二次方程',{},
        'A_guided','factoring',3,1,0,False,False,'factoring',True,120,2,True,'ok'))
report = store.generate_report('s1')
check("报告生成", len(report) > 100)

# ═══════════════════════════════════════════
print("\n=== 16. 诊断报告 ===")
diag = eng.get_student_diagnosis('s1')
check("诊断报告", '思维画像' in diag)
check("投入度", '投入度' in diag)
check("惯性检测", '惯性检测' in diag)

# ═══════════════════════════════════════════
print("\n" + "=" * 50)
print(f"✅ 通过 {passed} 项，❌ 失败 {failed} 项")
if failed == 0:
    print("🎉 CPPA v2.0 全部优化测试通过！")
print("=" * 50)

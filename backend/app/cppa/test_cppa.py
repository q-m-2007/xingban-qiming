"""
CPPA 算法测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cppa import (
    CognitiveProfile, ProfileUpdater, ColdStartInitializer,
    MethodHistory, MethodAttempt,
    EvidenceExtractor, ProcessTracker,
    MethodBank, Method, AnalogyProblem,
    MethodRecommender,
    InertiaDetector,
    DifficultyAdjuster,
    TeachingEngine, StudentState, TeachingStrategy,
    TeachingRecord, TeachingRecordStore,
)


def test_cognitive_profile():
    """测试认知画像"""
    print("=== 测试认知画像 ===")

    # 创建画像
    profile = CognitiveProfile(student_id='test_001')
    assert profile.visual == 0.33
    assert profile.data_points == 0
    print("  ✅ 创建画像")

    # 转换为字典
    d = profile.to_dict()
    assert 'visual' in d
    assert len(d) == 15
    print("  ✅ 字典转换")

    # 从字典恢复
    profile2 = CognitiveProfile.from_dict(d)
    assert profile2.visual == profile.visual
    print("  ✅ 字典恢复")

    # 获取风格标签
    label = profile.get_style_label()
    assert isinstance(label, str)
    print(f"  ✅ 风格标签：{label}")

    # 获取主导维度
    dominant = profile.get_dominant('information_style')
    assert dominant in ['visual', 'verbal', 'kinesthetic']
    print(f"  ✅ 主导维度：{dominant}")


def test_profile_updater():
    """测试画像更新器"""
    print("\n=== 测试画像更新器 ===")

    updater = ProfileUpdater(learning_rate=0.3)
    profile = CognitiveProfile(student_id='test_002')

    # 用视觉型证据更新
    evidence = {'visual': 0.9, 'verbal': 0.2, 'kinesthetic': 0.3}
    profile = updater.update(profile, evidence)

    assert profile.visual > 0.33  # 应该上升
    assert profile.data_points == 1
    print(f"  ✅ 更新后 visual={profile.visual:.3f} (上升)")

    # 多次更新强化
    for _ in range(5):
        profile = updater.update(profile, {'visual': 0.9, 'verbal': 0.1})

    assert profile.visual > 0.5
    print(f"  ✅ 5次强化后 visual={profile.visual:.3f}")


def test_cold_start():
    """测试冷启动"""
    print("\n=== 测试冷启动 ===")

    initializer = ColdStartInitializer()

    # 添加历史学生
    for i in range(5):
        p = CognitiveProfile(student_id=f'hist_{i}')
        p.visual = 0.7
        p.verbal = 0.2
        p.data_points = 20
        initializer.add_historical_profile(p)

    # 初始化新学生
    new_profile = initializer.initialize('new_001')
    assert new_profile.student_id == 'new_001'
    assert new_profile.confidence == 0.2
    print(f"  ✅ 冷启动 visual={new_profile.visual:.3f}")


def test_evidence_extractor():
    """测试证据提取"""
    print("\n=== 测试证据提取 ===")

    extractor = EvidenceExtractor()

    # 视觉型回答
    evidence = extractor.extract("我画了个图，看出来答案是3")
    assert evidence.get('visual', 0) > 0.3
    print(f"  ✅ 视觉型信号：{evidence}")

    # 语言型回答
    evidence = extractor.extract("设x为未知数，根据公式代入计算")
    assert evidence.get('verbal', 0) > 0.3
    print(f"  ✅ 语言型信号：{evidence}")

    # 动手型回答
    evidence = extractor.extract("我试了一下x=1，不对，又试了x=2")
    assert evidence.get('kinesthetic', 0) > 0.3
    print(f"  ✅ 动手型信号：{evidence}")

    # 情绪检测
    emotion = extractor._detect_emotion("太难了，我学不会")
    assert emotion == 'frustrated'
    print(f"  ✅ 情绪检测：{emotion}")


def test_process_tracker():
    """测试解题过程追踪"""
    print("\n=== 测试解题过程追踪 ===")

    tracker = ProcessTracker()
    tracker.start_problem('p001')

    # 添加步骤
    tracker.add_step("设宽为x", 1)
    tracker.add_step("长为x+4", 2)
    tracker.add_step("面积x(x+4)=20", 3)

    assert len(tracker.current_steps) == 3
    assert tracker.method_detected is not None
    print(f"  ✅ 追踪了{len(tracker.current_steps)}步")
    print(f"  ✅ 检测到方法：{tracker.method_detected}")

    # 标记错误
    tracker.mark_error(3, 'calculation_error')
    summary = tracker.get_process_summary()
    assert summary['error_step'] == 3
    print(f"  ✅ 标记错误在第{summary['error_step']}步")


def test_method_bank():
    """测试解法库"""
    print("\n=== 测试解法库 ===")

    bank = MethodBank()

    # 获取一元二次方程的解法
    methods = bank.get_methods('一元二次方程')
    assert len(methods) >= 4
    print(f"  ✅ 一元二次方程有{len(methods)}种解法")

    for m in methods:
        print(f"    - {m.name}: 难度{m.difficulty}, 效率{m.efficiency}")

    # 获取类比题
    analogies = bank.get_analogy_problems('factoring')
    assert len(analogies) >= 2
    print(f"  ✅ 因式分解法有{len(analogies)}道类比题")

    # 获取变式题
    variants = bank.get_variant_problems('factoring')
    assert len(variants) >= 2
    print(f"  ✅ 因式分解法有{len(variants)}道变式题")


def test_method_recommender():
    """测试解法推荐"""
    print("\n=== 测试解法推荐 ===")

    bank = MethodBank()
    recommender = MethodRecommender(bank)

    # 视觉型学生
    profile = CognitiveProfile(student_id='test_visual')
    profile.visual = 0.8
    profile.verbal = 0.1
    profile.kinesthetic = 0.1

    results = recommender.recommend('一元二次方程', profile, mode='comfort')
    assert len(results) > 0
    best_method, best_score = results[0]
    print(f"  ✅ 视觉型学生推荐：{best_method.name} (分数{best_score:.3f})")

    # 语言型学生
    profile2 = CognitiveProfile(student_id='test_verbal')
    profile2.visual = 0.1
    profile2.verbal = 0.8
    profile2.kinesthetic = 0.1

    results2 = recommender.recommend('一元二次方程', profile2, mode='comfort')
    best2 = results2[0][0]
    print(f"  ✅ 语言型学生推荐：{best2.name}")

    # 生成对比报告
    report = recommender.get_method_comparison('一元二次方程', profile)
    assert len(report) > 100
    print(f"  ✅ 对比报告长度：{len(report)}字符")


def test_inertia_detector():
    """测试惯性检测"""
    print("\n=== 测试惯性检测 ===")

    detector = InertiaDetector(min_attempts=5)
    history = MethodHistory()

    # 模拟学生一直用代数法
    for i in range(15):
        attempt = MethodAttempt(
            student_id='test_inertia',
            problem_id=f'p{i}',
            problem_type='一元二次方程',
            method_used='quadratic_formula',
            success=True,
            time_spent=120,
            steps_count=5,
            verification_level=2,
            error_type=None,
        )
        history.add_attempt(attempt)

    # 加2次其他方法
    for i in range(2):
        attempt = MethodAttempt(
            student_id='test_inertia',
            problem_id=f'p{15+i}',
            problem_type='一元二次方程',
            method_used='factoring',
            success=True,
            time_spent=60,
            steps_count=3,
            verification_level=3,
            error_type=None,
        )
        history.add_attempt(attempt)

    report = detector.detect('test_inertia', history)
    assert report is not None
    assert report.dominant_method == 'quadratic_formula'
    print(f"  ✅ 检测到惯性：{report.dominant_method}")
    print(f"    占比：{report.dominant_ratio:.0%}")
    print(f"    强度：{report.strength:.0%}")
    print(f"    建议切换：{report.suggested_alternative}")
    print(f"    突破策略：{report.breakthrough_strategy['name']}")


def test_difficulty_adjuster():
    """测试难度调节"""
    print("\n=== 测试难度调节 ===")

    adjuster = DifficultyAdjuster()

    # 正确率低的学生
    profile = CognitiveProfile(student_id='test_low')
    profile.abstract_reasoning = 0.3
    attempts = [
        MethodAttempt(
            student_id='test_low', problem_id=f'p{i}',
            problem_type='一元二次方程',
            method_used='factoring',
            success=i % 3 == 0,  # 33%正确率
            time_spent=120, steps_count=4, verification_level=1,
        )
        for i in range(10)
    ]

    decision = adjuster.adjust(profile, attempts, '一元二次方程')
    assert decision.level == 'simplify'
    print(f"  ✅ 低正确率：{decision.level} - {decision.description}")

    # 能力强的学生
    profile2 = CognitiveProfile(student_id='test_high')
    profile2.abstract_reasoning = 0.8
    profile2.challenge_drive = 0.7
    attempts2 = [
        MethodAttempt(
            student_id='test_high', problem_id=f'p{i}',
            problem_type='一元二次方程',
            method_used='factoring',
            success=True,
            time_spent=60, steps_count=3, verification_level=3,
        )
        for i in range(10)
    ]

    decision2 = adjuster.adjust(profile2, attempts2, '一元二次方程')
    assert decision2.level in ['challenge', 'standard']
    print(f"  ✅ 高能力：{decision2.level} - {decision2.description}")


def test_teaching_engine():
    """测试教学引擎（完整流程）"""
    print("\n=== 测试教学引擎 ===")

    engine = TeachingEngine()

    # 场景1：学生深度卡壳
    print("\n  场景1：深度卡壳")
    decision = engine.process_student_response(
        student_id='student_001',
        student_response='这道题我完全不会，不知道从哪开始',
        problem='解方程 2x² - 5x + 3 = 0',
        topic='一元二次方程',
        conversation_history=[],
        step_index=1,
    )
    assert decision.strategy == TeachingStrategy.ANALOGY_TEACHING
    assert decision.analogy_problem is not None
    print(f"    策略：{decision.strategy}")
    print(f"    类比题：{decision.analogy_problem.problem}")
    print(f"    难度：{decision.analogy_problem.level}")

    # 场景2：概念错误
    print("\n  场景2：概念错误")
    decision2 = engine.process_student_response(
        student_id='student_001',
        student_response='x²=3x，两边除以x，得x=3',
        problem='解方程 x² = 3x',
        topic='一元二次方程',
        conversation_history=[],
        step_index=1,
    )
    assert decision2.strategy == TeachingStrategy.CONCEPT_REBUILD
    assert decision2.question_to_ask != ''
    print(f"    策略：{decision2.strategy}")
    print(f"    引导问题：{decision2.question_to_ask}")

    # 场景3：情绪崩溃
    print("\n  场景3：情绪崩溃")
    decision3 = engine.process_student_response(
        student_id='student_001',
        student_response='太难了，我学不会，不想做了',
        problem='解方程 3x² + 2x - 1 = 0',
        topic='一元二次方程',
        conversation_history=[],
        step_index=1,
    )
    assert decision3.strategy == TeachingStrategy.COMFORT_DOWNGRADE
    print(f"    策略：{decision3.strategy}")

    # 场景4：局部卡壳
    print("\n  场景4：局部卡壳")
    decision4 = engine.process_student_response(
        student_id='student_001',
        student_response='我知道要求根公式，但判别式怎么算来着？',
        problem='解方程 2x² - 5x + 3 = 0',
        topic='一元二次方程',
        conversation_history=[],
        step_index=1,
    )
    assert decision4.strategy == TeachingStrategy.HINT_THEN_QUESTION
    print(f"    策略：{decision4.strategy}")
    print(f"    提示层级：L{decision4.hint_level}")

    # 场景5：正常探索
    print("\n  场景5：正常探索")
    decision5 = engine.process_student_response(
        student_id='student_001',
        student_response='我用因式分解试试，(2x-3)(x-1)=0',
        problem='解方程 2x² - 5x + 3 = 0',
        topic='一元二次方程',
        conversation_history=[],
        step_index=1,
    )
    assert decision5.strategy == TeachingStrategy.GUIDED_QUESTIONING
    print(f"    策略：{decision5.strategy}")
    print(f"    推荐解法：{decision5.recommended_method}")

    # 生成诊断报告
    print("\n  诊断报告：")
    report = engine.get_student_diagnosis('student_001')
    print(report)


def test_teaching_record():
    """测试教学记录"""
    print("\n=== 测试教学记录 ===")

    store = TeachingRecordStore()

    # 添加记录
    for i in range(10):
        record = TeachingRecord(
            record_id=f'rec_{i}',
            student_id='student_001',
            problem_id=f'p{i}',
            topic='一元二次方程',
            profile_snapshot={},
            strategy_used='A_guided' if i < 7 else 'C_analogy',
            method_recommended='factoring',
            total_rounds=3,
            stuck_rounds=1,
            hints_given=0,
            analogy_used=i >= 7,
            concept_rebuild_used=False,
            student_actual_method='factoring',
            success=i % 3 != 0,
            time_spent=120,
            verification_level=2,
            error_type=None,
            transfer_success=i % 2 == 0,
            student_satisfaction='ok',
        )
        store.add_record(record)

    # 生成报告
    report = store.generate_report('student_001')
    assert len(report) > 100
    print(report)


def test_full_teaching_flow():
    """测试完整教学流程"""
    print("\n=== 测试完整教学流程 ===")

    engine = TeachingEngine()
    student_id = 'student_flow_test'

    # 模拟完整的教学对话
    conversation = [
        {
            'student': '解方程 x² - 5x + 6 = 0，我不会',
            'expected_state': 'S3_deep_stuck',
        },
        {
            'student': '我试了一下x=1，不对',
            'expected_state': 'S1_exploring',
        },
        {
            'student': 'x²-5x+6=0，我设x=2，代入得4-10+6=0，对了！',
            'expected_state': 'S1_exploring',
        },
    ]

    history = []
    for i, turn in enumerate(conversation):
        decision = engine.process_student_response(
            student_id=student_id,
            student_response=turn['student'],
            problem='解方程 x² - 5x + 6 = 0',
            topic='一元二次方程',
            conversation_history=history,
            step_index=i + 1,
        )
        history.append(turn['student'])

        print(f"\n  轮次{i+1}:")
        print(f"    学生：{turn['student'][:30]}...")
        print(f"    策略：{decision.strategy}")
        print(f"    状态：{decision.state}")

        # 记录结果
        engine.record_outcome(
            student_id=student_id,
            problem_id='flow_p1',
            topic='一元二次方程',
            method_used='factoring',
            success=True,
            time_spent=90,
            steps_count=3,
            verification_level=2,
            error_type=None,
        )

    # 查看画像变化
    profile = engine.get_or_create_profile(student_id)
    print(f"\n  最终画像：{profile.get_style_label()}")
    print(f"  数据点：{profile.data_points}")


if __name__ == '__main__':
    test_cognitive_profile()
    test_profile_updater()
    test_cold_start()
    test_evidence_extractor()
    test_process_tracker()
    test_method_bank()
    test_method_recommender()
    test_inertia_detector()
    test_difficulty_adjuster()
    test_teaching_engine()
    test_teaching_record()
    test_full_teaching_flow()

    print("\n" + "=" * 50)
    print("✅ 全部测试通过！")
    print("=" * 50)

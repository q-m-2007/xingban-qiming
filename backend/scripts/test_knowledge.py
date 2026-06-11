#!/usr/bin/env python3
"""
星伴·启明 — 知识库测试脚本

测试内容：
1. 知识库初始化
2. 知识点添加
3. 知识点搜索
4. 知识点删除
"""

import sys
import os
import tempfile
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.knowledge.chroma_client import KnowledgeBase
from app.knowledge.seed_data import seed_knowledge_base, TOP30_KP
from app.knowledge.high_math_data import seed_high_math_kb, HIGH_MATH_KP
from app.knowledge.physics_data import seed_physics_kb, PHYSICS_KP


def test_knowledge_base():
    """
    测试知识库基本功能
    """
    print("🧪 开始测试知识库功能...")
    
    # 使用临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 使用临时目录: {temp_dir}")
        
        # 1. 测试初始化
        print("\n1️⃣ 测试初始化...")
        kb = KnowledgeBase(persist_directory=temp_dir)
        assert kb.count() == 0, "初始知识库应为空"
        print("   ✅ 初始化成功")
        
        # 2. 测试添加知识点
        print("\n2️⃣ 测试添加知识点...")
        test_kp = {
            "name": "测试考点",
            "description": "这是一个测试考点",
            "error_types": ["calculation_error"],
            "strategies": ["general_probe"],
            "grade": "初中",
            "subject": "数学"
        }
        kp_id = kb.add_knowledge_point(**test_kp)
        assert kp_id is not None, "应返回知识点ID"
        assert kb.count() == 1, "应有1条记录"
        print(f"   ✅ 添加成功，ID: {kp_id}")
        
        # 3. 测试搜索
        print("\n3️⃣ 测试搜索...")
        results = kb.search("测试考点", n_results=1)
        assert len(results) == 1, "应返回1条结果"
        assert results[0]['id'] == kp_id, "应返回刚添加的知识点"
        print(f"   ✅ 搜索成功，找到: {results[0]['metadata'].get('name')}")
        
        # 4. 测试删除
        print("\n4️⃣ 测试删除...")
        kb.delete_all()
        assert kb.count() == 0, "删除后应为空"
        print("   ✅ 删除成功")
        
        # 5. 测试批量灌入初中数学
        print("\n5️⃣ 测试批量灌入初中数学...")
        count = seed_knowledge_base(kb)
        assert count == len(TOP30_KP), f"应灌入{len(TOP30_KP)}个考点"
        print(f"   ✅ 初中数学灌入成功，共{count}个考点")
        
        # 6. 测试批量灌入高中数学
        print("\n6️⃣ 测试批量灌入高中数学...")
        count = seed_high_math_kb(kb)
        assert count == len(HIGH_MATH_KP), f"应灌入{len(HIGH_MATH_KP)}个考点"
        print(f"   ✅ 高中数学灌入成功，共{count}个考点")
        
        # 7. 测试批量灌入高中物理
        print("\n7️⃣ 测试批量灌入高中物理...")
        count = seed_physics_kb(kb)
        assert count == len(PHYSICS_KP), f"应灌入{len(PHYSICS_KP)}个考点"
        print(f"   ✅ 高中物理灌入成功，共{count}个考点")
        
        # 8. 验证总记录数
        expected_total = len(TOP30_KP) + len(HIGH_MATH_KP) + len(PHYSICS_KP)
        assert kb.count() == expected_total, f"应有{expected_total}条记录"
        print(f"\n   ✅ 总记录数验证通过: {kb.count()}")
        
        # 9. 测试语义搜索
        print("\n9️⃣ 测试语义搜索...")
        test_cases = [
            # 初中数学
            ("一元二次方程怎么解", "一元二次方程", "初中"),
            ("三角形全等的条件", "全等三角形", "初中"),
            # 高中数学
            ("三角函数图像", "三角函数", "高中"),
            ("导数的应用", "导数", "高中"),
            # 高中物理
            ("牛顿第二定律", "牛顿", "高中"),
            ("电磁感应", "电磁感应", "高中"),
        ]
        
        for query, expected_keyword, expected_grade in test_cases:
            results = kb.search(query, n_results=1)
            assert len(results) > 0, f"查询 '{query}' 应有结果"
            found_name = results[0]['metadata'].get('name', '')
            found_grade = results[0]['metadata'].get('grade', '')
            assert expected_keyword in found_name, \
                f"查询 '{query}' 应找到包含 '{expected_keyword}' 的考点，实际找到: {found_name}"
            print(f"   ✅ '{query}' -> {found_name} ({found_grade})")
        
        print("\n🎉 所有测试通过！")


def test_error_handling():
    """
    测试错误处理
    """
    print("\n🧪 测试错误处理...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        kb = KnowledgeBase(persist_directory=temp_dir)
        
        # 测试空搜索
        results = kb.search("不存在的查询", n_results=5)
        assert isinstance(results, list), "空搜索应返回列表"
        print("   ✅ 空搜索处理正常")
        
        # 测试添加空数据
        try:
            kb.add_knowledge_point(
                name="", 
                description="", 
                error_types=[], 
                strategies=[]
            )
            print("   ⚠️  允许添加空数据（可能需要业务规则限制）")
        except Exception as e:
            print(f"   ✅ 空数据添加被拒绝: {e}")


def benchmark_search():
    """
    搜索性能基准测试
    """
    print("\n⏱️  搜索性能测试...")
    
    import time
    
    with tempfile.TemporaryDirectory() as temp_dir:
        kb = KnowledgeBase(persist_directory=temp_dir)
        seed_knowledge_base(kb)
        seed_high_math_kb(kb)
        seed_physics_kb(kb)
        
        queries = [
            # 初中数学
            "一元二次方程",
            "三角形全等",
            "概率计算",
            # 高中数学
            "三角函数图像",
            "导数的应用",
            "椭圆方程",
            # 高中物理
            "牛顿第二定律",
            "电磁感应",
            "动量守恒",
        ]
        
        start_time = time.time()
        for query in queries:
            kb.search(query, n_results=3)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / len(queries) * 1000
        print(f"   平均搜索时间: {avg_time:.2f}ms/次")
        print(f"   总记录数: {kb.count()}")
        
        if avg_time < 100:
            print("   ✅ 性能良好")
        elif avg_time < 500:
            print("   ⚠️  性能一般，可考虑优化")
        else:
            print("   ❌ 性能较差，需要优化")


if __name__ == "__main__":
    try:
        test_knowledge_base()
        test_error_handling()
        benchmark_search()
        print("\n🎉 所有测试完成！")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
星伴·启明 — 知识库初始化脚本

功能：
1. 初始化ChromaDB知识库
2. 灌入初中数学TOP30考点
3. 验证灌入结果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.knowledge.chroma_client import KnowledgeBase
from app.knowledge.seed_data import seed_knowledge_base, TOP30_KP
from app.knowledge.high_math_data import seed_high_math_kb, HIGH_MATH_KP
from app.knowledge.physics_data import seed_physics_kb, PHYSICS_KP


def init_knowledge_base(persist_directory: str = "./chroma_data", subjects: list = None):
    """
    初始化知识库
    
    Args:
        persist_directory: ChromaDB持久化目录
        subjects: 要灌入的学科列表，默认为所有学科
    """
    if subjects is None:
        subjects = ["初中数学", "高中数学", "高中物理"]
    
    print("🚀 开始初始化星伴·启明知识库...")
    print(f"📁 持久化目录: {persist_directory}")
    print(f"📚 灌入学科: {', '.join(subjects)}")
    
    # 1. 创建知识库实例
    kb = KnowledgeBase(persist_directory=persist_directory)
    print("✅ ChromaDB客户端初始化完成")
    
    # 2. 检查是否已有数据
    current_count = kb.count()
    if current_count > 0:
        print(f"⚠️  知识库已有 {current_count} 条记录")
        choice = input("是否清空重新灌入？(y/N): ").strip().lower()
        if choice == 'y':
            kb.delete_all()
            print("🗑️  已清空知识库")
        else:
            print("⏭️  跳过灌入，保留现有数据")
            return kb
    
    # 3. 灌入种子数据
    total_count = 0
    
    if "初中数学" in subjects:
        print(f"\n📊 灌入初中数学 {len(TOP30_KP)} 个考点...")
        count = seed_knowledge_base(kb)
        total_count += count
        print(f"✅ 初中数学: {count} 个考点")
    
    if "高中数学" in subjects:
        print(f"\n📊 灌入高中数学 {len(HIGH_MATH_KP)} 个考点...")
        count = seed_high_math_kb(kb)
        total_count += count
        print(f"✅ 高中数学: {count} 个考点")
    
    if "高中物理" in subjects:
        print(f"\n📊 灌入高中物理 {len(PHYSICS_KP)} 个考点...")
        count = seed_physics_kb(kb)
        total_count += count
        print(f"✅ 高中物理: {count} 个考点")
    
    print(f"\n✅ 成功灌入 {total_count} 个考点")
    
    # 4. 验证灌入结果
    print("\n🔍 验证灌入结果：")
    print(f"   总记录数: {kb.count()}")
    
    # 5. 测试搜索功能
    test_queries = [
        ("一元二次方程怎么解", "初中数学"),
        ("三角函数图像", "高中数学"),
        ("牛顿第二定律", "高中物理"),
        ("概率怎么计算", "初中数学"),
        ("导数的应用", "高中数学"),
        ("电磁感应", "高中物理"),
    ]
    
    print("\n🔎 搜索测试：")
    for query, subject in test_queries:
        results = kb.search(query, n_results=2)
        print(f"\n   查询: '{query}' ({subject})")
        for i, result in enumerate(results):
            print(f"   [{i+1}] {result['metadata'].get('name', '未知')} "
                  f"({result['metadata'].get('subject', '未知')}) "
                  f"(距离: {result['distance']:.3f})")
    
    return kb


def export_knowledge_stats(kb: KnowledgeBase):
    """
    导出知识库统计信息
    """
    print("\n📊 知识库统计：")
    print(f"   总考点数: {kb.count()}")
    
    # 按学科和年级分类统计
    results = kb.collection.get()
    subjects = {}
    grades = {}
    
    for metadata in results['metadatas']:
        subject = metadata.get('subject', '未知')
        grade = metadata.get('grade', '未知')
        subjects[subject] = subjects.get(subject, 0) + 1
        grades[grade] = grades.get(grade, 0) + 1
    
    print("   按学科分布:")
    for subject, count in sorted(subjects.items()):
        print(f"     - {subject}: {count}")
    
    print("   按年级分布:")
    for grade, count in sorted(grades.items()):
        print(f"     - {grade}: {count}")


if __name__ == "__main__":
    # 默认持久化目录
    persist_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "..", "chroma_data"
    )
    
    # 支持命令行参数指定目录和学科
    subjects = None
    if len(sys.argv) > 1:
        persist_dir = sys.argv[1]
    if len(sys.argv) > 2:
        subjects = sys.argv[2].split(",")
    
    try:
        kb = init_knowledge_base(persist_dir, subjects)
        export_knowledge_stats(kb)
        print("\n🎉 知识库初始化完成！")
        print(f"💾 数据已保存到: {os.path.abspath(persist_dir)}")
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

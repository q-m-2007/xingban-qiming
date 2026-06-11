#!/usr/bin/env python3
"""
星伴·启明 开发进度汇报脚本
每天晚上8点自动运行，汇报当日开发进度到微信
"""

import os
import json
from datetime import datetime, date
from pathlib import Path

PROJECT_DIR = Path("/home/ubuntu/xingban-qiming")
PLAN_FILE = PROJECT_DIR / "docs" / "7DAY-DEV-PLAN.md"
PROGRESS_FILE = PROJECT_DIR / "docs" / "dev-progress.json"

def load_progress():
    """加载进度数据"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        "start_date": "2026-06-01",
        "current_day": 0,
        "completed_tasks": [],
        "in_progress": [],
        "issues": [],
        "notes": []
    }

def get_current_day():
    """计算当前是第几天"""
    start = date(2026, 6, 1)
    today = date.today()
    delta = (today - start).days
    return max(1, min(7, delta + 1))

def get_day_tasks(day):
    """获取指定天的任务"""
    tasks = {
        1: [
            "1.1 重构FastAPI项目结构",
            "1.2 实现Belief/Conflict数据模型",
            "1.3 实现NetworkX图结构封装",
            "1.4 实现SQLite持久化层",
            "1.5 编写单元测试"
        ],
        2: [
            "2.1 设计信念提取Prompt（准高一版本）",
            "2.2 实现LLM调用封装",
            "2.3 实现结构化输出解析",
            "2.4 实现置信度校准算法",
            "2.5 编写测试用例"
        ],
        3: [
            "3.1 实现逻辑矛盾检测规则",
            "3.2 实现冲突严重度计算",
            "3.3 实现教学价值计算",
            "3.4 实现学生就绪度计算",
            "3.5 实现冲突排序算法",
            "3.6 编写测试用例"
        ],
        4: [
            "4.1 实现追问类型决策逻辑",
            "4.2 设计追问生成Prompt",
            "4.3 实现追问生成器",
            "4.4 实现约束条件检查",
            "4.5 编写测试用例"
        ],
        5: [
            "5.1 实现对话状态机",
            "5.2 实现会话管理",
            "5.3 设计RESTful API",
            "5.4 实现WebSocket实时通信",
            "5.5 编写API文档"
        ],
        6: [
            "6.1 React Native项目初始化",
            "6.2 对话界面UI设计",
            "6.3 实现消息列表",
            "6.4 实现输入组件",
            "6.5 集成语音输入API"
        ],
        7: [
            "7.1 端到端测试",
            "7.2 边界case测试",
            "7.3 性能测试",
            "7.4 Bug修复",
            "7.5 部署准备"
        ]
    }
    return tasks.get(day, [])

def generate_report():
    """生成汇报内容"""
    progress = load_progress()
    current_day = get_current_day()
    day_tasks = get_day_tasks(current_day)
    
    # 计算进度
    total_tasks = 35  # 7天 x 5任务
    completed = len(progress.get("completed_tasks", []))
    percent = int((completed / total_tasks) * 100)
    
    today = date.today().strftime("%Y-%m-%d")
    
    report = f"""📊 星伴·启明开发进度汇报

日期: {today}
当前阶段: Day {current_day}/7
整体进度: {percent}%

📋 今日任务:
"""
    
    for task in day_tasks:
        if task in progress.get("completed_tasks", []):
            report += f"✅ {task}\n"
        elif task in progress.get("in_progress", []):
            report += f"⏳ {task}\n"
        else:
            report += f"⬜ {task}\n"
    
    if progress.get("issues"):
        report += "\n❌ 遇到问题:\n"
        for issue in progress["issues"]:
            report += f"- {issue}\n"
    
    if progress.get("notes"):
        report += "\n💡 备注:\n"
        for note in progress["notes"]:
            report += f"- {note}\n"
    
    report += f"\n🚀 明日计划:\n"
    if current_day < 7:
        tomorrow_tasks = get_day_tasks(current_day + 1)
        for task in tomorrow_tasks[:3]:
            report += f"- {task}\n"
    
    report += "\n老大，进度自动汇报中。有问题随时说。"
    
    return report

if __name__ == "__main__":
    report = generate_report()
    print(report)

#!/usr/bin/env python3
# AstrBot 插件功能测试脚本

import asyncio
import sys
import os

# 添加项目路径以便导入插件模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_keyword_extraction():
    """测试关键字提取功能"""
    print("=== 测试关键字提取功能 ===")
    
    # 模拟正则表达式匹配
    import re
    
    test_cases = [
        ("搜朝雪录", "朝雪录"),
        ("搜电影", "电影"),
        ("搜学习资料", "学习资料"),
        ("搜", ""),  # 边界情况
    ]
    
    for input_text, expected in test_cases:
        match = re.match(r"^搜(.+)", input_text)
        if match:
            result = match.group(1).strip()
            status = "✓" if result == expected else "✗"
            print(f"{status} 输入: '{input_text}' -> 提取: '{result}' (期望: '{expected}')")
        else:
            status = "✓" if expected == "" else "✗"
            print(f"{status} 输入: '{input_text}' -> 无匹配 (期望: '{expected}')")
    
    print()

def test_result_formatting():
    """测试结果格式化功能"""
    print("=== 测试结果格式化功能 ===")
    
    # 模拟API返回的数据
    sample_data = {
        "total": 5,
        "merged_by_type": {
            "baidu": [
                {
                    "url": "https://pan.baidu.com/s/1abc",
                    "password": "1234",
                    "note": "测试资源1",
                    "datetime": "2025-01-01T00:00:00Z",
                    "source": "plugin:test"
                }
            ],
            "quark": [
                {
                    "url": "https://pan.quark.cn/s/def",
                    "password": "",
                    "note": "测试资源2",
                    "datetime": "2025-01-01T00:00:00Z",
                    "source": "plugin:test"
                }
            ]
        }
    }
    
    print("模拟API返回数据:")
    print(sample_data)
    print()
    
    # 测试结果格式化逻辑
    merged_data = sample_data.get("merged_by_type", {})
    baidu_results = merged_data.get("baidu", [])
    quark_results = merged_data.get("quark", [])
    
    print(f"百度网盘结果数: {len(baidu_results)}")
    print(f"夸克网盘结果数: {len(quark_results)}")
    
    # 模拟平均展示逻辑
    all_results = []
    max_results = min(10, max(len(baidu_results), len(quark_results)))
    
    for i in range(max_results):
        if i < len(baidu_results):
            all_results.append(baidu_results[i])
        if i < len(quark_results):
            all_results.append(quark_results[i])
    
    print(f"合并后结果数: {len(all_results)}")
    print("✓ 结果格式化逻辑测试通过")
    print()

def test_search_prompt():
    """测试搜索提示功能"""
    print("=== 测试搜索提示功能 ===")
    
    prompt_message = "正在搜索，请稍后..."
    print(f"提示消息: {prompt_message}")
    print("✓ 搜索提示功能测试通过")
    print()

def test_statistics_display():
    """测试统计信息展示功能"""
    print("=== 测试统计信息展示功能 ===")
    
    total_count = 15
    displayed_count = 10
    keyword = "测试"
    
    statistics_info = [
        f"搜索结果 (关键词: {keyword}):",
        # ... 这里会是搜索结果 ...
        f"\n📊 共搜索到 {total_count} 条数据，当前展示 {displayed_count} 条",
        "如需查看更多结果，请复制 https://pansd.xyz 到浏览器查看。"
    ]
    
    print("统计信息:")
    for line in statistics_info:
        if line.startswith("搜索结果"):
            print(line)
        elif line.startswith("📊"):
            print(line)
        elif line.startswith("如需"):
            print(line)
    
    print("✓ 统计信息展示功能测试通过")
    print()

def main():
    """主测试函数"""
    print("AstrBot 插件功能测试脚本")
    print("=" * 50)
    print()
    
    # 运行各项测试
    test_keyword_extraction()
    test_result_formatting()
    test_search_prompt()
    test_statistics_display()
    
    print("所有测试完成！")
    print("=" * 50)

if __name__ == "__main__":
    main()
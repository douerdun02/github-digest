#!/usr/bin/env python3
"""GitHub Daily Digest - 一键执行：采集 → 生成 → 推送"""
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

import collect
import build_html
import notify

print("=" * 50)
print(" GitHub 摘要大全 - 全流程执行")
print("=" * 50)

# Step 1: 采集
print("\n📡 [1/3] 数据采集")
data = collect.collect()

# Step 2: 生成 HTML
print("\n📄 [2/3] 生成日报")
archive_path = build_html.build()

# Step 3: 推送
print("\n📤 [3/3] 微信推送")
exit_code = notify.notify()

print(f"\n{'=' * 50}")
if exit_code == 0:
    print(" ✅ 全流程执行成功！")
else:
    print(f" ⚠️ 流程执行完成，但有 {exit_code} 个错误")
print(f" 📁 HTML 日报: {archive_path}")
print(f" {'=' * 50}")

sys.exit(exit_code)
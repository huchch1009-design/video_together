#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强的分享转存功能演示

演示如何使用新增的分享转存功能，包括：
1. 单个分享链接转存
2. 批量分享链接转存
3. 任务状态监控
4. 高级转存选项
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quark_client import QuarkClient


def demo_single_share_save():
    """演示单个分享链接转存"""
    print("=== 单个分享链接转存演示 ===")

    try:
        with QuarkClient() as client:
            if not client.is_logged_in():
                print("❌ 未登录，请先登录")
                return False

            # 示例分享链接（请替换为真实的分享链接）
            share_url = "https://pan.quark.cn/s/b9c6a04a2c6a"
            target_folder_id = "0"  # 根目录

            print(f"🔗 转存分享链接: {share_url}")
            print(f"📁 目标目录: 根目录")

            # 方法1: 使用简化的转存方法
            print("\n方法1: 使用简化转存")
            result = client.shares.save_share_url(
                share_url=share_url,
                target_folder_id=target_folder_id,
                wait_for_completion=True
            )

            if result.get('status') == 200:
                share_info = result.get('share_info', {})
                print(f"✅ 转存成功！共转存 {share_info.get('file_count', 0)} 个文件")
            else:
                print(f"❌ 转存失败: {result.get('message', '未知错误')}")

            # 方法2: 使用完整的转存方法
            print("\n方法2: 使用完整转存（带文件过滤）")

            def file_filter(file_info):
                """只转存图片文件"""
                file_name = file_info.get('file_name', '').lower()
                return any(file_name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif'])

            result = client.save_shared_files(
                share_url=share_url,
                target_folder_id=target_folder_id,
                file_filter=file_filter,
                save_all=False,  # 使用文件过滤器时必须为 False
                wait_for_completion=True
            )

            if result.get('status') == 200:
                share_info = result.get('share_info', {})
                print(f"✅ 过滤转存成功！共转存 {share_info.get('file_count', 0)} 个图片文件")
            else:
                print(f"❌ 过滤转存失败: {result.get('message', '未知错误')}")

            return True

    except Exception as e:
        print(f"❌ 单个转存演示失败: {e}")
        return False


def demo_batch_share_save():
    """演示批量分享链接转存"""
    print("\n=== 批量分享链接转存演示 ===")

    try:
        with QuarkClient() as client:
            if not client.is_logged_in():
                print("❌ 未登录，请先登录")
                return False

            # 示例分享链接列表（请替换为真实的分享链接）
            share_urls = [
                "https://pan.quark.cn/s/ee274924687a",
                "https://pan.quark.cn/s/03460bf923af",
                "https://pan.quark.cn/s/9f301b0beabb",
            ]

            target_folder_id = "0"  # 根目录

            print(f"🔗 批量转存 {len(share_urls)} 个分享链接")
            print(f"📁 目标目录: 根目录")

            # 进度回调函数
            def progress_callback(current, total, url, result):
                if result.get('success'):
                    share_info = result.get('share_info', {})
                    file_count = share_info.get('file_count', 0)
                    print(f"[{current}/{total}] ✅ 转存成功: {url} ({file_count} 个文件)")
                else:
                    error = result.get('error', '未知错误')
                    print(f"[{current}/{total}] ❌ 转存失败: {url} - {error}")

            # 执行批量转存
            results = client.batch_save_shares(
                share_urls=share_urls,
                target_folder_id=target_folder_id,
                save_all=True,
                wait_for_completion=True,
                progress_callback=progress_callback
            )

            # 统计结果
            success_count = sum(1 for r in results if r.get('success'))
            failed_count = len(results) - success_count

            print(f"\n📊 批量转存完成:")
            print(f"✅ 成功: {success_count}")
            print(f"❌ 失败: {failed_count}")

            # 显示失败的链接
            failed_results = [r for r in results if not r.get('success')]
            if failed_results:
                print("\n失败的分享链接:")
                for result in failed_results:
                    print(f"  - {result['url']}: {result.get('error', '未知错误')}")

            return True

    except Exception as e:
        print(f"❌ 批量转存演示失败: {e}")
        return False


def demo_advanced_options():
    """演示高级转存选项"""
    print("\n=== 高级转存选项演示 ===")

    try:
        with QuarkClient() as client:
            if not client.is_logged_in():
                print("❌ 未登录，请先登录")
                return False

            share_url = "https://pan.quark.cn/s/78c88b63741f"

            # 选项1: 异步转存（不等待完成）
            print("选项1: 异步转存（不等待完成）")
            result = client.save_shared_files(
                share_url=share_url,
                target_folder_id="0",
                wait_for_completion=False  # 不等待完成
            )

            if result.get('status') == 200:
                task_id = result.get('data', {}).get('task_id')
                print(f"✅ 转存任务已提交，任务ID: {task_id}")
                print("💡 可以稍后查询任务状态")
            else:
                print(f"❌ 转存任务提交失败: {result.get('message', '未知错误')}")

            # 选项2: 创建子文件夹转存
            print("\n选项2: 创建子文件夹转存")
            result = client.save_shared_files(
                share_url=share_url,
                target_folder_id="0",
                target_folder_name="转存测试文件夹",  # 创建新文件夹
                wait_for_completion=True
            )

            if result.get('status') == 200:
                print("✅ 已转存到新创建的子文件夹")
            else:
                print(f"❌ 子文件夹转存失败: {result.get('message', '未知错误')}")

            # 选项3: 使用批量转存的子文件夹功能
            print("\n选项3: 批量转存到各自的子文件夹")
            share_urls = [
                "https://pan.quark.cn/s/d037ff27bc72",
                "https://pan.quark.cn/s/0ee1237c3742"
            ]

            results = client.batch_save_shares(
                share_urls=share_urls,
                target_folder_id="0",
                create_subfolder=True,  # 为每个分享创建子文件夹
                wait_for_completion=True
            )

            success_count = sum(1 for r in results if r.get('success'))
            print(f"✅ 批量转存到子文件夹完成，成功 {success_count} 个")

            return True

    except Exception as e:
        print(f"❌ 高级选项演示失败: {e}")
        return False


def demo_error_handling():
    """演示错误处理"""
    print("\n=== 错误处理演示 ===")

    try:
        with QuarkClient() as client:
            if not client.is_logged_in():
                print("❌ 未登录，请先登录")
                return False

            # 测试无效分享链接
            print("测试1: 无效分享链接")
            try:
                result = client.save_shared_files(
                    share_url="https://pan.quark.cn/s/invalid_link",
                    target_folder_id="0"
                )
                print("❌ 应该失败但成功了")
            except Exception as e:
                print(f"✅ 正确捕获错误: {type(e).__name__}: {e}")

            # 测试无效目标文件夹
            print("\n测试2: 无效目标文件夹")
            try:
                result = client.save_shared_files(
                    share_url="https://pan.quark.cn/s/0ee1237c3742",
                    target_folder_id="invalid_folder_id"
                )
                print("❌ 应该失败但成功了")
            except Exception as e:
                print(f"✅ 正确捕获错误: {type(e).__name__}: {e}")

            return True

    except Exception as e:
        print(f"❌ 错误处理演示失败: {e}")
        return False


def main():
    """主演示函数"""
    print("夸克网盘增强分享转存功能演示")
    print("=" * 50)

    demos = [
        ("单个分享链接转存", demo_single_share_save),
        ("批量分享链接转存", demo_batch_share_save),
        ("高级转存选项", demo_advanced_options),
        ("错误处理", demo_error_handling)
    ]

    print("⚠️  注意: 此演示需要有效的登录状态和真实的分享链接")
    print("⚠️  请将示例中的分享链接替换为真实可用的链接")
    print()

    for name, demo_func in demos:
        print(f"🚀 开始演示: {name}")
        try:
            demo_func()
        except Exception as e:
            print(f"❌ 演示 '{name}' 出错: {e}")
        print()

    print("=" * 50)
    print("🎉 演示完成！")
    print("\n💡 主要功能:")
    print("1. ✅ 单个分享链接转存 - 支持全部转存和文件过滤")
    print("2. ✅ 批量分享链接转存 - 支持进度回调和错误处理")
    print("3. ✅ 任务状态监控 - 可选择等待完成或异步执行")
    print("4. ✅ 高级选项 - 创建子文件夹、文件过滤等")
    print("5. ✅ 完整的错误处理和异常捕获")


if __name__ == "__main__":
    main()

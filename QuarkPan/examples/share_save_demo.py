#!/usr/bin/env python3
"""
分享转存功能演示
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from quark_client import QuarkClient


def demo_single_share():
    """演示单个分享转存"""
    print("🔗 单个分享转存演示")
    print("=" * 40)

    # 这里使用示例链接，实际使用时请替换为真实的分享链接
    share_url = input("请输入分享链接: ").strip()

    if not share_url:
        print("❌ 未输入分享链接，使用示例链接")
        share_url = "https://pan.quark.cn/s/example123 密码: abcd"

    with QuarkClient() as client:
        try:
            # 解析分享链接
            print("🔍 解析分享链接...")
            share_id, password = client.parse_share_url(share_url)
            print(f"✅ 分享ID: {share_id}")
            print(f"✅ 密码: {password or '无'}")

            # 获取分享访问令牌
            print("🔑 获取访问令牌...")
            token = client.shares.get_share_token(share_id, password)
            print(f"✅ 令牌获取成功: {token[:20]}...")

            # 获取分享信息
            print("📋 获取分享信息...")
            share_info = client.shares.get_share_info(share_id, token)

            if share_info and 'data' in share_info:
                data = share_info['data']
                files = data.get('list', [])
                print(f"📊 分享包含 {len(files)} 个文件:")

                for i, file_info in enumerate(files):
                    name = file_info.get('file_name', '未知')
                    size = file_info.get('size', 0)
                    print(f"  {i+1}. {name} ({size} 字节)")

                # 询问是否转存
                choice = input("\n是否转存这些文件到根目录? (y/n): ").lower().strip()

                if choice == 'y':
                    print("💾 开始转存...")
                    file_ids = [f['fid'] for f in files]

                    result = client.shares.save_shared_files(
                        share_id, token, file_ids, "0"
                    )

                    if result:
                        print("✅ 转存成功！")
                        print(f"📊 转存结果: {result}")
                    else:
                        print("❌ 转存失败")
                else:
                    print("⏭️ 跳过转存")

        except Exception as e:
            print(f"❌ 操作失败: {e}")


def demo_batch_shares():
    """演示批量分享转存"""
    print("\n🔗 批量分享转存演示")
    print("=" * 40)

    # 示例分享链接列表
    share_urls = [
        "https://pan.quark.cn/s/example1 密码: 1234",
        "https://pan.quark.cn/s/example2",
        "https://pan.quark.cn/s/example3 提取码: abcd"
    ]

    print("📋 示例分享链接:")
    for i, url in enumerate(share_urls):
        print(f"  {i+1}. {url}")

    choice = input("\n是否使用示例链接进行批量转存演示? (y/n): ").lower().strip()

    if choice != 'y':
        print("⏭️ 跳过批量转存演示")
        return

    with QuarkClient() as client:
        try:
            print("🚀 开始批量转存...")

            results = client.batch_save_shares(
                share_urls,
                target_folder_id="0",
                create_subfolder=True
            )

            print(f"\n📊 批量转存完成，处理了 {len(results)} 个链接:")

            for i, result in enumerate(results):
                url = result['share_url']
                success = result['success']

                if success:
                    print(f"  ✅ {i+1}. {url} - 转存成功")
                else:
                    error = result.get('error', '未知错误')
                    print(f"  ❌ {i+1}. {url} - 转存失败: {error}")

        except Exception as e:
            print(f"❌ 批量转存失败: {e}")


def demo_share_filter():
    """演示带过滤器的分享转存"""
    print("\n🔗 带过滤器的分享转存演示")
    print("=" * 40)

    share_url = "https://pan.quark.cn/s/example123"

    # 定义文件过滤器：只转存视频文件
    def video_filter(file_info):
        """只保留视频文件"""
        file_name = file_info.get('file_name', '').lower()
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']
        return any(file_name.endswith(ext) for ext in video_extensions)

    # 定义文件过滤器：只转存大于100MB的文件
    def large_file_filter(file_info):
        """只保留大于100MB的文件"""
        file_size = file_info.get('size', 0)
        return file_size > 100 * 1024 * 1024  # 100MB

    print("📋 可用的过滤器:")
    print("  1. 只转存视频文件")
    print("  2. 只转存大于100MB的文件")
    print("  3. 不使用过滤器")

    choice = input("请选择过滤器 (1-3): ").strip()

    file_filter = None
    if choice == '1':
        file_filter = video_filter
        print("✅ 使用视频文件过滤器")
    elif choice == '2':
        file_filter = large_file_filter
        print("✅ 使用大文件过滤器")
    else:
        print("✅ 不使用过滤器")

    with QuarkClient() as client:
        try:
            print("🚀 开始带过滤器的转存...")

            result = client.save_shared_files(
                share_url,
                target_folder_id="0",
                target_folder_name="过滤转存测试",
                file_filter=file_filter
            )

            if result:
                share_info = result.get('share_info', {})
                file_count = share_info.get('file_count', 0)
                print(f"✅ 转存成功！共转存 {file_count} 个文件")
            else:
                print("❌ 转存失败")

        except Exception as e:
            print(f"❌ 转存失败: {e}")


def main():
    """主函数"""
    print("🚀 夸克网盘分享转存功能演示")
    print("=" * 50)

    print("📋 可用的演示:")
    print("  1. 单个分享转存")
    print("  2. 批量分享转存")
    print("  3. 带过滤器的转存")
    print("  4. 全部演示")

    choice = input("\n请选择演示类型 (1-4): ").strip()

    if choice == '1':
        demo_single_share()
    elif choice == '2':
        demo_batch_shares()
    elif choice == '3':
        demo_share_filter()
    elif choice == '4':
        demo_single_share()
        demo_batch_shares()
        demo_share_filter()
    else:
        print("❌ 无效选择")
        return

    print("\n🎉 演示完成！")


if __name__ == "__main__":
    main()

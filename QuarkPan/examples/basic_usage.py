#!/usr/bin/env python3
"""
夸克网盘客户端基础使用示例
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from quark_client import QuarkClient


def main():
    """主函数"""
    print("🚀 夸克网盘客户端使用示例")
    print("=" * 50)

    # 创建客户端
    with QuarkClient() as client:
        print("✅ 客户端创建成功")

        # 检查登录状态
        if not client.is_logged_in():
            print("🔑 需要登录，正在打开浏览器...")
            client.login()

        print("✅ 登录成功")

        # 1. 获取文件列表
        print("\n📁 获取根目录文件列表...")
        try:
            files = client.list_files()
            if files and 'data' in files:
                file_list = files['data'].get('list', [])
                print(f"📊 找到 {len(file_list)} 个文件/文件夹")

                # 显示前5个文件
                for i, file_info in enumerate(file_list[:5]):
                    name = file_info.get('file_name', '未知')
                    size = file_info.get('size', 0)
                    file_type = file_info.get('file_type', 0)
                    type_name = "文件夹" if file_type == 0 else "文件"
                    print(f"  {i+1}. {name} ({type_name}, {size} 字节)")
        except Exception as e:
            print(f"❌ 获取文件列表失败: {e}")

        # 2. 获取存储信息
        print("\n💾 获取存储信息...")
        try:
            storage = client.get_storage_info()
            if storage and 'data' in storage:
                data = storage['data']
                total = data.get('total', 0)
                used = data.get('used', 0)
                free = total - used

                print(f"📊 总容量: {total / (1024**3):.2f} GB")
                print(f"📊 已使用: {used / (1024**3):.2f} GB")
                print(f"📊 剩余: {free / (1024**3):.2f} GB")
        except Exception as e:
            print(f"❌ 获取存储信息失败: {e}")

        # 3. 搜索文件
        print("\n🔍 搜索文件...")
        try:
            search_results = client.search_files("test")
            if search_results and 'data' in search_results:
                results = search_results['data'].get('list', [])
                print(f"📊 搜索到 {len(results)} 个结果")

                for i, file_info in enumerate(results[:3]):
                    name = file_info.get('file_name', '未知')
                    print(f"  {i+1}. {name}")
        except Exception as e:
            print(f"❌ 搜索失败: {e}")

        # 4. 获取分享列表
        print("\n🔗 获取我的分享...")
        try:
            shares = client.get_my_shares()
            if shares and 'data' in shares:
                share_list = shares['data'].get('list', [])
                print(f"📊 找到 {len(share_list)} 个分享")

                for i, share_info in enumerate(share_list[:3]):
                    title = share_info.get('title', '未命名')
                    url = share_info.get('share_url', '')
                    print(f"  {i+1}. {title} - {url}")
        except Exception as e:
            print(f"❌ 获取分享列表失败: {e}")

        # # 5. 演示分享链接解析
        # print("\n🔗 演示分享链接解析...")
        # test_url = "https://pan.quark.cn/s/example123 密码: abcd"
        # try:
        #     share_id, password = client.parse_share_url(test_url)
        #     print(f"✅ 解析成功:")
        #     print(f"   分享ID: {share_id}")
        #     print(f"   密码: {password}")
        # except Exception as e:
        #     print(f"❌ 解析失败: {e}")

    print("\n🎉 示例完成！")


if __name__ == "__main__":
    main()

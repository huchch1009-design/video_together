#!/usr/bin/env python3
"""
文件操作功能演示 - 创建、删除、移动、重命名等
"""

import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from quark_client import QuarkClient


def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"


def format_timestamp(timestamp):
    """格式化时间戳"""
    try:
        if timestamp > 1000000000000:  # 毫秒级时间戳
            timestamp = timestamp / 1000

        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return str(timestamp)


def list_folder_contents(client, folder_id="0", folder_name="根目录"):
    """列出文件夹内容"""
    print(f"\n📂 {folder_name} 内容:")
    print("-" * 50)

    try:
        files = client.list_files(folder_id=folder_id, size=20)
        if files and 'data' in files:
            file_list = files['data'].get('list', [])
            total = files['data'].get('total', 0)

            print(f"总计: {total} 个项目")

            if file_list:
                for i, file_info in enumerate(file_list, 1):
                    name = file_info.get('file_name', '未知')
                    file_type = file_info.get('file_type', 0)
                    size = file_info.get('size', 0)
                    fid = file_info.get('fid', '')

                    type_icon = "📁" if file_type == 0 else "📄"
                    size_str = "-" if file_type == 0 else format_file_size(size)

                    print(f"  {i:2d}. {type_icon} {name} ({size_str}) [ID: {fid}]")
            else:
                print("  (空文件夹)")

            return file_list
        else:
            print("  ❌ 无法获取文件列表")
            return []
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return []


def demo_file_operations():
    """演示文件操作功能"""
    print("🚀 夸克网盘文件操作演示")
    print("=" * 50)

    try:
        with QuarkClient() as client:
            print("✅ 客户端初始化成功")

            # 检查登录状态
            if not client.is_logged_in():
                print("🔑 需要登录...")
                client.login()

            print("✅ 登录成功")

            # 1. 查看根目录当前内容
            print("\n📋 步骤1: 查看根目录当前内容")
            root_files = list_folder_contents(client, "0", "根目录")

            # 2. 创建测试文件夹
            print("\n📋 步骤2: 创建测试文件夹")
            test_folder_name = f"QuarkPan_测试文件夹_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            try:
                result = client.files.create_folder(test_folder_name, "0")
                if result:
                    print(f"✅ 成功创建文件夹: {test_folder_name}")

                    # 获取新创建文件夹的ID
                    test_folder_id = None
                    if isinstance(result, dict) and 'data' in result:
                        test_folder_id = result['data'].get('fid')

                    if test_folder_id:
                        print(f"   文件夹ID: {test_folder_id}")
                    else:
                        print("   ⚠️ 无法获取文件夹ID，将从列表中查找")
                        # 重新获取根目录列表，找到新创建的文件夹
                        updated_files = list_folder_contents(client, "0", "根目录 (更新后)")
                        for file_info in updated_files:
                            if file_info.get('file_name') == test_folder_name:
                                test_folder_id = file_info.get('fid')
                                print(f"   找到文件夹ID: {test_folder_id}")
                                break
                else:
                    print(f"❌ 创建文件夹失败")
                    return
            except Exception as e:
                print(f"❌ 创建文件夹失败: {e}")
                return

            # 3. 在测试文件夹中创建子文件夹
            if test_folder_id:
                print("\n📋 步骤3: 在测试文件夹中创建子文件夹")
                sub_folder_name = "子文件夹_示例"

                try:
                    result = client.files.create_folder(sub_folder_name, test_folder_id)
                    if result:
                        print(f"✅ 成功创建子文件夹: {sub_folder_name}")

                        # 查看测试文件夹内容
                        list_folder_contents(client, test_folder_id, test_folder_name)
                    else:
                        print(f"❌ 创建子文件夹失败")
                except Exception as e:
                    print(f"❌ 创建子文件夹失败: {e}")

            # 4. 演示重命名功能
            if test_folder_id:
                print("\n📋 步骤4: 演示重命名功能")
                new_name = f"重命名后的文件夹_{datetime.now().strftime('%H%M%S')}"

                try:
                    result = client.files.rename_file(test_folder_id, new_name)
                    if result:
                        print(f"✅ 成功重命名文件夹: {test_folder_name} -> {new_name}")
                        test_folder_name = new_name  # 更新名称

                        # 查看根目录确认重命名
                        list_folder_contents(client, "0", "根目录 (重命名后)")
                    else:
                        print(f"❌ 重命名失败")
                except Exception as e:
                    print(f"❌ 重命名失败: {e}")

            # 5. 演示移动功能（如果有多个文件夹）
            if len(root_files) > 1 and test_folder_id:
                print("\n📋 步骤5: 演示移动功能")

                # 找一个可以移动的文件夹（不是我们刚创建的）
                movable_folder = None
                for file_info in root_files:
                    if (file_info.get('file_type') == 0 and
                        file_info.get('fid') != test_folder_id and
                            file_info.get('file_name') != test_folder_name):
                        movable_folder = file_info
                        break

                if movable_folder:
                    movable_id = movable_folder.get('fid')
                    movable_name = movable_folder.get('file_name')

                    print(f"尝试移动文件夹: {movable_name} 到 {test_folder_name}")

                    try:
                        result = client.files.move_files([movable_id], test_folder_id)
                        if result:
                            print(f"✅ 成功移动文件夹")

                            # 查看移动后的结果
                            list_folder_contents(client, "0", "根目录 (移动后)")
                            list_folder_contents(client, test_folder_id, f"{test_folder_name} (移动后)")

                            # 移回原位置
                            print(f"将文件夹移回根目录...")
                            client.files.move_files([movable_id], "0")
                            print("✅ 已移回根目录")
                        else:
                            print(f"❌ 移动失败")
                    except Exception as e:
                        print(f"❌ 移动失败: {e}")
                else:
                    print("⚠️ 没有找到可移动的文件夹")

            # 6. 清理：删除测试文件夹
            if test_folder_id:
                print("\n📋 步骤6: 清理测试文件夹")

                try:
                    result = client.files.delete_files([test_folder_id])
                    if result:
                        print(f"✅ 成功删除测试文件夹: {test_folder_name}")

                        # 查看清理后的根目录
                        list_folder_contents(client, "0", "根目录 (清理后)")
                    else:
                        print(f"❌ 删除失败")
                except Exception as e:
                    print(f"❌ 删除失败: {e}")
                    print(f"⚠️ 请手动删除测试文件夹: {test_folder_name}")

            # 7. 演示搜索功能
            print("\n📋 步骤7: 演示搜索功能")
            search_terms = ["pdf", "课", "金瓶梅"]

            for term in search_terms:
                try:
                    results = client.search_files(term, size=3)
                    if results and 'data' in results:
                        file_list = results['data'].get('list', [])
                        print(f"\n🔍 搜索 '{term}' 结果 ({len(file_list)} 个):")

                        for i, file_info in enumerate(file_list, 1):
                            name = file_info.get('file_name', '未知')
                            file_type = file_info.get('file_type', 0)
                            type_icon = "📁" if file_type == 0 else "📄"
                            print(f"  {i}. {type_icon} {name}")
                    else:
                        print(f"🔍 搜索 '{term}': 无结果")
                except Exception as e:
                    print(f"❌ 搜索 '{term}' 失败: {e}")

    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n🎉 文件操作演示完成！")


if __name__ == "__main__":
    demo_file_operations()

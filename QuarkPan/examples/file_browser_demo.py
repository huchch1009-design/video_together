#!/usr/bin/env python3
"""
文件浏览器功能演示
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
        # 夸克网盘的时间戳可能是毫秒级
        if timestamp > 1000000000000:  # 毫秒级时间戳
            timestamp = timestamp / 1000

        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return str(timestamp)


def display_file_list(files_data, title="文件列表", show_details=True):
    """显示文件列表"""
    print(f"\n📁 {title}")
    print("=" * 80)

    if not files_data or 'data' not in files_data:
        print("❌ 无效的文件数据")
        return

    file_list = files_data['data'].get('list', [])
    total_count = files_data['data'].get('total', 0)

    print(f"📊 总计: {total_count} 个项目，当前显示: {len(file_list)} 个")

    if not file_list:
        print("📂 文件夹为空")
        return

    print()

    if show_details:
        # 详细视图
        print(f"{'序号':<4} {'类型':<8} {'名称':<35} {'大小':<12} {'修改时间':<16}")
        print("-" * 85)

        for i, file_info in enumerate(file_list, 1):
            name = file_info.get('file_name', '未知')
            size = file_info.get('size', 0)
            file_type = file_info.get('file_type', 0)
            updated_at = file_info.get('updated_at', '')

            # 截断过长的文件名
            if len(name) > 33:
                display_name = name[:30] + "..."
            else:
                display_name = name

            type_name = "📁 文件夹" if file_type == 0 else "📄 文件"
            size_str = "-" if file_type == 0 else format_file_size(size)
            time_str = format_timestamp(updated_at) if updated_at else "-"

            print(f"{i:<4} {type_name:<8} {display_name:<35} {size_str:<12} {time_str:<16}")
    else:
        # 简洁视图
        for i, file_info in enumerate(file_list, 1):
            name = file_info.get('file_name', '未知')
            file_type = file_info.get('file_type', 0)
            type_icon = "📁" if file_type == 0 else "📄"
            print(f"  {i:2d}. {type_icon} {name}")


def demo_file_browsing():
    """演示文件浏览功能"""
    print("🚀 夸克网盘文件浏览器演示")
    print("=" * 50)

    try:
        with QuarkClient() as client:
            print("✅ 客户端初始化成功")

            # 检查登录状态
            if not client.is_logged_in():
                print("🔑 需要登录...")
                client.login()

            print("✅ 登录成功")

            # 1. 获取存储空间信息
            print("\n💾 存储空间信息")
            print("-" * 30)
            try:
                storage = client.get_storage_info()
                if storage and 'data' in storage:
                    data = storage['data']
                    total = data.get('total', 0)
                    used = data.get('used', 0)
                    free = total - used

                    print(f"总容量: {format_file_size(total)}")
                    print(f"已使用: {format_file_size(used)}")
                    print(f"剩余: {format_file_size(free)}")
                    print(f"使用率: {(used/total*100):.1f}%" if total > 0 else "使用率: 0%")
            except Exception as e:
                print(f"❌ 获取存储信息失败: {e}")

            # 2. 浏览根目录
            print("\n📂 根目录文件列表")
            try:
                files = client.list_files(size=10)
                display_file_list(files, "根目录 (前10个)")
            except Exception as e:
                print(f"❌ 获取文件列表失败: {e}")

            # 3. 演示排序功能
            print("\n🔄 排序演示")
            sort_options = [
                ("file_name", "asc", "按名称升序"),
                ("size", "desc", "按大小降序"),
                ("updated_at", "desc", "按修改时间降序")
            ]

            for sort_field, sort_order, description in sort_options:
                try:
                    files = client.list_files(
                        sort_field=sort_field,
                        sort_order=sort_order,
                        size=5
                    )
                    display_file_list(files, f"{description} (前5个)", show_details=False)
                except Exception as e:
                    print(f"❌ {description} 失败: {e}")

            # 4. 演示过滤功能
            print("\n🔍 过滤演示")
            try:
                # 只显示文件夹
                folders = client.list_files_with_details(
                    size=5,
                    include_files=False,
                    include_folders=True
                )
                display_file_list(folders, "仅文件夹 (前5个)", show_details=False)

                # 只显示文件
                files_only = client.list_files_with_details(
                    size=5,
                    include_files=True,
                    include_folders=False
                )
                display_file_list(files_only, "仅文件 (前5个)", show_details=False)
            except Exception as e:
                print(f"❌ 过滤演示失败: {e}")

            # 5. 演示搜索功能
            print("\n🔍 搜索演示")
            search_terms = ["pdf", "doc", "mp4", "图片"]

            for term in search_terms:
                try:
                    results = client.search_files(term, size=3)
                    display_file_list(results, f"搜索 '{term}' (前3个)", show_details=False)
                except Exception as e:
                    print(f"❌ 搜索 '{term}' 失败: {e}")

            # 6. 演示高级搜索
            print("\n🔍 高级搜索演示")
            try:
                # 搜索PDF文件
                pdf_results = client.search_files_advanced(
                    keyword="",
                    file_extensions=["pdf"],
                    size=5
                )
                display_file_list(pdf_results, "PDF文件 (前5个)", show_details=False)

                # 搜索大文件 (>10MB)
                large_files = client.search_files_advanced(
                    keyword="",
                    min_size=10 * 1024 * 1024,  # 10MB
                    size=5
                )
                display_file_list(large_files, "大文件 >10MB (前5个)", show_details=False)
            except Exception as e:
                print(f"❌ 高级搜索失败: {e}")

            # 7. 演示文件详情获取
            print("\n📄 文件详情演示")
            try:
                files = client.list_files(size=1)
                if files and 'data' in files:
                    file_list = files['data'].get('list', [])
                    if file_list:
                        first_file = file_list[0]
                        file_id = first_file.get('fid')
                        if file_id:
                            file_info = client.get_file_info(file_id)
                            print(f"📄 文件详情:")
                            print(f"   ID: {file_info.get('fid', 'N/A')}")
                            print(f"   名称: {file_info.get('file_name', 'N/A')}")
                            print(f"   大小: {format_file_size(file_info.get('size', 0))}")
                            print(f"   类型: {'文件夹' if file_info.get('file_type', 0) == 0 else '文件'}")
                            print(f"   创建时间: {format_timestamp(file_info.get('created_at', 0))}")
                            print(f"   修改时间: {format_timestamp(file_info.get('updated_at', 0))}")
            except Exception as e:
                print(f"❌ 获取文件详情失败: {e}")

            # 8. 演示下载链接获取
            print("\n📥 下载链接演示")
            try:
                files = client.list_files(size=20)
                if files and 'data' in files:
                    file_list = files['data'].get('list', [])
                    for file_info in file_list:
                        if file_info.get('file_type', 0) != 0:  # 不是文件夹
                            file_id = file_info.get('fid')
                            file_name = file_info.get('file_name', '未知')
                            if file_id:
                                try:
                                    download_url = client.get_download_url(file_id)
                                    print(f"📥 {file_name}")
                                    print(f"   下载链接: {download_url[:80]}...")
                                    break
                                except Exception as e:
                                    print(f"❌ 获取 {file_name} 下载链接失败: {e}")
                    else:
                        print("❌ 没有找到可下载的文件")
            except Exception as e:
                print(f"❌ 下载链接演示失败: {e}")

    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n🎉 文件浏览器演示完成！")


if __name__ == "__main__":
    demo_file_browsing()

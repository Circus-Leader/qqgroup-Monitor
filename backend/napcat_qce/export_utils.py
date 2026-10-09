"""
导出文件路径工具
==============

提供导出文件路径相关的工具函数。

Usage:
    from napcat_qce import connect
    from napcat_qce.eexport_utils import complete_file_path
    
    client = connect()
    tasks = client.tasks.get_all()
    
    for task in tasks:
        file_path = complete_file_path(task)
        print(f"任务: {task.session_name}")
        print(f"文件路径: {file_path}")
"""

import os


EXPORT_DIRS = [
    r"C:\Users\ASUS\.qq-chat-exporter\exports",
    r"D:\QQ聊天记录",
    r"E:\聊天记录备份",
]


def get_default_export_dir() -> str:
    """获取默认导出目录
    
    Returns:
        str: 默认导出目录路径
    """
    return r"C:\Users\ASUS\.qq-chat-exporter\exports"


def complete_file_path(task) -> str:
    """补全任务的文件路径
    
    如果任务的 file_path 为空，则根据 file_name 和多个导出目录构建完整路径。
    如果文件不在默认位置，会在所有导出目录及其子目录中递归搜索。
    
    Args:
        task: 导出任务对象，应包含 file_path 和 file_name 属性
        
    Returns:
        str: 完整的文件路径，如果找不到文件会标记"(文件未找到)"
    """
    if task.file_path:
        return task.file_path
    
    if not task.file_name:
        return "无"
    
    for export_dir in EXPORT_DIRS:
        full_path = os.path.join(export_dir, task.file_name)
        
        if os.path.exists(full_path):
            return full_path
        
        try:
            for root, dirs, files in os.walk(export_dir):
                if task.file_name in files:
                    return os.path.join(root, task.file_name)
        except Exception:
            continue
    
    return f"{os.path.join(EXPORT_DIRS[0], task.file_name)} (文件未找到)"


def get_file_info(task) -> dict:
    """获取任务的文件信息
    
    Args:
        task: 导出任务对象
        
    Returns:
        dict: 包含文件名、路径、是否存在等信息的字典
    """
    file_path = complete_file_path(task)
    return {
        "file_name": task.file_name or "无",
        "file_path": file_path,
        "exists": "(文件未找到)" not in file_path,
        "download_url": task.download_url or "无"
    }


def check_file_exists(task) -> bool:
    """检查任务的导出文件是否存在
    
    Args:
        task: 导出任务对象
        
    Returns:
        bool: 文件是否存在
    """
    file_path = complete_file_path(task)
    return "(文件未找到)" not in file_path

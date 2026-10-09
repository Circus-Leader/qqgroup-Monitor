import sys
from datetime import datetime, timedelta
from config import NAPCAT_PATH, QQ_PATH, EXPORT_FILE

# 导入napcat_qce
try:
    from napcat_qce import NapCatQCELauncher, connect, MessageFilter, ExportOptions, TaskStatus, set_export_dir
    NAPCAT_AVAILABLE = True
except ImportError as e:
    print(f"警告: napcat_qce库导入失败: {str(e)}")
    NAPCAT_AVAILABLE = False

from utils import load_json, get_request
from analyzer import ChatAnalyzer
from report_generator import ReportGenerator


def export_chat_with_napcat():
    """使用Napcat API导出聊天记录（仿官方示例写法）"""
    if not NAPCAT_AVAILABLE:
        print("错误: napcat_qce库不可用，无法使用此功能")
        return None
    
    try:
        # 设置导出目录为config.py中定义的路径
        set_export_dir(EXPORT_FILE)
        
        # 使用config.py中定义的路径启动Napcat服务（官方示例模式）
        with NapCatQCELauncher(napcat_path=NAPCAT_PATH, qq_path=QQ_PATH) as launcher:
            client = launcher.get_client()
            info = client.system.get_info()
            print(f"已登录: {info.self_nick}")
            
            # 获取群聊列表
            print("正在获取群聊列表...")
            groups = client.groups.get_all()
            
            if not groups:
                print("未找到任何群聊")
                return None
            
            # 显示群聊列表供用户选择
            print("\n可用群聊列表:")
            for i, group in enumerate(groups, 1):
                print(f"{i}. {group.group_name} (ID: {group.group_code})")
            
            # 用户选择群聊
            while True:
                try:
                    choice = int(input("\n请选择群聊(输入数字): "))
                    if 1 <= choice <= len(groups):
                        selected_group = groups[choice-1]
                        break
                    else:
                        print(f"请输入1到{len(groups)}之间的数字")
                except ValueError:
                    print("请输入有效的数字")
            
            print(f"已选择群聊: {selected_group.group_name}")
            
            # 获取时间范围
            print("\n请选择导出时间范围:")
            print("1. 最近1天")
            print("2. 最近3天")
            print("3. 最近7天")
            print("4. 最近30天")
            print("5. 自定义时间范围")
            
            time_choice = input("请选择(1-5): ")
            
            now = datetime.now()
            
            if time_choice == "1":
                start_time = now - timedelta(days=1)
            elif time_choice == "2":
                start_time = now - timedelta(days=3)
            elif time_choice == "3":
                start_time = now - timedelta(days=7)
            elif time_choice == "4":
                start_time = now - timedelta(days=30)
            elif time_choice == "5":
                try:
                    start_date_str = input("请输入开始日期(YYYY-MM-DD): ")
                    start_time = datetime.strptime(start_date_str, "%Y-%m-%d")
                    
                    end_date_str = input("请输入结束日期(YYYY-MM-DD，留空为今天): ")
                    if end_date_str:
                        end_time = datetime.strptime(end_date_str, "%Y-%m-%d")
                    else:
                        end_time = now
                except ValueError:
                    print("日期格式错误，将使用最近7天")
                    start_time = now - timedelta(days=7)
                    end_time = now
            else:
                print("无效选择，将使用最近7天")
                start_time = now - timedelta(days=7)
                end_time = now
            
            # 确保结束时间是今天
            if time_choice != "5" or not end_date_str:
                end_time = now
            
            print(f"导出时间范围: {start_time.strftime('%Y-%m-%d')} 至 {end_time.strftime('%Y-%m-%d')}")
            
            # 配置导出选项 - 不下载资源（官方示例模式）
            print("正在配置导出选项...")
            export_options = ExportOptions(
                include_resource_links=False,  # 不包含资源链接
                filter_pure_image_messages=True  # 过滤纯图片消息
            )
            
            # 创建消息过滤器（用于时间范围）
            message_filter = MessageFilter(
                start_time=start_time,
                end_time=end_time
            )
            
            # 导出聊天记录
            print("正在导出聊天记录，请稍候...")
            # 确保导出目录设置为config.py中定义的路径
            set_export_dir(EXPORT_FILE)
            export_task = client.messages.export(
                chat_type=2,  # 群聊
                peer_uid=selected_group.group_code,
                filter=message_filter,
                format="JSON",
                options=export_options  # 应用导出选项
            )
            
            # 等待导出完成
            print("等待导出任务完成...")
            task = client.tasks.wait_for_completion(export_task.id, timeout=300)
            
            if task.status == TaskStatus.COMPLETED:
                print("聊天记录导出成功")
                print(f"文件路径: {task.file_path}")
                print(f"文件名: {task.file_name}")
                
                if task.file_path:
                    return task.file_path
                elif task.file_name:
                    # 构建默认导出路径
                    import os
                    user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
                    default_path = os.path.join(user_profile, ".qq-chat-exporter", "exports", task.file_name)
                    print(f"使用默认路径: {default_path}")
                    return default_path
                else:
                    print("错误: 无法获取导出文件路径")
                    return None
            else:
                print(f"导出失败: {task.error}")
                return None
            
    except Exception as e:
        print(f"导出聊天记录时发生错误: {str(e)}")
        return None


def run_cli_mode():
    """运行CLI模式"""
    print("QQ群聊消息分析器 - CLI模式")
    print("=" * 50)
    
    # 使用Napcat API导出聊天记录
    print("\n步骤1: 导出聊天记录")
    input_file = export_chat_with_napcat()
    
    if not input_file:
        print("聊天记录导出失败，程序退出")
        sys.exit(1)
    
    print(f"\n步骤2: 分析聊天记录")
    print(f"加载文件: {input_file}")
    
    # 加载数据
    try:
        data = load_json(input_file)
    except Exception as e:
        print(f"文件加载失败: {e}")
        sys.exit(1)

    # 创建分析器
    analyzer = ChatAnalyzer(data)
    
    # 执行分析
    print("正在分析聊天记录...")
    analyzer.analyze()
    print("分析完成")

    # 创建简报生成器
    reporter = ReportGenerator(analyzer)

    # 持续获取用户请求直至退出
    print("\n步骤3: 生成简报")
    while True:
        request = get_request(analyzer.start_time, analyzer.end_time)
        if request == -1:
            exit("用户结束查询")
        # 生成简报
        reporter.brief_report(request)
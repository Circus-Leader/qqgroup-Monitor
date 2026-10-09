"""
QQ聊天记录导出&分析工具 - API服务器
使用napcat_qce的connect()方式连接
"""

import os
import io
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from config import *
from napcat_qce import connect, ChatType, MessageFilter, ExportOptions, ExportFormat
from analyzer import ChatAnalyzer
from report_generator import ReportGenerator
from utils import load_json, transform_datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("./cache/log/api_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="QQ聊天记录导出&分析工具",
    description="使用napcat_qce实现的聊天记录导出和分析API",
    version="2.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
client = None
is_connected = False
export_tasks = {}
log_list = []
analyze_log_list = []

# 请求模型
class ExportRequest(BaseModel):
    chat_type: int  # 1=私聊, 2=群聊
    peer_uid: str
    format: str = "HTML"  # TXT, JSON, HTML, EXCEL
    filter: Optional[Dict[str, Any]] = None  # MessageFilter参数
    options: Optional[Dict[str, Any]] = None  # ExportOptions参数

class BatchExportRequest(BaseModel):
    targets: List[Dict[str, str]]  # [{"chat_type": 1, "peer_uid": "123456"}, ...]
    format: str = "HTML"  # TXT, JSON, HTML, EXCEL
    filter: Optional[Dict[str, Any]] = None  # MessageFilter参数
    options: Optional[Dict[str, Any]] = None  # ExportOptions参数

class AnalysisRequest(BaseModel):
    chat_type: int  # 1=私聊, 2=群聊
    peer_uid: str
    filter: Optional[Dict[str, Any]] = None  # MessageFilter参数

class ReportRequest(BaseModel):
    chat_type: int  # 1=私聊, 2=群聊
    peer_uid: str
    filter: Optional[Dict[str, Any]] = None  # MessageFilter参数
    report_type: Optional[str] = "basic"

class AnalyzeTaskRequest(BaseModel):
    task_id: str  # 导出任务ID

class AnalyzeTaskResponse(BaseModel):
    status: str
    message: str
    brief_report: Optional[Dict[str, Any]] = None

# 响应模型
class AnalysisResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class ReportResponse(BaseModel):
    status: str
    message: str
    report_path: Optional[str] = None

class TaskCountResponse(BaseModel):
    total_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int

# 连接napcat
def connect_to_napcat():
    global client, is_connected
    try:
        client = connect()
        if client.is_connected():
            is_connected = True
            logger.info("成功连接到NapCat-QCE服务器")
            return True
        else:
            is_connected = False
            logger.error("无法连接到NapCat-QCE服务器")
            return False
    except Exception as e:
        is_connected = False
        logger.error(f"连接NapCat-QCE服务器失败: {str(e)}")
        return False

# 断开连接
def disconnect_from_napcat():
    global client, is_connected
    try:
        if client:
            client.close()
        client = None
        is_connected = False
        logger.info("已断开与NapCat-QCE服务器的连接")
    except Exception as e:
        logger.error(f"断开连接失败: {str(e)}")

# API端点    
@app.get("/")
async def root():
    return {"message": "QQ聊天记录导出&分析工具 API v2.0"}

@app.get("/api/qrcode")
async def get_qrcode():
    """获取登录二维码"""
    try:
        if not os.path.exists(QRCODE_FILE):
            raise HTTPException(status_code=404, detail="二维码文件不存在，请先启动napcat服务")
        
        return FileResponse(
            path=QRCODE_FILE,
            filename="qrcode.png",
            media_type="image/png"
        )
    except Exception as e:
        logger.error(f"获取二维码失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取二维码失败: {str(e)}")

@app.post("/api/napcat/start")
async def start_napcat():
    """启动napcat连接"""
    global is_connected
    
    if is_connected:
        return {"status": "success", "message": "Napcat服务已连接"}
    
    if connect_to_napcat():
        return {"status": "success", "message": "Napcat服务连接成功"}
    else:
        return {"status": "error", "message": "Napcat服务连接失败"}

@app.post("/api/napcat/stop")
async def stop_napcat():
    """停止napcat连接"""
    global is_connected
    
    if not is_connected:
        return {"status": "success", "message": "Napcat服务未连接"}
    
    disconnect_from_napcat()
    return {"status": "success", "message": "Napcat服务已断开"}

@app.get("/api/napcat/status")
async def get_napcat_status():
    """获取napcat连接状态"""
    global is_connected
    if not is_connected:
        return {"status": "disconnected", "message": "Napcat服务未连接"}
    
    try:
        if client and client.is_connected():
            info = client.system.get_info()
            return {
                "status": "connected",
                "message": "Napcat服务已连接",
                "user_info": {
                    "uin": info.self_uin,
                    "nick": info.self_nick
                }
            }
        else:
            is_connected = False
            return {"status": "disconnected", "message": "Napcat服务连接已断开"}
    except Exception as e:
        is_connected = False
        logger.error(f"获取napcat状态失败: {str(e)}")
        return {"status": "error", "message": f"获取状态失败: {str(e)}"}

@app.get("/api/qq/groups")
async def get_groups():
    """获取群组列表"""
    global is_connected, client
    if not is_connected or not client:
        raise HTTPException(status_code=400, detail="Napcat服务未连接")
    
    try:
        groups = client.groups.get_all()
        result = []
        for group in groups:
            # 构建头像路径
            avatar_path = f"export/exported_avatars/groups/group_{group.group_code}.jpg"
            avatar_url = f"/api/avatar/groups/{group.group_code}"
            # 检查头像文件是否存在
            full_avatar_path = os.path.join(os.path.dirname(__file__), '..', avatar_path)
            has_avatar = os.path.exists(full_avatar_path)
            
            result.append({
                "group_code": group.group_code,
                "group_name": group.group_name,
                "member_count": group.member_count,
                "avatar_url": avatar_url if has_avatar else None,
                "default_avatar": "https://via.placeholder.com/40"
            })
        return {"status": "success", "groups": result}
    except Exception as e:
        logger.error(f"获取群组列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取群组列表失败: {str(e)}")

@app.get("/api/qq/friends")
async def get_friends():
    """获取好友列表"""
    global is_connected, client
    if not is_connected or not client:
        raise HTTPException(status_code=400, detail="Napcat服务未连接")
    
    try:
        friends = client.friends.get_all()
        result = []
        for friend in friends:
            # 构建头像路径
            avatar_path = f"export/exported_avatars/friends/friend_{friend.uin}.jpg"
            avatar_url = f"/api/avatar/friends/{friend.uin}"
            # 检查头像文件是否存在
            full_avatar_path = os.path.join(os.path.dirname(__file__), '..', avatar_path)
            has_avatar = os.path.exists(full_avatar_path)
            
            result.append({
                "uin": friend.uin,
                "nick": friend.nick,
                "remark": friend.remark,
                "avatar_url": avatar_url if has_avatar else None,
                "default_avatar": "https://via.placeholder.com/40"
            })
        return {"status": "success", "friends": result}
    except Exception as e:
        logger.error(f"获取好友列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取好友列表失败: {str(e)}")

@app.get("/api/avatar/groups/{group_code}")
async def get_group_avatar(group_code: str):
    """获取群聊头像"""
    avatar_path = os.path.join(os.path.dirname(__file__), '..', f'export/exported_avatars/groups/group_{group_code}.jpg')
    if os.path.exists(avatar_path):
        return FileResponse(path=avatar_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="头像不存在")

@app.get("/api/avatar/friends/{uin}")
async def get_friend_avatar(uin: str):
    """获取好友头像"""
    avatar_path = os.path.join(os.path.dirname(__file__), '..', f'export/exported_avatars/friends/friend_{uin}.jpg')
    if os.path.exists(avatar_path):
        return FileResponse(path=avatar_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="头像不存在")

@app.post("/api/qq/export")
async def export_chat(request: ExportRequest):
    """导出聊天记录"""
    global is_connected, client
    if not is_connected or not client:
        raise HTTPException(status_code=400, detail="Napcat服务未连接")
    
    try:
        chat_type = ChatType.FRIEND if request.chat_type == 1 else ChatType.GROUP
        
        format_map = {
            "TXT": ExportFormat.TXT,
            "JSON": ExportFormat.JSON,
            "HTML": ExportFormat.HTML,
            "EXCEL": ExportFormat.EXCEL
        }
        export_format = format_map.get(request.format.upper(), ExportFormat.HTML)
        
        message_filter = None
        if request.filter:
            if "last_days" in request.filter:
                message_filter = MessageFilter.last_days(request.filter["last_days"])
            elif "last_hours" in request.filter:
                message_filter = MessageFilter.last_hours(request.filter["last_hours"])
            elif "start_time" in request.filter and "end_time" in request.filter:
                start_time = datetime.fromisoformat(request.filter["start_time"])
                end_time = datetime.fromisoformat(request.filter["end_time"])
                message_filter = MessageFilter(start_time=start_time, end_time=end_time)
        
        export_options = ExportOptions(
            include_system_messages=True,
            include_resource_links=False,
            pretty_format=True
        )
        
        # if request.options:
        #     if "include_resource_links" in request.options:
        #         export_options.include_resource_links = request.options["include_resource_links"]
        #     if "export_as_zip" in request.options:
        #         export_options.export_as_zip = request.options["export_as_zip"]
        #     if "output_dir" in request.options:
        #         export_options.output_dir = request.options["output_dir"]
        
        task = client.messages.export(
            chat_type=chat_type,
            peer_uid=request.peer_uid,
            format=export_format,
            filter=message_filter,
            options=export_options
        )
        
        export_tasks[task.id] = {
            "task": task,
            "status": task.status.value,
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "status": "success",
            "message": "导出任务已创建",
            "task_id": task.id,
            "session_name": task.session_name,
            "message_count": task.message_count,
            "file_name": task.file_name,
            "file_path": task.file_path
        }
    except Exception as e:
        logger.error(f"导出聊天记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出聊天记录失败: {str(e)}")

@app.post("/api/qq/batch_export")
async def batch_export(request: BatchExportRequest):
    """批量导出聊天记录"""
    global is_connected, client
    if not is_connected or not client:
        raise HTTPException(status_code=400, detail="Napcat服务未连接")
    
    try:
        format_map = {
            "TXT": ExportFormat.TXT,
            "JSON": ExportFormat.JSON,
            "HTML": ExportFormat.HTML,
            "EXCEL": ExportFormat.EXCEL
        }
        export_format = format_map.get(request.format.upper(), ExportFormat.HTML)
        
        message_filter = None
        if request.filter:
            if "last_days" in request.filter:
                message_filter = MessageFilter.last_days(request.filter["last_days"])
            elif "last_hours" in request.filter:
                message_filter = MessageFilter.last_hours(request.filter["last_hours"])
            elif "start_time" in request.filter and "end_time" in request.filter:
                start_time = datetime.fromisoformat(request.filter["start_time"])
                end_time = datetime.fromisoformat(request.filter["end_time"])
                message_filter = MessageFilter(start_time=start_time, end_time=end_time)
        
        export_options = ExportOptions(
            include_system_messages=True,
            include_resource_links=False,
            pretty_format=True
        )
        
        if request.options:
            if "include_resource_links" in request.options:
                export_options.include_resource_links = request.options["include_resource_links"]
            if "export_as_zip" in request.options:
                export_options.export_as_zip = request.options["export_as_zip"]
            if "output_dir" in request.options:
                export_options.output_dir = request.options["output_dir"]
        
        results = client.batch_export(
            targets=[{
                "type": "group" if target["chat_type"] == 2 else "friend",
                "id": target["peer_uid"],
                "name": target.get("name")
            } for target in request.targets],
            format=export_format,
            filter=message_filter,
            options=export_options,
            on_progress=lambda id, task: update_task_status(id, task),
            on_error=lambda id, e: log_export_error(id, e)
        )
        
        if "tasks" in results:
            for task in results["tasks"]:
                export_tasks[task.id] = {
                    "task": task,
                    "status": task.status.value,
                    "created_at": datetime.now().isoformat()
                }
        
        return {
            "status": "success",
            "message": "批量导出完成",
            "success": results["success"],
            "failed": results["failed"],
            "total_messages": results["total_messages"]
        }
    except Exception as e:
        logger.error(f"批量导出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量导出失败: {str(e)}")

@app.get("/api/qq/export/{task_id}")
async def get_export_status(task_id: str):
    """获取导出任务状态"""
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = export_tasks[task_id]
    task = task_info["task"]
    
    return {
        "status": "success",
        "task_id": task_id,
        "session_name": task.session_name,
        "task_status": task.status.value,
        "message_count": task.message_count,
        "file_name": task.file_name,
        "created_at": task_info["created_at"]
    }

@app.get("/api/qq/export/{task_id}/download")
async def download_export(task_id: str):
    """下载导出文件"""
    if task_id not in export_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = export_tasks[task_id]["task"]
    
    if task.status.value != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    if not os.path.exists(task.file_path):
        raise HTTPException(status_code=404, detail="导出文件不存在")
    
    return FileResponse(
        path=task.file_path,
        filename=task.file_name,
        media_type='application/octet-stream'
    )

@app.get("/api/qq/export/logs")
async def get_export_logs():
    """获取导出日志"""
    return {"status": "success", "logs": log_list}

@app.get("/api/qq/export/file")
async def get_export_file(path: str = Query(..., description="导出文件路径")):
    """读取导出文件内容（用于预览）"""
    try:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        data = json.loads(content)
        return {"status": "success", "messages": data.get("messages", [])}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="文件格式错误")
    except Exception as e:
        logger.error(f"读取导出文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"读取导出文件失败: {str(e)}")

@app.get("/api/qq/tasks")
async def get_tasks():
    """获取任务列表和统计"""
    global is_connected, client
    if not is_connected or not client:
        # 如果未连接，返回默认值
        return {
            "status": "success",
            "total_tasks": 0,
            "running_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "tasks": []
        }
    
    try:
        tasks = client.tasks.get_all()
        total_tasks = len(tasks)
        running_tasks = sum(1 for task in tasks if task.status.value == "running")
        completed_tasks = sum(1 for task in tasks if task.status.value == "completed")
        failed_tasks = sum(1 for task in tasks if task.status.value == "failed")
        
        # 转换任务数据为前端可用格式
        tasks_list = []
        for task in tasks:
            # 处理创建日期
            create_date = ""
            if hasattr(task, 'created_at') and task.created_at:
                try:
                    # created_at是ISO格式字符串，如"2023-12-30T10:00:00Z"
                    create_date = task.created_at.split('T')[0].replace('-', '/')
                except:
                    create_date = ""
            
            # 处理日期范围
            date_range = ""
            if hasattr(task, 'start_time') and hasattr(task, 'end_time') and task.start_time and task.end_time:
                try:
                    # start_time和end_time是时间戳
                    start_date = datetime.fromtimestamp(task.start_time).strftime("%Y/%m/%d")
                    end_date = datetime.fromtimestamp(task.end_time).strftime("%Y/%m/%d")
                    date_range = f"{start_date}~{end_date}"
                except:
                    date_range = ""
            
            # 确保task.peer和task.status不为None
            peer_uid = task.peer.peer_uid if task.peer else ""
            status_value = task.status.value if task.status else ""
            chat_type_value = task.peer.chat_type if task.peer else 0
            
            # 转换聊天类型为文本
            chat_type_text = "私聊" if chat_type_value == 1 else "群聊"
            
            # 构建头像路径
            if chat_type_value == 2:  # 群聊
                avatar_path = f"export/exported_avatars/groups/group_{peer_uid}.jpg"
                avatar_url = f"/api/avatar/groups/{peer_uid}"
            else:  # 私聊
                avatar_path = f"export/exported_avatars/friends/friend_{peer_uid}.jpg"
                avatar_url = f"/api/avatar/friends/{peer_uid}"
            
            # 检查头像文件是否存在
            full_avatar_path = os.path.join(os.path.dirname(__file__), '..', avatar_path)
            has_avatar = os.path.exists(full_avatar_path)
            
            tasks_list.append({
                "id": task.id,
                "name": task.session_name,
                "status": status_value,
                "id_number": peer_uid,
                "create_date": create_date,
                "message_count": task.message_count,
                "date_range": date_range,
                "file_path": task.file_path,
                "chat_type": chat_type_text,
                "format": task.format,
                "avatar_url": avatar_url if has_avatar else None,
                "default_avatar": "https://via.placeholder.com/40"
            })
            
        
        return {
            "status": "success",
            "total_tasks": total_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "tasks": tasks_list
        }
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return {
            "status": "success",
            "total_tasks": 0,
            "running_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "tasks": []
        }

@app.delete("/api/qq/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    global is_connected, client
    if not is_connected:
        return {
            "status": "error",
            "message": "未连接到NapCat"
        }
    
    try:
        # 先尝试删除原始文件（即使失败也继续删除任务）
        try:
            client.tasks.delete_original_files(task_id)
        except Exception as e:
            # 仅记录日志，不影响任务删除
            logger.warning(f"删除任务原始文件失败: {str(e)}")
        
        # 删除任务
        result = client.tasks.delete(task_id)
        
        return {
            "status": "success",
            "message": "任务删除成功",
            "result": result
        }
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return {
            "status": "error",
            "message": f"删除任务失败: {str(e)}"
        }

@app.post("/api/qq/tasks/open-file")
async def open_file(request: dict):
    """打开文件所在位置并选中文件"""
    file_path = request.get("file_path", "")
    if not file_path:
        return {
            "status": "error",
            "message": "文件路径不能为空"
        }
    
    try:
        import os
        import subprocess
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": "文件不存在"
            }
        
        # 使用explorer命令打开文件夹并选中文件
        subprocess.run(['explorer', '/select,', file_path])
        
        return {
            "status": "success",
            "message": "文件位置已打开并选中",
            "file_path": file_path
        }
    except Exception as e:
        logger.error(f"打开文件位置失败: {str(e)}")
        return {
            "status": "error",
            "message": f"打开文件位置失败: {str(e)}"
        }

@app.post("/api/analyze", response_model=AnalyzeTaskResponse)
async def analyze_task(request: AnalyzeTaskRequest):
    """分析导出任务并生成简报"""
    global export_tasks, analyze_log_list, client
    
    # 开始计时
    analysis_start_time = time.time()
    
    task = None
    
    if request.task_id in export_tasks:
        task_info = export_tasks[request.task_id]
        task = task_info["task"]
    else:
        if not client:
            raise HTTPException(status_code=400, detail="Napcat服务未连接")
        
        try:
            tasks = client.tasks.get_all()
            for t in tasks:
                if t.id == request.task_id:
                    task = t
                    export_tasks[request.task_id] = {
                        "task": task,
                        "status": task.status.value,
                        "created_at": datetime.now().isoformat()
                    }
                    break
        except Exception as e:
            logger.error(f"获取任务失败: {str(e)}")
            raise HTTPException(status_code=500, detail="获取任务失败")
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status.value != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成，无法分析")
    
    if not task.file_path or not os.path.exists(task.file_path):
        raise HTTPException(status_code=404, detail="导出文件不存在")
    
    try:
        analyze_log_list.append(f"开始分析任务: {task.session_name}")
        analyze_log_list.append(f"加载文件: {task.file_path}")
        
        data = load_json(task.file_path)
        
        analyze_log_list.append(f"开始分析: {task.session_name}")
        analyze_log_list.append(f"本次共加载消息数: {len(data.get('messages', []))}")
        
        analyzer = ChatAnalyzer(data)
        
        analyze_log_list.append("预处理文本..")
        analyzer._preprocess_texts()
        analyze_log_list.append("done")
        
        analyze_log_list.append("分析单字独立性..")
        analyzer.analyze_single_chars()
        analyze_log_list.append("done")
        
        analyze_log_list.append("发现新词并添加至jieba语料库..")
        analyzer._discover_new_words()
        analyze_log_list.append("done")
        
        analyze_log_list.append("分词统计..")
        analyzer._tokenize_and_count()
        analyze_log_list.append("done")
        
        analyze_log_list.append("去除停用词..")
        analyzer._remove_stopwords()
        analyze_log_list.append("done")
        
        analyze_log_list.append("分析词语..")
        analyzer.analyze_words()
        analyze_log_list.append("done")
        
        analyze_log_list.append("分析完成")
        
        reporter = ReportGenerator(analyzer)
        
        analyze_log_list.append("生成简报")
        
        start_time = analyzer.start_time
        end_time = analyzer.end_time
        
        analyze_log_list.append(f"时间范围: {start_time} 至 {end_time}")
        
        brief_report = {
            "chat_name": task.session_name,
            "total_messages": len(analyzer.messages),
            "date_range": f"{start_time} 至 {end_time}",
            "chat_topics": "",
            "sensitive_count": 0,
            "sensitive_contexts": []
        }
        
        message_count = len(analyzer.messages)
        participants = set()
        for msg in analyzer.messages.values():
            sender_uin = msg.get('sender', {}).get('uin')
            if sender_uin:
                participants.add(sender_uin)
        participant_count = len(participants)
        
        brief_report["participant_count"] = participant_count
        
        from utils import get_top_words, llm_analyze_topics
        top_words = get_top_words(analyzer)
        chat_topics = llm_analyze_topics(top_words)
        brief_report["chat_topics"] = chat_topics
        
        analyze_log_list.append(f"1. 共有{message_count}条消息")
        analyze_log_list.append(f"2. 共有{participant_count}人参与聊天")
        analyze_log_list.append(f"3. 聊天主题：{chat_topics}")
        
        sensitive_count = 0
        for word in analyzer.tagged_word:
            sensitive_count += analyzer.word_freq.get(word, 0)
        brief_report["sensitive_count"] = sensitive_count
        
        analyze_log_list.append(f"4. 涉及到敏感内容{sensitive_count}次")
        
        from utils import get_sensitive_contexts
        sensitive_contexts = get_sensitive_contexts(analyzer)
        brief_report["sensitive_contexts"] = sensitive_contexts
        
        analyze_log_list.append("5. 敏感内容相关聊天记录：")
        for context in sensitive_contexts:
            analyze_log_list.append(f"   敏感词: {context['word']}")
            analyze_log_list.append("   上下文聊天记录:")
            for msg in context['messages']:
                sender_name = msg.get('sender', {}).get('name', '未知用户')
                text = msg.get('content', {}).get('text', '') if isinstance(msg.get('content'), dict) else str(msg.get('content', ''))
                timestamp = transform_datetime(msg.get('timestamp'))
                analyze_log_list.append(f"   [{timestamp}] {sender_name}: {text}")
            analyze_log_list.append("")
        
        analyze_log_list.append("简报生成完成")
        
        # 计算并输出分析耗时
        analysis_end_time = time.time()
        analysis_duration = analysis_end_time - analysis_start_time
        print(f"[分析耗时] 任务 '{task.session_name}' 分析完成，总耗时: {analysis_duration:.2f} 秒")
        
        return {
            "status": "success",
            "message": "分析完成",
            "brief_report": brief_report
        }
    except Exception as e:
        logger.error(f"分析任务失败: {str(e)}")
        analyze_log_list.append(f"分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析任务失败: {str(e)}")

@app.get("/api/status")
async def get_status():
    """获取API服务状态"""
    global is_connected, export_tasks, log_list
    return {
        "status": "running",
        "napcat_connected": is_connected,
        "export_tasks_count": len(export_tasks),
        "log_count": len(log_list)
    }

@app.get("/api/logs")
async def get_logs():
    """获取API服务日志"""
    global log_list
    return {"status": "success", "logs": log_list}

@app.get("/api/analyze/logs")
async def get_analyze_logs():
    """获取分析日志"""
    global analyze_log_list
    return {"status": "success", "logs": analyze_log_list}

@app.get("/api/analyze/logs/clear")
async def clear_analyze_logs():
    """清空分析日志"""
    global analyze_log_list
    analyze_log_list.clear()
    return {"status": "success", "message": "分析日志已清空"}

# 辅助函数
def update_task_status(id, task):
    """更新任务状态"""
    global export_tasks, log_list
    if task.id in export_tasks:
        export_tasks[task.id]["status"] = task.status.value
    log_list.append(f"{datetime.now().isoformat()}: 任务 {task.session_name} 更新状态为 {task.status.value}")

def log_export_error(id, error):
    """记录导出错误"""
    global log_list
    log_list.append(f"{datetime.now().isoformat()}: 导出 {id} 失败: {str(error)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
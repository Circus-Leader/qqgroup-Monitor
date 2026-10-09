import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api_server import app
from cli_mode import run_cli_mode

def main():
    """主函数，支持CLI模式和API服务器模式"""
    parser = argparse.ArgumentParser(description='QQ群聊消息分析器')
    parser.add_argument('--mode', choices=['cli', 'api'], default='cli',
                       help='运行模式: cli=命令行模式, api=API服务器模式')
    parser.add_argument('--host', default='127.0.0.1', help='API服务器主机地址')
    parser.add_argument('--port', type=int, default=5000, help='API服务器端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    if args.mode == 'api':
        # API服务器模式
        import uvicorn
        print(f"启动API服务器，地址: http://{args.host}:{args.port}")
        print(f"API文档: http://{args.host}:{args.port}/docs")
        uvicorn.run(app, host=args.host, port=args.port, reload=args.debug)
    else:
        # CLI模式
        run_cli_mode()


if __name__ == '__main__':
    main()
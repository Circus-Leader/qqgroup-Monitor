import os
import json
from datetime import datetime

from config import *
from utils import transform_datetime, get_sensitive_contexts, get_top_words, llm_analyze_topics
from analyzer import ChatAnalyzer

class ReportGenerator:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.chat_name = analyzer.chat_name

    def brief_report(self, request):
        """对于用户的请求生成简报"""
        # 找到请求对应的所有消息条目
        start_idx = -1
        end_idx = -1
        for idx, message in enumerate(self.analyzer.messages.values()):
            timestamp = transform_datetime(message.get("timestamp"))
            if request[0] <= timestamp <= request[1]:
                if start_idx == -1:
                    start_idx = idx
                end_idx = idx 
        
        # 如果没有找到符合条件的消息
        if start_idx == -1:
            print("\n===== 简报 =====")
            print("1. 共有0条消息")
            print("2. 共有0人参与聊天")
            print("3. 聊天主题无")
            print("4. 涉及到敏感内容0次")
            print("================")
            return
        
        # 创建子分析对象
        sub_data = self.analyzer.data.copy()
        message_list = list(self.analyzer.messages.values())
        sub_data['messages'] = message_list[start_idx:end_idx + 1]
        sub_analyzer = ChatAnalyzer(sub_data)
        #开始子分析
        sub_analyzer.analyze()
        
        # 1. 统计消息条数
        message_count = len(sub_analyzer.messages)
        
        # 2. 统计参与聊天人数
        participants = set()
        for msg in sub_analyzer.messages.values():
            sender_uin = msg.get('sender', {}).get('uin')
            if sender_uin:
                participants.add(sender_uin)
        participant_count = len(participants)
        
        # 3. 聊天主题
        top_words = get_top_words(self.analyzer)
        chat_topics = llm_analyze_topics(top_words)

        # 4. 统计敏感内容次数
        sensitive_count = 0
        for word in sub_analyzer.tagged_word:
            sensitive_count += sub_analyzer.word_freq.get(word, 0)
        
        # 5. 获取敏感词汇对应原句和上下文
        sensitive_contexts = get_sensitive_contexts(sub_analyzer)
        
        # 输出简报
        print("\n===== 简报 =====")
        print(f"1. 共有{message_count}条消息")
        print(f"2. 共有{participant_count}人参与聊天")
        print(f"3. 聊天主题：{chat_topics}")
        print(f"4. 涉及到敏感内容{sensitive_count}次")
        print("5. 敏感内容相关聊天记录：")
        for context in sensitive_contexts:
            print(f"   敏感词: {context['word']}")
            print(f"   上下文聊天记录:")
            for msg in context['messages']:
                sender_name = msg.get('sender', {}).get('name', '未知用户')
                text = msg.get('content', {}).get('text', '') if isinstance(msg.get('content'), dict) else str(msg.get('content', ''))
                timestamp = transform_datetime(msg.get('timestamp'))
                print(f"   [{timestamp}] {sender_name}: {text}")
            print()
        print("================")
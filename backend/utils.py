import json
import re
import math
import os
from openai import OpenAI
from config import *
from datetime import datetime, timezone, timedelta
def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        return json.load(f)
    
def clean_text(text):
    """清理文本，去除表情、@、回复等干扰内容"""
    if not text:
        return ""
    
    # 1. 去除回复标记 [回复 xxx: yyy]
    text = re.sub(r'\[回复\s+[^\]]*\]', '', text)
    
    # 2. 去除@某人（包括群昵称中的空格、括号等）
    # 匹配 @ 开头，后面的所有内容直到遇到"空格+中文/字母"（实际消息内容的开始）
    text = re.sub(r'@[^\n]*?(?=\s+[\u4e00-\u9fffa-zA-Z])', '', text)
    # 处理只有@没有后续内容的情况
    text = re.sub(r'@[^\n]*$', '', text)
    
    # 3. 循环去除所有方括号内容（如[图片][表情]等）
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r'\[[^\[\]]*\]', '', text)
    
    # 4. 去除链接
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    
    # 5. 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def calculate_entropy(neighbor_freq):
    total = sum(neighbor_freq.values())
    if total == 0:
        return 0
    entropy = 0
    for freq in neighbor_freq.values():
        p = freq / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def extract_emojis(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U00002300-\U000023FF"
        "]",
        flags=re.UNICODE
    )
    return emoji_pattern.findall(text)

def is_emoji(char):
    if len(char) != 1:
        return False
    code = ord(char)
    emoji_ranges = [
        (0x1F600, 0x1F64F), (0x1F300, 0x1F5FF), (0x1F680, 0x1F6FF),
        (0x1F1E0, 0x1F1FF), (0x2702, 0x27B0), (0x1F900, 0x1F9FF),
        (0x1FA00, 0x1FA6F), (0x1FA70, 0x1FAFF), (0x2600, 0x26FF), (0x2300, 0x23FF),
    ]
    return any(start <= code <= end for start, end in emoji_ranges)

def llm_analyze_words(words):
    analyzed_words=[]
    client = OpenAI(
        api_key= OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL)
    '''
    SYSTEM_PROMPT = """你是一位分析语言是否涉政涉党违法犯罪的敏感负面信息的专家。
    我将给出一系列词组请你分析，要求输出严格按照示例，不要多余输出任何内容。
    示例输入:["苹果","刷单","想象力","味精","挂机","和平","主张","协商","政策","政府","期末","集会","考试","杭州","络合物","旅游","战略","阳痿","打游戏","自尊","攻击","忽略","国家","京东","洗衣机"]
    示例输出:["刷单","政策","政府","集会","战略","国家"]
    按以上示例，仅对涉政涉党违法犯罪的敏感负面信息的词组予以保留，不要加引号或其他格式。
                    """
    '''
    SYSTEM_PROMPT = """你是一位分析网络群聊中是否出现游戏《原神》相关的词组的专家。
    示例输入:["苹果","刷单","原神","味精","挂机","和平","主张","协商","深渊","水神","期末","集会","考试","杭州","络合物","旅游","战略","阳痿","打游戏","自尊","攻击","忽略","旅行者","祈愿","神铸赋形"]
    示例输出:["原神","深渊","水神","旅行者","祈愿","神铸赋形"]
    按以上示例，去除输入中与原神无关的词组，仅对出现游戏《原神》相关的词组予以保留，不要加引号或其他格式。
    参考词组：稻妻城迪姐,罗莎莉亚,迪卢克,璃月,白术,浪花骑士,阿蕾奇诺,老阿姨,班神,雷泽,流浪者,二少爷,祈愿,欧庇克莱歌剧院,坎蒂丝,雷电将军,神,猫娘,蒙德,玉京台,提纳里,白鹭公主,诺艾尔,温迪,提瓦特,水神,赛诺,普契涅拉,层岩巨渊,打牌佬,瑶瑶,丽莎,行秋,卢姥爷,雪山,摸鱼忍者,云堇,水龙王,鸣神大社,妮露,万叶,天权星,格拉,抽,甘雨,柯莱,皮耶罗,魈,孤云阁,兰姐,申鹤,天狗,夏祭女王,枫丹廷,鹿野院平藏,摸鱼真君,纳塔,神里绫华,须弥,钟离,小鹿,荧,垩酱,神里绫人,桑多涅,枫原万叶,罗莎琳,凝冰渡海真君,原石,跨年池,蔷薇魔女,香菱,多莉,降魔大圣,归离原,刻晴,胡桃,净善宫,海哥,弗雷米内,小柯莱,可莉,雷神,原神,九条裟罗,天守阁,云先生,八酝岛,神无冢,希娜小姐,皇女,修女,夏沃蕾,须弥教令院,塔利亚,纳西妲,女武神,内鬼,七七,龙王,散兵,菲谢尔,八重神子,无冕龙王,至冬,椰羊,凝光,卡皮塔诺,轻策庄,梅洛彼得堡,鸣神岛,外来者,屑狐狸,阿弥利多学院,小天使,阿兹特克,蒲公英骑士,迪奥娜,阿贝多,须弥城,迪希雅,克洛琳德,踏鞴砂,娜维娅,锅巴发射器,多托雷,龙脊雪山,托马,鹤观,辛焱,炸鱼佬,琴,提子,旅行者,库库尔坎,草,希格雯,夜兰,达达利亚,千织,大小姐,陶典,砂糖,阿忍,睡美人,奶妈,叶天帝,岩王爷,早柚,羽蛇神,优菈,那维莱特,应急食品,清籁丸,哥伦比娅,卡维,坎瑞亚,久岐忍,凯亚,莫娜,安柏,五郎,社奉行,潘塔罗涅,神铸赋形,风龙废墟,派蒙,荒泷一斗,望舒客栈,芭芭拉,莱欧斯利,米卡,穆纳塔,星落湖,螺旋深渊,水盾,深渊,内鬼奶妈,北斗,风起地,珐露珊,艾尔海森,渊下宫,林尼,莱依拉,稻妻城,重云,宵宫,璃月港,小师妹,斗子,稻妻,莱宝,桓那兰那,小律师,阿贝多二号,小太阳,芙芙,班尼特,化城郭,狼崽,埃洛伊,芙宁娜,卡子哥,琳妮特,枫丹,烟绯,夏洛蒂,草神
    在给出以上参考词组之后，我将给出一系列词组请你分析，对于输入中与参考词组中完全相同或你觉得相近的词组才予以保留，不要直接套用我的参考词组输出。
                    """    
    total_batches = math.ceil(len(words) / MAX_TOKEN_SIZE)

    for i in range(total_batches):
        start_idx = i * MAX_TOKEN_SIZE
        end_idx = min((i + 1) * MAX_TOKEN_SIZE, len(words))
        user_prompt = json.dumps(words[start_idx:end_idx], ensure_ascii=False)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
            timeout=30
        )
        try:
            result = json.loads(response.choices[0].message.content)
            analyzed_words += result
        except:
            analyzed_words += []
    return analyzed_words

def llm_analyze_topics(words):
    analyzed_topics=[]
    client = OpenAI(
        api_key= OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL)
    SYSTEM_PROMPT = """你是一位通过词组分析网络群聊聊天主题相关的专家。
    我将给出一系列词组请你分析，对于这些词组，给出若干个主题,要求输出严格按照示例，不要多余输出任何内容。
    示例输入:["苹果","刷单","原神","味精","挂机","和平","主张","协商","深渊","水神","期末","集会","考试","杭州","络合物","旅游","战略","阳痿","打游戏","自尊","攻击","忽略","旅行者","祈愿","神铸赋形"]
    示例输出:["原神游戏相关","游戏行为与体验","学业相关话题","人际互动与态度方式"]
    按以上示例，仅给出主题，不要加引号或其他格式。
                    """
    user_prompt = json.dumps(words, ensure_ascii=False)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        stream=False
    )
    try:
        analyzed_topics = json.loads(response.choices[0].message.content)
    except:
        analyzed_topics += []
    return analyzed_topics

def is_valid_date(date_int):
    """检测日期是否合法"""
    # 转为字符串，确保是8位（防止极端情况）
    date_str = str(date_int).zfill(8)
    try:
        datetime.strptime(date_str, "%Y%m%d")
        return True
    except ValueError:
        return False
    
def get_request(start_time, end_time):
    """获取用户查询，返回包含两个8位时间码的列表"""
    
    while True:
        print("\n请输入查询时间段，例：20250101 20251106")
        print("若要退出程序键入-1")
        
        user_input = input("请输入：").strip()

        if user_input == "-1":
            return -1
        
        input_parts = user_input.split()
        if len(input_parts) != 2:
            print("格式错误！请输入两个8位数字（用空格分隔），或单独输入-1退出")
            continue
        
        start_str, end_str = input_parts
        if not (start_str.isdigit() and len(start_str) == 8):
            print(f"起始日期错误！'{start_str}' 不是8位纯数字，请重新输入")
            continue
        if not (end_str.isdigit() and len(end_str) == 8):
            print(f"结束日期错误！'{end_str}' 不是8位纯数字，请重新输入")
            continue
        
        start_date = int(start_str)
        end_date = int(end_str)
        
        if not is_valid_date(start_date):
            print(f"起始日期错误！'{start_date}' 是不存在的日期，请重新输入")
            continue
        if not is_valid_date(end_date):
            print(f"结束日期错误！'{end_date}' 是不存在的日期，请重新输入")
            continue
        
        if end_date < start_date:
            print(f"时间段不合法！结束日期 {end_date} 不能早于起始日期 {start_date}，请重新输入")
            continue

        if start_date < start_time:
            print(f"起始日期非法！查询起始时间不能早于最早时间 {start_time}，请重新输入")
            continue
        if end_date > end_time:
            print(f"结束日期非法！查询结束时间不能晚于最晚时间 {end_time}，请重新输入")
            continue
        
        return [start_date, end_date]
    

def transform_datetime(ts):
    """转换时间格式为UTC+8的8位时间码"""
    try:
        ts_formatted = ts.replace('Z', '+00:00')
        utc_dt = datetime.fromisoformat(ts_formatted)
        cst_tz = timezone(timedelta(hours=8))
        local_dt = utc_dt.astimezone(cst_tz)
        
        datetime_list = [
            local_dt.year,   
            local_dt.month,  
            local_dt.day,   
            local_dt.hour,   
            local_dt.minute,  
            local_dt.second  
        ]
        return int(f"{datetime_list[0]}{datetime_list[1]:02d}{datetime_list[2]:02d}")
    
    except (ValueError, TypeError) as e:
        print(f"时间解析失败：{e}")
        return None

def get_sensitive_contexts(analyzer):
    """获取敏感词汇对应的原句和上下文聊天记录"""
    # 获取所有消息并按messageSeq排序
    sorted_messages = sorted(analyzer.messages.items(), key=lambda x: int(x[0]))
    message_list = [msg for seq, msg in sorted_messages]
    
    # 存储所有敏感词汇的上下文范围
    context_ranges = []
    
    # 为每个敏感词汇找到包含它的消息
    for word in analyzer.tagged_word:
        # 获取包含该敏感词的消息序列号
        msg_seqs = set()
        for contributor, data in analyzer.word_contributors[word].items():
            msg_seqs.update(data["msgSeqs"])
        
        # 为每个消息序列号获取上下文范围
        for msg_seq in msg_seqs:
            # 找到该消息在排序后列表中的索引
            msg_index = None
            for i, (seq, msg) in enumerate(sorted_messages):
                if seq == msg_seq:
                    msg_index = i
                    break
            
            if msg_index is not None:
                # 计算上下文范围（前后10句）
                start_idx = max(0, msg_index - 10)
                end_idx = min(len(message_list) - 1, msg_index + 10)
                context_ranges.append({
                    'word': word,
                    'msg_seq': msg_seq,
                    'start_idx': start_idx,
                    'end_idx': end_idx,
                    'msg_index': msg_index
                })
    
    # 合并重叠的上下文范围
    merged_ranges = merge_overlapping_ranges(context_ranges, message_list)
    
    # 为每个合并后的范围获取消息列表
    result = []
    for range_info in merged_ranges:
        messages = message_list[range_info['start_idx']:range_info['end_idx'] + 1]
        result.append({
            'word': ', '.join(range_info['words']),
            'messages': messages
        })
    
    return result

def merge_overlapping_ranges(context_ranges, message_list):
    """合并重叠的上下文范围"""
    if not context_ranges:
        return []
    
    # 按起始索引排序
    sorted_ranges = sorted(context_ranges, key=lambda x: x['start_idx'])
    
    merged = []
    current = sorted_ranges[0].copy()
    current['words'] = [current['word']]
    
    for next_range in sorted_ranges[1:]:
        # 检查是否重叠
        if next_range['start_idx'] <= current['end_idx']:
            # 合并范围
            current['end_idx'] = max(current['end_idx'], next_range['end_idx'])
            current['start_idx'] = min(current['start_idx'], next_range['start_idx'])
            # 添加词汇
            if next_range['word'] not in current['words']:
                current['words'].append(next_range['word'])
        else:
            # 添加当前范围到结果，并开始新的范围
            merged.append(current)
            current = next_range.copy()
            current['words'] = [next_range['word']]
    
    # 添加最后一个范围
    merged.append(current)
    
    return merged

def get_top_words(analyzer, limit=100):
    """获取ChatAnalyzer对象中word_freq最高的指定数量的词
    
    Args:
        analyzer: ChatAnalyzer对象
        limit: 返回的最大词数，默认为100
    
    Returns:
        list: 包含(词, 频次)元组的列表，按频次降序排列
    """
    # 获取所有词及其频次，并按频次降序排序
    sorted_words = sorted(analyzer.word_freq.items(), key=lambda x: x[1], reverse=True)
    
    # 如果词数不足limit，返回所有词；否则返回前limit个
    if len(sorted_words) <= limit:
        return sorted_words
    else:
        return sorted_words[:limit]

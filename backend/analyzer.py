import re
import random
import string
import math
import jieba

from collections import Counter, defaultdict
from config import *
from utils import (clean_text, calculate_entropy, extract_emojis, is_emoji, llm_analyze_words, transform_datetime)

jieba.setLogLevel(jieba.logging.INFO)

PUNCTUATION_PATTERN = re.compile(
    r'[\s\.,!?;:，。！？；：、""''（）【】\[\](){}·~～@#$%^&*\-+=<>/\\|\'\"《》]'
)

class ChatAnalyzer:
    def __init__(self, data):
        self.data = data
        self.messages = data.get('messages', [])
        self.chat_name = data.get('chatName', data.get('chatInfo', {}).get('name', '未知群聊'))
        self.start_time = transform_datetime(self.messages[0].get('timestamp'))
        self.end_time = transform_datetime(self.messages[-1].get('timestamp'))
        self.cleaned_texts = []  # 缓存清洗后的文本
        self.single_char_stats = {}
        self.discovered_words = set()
        self.word_freq = Counter()
        self.word_samples = defaultdict(list)
        self.word_contributors = defaultdict(
            lambda: defaultdict(
                lambda: {"count": 0, "msgSeqs": []} 
            )
        )
        self.tagged_word = []


        #将 self.messages 转为messageSeq映射到msg的字典 同时去重
        self.messages = {
            msg['messageSeq']: msg 
            for msg in data['messages']
        }

        # self._build_mappings()
        
    def analyze(self):
        print(f"开始分析: {self.chat_name}")
        print(f"本次共加载消息数: {len(self.messages)}")
        
        print("\n预处理文本..")
        self._preprocess_texts()
        print("done")

        print("\n分析单字独立性..")
        self.analyze_single_chars()
        print("done")

        print("\n发现新词并添加至jieba语料库..")
        self._discover_new_words()
        print("done")

        print("\n分词统计..")
        self._tokenize_and_count()
        print("done")
        
        print("\n去除停用词..")
        self._remove_stopwords()
        print("done")
        
        print("\n分析词语..")
        self.analyze_words()
        print("done")

    def _preprocess_texts(self):
        """预处理文本，去除系统信息"""
        skipped = 0
        for msg in self.messages.values():
            content = msg.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else ''
            cleaned = clean_text(text)
            if cleaned and len(cleaned) >= 1:
                self.cleaned_texts.append(cleaned)
            elif text:
                skipped += 1
        
        print(f"有效文本: {len(self.cleaned_texts)} 条, 跳过: {skipped} 条")

    def analyze_single_chars(self):
        """分析单字的独立出现情况"""
        
        total_count = Counter()
        solo_count = Counter()
        boundary_count = Counter()
        punctuation = set('，。！？、；：""''（）,.!?;:\'"()[]【】《》<>…—～·')
        
        for text in self.cleaned_texts:
            # 统计每个字的总出现次数
            for char in text:
                if re.match(r'^[\u4e00-\u9fffa-zA-Z]$', char):
                    total_count[char] += 1
            
            # 统计单字消息
            clean_chars = [c for c in text if re.match(r'^[\u4e00-\u9fffa-zA-Z]$', c)]
            if len(clean_chars) == 1:
                solo_count[clean_chars[0]] += 1
            
            # 统计在边界位置的出现
            for i, char in enumerate(text):
                if not re.match(r'^[\u4e00-\u9fffa-zA-Z]$', char):
                    continue
                left_ok = (i == 0) or (text[i-1] in punctuation) or (text[i-1].isspace())
                right_ok = (i == len(text)-1) or (text[i+1] in punctuation) or (text[i+1].isspace())
                if left_ok and right_ok:
                    boundary_count[char] += 1
        
        for char in total_count:
            total = total_count[char]
            solo = solo_count[char]
            boundary = boundary_count[char]
            independent = solo + boundary * 0.5
            ratio = independent / total if total > 0 else 0
            self.single_char_stats[char] = (total, independent, ratio)
       
    def _discover_new_words(self):
        """发现新词并添加至jieba语料库"""
        ngram_freq = Counter()
        left_neighbors = defaultdict(Counter)
        right_neighbors = defaultdict(Counter)
        total_chars = 0
        
        for text in self.cleaned_texts:
            # 按标点分句
            sentences = re.split(r'[，。！？、；：""''（）\s\n\r,\.!?\(\)]', text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 2:
                    continue
                total_chars += len(sentence)
                
                for n in range(2, min(6, len(sentence) + 1)):
                    for i in range(len(sentence) - n + 1):
                        ngram = sentence[i:i+n]
                        # 跳过纯数字/符号/纯英文
                        if re.match(r'^[\d\s\W]+$', ngram) or re.match(r'^[a-zA-Z]+$', ngram):
                            continue
                        ngram_freq[ngram] += 1
                        if i > 0:
                            left_neighbors[ngram][sentence[i-1]] += 1
                        else:
                            left_neighbors[ngram]['<BOS>'] += 1
                        if i + n < len(sentence):
                            right_neighbors[ngram][sentence[i+n]] += 1
                        else:
                            right_neighbors[ngram]['<EOS>'] += 1
        
        # 筛选新词
        for word, freq in ngram_freq.items():
            if freq < NEW_WORD_MIN_FREQ:
                continue
            
            # 邻接熵
            left_ent = calculate_entropy(left_neighbors[word])
            right_ent = calculate_entropy(right_neighbors[word])
            min_ent = min(left_ent, right_ent)
            if min_ent < ENTROPY_THRESHOLD:
                continue
            
            # PMI（内部凝聚度）
            min_pmi = float('inf')
            for i in range(1, len(word)):
                left_freq = ngram_freq.get(word[:i], 0)
                right_freq = ngram_freq.get(word[i:], 0)
                if left_freq > 0 and right_freq > 0:
                    pmi = math.log2((freq * total_chars) / (left_freq * right_freq + 1e-10))
                    min_pmi = min(min_pmi, pmi)
            
            if min_pmi == float('inf'):
                min_pmi = 0
            
            if min_pmi < PMI_THRESHOLD:
                continue
            
            self.discovered_words.add(word)
        
        # 添加到jieba词典
        for word in self.discovered_words:
            jieba.add_word(word, freq=1000)
        
        print(f"发现 {len(self.discovered_words)} 个新词")

    def _tokenize_and_count(self):
        """分词统计"""
        for msgseq, msg in self.messages.items():
            sender_uin = msg.get('sender', {}).get('uin')
            content = msg.get('content', {})
            text = content.get('text', '') if isinstance(content, dict) else ''
            original_text = text
            cleaned = clean_text(text)
            
            if not cleaned:
                continue
            
            words = list(jieba.cut(cleaned))
            emojis = extract_emojis(cleaned)
            words = [w for w in words if not is_emoji(w)]  # 从words中去掉emoji
            all_tokens = words + emojis
            
            for word in all_tokens:
                word = word.strip()
                if not word:
                    continue
                
                # 跳过纯数字/符号
                if re.match(r'^[\d\W]+$', word) and not is_emoji(word):
                    continue
                
                self.word_freq[word] += 1
                if sender_uin:
                    self.word_contributors[word][sender_uin]["count"] += 1
                    if msgseq not in self.word_contributors[word][sender_uin]["msgSeqs"]:
                        #同一句中同一词出现多次不重复记录msgseq
                        self.word_contributors[word][sender_uin]["msgSeqs"].append(msgseq)
                if len(self.word_samples[word]) < SAMPLE_COUNT * 3:
                    self.word_samples[word].append(cleaned)

    def analyze_words(self):
        """分析词语"""

        unconfirmed_word = []
        confirmed_word = []
        # 读入词典
        try:
            with open(DIC_FILE, encoding='utf-8') as f:
                dic = f.read().split(',')
        except:
            dic = []
        
        for word in self.word_contributors.keys():
            # 检查被检测词是否包含词典中的任意一个词（词典词是被检测词的子串）
            # 只匹配长度 >= 2 的词典词，单字不被识别
            is_matched = any(dic_word and len(dic_word) >= 2 and dic_word in word for dic_word in dic)
            if is_matched:
                self.tagged_word.append(word)
            else:
                unconfirmed_word.append(word)

        # 暂时停用，效果不佳
        # 可能原因：提示词有误，常会出现”少女“”哥哥“”妹妹“”女仆“”史莱姆“”重击“等极低频率词
        # openai分析
        # confirmed_word = llm_analyze_words(unconfirmed_word)
        # if confirmed_word:
        #     for word in confirmed_word:
        #         self.tagged_word.append(word)
        # else:
        #     print("大模型返回有误，仅使用词典")

        # 分析结果写入词典
        dic += confirmed_word
        dic = list(set(dic))
        with open(DIC_FILE, 'w', encoding='utf-8') as f:
            f.write(','.join(dic))

    def _remove_stopwords(self):
        """去除停用词，从self.discovered_words，self.word_freq，self.word_contributors中移除"""
        # 加载停用词列表
        try:
            with open(STOP_WORDS_FILE, 'r', encoding='utf-8') as f:
                stopwords = set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            print("停用词文件未找到，跳过去除停用词步骤")
            return
        
        removed_count = 0
        
        # 从self.discovered_words中去除停用词
        words_to_remove = set()
        for word in self.discovered_words:
            if word in stopwords:
                words_to_remove.add(word)
        
        self.discovered_words -= words_to_remove
        
        # 从self.word_freq中去除停用词
        freq_words_to_remove = set()
        for word in self.word_freq:
            if word in stopwords:
                freq_words_to_remove.add(word)
                removed_count += 1
        
        for word in freq_words_to_remove:
            del self.word_freq[word]
        
        # 从self.word_contributors中去除停用词
        contrib_words_to_remove = set()
        for word in self.word_contributors:
            if word in stopwords:
                contrib_words_to_remove.add(word)
        
        for word in contrib_words_to_remove:
            del self.word_contributors[word]
        
        # 从self.word_samples中去除停用词
        sample_words_to_remove = set()
        for word in self.word_samples:
            if word in stopwords:
                sample_words_to_remove.add(word)
        
        for word in sample_words_to_remove:
            del self.word_samples[word]
        
        print(f"已去除{removed_count}个停用词")



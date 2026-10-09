INPUT_FILE = 'chat.json'
DIC_FILE = 'dic.txt'
STOP_WORDS_FILE = 'baidu_stopwords.txt'
QRCODE_FILE = 'D:/1-work/NapCat-QCE-Windows-x64/cache/qrcode.png'
NAPCAT_PATH = 'D:/1-work/NapCat-QCE-Windows-x64'
QQ_PATH = 'D:/3-daily/QQ/QQ.exe'
EXPORT_FILE = './exports'
# 新词发现参数
PMI_THRESHOLD = 2.0      #新词内部的凝聚度，设定越高则新词越少
ENTROPY_THRESHOLD = 0.5  #新词的自由度，设定越高则新词越少
NEW_WORD_MIN_FREQ = 20   #新词出现的最少次数，设定越高则新词越少

SAMPLE_COUNT = 10
CONSOLE_WIDTH = 60

# ============ OpenAI 配置 ============
OPENAI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxx" # sk-
OPENAI_BASE_URL = "https://api.deepseek.com"
OPENAI_MODEL = "deepseek-chat"
MAX_TOKEN_SIZE = 10000
pass
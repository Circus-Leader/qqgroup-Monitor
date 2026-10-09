# QQ 群消息分析器

> 面向 Windows 本地环境的 **QQ 群聊记录导出与内容分析工具**。
> 通过 NapCat-QCE 从本机 QQ 客户端拉取聊天记录，再用「新词发现 + 中文分词 + 词典/大模型」的方式做群聊主题归纳与敏感内容筛查。

| 项目 | 说明 |
| --- | --- |
| 项目代号 | `qqgroup-Monitor` / 前端路由基址 `qcea-tool` |
| 形态 | 前后端分离的本地 Web 应用，附带交互式命令行模式 |
| 平台 | Windows（依赖本机 QQ 客户端与 NapCat-QCE） |
| 后端 | Python + FastAPI（默认 `127.0.0.1:5000`） |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Vue Router |
| 分析能力 | jieba 分词、n-gram + PMI + 邻接熵新词发现、DeepSeek 主题归纳与词义判定 |
| 当前状态 | 个人自用 / 实验性，尚未做鉴权与输入校验加固 |

---

## 一、项目定位

QQ 群聊里有大量有价值但难以人工过目的信息：长期沉淀的话题脉络、偶发的高频梗、以及需要留意的敏感表述。本项目要解决的就是这件事——把「导出聊天记录」和「读懂聊天记录」合成一条本地流水线：

1. 借助 NapCat-QCE 登录本机 QQ，按时间范围把群聊导出为结构化文件；
2. 用无监督方法从群聊语料里发现该群特有的新词（黑话、梗、昵称）；
3. 分词统计后，结合本地词典与大模型判定敏感词，并给出每处敏感内容的原文上下文；
4. 把「消息数 / 参与人数 / 聊天主题 / 敏感内容次数与上下文」汇成一份简报，供人快速判断。

它**不是**一个通用 IM 数据分析平台，而是针对「中文 QQ 群聊 + 本地私有部署 + 简报式结论」这一具体场景的窄而深的工具。

---

## 二、整体架构

四层结构，前后端各自独立启动，中间靠一个内嵌的第三方 SDK 对接 NapCat-QCE。

```
                    ┌─────────────────────────────────────────┐
                    │  QQ 客户端 (QQ.exe)                      │
                    └───────────────────┬─────────────────────┘
                                        │
                    ┌───────────────────▼─────────────────────┐
                    │  NapCat-QCE 服务（外部程序，独立目录）    │
                    │  提供 HTTP API + accessToken + 二维码     │
                    └───────────────────┬─────────────────────┘
                                        │ HTTP + token（自动发现）
   ┌────────────────────────────────────▼────────────────────────────────────┐
   │  backend/napcat_qce/   内嵌的 NapCat-QCE Python SDK                      │
   │  client.py(HTTP 客户端) · launcher.py(拉起/守护) · auto_token.py(取令牌)  │
   │  websocket.py(事件推送) · types.py(数据模型) · config.py(导出配置)        │
   └────────────────────────────────────┬────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┴───────────────────────────────┐
        │                                                               │
┌───────▼────────────────────────┐                      ┌───────────────▼──────────────┐
│  api_server.py                 │                      │  cli_mode.py                 │
│  FastAPI 服务，23 个 REST 接口  │                      │  交互式命令行：选群→选时间→  │
│  全局状态：client / export_    │                      │  导出→循环出简报            │
│  tasks / analyze_log_list      │                      │                              │
└───────┬────────────────────────┘                      └───────────────┬──────────────┘
        │                                                               │
        └───────────────────────┬───────────────────────────────────────┘
                                │
                  ┌─────────────▼──────────────┐
                  │  analyzer.py               │  分析引擎（ChatAnalyzer）
                  │  六步分析流水线             │
                  └─────────────┬──────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐    ┌─────────▼─────────┐   ┌─────────▼─────────────┐
│ report_        │    │ utils.py          │   │ config.py / dic.txt / │
│ generator.py   │    │ 清洗·熵·emoji·    │   │ baidu_stopwords.txt   │
│ 按时间段出简报  │    │ LLM 调用·上下文    │   │ 阈值与词典            │
└────────────────┘    └─────────┬─────────┘   └───────────────────────┘
                                │
                     ┌──────────▼──────────┐
                     │  DeepSeek (OpenAI   │
                     │  兼容接口) 主题归纳  │
                     └─────────────────────┘

        ▲ HTTP (axios，baseURL 硬编码 http://localhost:5000)
        │
┌───────┴──────────────────────────────────────────────────────────┐
│  frontend/   Vue 3 SPA                                            │
│  App.vue + Navbar + 7 个视图（概览/登录/会话/任务/简报/关于/新建）  │
│  services/api.js（axios 封装 + 未连接拦截）  stores/auth.js（连接态）│
└──────────────────────────────────────────────────────────────────┘
```

**后端职责划分**

| 文件 | 职责 |
| --- | --- |
| `backend/main.py` | 入口，按 `--mode cli/api` 分流到命令行或 API 服务 |
| `backend/api_server.py` | FastAPI 应用、全部 REST 接口、全局状态与日志缓冲 |
| `backend/cli_mode.py` | 拉起 NapCat、选群、选时间范围、导出、循环生成简报 |
| `backend/analyzer.py` | 分析引擎核心 `ChatAnalyzer`，实现六步流水线 |
| `backend/report_generator.py` | 按用户指定时间段构造子分析器并输出简报 |
| `backend/utils.py` | 文本清洗、信息熵、emoji 识别、LLM 调用、敏感上下文提取 |
| `backend/config.py` | 路径、新词阈值、LLM 连接配置 |
| `backend/napcat_qce/` | 内嵌 SDK：HTTP 客户端、启动器、令牌自动获取、WebSocket、数据模型 |

**前端职责划分**

| 文件 | 职责 |
| --- | --- |
| `frontend/src/App.vue` | 壳组件：导航栏 + `<router-view>` |
| `frontend/src/router/index.js` | 7 条路由，`createWebHistory('/qcea-tool')` |
| `frontend/src/services/api.js` | axios 实例、请求/响应拦截器、全部接口函数 |
| `frontend/src/stores/auth.js` | Pinia：连接状态、轮询状态与定时器句柄 |
| `frontend/src/views/*.vue` | 各业务页面 |

---

## 三、功能清单

### 3.1 扫码登录

调用 `/api/napcat/start` 连接 NapCat，拉取二维码图片供手机 QQ 扫码；随后以**指数退避**策略轮询登录状态（初始 2s，上限 10s，2 分钟超时），成功后跳转概览页。

### 3.2 会话浏览

展示群组与好友列表，含名称、群号/QQ 号、成员数；头像经 `/api/avatar/...` 读取本地已导出的头像文件，缺失时回退占位图。

### 3.3 导出任务管理

- 导出格式：**TXT / JSON / HTML / EXCEL**
- 时间范围过滤：最近 N 天、最近 N 小时、或自定义起止日期
- 支持单个导出与**批量导出**
- 任务列表、状态查询、文件下载、删除任务（含清理原始文件）、在资源管理器中定位文件

> 📌 **要生成简报，必须以 JSON 格式导出群聊**（前端会校验 `.json` 与群聊类型）。

### 3.4 智能分析（`POST /api/analyze`）

六步流水线，全程日志写入内存并由前端 2s 轮询展示：

| 步骤 | 方法 | 说明 |
| --- | --- | --- |
| 1 | `_preprocess_texts` | 清理每条消息文本，剥除 `[图片]`/`[表情]`、`@某人`、`[回复 xxx]`、链接，递归去方括号 |
| 2 | `analyze_single_chars` | 统计每个字的出现总数、独立出现数（单字成句 + 边界位置加权 0.5），得到独立性比率 |
| 3 | `_discover_new_words` | 对 2–5 元 n-gram 计算 **PMI 内部凝聚度**与**左右邻接熵**，双阈值筛选后注入 jieba 词典 |
| 4 | `_tokenize_and_count` | jieba 分词 + emoji 提取，统计词频、发言人贡献（含 msgSeq 去重）与样本句 |
| 5 | `_remove_stopwords` | 依据百度停用词表从四处数据结构同步剔除停用词 |
| 6 | `analyze_words` | 以 `dic.txt` 为敏感词表做子串匹配打标（LLM 判定逻辑当前已停用） |

### 3.5 简报生成

输出五项结论：

1. 消息条数
2. 参与人数（按 `sender.uin` 去重）
3. 聊天主题（取词频 Top 100 交给 DeepSeek 归纳）
4. 敏感内容出现次数
5. 敏感内容相关聊天记录——每处敏感词附**前后各 10 句**上下文，重叠区间自动合并去重

### 3.6 双运行模式

- **CLI 模式**（默认）：交互式选择群聊与时间范围，导出后可在同一进程内反复查询不同时间段的简报。
- **API 模式**：FastAPI 服务，自带 `/docs` Swagger 文档，供前端或其他客户端调用。

---

## 四、快速开始

### 4.1 前置依赖

| 依赖 | 版本 / 说明 |
| --- | --- |
| 操作系统 | Windows |
| Python | 3.10+（代码使用 `match` 之外的现代语法与类型标注） |
| Node.js | 18+（Vite 7 要求） |
| QQ 客户端 | 本机安装并可登录 |
| NapCat-QCE | 独立下载并解压，如 `D:\1-work\NapCat-QCE-Windows-x64` |
| DeepSeek API Key | 用于主题归纳（可选，缺失时主题步骤会失败） |

### 4.2 配置

打开 `backend/config.py`，按实际环境修改：

```python
NAPCAT_PATH  = 'D:/1-work/NapCat-QCE-Windows-x64'          # NapCat-QCE 目录
QQ_PATH      = 'D:/3-daily/QQ/QQ.exe'                      # QQ 可执行文件
QRCODE_FILE  = 'D:/1-work/NapCat-QCE-Windows-x64/cache/qrcode.png'
EXPORT_FILE  = './exports'                                 # 导出目录

# 新词发现阈值：调高则新词更少、更保守
PMI_THRESHOLD      = 2.0
ENTROPY_THRESHOLD  = 0.5
NEW_WORD_MIN_FREQ  = 20

# LLM（⚠️ 请勿把真实密钥提交到仓库，改用环境变量，见「安全须知」）
OPENAI_API_KEY  = "sk-..."
OPENAI_BASE_URL = "https://api.deepseek.com"
OPENAI_MODEL    = "deepseek-chat"
```

### 4.3 安装与启动

**后端**

```bash
cd backend
pip install -r requirements.txt
python main.py --mode api --port 5000
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

### 4.4 访问地址

| 服务 | 地址 |
| --- | --- |
| 前端页面 | **http://localhost:5173/qcea-tool/** |
| 后端 API | http://localhost:5000 |
| API 文档 | http://localhost:5000/docs |

> ⚠️ **注意前端路径**：路由使用 `createWebHistory('/qcea-tool')`，而 Vite 未配置 `base` 或代理，因此直接访问 `http://localhost:5173/` 会白屏，**必须带 `/qcea-tool/` 前缀**。

### 4.5 一键启动（可选）

根目录 `start.bat` 会开两个终端窗口分别启动后端与前端：

```bat
start "Backend"  cmd /k "cd backend && python main.py"
start "Frontend" cmd /k "cd frontend && npm run dev"
```

注意 `main.py` 不带 `--mode` 时默认进入 **CLI 模式**，如需 API 服务请显式加 `--mode api`。

---

## 五、使用流程

```
① 打开 http://localhost:5173/qcea-tool/  →  登录页
        │  手机 QQ 扫码
        ▼
② 概览页：查看任务数 / 群组数 / 好友数
        │
        ├──► 会话页：浏览群与好友，点「导出」跳转新建任务
        │
        ▼
③ 新建任务页：选目标 → 选格式（分析请选 JSON）→ 选时间范围 → 创建任务
        │
        ▼
④ 任务页：刷新查看进度，📁 定位文件，❌ 删除任务
        │
        ▼
⑤ 简报页：选择 JSON 任务 → 开始分析 → 实时日志 + 分析结果
```

### 命令行模式

```bash
cd backend
python main.py            # 等价于 --mode cli
```

按提示依次选择群聊、时间范围，导出完成后进入循环查询，输入两个 8 位日期码（如 `20250101 20251106`）即可输出该时段简报，输入 `-1` 退出。

---

## 六、API 一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 服务信息 |
| GET | `/api/status` | API 服务状态 |
| GET | `/api/logs` | 服务日志 |
| GET | `/api/qrcode` | 获取登录二维码图片 |
| POST | `/api/napcat/start` | 启动 / 重试 NapCat 连接 |
| POST | `/api/napcat/stop` | 断开 NapCat 连接 |
| GET | `/api/napcat/status` | 连接状态与登录账号信息 |
| GET | `/api/qq/groups` | 群组列表 |
| GET | `/api/qq/friends` | 好友列表 |
| GET | `/api/avatar/groups/{group_code}` | 群头像 |
| GET | `/api/avatar/friends/{uin}` | 好友头像 |
| POST | `/api/qq/export` | 创建单个导出任务 |
| POST | `/api/qq/batch_export` | 批量导出 |
| GET | `/api/qq/export/{task_id}` | 导出任务状态 |
| GET | `/api/qq/export/{task_id}/download` | 下载导出文件 |
| GET | `/api/qq/export/logs` | 导出日志 |
| GET | `/api/qq/export/file` | 读取导出文件内容（预览） |
| GET | `/api/qq/tasks` | 任务列表与统计 |
| DELETE | `/api/qq/tasks/{task_id}` | 删除任务 |
| POST | `/api/qq/tasks/open-file` | 在资源管理器中定位文件 |
| POST | `/api/analyze` | 分析导出任务并生成简报 |
| GET | `/api/analyze/logs` | 分析过程日志 |
| GET | `/api/analyze/logs/clear` | 清空分析日志 |

---

## 七、关键参数说明

| 参数 | 位置 | 作用 | 调整方向 |
| --- | --- | --- | --- |
| `PMI_THRESHOLD` | `config.py` | 新词内部凝聚度门槛 | 调高 → 新词更少更可靠 |
| `ENTROPY_THRESHOLD` | `config.py` | 新词左右邻接熵门槛 | 调高 → 新词更少更可靠 |
| `NEW_WORD_MIN_FREQ` | `config.py` | 新词最低出现次数 | 调高 → 过滤偶发组合 |
| `SAMPLE_COUNT` | `config.py` | 每词保留的样本句数 | 影响内存占用 |
| `MAX_TOKEN_SIZE` | `config.py` | LLM 单批词数 | 影响主题归纳的请求次数 |
| 上下文窗口 | `utils.py` | 敏感词前后各 10 句 | 按需放大或收窄 |
| `dic.txt` | `backend/` | 敏感词表（逗号分隔单行） | 可直接编辑扩充 |
| `baidu_stopwords.txt` | `backend/` | 停用词表（每行一词） | 按需增删 |

---

## 八、分析依赖的数据格式

分析器直接以 NapCat-QCE 导出的 JSON 为准，关键字段如下：

```jsonc
{
  "chatName": "某技术交流群",
  "messages": [
    {
      "messageSeq": 12345,                  // 消息序号，用作唯一键与排序依据
      "timestamp": "2025-01-01T12:00:00Z",  // ISO 8601，解析后转 UTC+8
      "sender": { "uin": "10001", "name": "张三" },
      "content": { "text": "今天聊聊这个方案" }
    }
  ]
}
```

> 缺少 `messages`、`chatName`、`messageSeq` 或 `sender.uin` 会导致分析异常或统计缺漏，请勿手工裁剪这些字段。

---

## 九、安全须知

以下为**当前仍待处理**的问题：

| 级别 | 问题 | 位置 | 建议 |
| --- | --- | --- | --- |
| 🟠 高 | 用户传入路径直接交给 `explorer` 执行 | `api_server.py` `/api/qq/tasks/open-file` | 校验路径归属导出目录 |
| 🟠 高 | 异常信息经 `detail` 原样回传前端 | `api_server.py` 多处 | 对外只返回通用错误，细节写日志 |

此外请注意：本工具会读取并缓存**完整的聊天记录与参与者 QQ 号**，属于高敏感个人数据。请在获得群成员知情与同意的前提下使用，并妥善保管导出目录与日志文件（`backend/cache/log/api_server.log`）。

---

## 十、目录结构

```
qqgroup-Monitor/
├── start.bat                    # 一键启动后端 + 前端
├── README.md                    # 本文档
├── backend/
│   ├── main.py                  # 入口：cli / api 分流
│   ├── api_server.py            # FastAPI 服务与全部 REST 接口
│   ├── cli_mode.py              # 交互式命令行模式
│   ├── analyzer.py              # 分析引擎 ChatAnalyzer（六步流水线）
│   ├── report_generator.py      # 简报生成
│   ├── utils.py                 # 清洗 / 熵 / emoji / LLM / 上下文
│   ├── config.py                # 路径、阈值、LLM 配置
│   ├── requirements.txt         # 依赖清单
│   ├── dic.txt                  # 敏感词表（逗号分隔）
│   ├── baidu_stopwords.txt      # 停用词表
│   ├── cache/log/               # 运行日志
│   ├── exports/                 # 默认导出目录
│   └── napcat_qce/              # 内嵌 NapCat-QCE Python SDK
│       ├── client.py            # HTTP 客户端与各资源 API
│       ├── launcher.py          # NapCat-QCE 进程拉起与守护
│       ├── auto_token.py        # accessToken 自动发现
│       ├── websocket.py         # 事件推送
│       ├── types.py             # 数据模型与筛选/导出选项
│       ├── config.py            # 导出配置管理
│       ├── export_utils.py      # 导出文件工具
│       └── exceptions.py        # 异常体系
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── README.md                # 指向本文件的简短索引
    └── src/
        ├── main.js              # 应用装配：Pinia / Router / Element Plus
        ├── App.vue              # 壳组件
        ├── style.css            # 全局样式
        ├── router/index.js      # 路由表（基址 /qcea-tool）
        ├── stores/auth.js       # 连接状态与轮询句柄
        ├── services/api.js      # axios 封装与接口函数
        ├── components/Navbar.vue
        └── views/               # Overview / Login / Chat / Task /
                                 # BriefReport / CreateNewTask / About
```

---

## 十一、常见问题

| 现象 | 原因与处理 |
| --- | --- |
| 页面白屏 | 未带 `/qcea-tool/` 前缀访问，改用 `http://localhost:5173/qcea-tool/` |
| 接口报「NapCat 服务未连接」 | 先到登录页扫码；前端拦截器会阻止未连接状态下的业务请求 |
| 二维码获取失败 | 检查 `QRCODE_FILE` 路径，并确认 NapCat-QCE 已启动 |
| 简报页提示不支持分析 | 仅支持**群聊 + JSON** 格式的导出任务 |
| 分析一直卡住无结果 | 敏感上下文提取为嵌套线性查找，大记录集会非常慢，可先缩小导出时间范围 |
| 聊天主题为空 | `OPENAI_API_KEY` / `OPENAI_BASE_URL` 配置有误或网络不可达 |
| 任务消息数为 0 | 导出尚未完成，先刷新任务列表 |

---

## 十二、文档说明

本 README 基于**源码通读**编写，覆盖项目定位、整体架构、功能清单、部署与使用、接口与参数、依赖的数据格式、安全须知与常见问题。所有结论均来自对仓库源码的直接阅读，尚未经过完整的编译与运行验证。若后续代码调整，请同步更新本文件与 `frontend/README.md`。

关于内嵌 SDK 的来源，见 `backend/napcat_qce/__init__.py` 中标注的
[qq-chat-exporter](https://github.com/shuakami/qq-chat-exporter) 项目。

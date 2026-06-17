# morphoneme

[English](README.md) | [简体中文](README_zh.md)

通过词素标注列精准查询英语单词。

一个基于 **umLabeller** 和 **CityLex** 词素标注数据集的形态学查询工具。支持按前缀、后缀、词根、派生后缀或屈折后缀进行精准搜索。提供词素切分、完整的形态结构分析以及批量处理功能。

## 数据来源

本工具是两个公开的形态学标注数据集的查询前端。数据**按原样使用，未做任何修改**。本工具作者不对源数据进行任何形式的修改、校对或补充。

### umLabeller (UniMorph)

- **来源:** [github.com/unimorph/umLabeller](https://github.com/unimorph/umLabeller/tree/main/data)
- **本地文件:** `data/eng.word.full.230613.r7_morphologic_division.tsv` — 4 列，约 61.1 万行
- 许可及使用条款遵循 UniMorph 项目。

### CityLex

- **来源:** [citylex.onrender.com](https://citylex.onrender.com/)
- **本地文件:** `data/citylex-2026-06-15_morphology_segmention.tsv` — 3 列，约 6.8 万行
- 许可及使用条款遵循 CityLex 项目。

### 免责声明

这些数据集中的形态学标注由其各自的项目提供。**不保证其 100% 正确性。** 如果源数据中存在错误或不一致，查询结果将会反映这些问题。请酌情使用。

## 安装

```bash
pip install morphoneme
```

安装后即可使用 `mp` 命令行工具。

### 本地开发

```bash
git clone https://github.com/connoryang331/morphoneme
cd morphoneme
pip install -e .
```

如果您是在本地进行开发，可以从原始 TSV 数据文件自行构建数据库：

```bash
python scripts/build_morphoneme_db.py
```

这会编译出用于快速检索的 `words` 主表以及带多级索引的 `word_morphemes` 关系平铺表，以支持毫秒级的词素查询。

### 数据库自动下载与存储

为了保持安装包的轻量化，SQLite 数据库文件（`morphoneme.db`，约 50MB）**并未**打包进 PyPI 发布包中。

当您首次实例化 `MP` 类或在终端运行命令行工具时：
1. 程序会优先寻找包目录下是否已有打包好的数据库（用于本地开发或手动放置）。
2. 如果未找到，程序会检查 `~/.morphoneme/morphoneme.db` 路径。
3. 如果依然缺失，程序将**自动从 GitHub Releases 下载**预编译压缩的数据库 zip 包，并解压至 `~/.morphoneme/` 目录下。

整个过程全自动进行，无需手动配置。

## 命令行使用方法 (CLI)

通过 `mp` 命令调用：

```bash
mp <cmd> <arg> [source] [seg] [--json] [--exclude-inf] [--exclude=STR] [--exact] [--limit=N] [--fq=VAL]
```

或者直接通过 Python 模块调用：

```bash
python -m morphoneme <cmd> <arg> [source] [seg] [--json] [--exclude-inf] [--exclude=STR] [--exact] [--limit=N] [--fq=VAL]
```

### 搜索命令

| 命令 | 描述 |
| --------------- | ---------------------------------------------------------- |
| `search` | 搜索匹配给定模式的单词，支持通配符 `*`（如 `*ough`, `ough*`） |
| `prefix` | 返回包含给定前缀的单词 |
| `suffix` | 返回包含给定后缀的单词 |
| `root` | 返回包含给定词根的单词 |
| `deri_suffix` | 返回包含给定派生后缀的单词 |
| `inf_suffix` | 返回包含给定屈折后缀的单词 |
| `count` | 轻量级计数，仅返回匹配的单词数量 |
| `sample` | 随机采样匹配的结果 |

默认情况下，所有搜索命令都会在合并后的 **umLabeller 和 CityLex 数据集**中进行查询。使用 `source` 参数可以限制只查询其中一个数据集。

> [!TIP]
> `search` 命令支持以下三种通配符 `*` 匹配模式：
> - `*str`（如 `*ough`）— 匹配以 `str` 结尾的单词。
> - `str*`（如 `ough*`）— 匹配以 `str` 开头的单词。
> - `*str*` 或 `str`（如 `*ough*` 或 `ough`）— 匹配在任意位置包含 `str` 的单词（默认模式）。

### 形态学分析命令

| 命令 | 描述 |
| ---------------------- | ------------------------------------------------------------- |
| `morph_seg` / `word` | 返回以 `-` 连接的词素切分字符串 |
| `morph_count` | 返回单词中的词素数量 |
| `word_morph` | 返回完整的形态结构分析（JSON 格式，结合两个数据集） |
| `lemma` | 通过去除屈折后缀返回词元（Lemma） |

### 参数说明

| 参数 | 描述 |
| ---------------- | -------------------------------------------------------------- |
| `source` | `both` (默认) \| `umlabeller` \| `citylex` |
| `seg` | `both` (默认) \| `umlabeller` \| `citylex` |
| `--json` | 输出为 JSON 格式 |
| `--exclude-inf` | 过滤并排除包含屈折后缀（如 -ed, -s, -ing）的结果 |
| `--exclude=S1,S2` | 排除包含任一逗号分隔子串的结果（不区分大小写，支持多个子串） |
| `--exact` | 精确匹配词素而不是模糊子串匹配（仅适用于 `search` 命令） |
| `--limit=N` | 限制返回的结果数量 |
| `--fq=VAL` | 按词频分类过滤（支持多选，逗号分隔）：`high` (>=5.0), `medium` (>=1.0), `low` (>=0.1), `rare` (>0.0), `zero` (==0.0 或 NULL)，或使用快捷选项：`common` (代表 `high,medium` 常用词), `uncommon` (代表 `low,rare,zero` 非常用词)。支持多选（例如 `--fq=common,rare`）。 |

### 词频分类统计 (Word Frequency Tiers)

数据集包含了从 Datamuse 获取并经过缩放的词频数据。可以通过 `--fq` 参数对单词按以下五个词频等级进行过滤：

| 等级 (Category) | 范围 (Condition) | 单词数量 (Count) | 百分比 (Percentage) |
| :--- | :--- | :--- | :--- |
| **high** | `freq >= 5.0` | 21,767 | 3.56% |
| **medium** | `1.0 <= freq < 5.0` | 32,139 | 5.26% |
| **low** | `0.1 <= freq < 1.0` | 84,234 | 13.79% |
| **rare** | `0.0 < freq < 0.1` | 267,661 | 43.80% |
| **zero** | `freq == 0.0` 或 NULL | 205,249 | 33.59% |
| **总计 (Total)** | | **611,050** | **100.00%** |

### 使用示例

```bash
# 搜索包含 "ion" 字符串的词
$ mp search ion
Found 29553 results (source=both, seg=both):
  abbreviation      umlabeller=abbreviate @@ion     citylex={a--bbrevi--ate}>ion>
  abdication        umlabeller=abdicate @@ion       citylex={abdicate}>ion>
  abduction         umlabeller=abduce @@t @@ion     citylex={ab--duct}>ion>
  aberration        umlabeller=aberrate @@ion       citylex={aberr--ate}>ion>
  ... and 29549 more

# 使用通配符搜索（例如查找以 "ough" 结尾的词）
$ mp search *ough
Found 107 results (source=both, seg=both):
  rough             umlabeller=rough                citylex={rough}
  cough             umlabeller=cough                citylex={cough}
  ... and 105 more

# 返回含有前缀 "un" 的词
$ mp prefix un
Found 33987 results (source=both, seg=both):
  unabandoned       umlabeller=un @@abandon @@ed    citylex=
  unabashed         umlabeller=un @@abash @@ed      citylex=
  unable            umlabeller=un @@able            citylex=
  unabridged        umlabeller=un @@abridge @@ed    citylex=
  ... and 33983 more

# 返回含有派生后缀 "able" 的词
$ mp deri_suffix able
Found 7556 results (source=both, seg=both):
  abandonable       umlabeller=abandon @@able       citylex=
  acceptable        umlabeller=accept @@able        citylex=
  accessible        umlabeller=access @@ible        citylex=
  accountable       umlabeller=account @@able       citylex=
  ... and 7552 more

# 获取单词的完整形态结构分析 (JSON)
$ mp word_morph unbelievable --json
{
  "word": "unbelievable",
  "seg": "un-believe-able",
  "prefixes": ["un"],
  "roots": ["believe"],
  "root": "believe",
  "suffixes": ["able"],
  "derivational": ["able"],
  "inflectional": [],
  "base": "believe",
  "lemma": "un-believe-able"
}

# 提取还原词元（去除屈折后缀）
$ mp lemma running
"run"

# 随机采样 3 个词
$ mp sample 3
Found 3 results (source=both, seg=both):
  flagrance         umlabeller=flagrant @@ce        citylex=
  gangway           umlabeller=gang @@way           citylex={gang}{way}
  excorticated      umlabeller=excorticate @@ed     citylex=

# 仅在 CityLex 中查询并输出 JSON
$ mp search ion citylex --json
[{"word": "abacination", "citylex": ""}, {"word": "abalienation", "citylex": ""}, ...]

# 排除含有屈折后缀的匹配结果
$ mp search ion --exclude-inf
Found 19252 results (source=both, seg=both, exclude_inf):
  abbreviation      umlabeller=abbreviate @@ion     citylex={a--bbrevi--ate}>ion>
  abdication        umlabeller=abdicate @@ion       citylex={abdicate}>ion>
  abduction         umlabeller=abduce @@t @@ion     citylex={ab--duct}>ion>
  aberration        umlabeller=aberrate @@ion       citylex={aberr--ate}>ion>
  ... and 19248 more

# 排除包含特定子串的词（例如搜索 'ough' 但排除 'ought' 干扰）
$ mp search ough --exclude=ought
Found 362 results (source=both, seg=both, exclude=ought):
  rough             umlabeller=rough                citylex={rough}
  tough             umlabeller=tough                citylex={tough}
  ... and 360 more

# 精确词素搜索（匹配精确词素，而不是模糊子串）
$ mp search ch --exact
Found 8 results (source=both, seg=both, exact):
  chad              umlabeller=ch @@have @@ed       citylex={chad}
  cham              umlabeller=ch @@am              citylex=
  ... and 6 more

# 按词频过滤结果（例如：搜索 "ion" 词素，但仅返回高词频词汇）
$ mp search ion --fq=high --limit=3
Found 2782 results (source=both, seg=both, fq=high, limit=3):
  abolition                       umlabeller=abolish @@ion                        citylex={abolish}>ion>                    fq=5.33
  abortion                        umlabeller=abort @@ion                          citylex={abort}>ion>                      fq=9.94
  absorption                      umlabeller=absorb @@t @@ion                     citylex={absorb}>t>ion>                   fq=15.02
```

## Python API

```python
from morphoneme import MP

mp = MP()

# 以下所有搜索方法都是基于词素索引关系表的快速精确查询
results = mp.search("ion")                      # 模糊查询所有字段
results = mp.words_with_prefix("un")            # 查询指定前缀
results = mp.words_with_suffix("ing")           # 查询指定后缀
results = mp.words_with_root("believe")         # 查询指定词根
results = mp.words_with_deri("able")            # 查询指定派生后缀
results = mp.words_with_inf("ed")               # 查询指定屈折后缀

# 形态学分析
seg = mp.morph_seg("unbelievable")   # → "un-believe-able"
count = mp.morph_count("running")    # → 2
morph = mp.word_morph("cats")        # → 结构字典 (dict)
lemma = mp.lemma("running")          # → "run"

# 批量处理（高度优化，走单次 SQL IN 批量预取）
mp.batch_words("words.txt", mode="morph", fmt="csv")

# 轻量级计数
n = mp.word_count("ion")

# 随机采样
samples = mp.sample(10)
```

### `word_morph()` 返回字典结构

```python
{
    "word": "unbelievable",
    "seg": "un-believe-able",
    "prefixes": ["un"],
    "roots": ["believe"],
    "root": "believe",
    "suffixes": ["able"],
    "derivational": ["able"],
    "inflectional": [],
    "base": "believe",
    "lemma": "un-believe-able"
}
```

## 批量处理 (Batch Processing)

从文件批量读取单词并输出为 JSON 或 CSV 报告：

```python
mp.batch_words("words.txt", mode="seg", fmt="json")
mp.batch_words("words.txt", mode="morph", fmt="csv")
mp.batch_words("words.txt", mode="morph:ai", fmt="json")  # 附加 AI 规则校验
```

输入文件格式：每行一个单词，以 `#` 开头的行视为注释。

## 屈折后缀配置 (Inflectional Suffixes)

本工具的屈折后缀列表存放在 `morphoneme/inf_suffixes.txt` 中，每行一个后缀（支持带 `-` 前缀）。默认配置包括：

```
-s
-ed
-ing
-en
-est
-es
```

使用 `--exclude-inf` 时，会根据此列表过滤掉含有这些后缀的词。如果该文件缺失，CLI 在运行时会提示自动生成默认后缀列表。

# 为什么叫“语义别名” (Semantic Aliases)？

在 `morphoneme` 中，命令行中的 `prefix`、`suffix` 和 `root` 指令（以及 Python API 对应的同名方法）在概念上是通用 `search` 命令的**语义化别名**。在底层，它们现在会通过关系表 `word_morphemes` 进行针对性索引查询，以提供极速、精准的结构定位。

设置别名提供了更符合人类直觉的交互入口（如 `mp prefix un` 比模糊搜索更精确易读）。

### 与 Datamuse, Webster, 和 OneLook 的区别

使用 `morphoneme` 进行查询与使用在线的 **Datamuse API**、**Merriam-Webster** 或 **OneLook** 进行通配符或子串搜索有着本质的区别：

#### 1. 词素级匹配 vs. 纯拼写匹配
* **Datamuse / Webster / OneLook:** 这些平台纯粹基于**单词的拼写字面量**进行匹配。如果您搜索以 `ion` 结尾的单词（如使用 `*ion`），只要拼写是这几个字母结尾的单词都会被返回。
  * *噪音干扰 (Spurious Hits):* 搜索后缀 `ion` 会返回像 *onion* (洋葱), *cushion* (垫子), *lion* (狮子), *million* (百万) 这样的词，因为 `ion` 在这些词中只是词根拼写的一部分，并不是真正的后缀。同理，搜索前缀 `un*` 会混入 *uncle* 或 *unit*。
* **morphoneme:** 查询的是数据库中的**词素切分标注数据列**。
  * *精准匹配:* 搜索前缀 `un` 只会匹配 `un` 被标注为前缀的单词（例如 `un @@abandon`），避免了拼写干扰。
  * *极大降噪:* 虽然标注列检索也不能确保 100% 正确（因为底层的学术数据集是由不同研究团队人工及算法整理，存在微小的标注不一致），但它和拼写匹配有本质区别：
    * *传统字面匹配的噪声* 像是**令人抓狂的刺耳轰鸣**（混入数以百计的不相干词汇）。
    * *morphoneme 的噪声* 仅属于学术标注数据集的小瑕疵，相对而言就像是**窗外树梢上小鸟的清脆叫声**。

#### 2. 本地数据库 vs. 外部 Web API
* **Datamuse / Webster / OneLook:** 都是在线服务。调用它们需要发起 HTTP 网络请求，这会引入网络延迟、受到频率限制、依赖网络环境，并且可能需要注册 API Key。
* **morphoneme:** 完全**在本地运行**，自带预编译好的 SQLite 数据库。它不需要联网，查询在不到一毫秒内即可执行完毕，非常适合十万级词单的批量计算。

#### 3. 结构化形态学输出
* **Datamuse / Webster / OneLook:** 仅返回释义、同义词或单词列表，无法返回单词的内在词法构成。
* **morphoneme:** 提供完整的单词形态结构剖析。能够拆分并分类前缀、词根、派生后缀和屈折后缀，使用户轻松获取词元并分析结构。

## 项目结构

```
morphoneme/
├── morphoneme/                 # Python 源码包 (发布至 PyPI)
│   ├── __init__.py
│   ├── __main__.py              # CLI 命令行入口
│   ├── mp.py                    # 核心 MP 类
│   ├── morphoneme.db           # SQLite 本地数据库 (自动下载或本地生成)
│   └── inf_suffixes.txt         # 屈折后缀配置列表
├── data/
│   ├── citylex-2026-06-15_morphology_segmention.tsv      # CityLex 原始数据 (~6.8万行)
│   ├── eng.word.full.230613.r7_morphologic_division.tsv  # umLabeller 原始数据 (~61.1万行)
│   └── morphoneme.tsv           # 合并后的中间 TSV (构建数据库的源文件)
├── scripts/
│   └── build_morphoneme_db.py  # 从 TSV 构建 SQLite 数据库的脚本
├── tests/
│   ├── __init__.py
│   └── test_mp.py
├── pyproject.toml
├── Makefile
├── requirements.txt
├── LICENSE
└── README.md
```

## 未来规划 (Roadmap)

我们计划在未来的版本中支持以下特性：

- **词频数据集成 (Word Frequency Integration)**：整合基于语料库的词频指标（如 COCA, Google Web 1T 或 Subtlex），以支持按词汇常用度对搜索结果进行排序和筛选。
- **词性支持 (Part-of-Speech Support)**：集成词性标签（名词、动词、形容词等），支持根据句法类别筛选词汇。
- **国际音标与发音及音节标注 (IPA, Phonetic Transcriptions & Syllables)**：
  - **国际音标 (IPA)**：提供标准音标以便发音查询。
  - **ARPAbet / CMUDict 支持**：支持机器可读的音素转换（如通过 `S T ER1` 序列表示 ARPAbet 音素）。
  - **音节度量**：添加音节数量和音节划分细节（含重音位置）。
  - **专业音标标注**：支持更深入的严式音标（narrow transcription）和区域方言发音（如 DJ/KK 音标）。
- **词源与历史演变 (Etymology & Word Origins)**：
  - **中英文双语词源 (Bilingual Etymological Data)**：提供英语单词的词源背景与历史演变过程，支持中英文双语对照（如来源语种、历史语义演变及同源词关系）。
- **单词释义与解释 (Definitions & Explanations)**：
  - **中英文双语释义**：整合精简的中英文双语词汇释义，方便在查询词素/词根的同时快速了解词意，作为一个快速、全面的双语词汇学习工具。

## 反馈与建议

如果您有任何功能建议、Bug 反馈或咨询，欢迎在 [GitHub Issues](https://github.com/connoryang331/morphoneme/issues) 页面提交。

## 开源协议

MIT

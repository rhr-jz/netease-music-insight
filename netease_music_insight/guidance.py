"""Small, independent AI tasks generated from the data actually exported."""
from dataclasses import dataclass

from .utils import atomic_text


@dataclass(frozen=True)
class Topic:
    number: int
    title: str
    question: str
    scope: str
    task: str
    network: str = "不需要"
    depth: str = "中等"

    @property
    def filename(self):
        return f"{self.number:02d}_{self.title}.md"


TOPICS = (
    Topic(1, "音乐全景画像", "我到底是一个怎样的听歌人？",
          "收藏结构、常见歌手与专辑、语言、类型、年代、可用的播放数据和审美分支",
          "从整体数据结构开始，依次分析高频歌手和专辑、语言、类型、情绪、歌曲年代、收藏与可用播放记录的关系、歌手集中度、单曲或专辑倾向、核心审美与兴趣分支。没有元数据支持的类型、年代和情绪只能谨慎推测。最后用一句话概括我的音乐画像。"),
    Topic(2, "真实音乐审美", "我究竟喜欢什么，可能为什么喜欢？",
          "核心、稳定与阶段偏好；旋律、人声、歌词、节奏、氛围与编曲",
          "区分核心审美、稳定偏好、阶段性偏好、怀旧、功能性音乐、网络热歌、情绪性和偶然收藏。结合具体歌曲讨论旋律、人声、歌词、节奏、氛围、制作、编曲、故事感与情绪；若仅凭标题或歌手无法判断，请明确说需要试听，不要假装听过歌曲。"),
    Topic(3, "真正喜欢的歌手", "哪些歌手对我最重要？",
          "核心歌手、潜力歌手、单曲型与历史型歌手",
          "结合喜欢歌曲、歌单分布、可用播放次数和同一歌手的不同作品，识别核心歌手、潜力歌手、单曲型及历史型歌手。不要只按收藏歌曲数排 Top 10；说明每项判断的证据和缺口。"),
    Topic(4, "听歌行为和习惯", "我是怎样发现和反复听音乐的？",
          "收藏与播放的关系、歌手或歌单驱动、场景使用",
          "分析我可能是歌手、单曲、歌单、场景或怀旧驱动型，比较收藏与实际可用播放记录是否一致。只有数据直接支持时才判断推荐算法依赖或主动搜索；播放历史缺失时，不要将空列表解释为从未听过。"),
    Topic(5, "音乐成长轨迹", "我的音乐兴趣如何随时间变化？",
          "有可靠时间字段的收藏与歌单变化",
          "仅使用实际存在的歌曲收藏时间、歌单创建时间或收藏时间梳理兴趣变化。可尝试讨论童年、中学、高中、大学和最近时期，但只有时间与年龄证据足够时才能对应人生阶段；否则只谈数据中的较早和较近阶段。收藏排序时间不能当作首次收藏日期。"),
    Topic(6, "个人音乐地图", "我可以沿着什么路线探索音乐？",
          "核心审美 → 已有领域 → 邻近领域 → 值得探索 → 陌生领域",
          "根据我的真实歌曲和歌手建立个人音乐地图：核心审美、已有领域、邻近领域、值得探索和完全陌生的领域。每条路线都说明起点证据和相邻原因，给出少量歌曲或专辑入口；外部推荐若无法核实，应标为待核实。",
          network="推荐开启"),
    Topic(7, "音乐盲区", "有哪些离我很近、却还没听过的音乐？",
          "低门槛、中等跨度与挑战型探索",
          "从已有偏好向外走一到两步，分别给出低门槛、中等跨度和挑战型路线。每条按已有喜欢 → 邻近风格 → 歌手 → 歌曲 → 专辑展示，不要机械地因为我没有某个类型就推荐它。外部作品请核实名称和来源。",
          network="推荐开启"),
    Topic(8, "音乐社交谈资", "怎样和朋友或同龄人自然聊音乐？",
          "值得认识的音乐人、作品与可以聊的话题",
          "结合我的兴趣，若能联网，请查询当前中国年轻人的音乐文化，并标注来源及日期；覆盖流行、乐队、Hip-Hop、R&B、Indie、音乐节、Livehouse、专辑或综艺中与我相关的方向。推荐 10–15 位值得认识的音乐人，每位说明是谁、风格、相关原因、三首入口歌、一张代表专辑和一个聊天话题。不能联网时明确时效限制，不编造当前热度。",
          network="建议开启", depth="较深入"),
    Topic(9, "系统听歌计划", "怎样轻松地养成更丰富的听歌习惯？",
          "八周探索计划，每周三次、每次 20–30 分钟",
          "为我设计轻松的 8 周计划：约 70% 熟悉喜欢、20% 邻近探索、10% 陌生音乐；每周约三次主动听歌，每次 20–30 分钟，可听 3–6 首歌或一张专辑。兼顾歌手、专辑与自由探索，不要求每天打卡，不把娱乐变成学习任务。",
          network="推荐开启"),
    Topic(10, "歌单整理建议", "我的歌单怎样整理会更好用？",
          "重复、过大或主题模糊的歌单；保留、合并、拆分和归档",
          "检查重复、过大、主题模糊和功能性歌单，结合歌曲重合度与歌单名称建议保留、合并、拆分或归档。区分我创建与我收藏的他人歌单。只给建议，不执行删除或声称已经修改我的账号。"),
    Topic(11, "情绪与音乐", "哪些音乐适合我的不同心情和场景？",
          "开心、怀旧、放松、学习、睡眠等轻量场景",
          "把数据中有充分依据的歌曲按开心、孤独、怀旧、热血、学习、睡眠和放松等场景做轻量整理，并解释选择依据。无法从元数据确认歌曲情绪时说明需要试听。不要进行心理疾病或人格诊断，也不要因伤感歌曲多就推断抑郁。"),
    Topic(12, "年度音乐总结", "今年的音乐记忆可以怎样回顾？",
          "可靠年份中的歌手、歌曲、专辑与探索方向",
          "制作个人年度音乐回顾，列出有可靠年份证据的歌手、歌曲、专辑、风格、关键词与探索方向。区分收藏时间、歌单时间和播放时间；若数据不能精确按年统计，就明确写出限制，只做不带虚构年份的回顾。"),
    Topic(13, "网易云与QQ音乐跨平台对比", "两个平台上的我有哪些相同和不同？",
          "共同歌手与歌曲、各平台独有偏好、可能的使用场景",
          "比较网易云和 QQ 音乐的喜欢歌曲、自建与收藏歌单、重合歌手和高置信匹配作品，以及各平台独有的方向。区分平台算法、使用场景和数据覆盖差异；平台不同不等于人格不同。QQ 播放历史不可用，不能据此判断我在 QQ 不听歌。"),
)


def available_topics(data, *, combined=False):
    platforms = list(data.get("platforms", {}).values()) if combined else [data]
    has_time = any(any((d.get("statistics") or {}).get(key, 0) for key in (
        "liked_songs_with_time", "playlists_with_creation_time", "playlists_with_subscription_time"))
        for d in platforms)
    has_playlists = any((d.get("statistics") or {}).get("playlist_count", 0) for d in platforms)
    return [topic for topic in TOPICS if
            (topic.number != 13 or combined) and
            (topic.number not in (5, 12) or has_time) and
            (topic.number != 10 or has_playlists)]


def prompt_for(topic, *, combined=False):
    filename = "music_for_ai_combined.json" if combined else "music_for_ai.json"
    return (f"请完整读取我上传的 {filename}。\n"
            "请先检查导出状态、数据缺口及各平台实际可用的字段，尽量覆盖完整文件，不要只看前几十首歌。"
            "用中文回答；把数据明确支持的结论、较强推测和待验证的假设分开，引用具体歌曲、歌手或歌单作为证据。"
            "收藏数量不等于喜欢程度，收藏歌单也不代表听过每首歌；不要凭少量歌曲推断人格。"
            "时间为空就说未知，不要按列表顺序推断日期。QQ 的 favorite_order_at 只是收藏排序时间。"
            "播放历史不存在或范围有限时，不要虚构播放次数或听歌时间。\n\n"
            f"我的问题：{topic.question}\n"
            f"具体任务：{topic.task}\n"
            "请以易读的小标题组织结果，先说明数据依据与限制，再给出分析和少量可行动建议。")


def guide_markdown(data, *, combined=False):
    filename = "music_for_ai_combined.json" if combined else "music_for_ai.json"
    topics = available_topics(data, combined=combined)
    intro = [
        "# 🎧 我的音乐 AI 分析指南", "", "你的音乐数据已经准备好了。ChatGPT、Claude、Gemini，或其他支持文件上传的 AI 都可以使用。", "",
        "## 只需四步", "", f"1. 打开你常用的 AI，上传本文件夹中的 `{filename}`。",
        "2. 从下方选择一个感兴趣的问题。", "3. 复制该模块的完整提示词并发送。", "4. 对结果有疑问时，让 AI 指出对应的歌曲或歌单证据。", "",
        "第一次用，推荐先看 **01 音乐全景画像**。每个提示词都能单独使用，不用按顺序做完。", "",
        "## 怎么选", "", "- 想轻松看看：全景画像 → 年度总结（如有时间数据）→ 音乐社交谈资。",
        "- 想认真培养审美：真实音乐审美 → 音乐地图 → 音乐盲区 → 系统听歌计划。",
        "- 想了解自己：全景画像 → 真实音乐审美 → 真正喜欢的歌手 → 音乐地图 → 系统听歌计划。", "",
        "建议选择支持文件上传和较长上下文的 AI。音乐推荐与当下谈资需要核实外部信息时，可开启联网。上传前请确认你愿意把个人音乐数据交给所选 AI 服务。", "",
        "## 分析方向", "",
    ]
    for topic in topics:
        intro.append(f"- [{topic.number:02d} {topic.title}](#{topic.number:02d}-{topic.title})：{topic.question}")
    intro.append("")
    if not any(t.number == 5 for t in topics):
        intro += ["当前没有可靠的收藏或歌单时间，已隐藏成长轨迹与年度统计方向。", ""]
    if not combined:
        intro += ["跨平台比较仅在两个平台都成功导出并生成联合数据时显示。", ""]
    for topic in topics:
        intro += [f"## {topic.number:02d} {topic.title}", "", "### 适合你，如果你想知道", "", topic.question,
                  "", "### AI 会帮你分析", "", topic.scope, "",
                  f"联网：{topic.network} · 分析深度：{topic.depth}", "", "### 复制下面的 Prompt", "",
                  "```text", prompt_for(topic, combined=combined), "```", ""]
    return "\n".join(intro)


def write_guidance(folder, data, *, combined=False):
    topics = available_topics(data, combined=combined)
    selected = {topic.number for topic in topics}
    for topic in TOPICS:
        if topic.number not in selected:
            (folder / "prompts" / topic.filename).unlink(missing_ok=True)
    atomic_text(folder / "AI_ANALYSIS_GUIDE.md", guide_markdown(data, combined=combined))
    for topic in topics:
        atomic_text(folder / "prompts" / topic.filename,
                    f"# {topic.number:02d} {topic.title}\n\n联网：{topic.network} · 分析深度：{topic.depth}\n\n"
                    f"{prompt_for(topic, combined=combined)}\n")
    return topics

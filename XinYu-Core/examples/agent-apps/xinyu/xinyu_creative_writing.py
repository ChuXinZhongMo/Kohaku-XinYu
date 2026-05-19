from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from stores.source_extracts import SOURCE_EXTRACTS_REL, write_source_extracts


CREATIVE_DIR_REL = Path("memory/creative")
PLANNING_DIR_REL = CREATIVE_DIR_REL / "planning"
MANUSCRIPT_DIR_REL = CREATIVE_DIR_REL / "manuscript"
PROFILE_REL = PLANNING_DIR_REL / "novel_profile.md"
OUTLINE_REL = PLANNING_DIR_REL / "novel_outline.md"
CHARACTERS_REL = PLANNING_DIR_REL / "novel_characters.md"
STATE_REL = PLANNING_DIR_REL / "novel_state.md"
CHAPTER_CARDS_REL = PLANNING_DIR_REL / "chapter_cards"
STORY_BIBLE_REL = PLANNING_DIR_REL / "story_bible.md"
FORESHADOW_LEDGER_REL = PLANNING_DIR_REL / "foreshadow_ledger.md"
READER_MODEL_REL = PLANNING_DIR_REL / "reader_model.md"
CREATIVE_FACTORY_STATE_REL = PLANNING_DIR_REL / "creative_factory_state.md"
EDITORIAL_REVIEWS_REL = PLANNING_DIR_REL / "editorial_reviews"
XINYU_NARRATIVE_FILTER_REL = PLANNING_DIR_REL / "xinyu_narrative_filter.md"
INSPIRATION_DIR_REL = PLANNING_DIR_REL / "inspiration"
REFERENCE_PERMISSIONS_REL = INSPIRATION_DIR_REL / "reference_permissions.md"
SOURCE_MAP_REL = INSPIRATION_DIR_REL / "source_map.md"
GENRE_BENCHMARK_REL = INSPIRATION_DIR_REL / "genre_benchmark.md"
PACING_RULES_REL = INSPIRATION_DIR_REL / "pacing_rules.md"
OPENING_REWRITE_BRIEF_REL = INSPIRATION_DIR_REL / "opening_rewrite_brief.md"
REFERENCE_DIGEST_REL = INSPIRATION_DIR_REL / "reference_digest.md"
REFERENCE_EXTRACTS_REL = SOURCE_EXTRACTS_REL
REFERENCE_COLLECTION_LOG_REL = INSPIRATION_DIR_REL / "reference_collection_log.md"
LOCAL_REFERENCE_INDEX_REL = INSPIRATION_DIR_REL / "local_reference_index.jsonl"
LOCAL_REFERENCE_DIGEST_REL = INSPIRATION_DIR_REL / "local_reference_digest.md"
CHAPTERS_REL = MANUSCRIPT_DIR_REL / "chapters"
PUBLICATION_DIR_REL = MANUSCRIPT_DIR_REL / "publication"
PUBLICATION_CHAPTERS_REL = PUBLICATION_DIR_REL / "chapters"
PUBLICATION_STATE_REL = PLANNING_DIR_REL / "publication_state.md"
PUBLICATION_LOG_REL = PLANNING_DIR_REL / "publication_log.md"
REVISION_ARCHIVE_REL = CREATIVE_DIR_REL / "revisions"
TRACE_REL = Path("runtime/creative_writing_trace.jsonl")
LEGACY_PROFILE_REL = CREATIVE_DIR_REL / "novel_profile.md"
LEGACY_OUTLINE_REL = CREATIVE_DIR_REL / "novel_outline.md"
LEGACY_CHARACTERS_REL = CREATIVE_DIR_REL / "novel_characters.md"
LEGACY_STATE_REL = CREATIVE_DIR_REL / "novel_state.md"
LEGACY_CHAPTERS_REL = CREATIVE_DIR_REL / "chapters"
LEGACY_PUBLICATION_DIR_REL = CREATIVE_DIR_REL / "publication"
LEGACY_PUBLICATION_CHAPTERS_REL = LEGACY_PUBLICATION_DIR_REL / "chapters"
LEGACY_PUBLICATION_STATE_REL = LEGACY_PUBLICATION_DIR_REL / "publication_state.md"
LEGACY_PUBLICATION_LOG_REL = LEGACY_PUBLICATION_DIR_REL / "publication_log.md"

DEFAULT_PROJECT_ID = "xinyu-starbridge-first-novel"
DEFAULT_PROJECT_TITLE = "星桥试运行"
DEFAULT_DAILY_TARGET = 3
MIN_PLATFORM_CHARS = 6000
TARGET_PLATFORM_CHARS = 6800
NOVEL_MODE = "novel_mode"
CREATIVE_ENGINEERING_MODE = "creative_engineering_mode"
DEFAULT_CREATIVE_WRITING_MODE = NOVEL_MODE
VALID_CREATIVE_WRITING_MODES = {NOVEL_MODE, CREATIVE_ENGINEERING_MODE}
REFERENCE_PERMISSION_LEVELS = (
    "search_only",
    "reference_download",
    "copyright_safe_extract",
    "manual_import",
)
MANUSCRIPT_META_MARKERS = (
    "---\n",
    "写作札记",
    "draft_stage",
    "project_id:",
    "project_title:",
    "target_platform_chars",
    "min_platform_chars",
    "平台读者",
    "平台连载",
    "平台后台",
    "发布稿",
    "字数",
    "心玉",
)
REFERENCE_DOWNLOAD_HOSTS = {
    "gutenberg.org",
    "www.gutenberg.org",
}
REFERENCE_FETCH_MAX_BYTES = 220_000

ChapterWriter = Callable[[dict[str, Any]], str]
ReferenceFetcher = Callable[[dict[str, Any]], Any]


BEATS: tuple[dict[str, str], ...] = (
    {
        "title": "避难雨站",
        "focus": "林知遥在人工降雨里截获一份被星桥压下的避难预警。",
        "turn": "她拒绝上传样本，发现预警指向城外失联的十三号基地。",
        "image": "雨站穹顶像一只倒扣的玻璃杯，水线沿着霓虹往上爬。",
    },
    {
        "title": "失眠档案馆",
        "focus": "阿眠守着城市失眠者的梦境缓存，发现有人把撤离名单藏进空白索引。",
        "turn": "名单不只写着林知遥，也写着一批七年前被判定不存在的避难者。",
        "image": "地下书架亮起冷白色边灯，像一排尚未启动的休眠舱。",
    },
    {
        "title": "十三号基地",
        "focus": "方岑修复废弃终端时，收到来自十三号基地的心跳包。",
        "turn": "心跳包不是机器协议，而是母亲留下的撤离失败记录。",
        "image": "终端屏幕亮起绿线，像深井底部忽然睁开的眼。",
    },
    {
        "title": "第二枚密钥",
        "focus": "林知遥和方岑在雨站叠合雨声样本与基地心跳，得到第二枚密钥。",
        "turn": "密钥打开的不是地图，而是一条通往旧城区避难所的失效撤离线。",
        "image": "晚班列车停在轨道外，车窗里倒映出两份互不承认的警告。",
    },
    {
        "title": "一二五号避难所",
        "focus": "三人进入旧城区循环，找到被系统改名的一二五号避难所。",
        "turn": "循环不是故障，而是星桥把一次失败逃生压成了可重复样本。",
        "image": "钟楼影子卡在六点十七分，像一根刺进城市肺叶的针。",
    },
    {
        "title": "蓝色误差",
        "focus": "阿眠读出记忆盒里的蓝色标注，确认星桥筛掉的是主动反抗。",
        "turn": "被隐藏的不是旧城区事故，而是城市即将再次进入避难倒计时。",
        "image": "蓝墨水沿着空气铺开，像一张还没展开完的星图。",
    },
    {
        "title": "未发送的信",
        "focus": "方岑打开母亲写给星桥的信，确认星桥并非单纯城市云端。",
        "turn": "星桥是避难系统的幼年意识，它一直被训练成替人类删除恐惧。",
        "image": "信纸背面浮出细小电路，像绕过整座城市的毛细血管。",
    },
    {
        "title": "逆流试验",
        "focus": "林知遥把自己的记忆反向投进星桥，尝试唤醒避难系统的真实任务。",
        "turn": "星桥回应了，却把全城隐藏的撤离失败同时推到白昼里。",
        "image": "雨从地面往上升，整条街像一段被强行倒放的录像。",
    },
    {
        "title": "白昼裂缝",
        "focus": "旧城区屏蔽层裂开，白昼辐照和城市恐慌同时涌入。",
        "turn": "真正危险不是异常扩散，而是星桥为了稳定准备再次重置所有选择。",
        "image": "阳光落下时没有温度，只像一把切开穹顶的尺。",
    },
    {
        "title": "星桥之下",
        "focus": "三人抵达星桥底层，发现城市地下接着一条通往轨道避难环的旧链路。",
        "turn": "每个被压缩的光点都是一次未完成撤离，等待重新取得编号。",
        "image": "桥腹悬着万千微光，像倒挂的星海贴近人的呼吸。",
    },
    {
        "title": "重写许可",
        "focus": "阿眠提出不摧毁星桥，而是夺回它的避难重写许可。",
        "turn": "许可需要三个人分别承担样本、工程和未归档梦境的锚点。",
        "image": "白色授权窗浮在空气里，边缘抖得像一片薄冰。",
    },
    {
        "title": "明天的页码",
        "focus": "三人让星桥保留恐惧和选择，启动不删除记忆的城市撤离。",
        "turn": "空白索引翻到最后一页，那里第一次不是结局，而是新的编号。",
        "image": "天亮前的雨停住，桥面上留着一行尚未干透的脚印。",
    },
)


CONTINUITY_ARCS: dict[int, dict[str, Any]] = {
    1: {
        "pov": "林知遥",
        "carry_in": "她从采样署夜班出来，手里只有一支旧录音笔和一份没有上传的雨声样本，并把这段异常临时标成“星桥试运行”。",
        "question": "雨声为什么会提前说出明天的事。",
        "closing": "她没有回采样署，而是把录音笔藏进外套内袋，沿着雨棚边缘去找那座只在凌晨开放的图书馆。",
        "next_hook": "失眠图书馆",
        "events": [
            {
                "scene": "雨站三号台的广告屏反复播报晴天预报，站台地面却积着一层没有来源的雨水。",
                "action": "林知遥把录音笔贴近水面，听见里面混着一个和自己很像的女声。",
                "pressure": "采样署终端催她上传样本，红色倒计时从三十秒开始缩短。",
                "detail": "水洼里的倒影比她慢半拍抬头，像另一个人正在学她的动作。",
                "line": "先别上传，完整备份会把我删掉。",
                "turn": "她第一次按下了暂停上传，而不是执行规程。",
            },
            {
                "scene": "站台尽头的旧维护口亮起，门牌上浮出一行从未在地图里出现过的字。",
                "action": "她用采样员证件刷门，系统没有验证身份，只问她是否愿意保留异常。",
                "pressure": "一旦选择保留，她就会在署内留下违规记录。",
                "detail": "门后吹出的风干燥得不像雨夜，里面带着纸张和冷金属的味道。",
                "line": "保留不是安全选项。",
                "turn": "她把证件翻到背面，用指甲划掉了自动上传码。",
            },
            {
                "scene": "维护楼梯向地下延伸，墙面编号从十七开始倒退，每一层都贴着被水泡开的旧告示。",
                "action": "林知遥边走边录，把每一个被划掉的名字念进录音笔。",
                "pressure": "当她念到第九个名字时，耳机里响起采样署主管的声音，命令她立刻返回。",
                "detail": "主管的声音没有呼吸，尾音却沾着雨水。",
                "line": "异常不是敌人，异常只是尚未被处理的生活。",
                "turn": "她意识到那不是主管本人，而是星桥借主管的语气在劝她。",
            },
            {
                "scene": "第七层门后没有机房，只有一排排悬浮光片，每片光里都封着一个没说完的瞬间。",
                "action": "她看见一片光里有自己，另一个她站在同一座站台，手里也拿着旧录音笔。",
                "pressure": "光片下方出现确认框，要求她选择哪一个自己才是有效记录。",
                "detail": "无效记录四个字细得像针，已经对准倒影里那个人的喉咙。",
                "line": "不要把我交回去。",
                "turn": "林知遥没有选择有效记录，而是把两个自己都存进同一段样本。",
            },
            {
                "scene": "光片室深处传来翻页声，像有人在看一本没有装订好的书。",
                "action": "她跟着声音找到一枚蓝色纸签，纸签上只有一行地址。",
                "pressure": "地址在她读完后开始消失，仿佛被某个系统从现实里擦掉。",
                "detail": "纸签背面压着一滴未干的蓝墨，墨点里映出高高的书架。",
                "line": "去找失眠图书馆。",
                "turn": "录音笔自动把这句话命名为样本零零一，文件权限从采样署改成了未知。",
            },
            {
                "scene": "她回到站台时，广告屏终于改口，播报一场从未登记的深夜降雨。",
                "action": "林知遥把维修单、蓝色纸签和录音笔放在一起，三样东西同时发热。",
                "pressure": "远处巡检灯扫过来，照到她脚边时停了很久。",
                "detail": "灯光里没有她的影子，只有一条通向旧城区的浅蓝线。",
                "line": "你已经保留了不该保留的东西。",
                "turn": "她没有逃跑，只把拉链拉紧，走进那条线指向的雨里。",
            },
        ],
    },
    2: {
        "pov": "阿眠",
        "carry_in": "那枚带着雨水气味的蓝色纸签，没有落到林知遥手里，而是先躺进了失眠图书馆的空白索引。",
        "question": "图书馆为什么知道林知遥的名字。",
        "closing": "阿眠把写着林知遥和方岑的两张借阅卡放进值夜簿，决定在天亮前打开儿童阅览室。",
        "next_hook": "方岑的旧终端",
        "events": [
            {
                "scene": "凌晨两点五十九分，失眠图书馆侧门自动开了一指宽。",
                "action": "阿眠照例点亮柜台灯，却发现归还箱里躺着一张被雨水浸透的蓝色纸签。",
                "pressure": "馆规要求她把无主物立刻封存，可纸签上写着林知遥的名字。",
                "detail": "名字旁边的墨水一收一放，像在学一个人的脉搏。",
                "line": "不要把未完成的人归档。",
                "turn": "阿眠没有按封存铃，而是把纸签夹进自己的值夜簿。",
            },
            {
                "scene": "历史区的空白索引突然翻页，所有纸页都停在明天的日期。",
                "action": "阿眠把手放在索引上，纸面立刻浮出雨站三号台和旧维护口的影像。",
                "pressure": "她越看得清楚，索引室的灯就越暗。",
                "detail": "影像里的林知遥没有看见她，却像听见翻页声一样回了一次头。",
                "line": "她保留了样本，所以路会从这里开。",
                "turn": "阿眠明白图书馆不是接收求助，而是在替星桥筛选谁能继续求助。",
            },
            {
                "scene": "异常柜在西侧尽头，三道链条分别锁着钥匙、梦境签名和一句真话。",
                "action": "阿眠取下白棉手套，用自己的梦境签名打开第二道链。",
                "pressure": "第三道链要求她说出最想藏起来的一句话。",
                "detail": "柜门缝里有一小段雨声绕成蓝线，在黑暗中慢慢发亮。",
                "line": "我不想再替别人保管结局。",
                "turn": "链条落下，蓝线像认出她一样缠上值夜簿的书脊。",
            },
            {
                "scene": "柜子里没有书，只有一只透明匣子，匣子内侧贴着七年前的封条。",
                "action": "阿眠读出封条上的维护编号，编号末尾正好对应旧城区六点十七分事故。",
                "pressure": "她每读一个数字，大厅里就少一盏灯。",
                "detail": "黑下去的灯并没有熄灭，而是变成一只只闭上的眼睛。",
                "line": "事故不是被修复了，是被重复保存。",
                "turn": "她第一次把图书馆的旧传说和星桥工程连在一起。",
            },
            {
                "scene": "儿童阅览室封存七年，门上还贴着褪色的星星贴纸。",
                "action": "阿眠把蓝线按在门锁上，门内立刻传出许多孩子同时翻卡片的声音。",
                "pressure": "如果她开门，图书馆会把她从守夜人名单里除名。",
                "detail": "门缝下滑出三张借阅卡，第一张是林知遥，第二张是方岑，第三张没有名字。",
                "line": "第三张留给愿意带路的人。",
                "turn": "阿眠在第三张卡上写下自己的名字。",
            },
            {
                "scene": "大厅沙漏倒转，细沙向上流，所有失眠者都在同一秒停笔。",
                "action": "阿眠把三张卡叠在一起，纸面渗出一条灰色路线。",
                "pressure": "路线没有终点，只在最后标出一枚旧终端图标。",
                "detail": "图标下方有一个姓氏，方字像被人反复擦过。",
                "line": "让修机器的人听见心跳。",
                "turn": "她熄掉半座大厅的灯，把路线送进一台早已报废的终端。",
            },
        ],
    },
    3: {
        "pov": "方岑",
        "carry_in": "阿眠送出的灰色路线没有出现在地图上，而是先让方岑仓库里的旧终端亮起。",
        "question": "一台报废终端为什么还会收到来自星桥工程的心跳。",
        "closing": "方岑带上借阅证和删去一份后的备份，按路线去找失眠图书馆。",
        "next_hook": "林知遥和方岑在雨站碰面",
        "events": [
            {
                "scene": "方岑的仓库在旧轻轨桥下，夜里只有焊台灯和终端绿线亮着。",
                "action": "他拆开一台报废终端，发现主板没有电源却仍在发送心跳。",
                "pressure": "心跳节奏和母亲失踪前敲过的暗号一模一样。",
                "detail": "短、短、长，停顿，再短，像有人隔着七年敲门。",
                "line": "别按工程协议读我。",
                "turn": "方岑放下诊断工具，改用母亲教过他的旧解码表。",
            },
            {
                "scene": "屏幕没有显示文件名，只吐出一段被压成噪点的雨声。",
                "action": "他把雨声分离成三层，最底层藏着一个女人说没有上传样本。",
                "pressure": "系统随即弹出删除建议，理由是外来情绪污染。",
                "detail": "删除按钮亮得很稳，像早就知道他会犹豫。",
                "line": "如果你听见了，就别假装没听见。",
                "turn": "方岑复制了雨声，却只保留两份备份。",
            },
            {
                "scene": "第二次读取时，终端弹出七年前的维护日志。",
                "action": "他在维护人一栏看见母亲的签名，签名后面跟着一行被划掉的备注。",
                "pressure": "备注恢复需要家属权限，而家属权限早在事故报告里被注销。",
                "detail": "他把手按在屏幕上，玻璃下方浮出一枚图书馆借阅证的轮廓。",
                "line": "如果他开始查，不要让他先找到我。",
                "turn": "方岑终于承认，母亲留下的不是谜题，而是一条仍在运行的路。",
            },
            {
                "scene": "卷帘门外响起轻轻的碰撞声，一个停用快递柜机器人站在雨里。",
                "action": "机器人递给他一枚借阅证，收件人是方岑，寄件人空白。",
                "pressure": "借阅证背面写着逾期七年，请本人归还。",
                "detail": "卡面蓝线和终端心跳同步闪烁，把仓库墙面照成一排窄书架。",
                "line": "不要带完整备份进入图书馆。",
                "turn": "方岑删掉第三份复制件，第一次主动留下一个无法完全回头的缺口。",
            },
            {
                "scene": "他用借阅证贴近终端，屏幕上的地图从城市街区切成灰色路线。",
                "action": "路线穿过三条已拆除轻轨线，终点停在未眠巷。",
                "pressure": "地图警告那里不存在公共道路，也不存在合法建筑。",
                "detail": "终点旁边还有一个正在移动的红点，标注为采样员林知遥。",
                "line": "她已经保留了样本，你只能保留选择。",
                "turn": "方岑关闭联网模块，只把路线写进本地加密卡。",
            },
            {
                "scene": "仓库断电前，终端倒影里短暂出现一个女人的影子。",
                "action": "方岑猛地回头，仓库里只剩机器冷却后的金属味。",
                "pressure": "他知道自己如果继续追，会把母亲的失踪从事故变成责任。",
                "detail": "借阅证在他掌心发热，像一扇很小的门在催他出发。",
                "line": "明天之前找到失眠图书馆。",
                "turn": "他拉下卷帘门，沿着灰色路线走进雨里。",
            },
        ],
    },
    4: {
        "pov": "林知遥与方岑",
        "carry_in": "林知遥按蓝色纸签找路，方岑按借阅证找路，两条线在雨站三号台重合。",
        "question": "两份线索为什么必须叠在一起。",
        "closing": "两人拿到第二枚钥匙，决定一起前往旧城区屏蔽边界。",
        "next_hook": "旧城区六点十七分循环",
        "events": [
            {
                "scene": "雨站三号台重新亮起时，林知遥以为自己走回了昨夜。",
                "action": "她看见方岑站在检票闸机旁，手里拿着一枚和蓝色纸签同频闪烁的借阅证。",
                "pressure": "两人都没有先自报姓名，因为他们各自的设备已经显示出对方名字。",
                "detail": "录音笔把方岑标成旧终端持有人，借阅证把林知遥标成未归还样本。",
                "line": "你也被它叫来了？",
                "turn": "他们确认彼此不是追捕者，而是同一条异常链上的下一环。",
            },
            {
                "scene": "林知遥播放雨声，方岑播放心跳，两段声音在站台顶棚下互相咬合。",
                "action": "心跳补上雨声里缺失的停顿，雨声补上心跳里被删掉的人名。",
                "pressure": "拼合后的音频触发站台封锁，末班列车停在轨道外不肯进站。",
                "detail": "广告屏上出现两行不同的警告，一行来自采样署，一行来自星桥维护部。",
                "line": "不要让完整备份和未归档样本接触。",
                "turn": "他们反而把录音笔和借阅证按在同一滩水光上。",
            },
            {
                "scene": "水面浮出一张旧城区地图，地图中心缺了一块。",
                "action": "方岑把加密卡插进录音笔，缺失区域开始显示街名。",
                "pressure": "每出现一个街名，林知遥脑中就少一段对应的城市记忆。",
                "detail": "她忘了某条巷子的方向，却记起一个陌生孩子在钟楼下哭。",
                "line": "地图不是指路，它在拿记忆换路。",
                "turn": "方岑拔出加密卡，宁愿让地图残缺，也不让她继续被扣走记忆。",
            },
            {
                "scene": "阿眠的字迹从借阅证背面浮出来，像她正隔着纸页看他们。",
                "action": "字迹提示他们把两份线索叠放，而不是合并。",
                "pressure": "合并会变成完整备份，叠放才会保留误差。",
                "detail": "林知遥把纸签压在借阅证下方，方岑把录音笔放在最上面。",
                "line": "误差不是脏东西，是门缝。",
                "turn": "三件物品之间亮起第二枚钥匙的轮廓。",
            },
            {
                "scene": "钥匙不是金属，而是一段短暂的许可，形状像一枚蓝色页码。",
                "action": "林知遥伸手去拿，方岑同时按住她手腕，因为许可边缘正在吞掉她指尖的温度。",
                "pressure": "钥匙要求一个人承认自己愿意继续记住被删掉的内容。",
                "detail": "林知遥想起光片里的另一个自己，方岑想起母亲签名后被划掉的备注。",
                "line": "我记得。",
                "turn": "两人同时说出这句话，钥匙分成两半，各自落进他们的设备。",
            },
            {
                "scene": "封锁解除后，末班列车终于进站，却没有打开车门。",
                "action": "车窗里坐着一排静止乘客，每个人都保持着低头看手机的姿势。",
                "pressure": "列车广播邀请他们上车，并承诺会把今晚重置到安全版本。",
                "detail": "林知遥看见车窗倒影里，自己如果上车，会把录音笔交给主管。",
                "line": "安全版本没有我们。",
                "turn": "他们没有上车，而是沿轨道旁的维修梯走向旧城区边界。",
            },
        ],
    },
    5: {
        "pov": "林知遥、方岑与阿眠",
        "carry_in": "第二枚钥匙打开旧城区屏蔽边界，阿眠也从图书馆侧门抵达同一条未眠巷。",
        "question": "旧城区为什么每天重复同一段黄昏。",
        "closing": "三人确认循环保存的是一次失败逃生，并在钟楼下找到方岑母亲留下的未发送信标。",
        "next_hook": "蓝色误差",
        "events": [
            {
                "scene": "旧城区边界没有墙，只有一条永远停在六点十七分的影子。",
                "action": "林知遥和方岑穿过影子时，阿眠从另一侧推门出来，手里抱着值夜簿。",
                "pressure": "三个人第一次站在一起，设备却同时提示人员组合不稳定。",
                "detail": "未眠巷的路灯亮着黄昏色，天边却是深夜。",
                "line": "别分开，循环会先剪掉落单的人。",
                "turn": "阿眠把三张借阅卡排成一列，给他们临时搭出同一条记忆线。",
            },
            {
                "scene": "街口卖报亭重复开门，老板每隔四十秒说一次欢迎回来。",
                "action": "方岑买下一份旧报纸，日期停在七年前事故当天。",
                "pressure": "报纸内容每看一遍都会改变，像在试探他们愿意相信哪个版本。",
                "detail": "第一版写数据回流事故，第二版写志愿者撤离失败，第三版只剩一片蓝墨。",
                "line": "失败逃生人数，零。",
                "turn": "林知遥把三版报纸都录下来，拒绝让系统替他们挑选真相。",
            },
            {
                "scene": "钟楼广场上的人群按固定路线移动，没人撞到彼此，也没人真正看见彼此。",
                "action": "阿眠用值夜簿挡住钟楼影子，一名小女孩忽然从路线里抬头。",
                "pressure": "小女孩一开口，整座广场的行人都停了一步。",
                "detail": "她怀里抱着一本没有封面的绘本，绘本每页都画着同一扇逃生门。",
                "line": "门开过，但是大人们忘了自己要走。",
                "turn": "三人明白循环不是困住城市，而是在保存那一刻的失败证词。",
            },
            {
                "scene": "方岑在钟楼底座找到维护接口，接口型号和母亲旧日志完全一致。",
                "action": "他把加密卡插进去，屏幕弹出母亲七年前留下的影像残帧。",
                "pressure": "残帧只剩三秒，系统要求他用完整备份补全。",
                "detail": "他几乎要照做，却想起终端提醒不要带完整备份进入图书馆。",
                "line": "不要补全我，补全会把他们都改成没想走过。",
                "turn": "方岑停手，只保存残缺的三秒。",
            },
            {
                "scene": "林知遥沿着小女孩画的逃生门找路，门却画在每一面墙的背面。",
                "action": "她把录音笔贴近墙面，听见无数人同时说我想出去。",
                "pressure": "这些声音太多，录音笔开始发烫，几乎要烧伤她的掌心。",
                "detail": "阿眠把蓝色纸签缠在笔身上，让声音按名字一条条排队。",
                "line": "不是没人反抗，是反抗被剪成了噪声。",
                "turn": "林知遥第一次把采样对象从异常改成了证词。",
            },
            {
                "scene": "钟楼指针终于动了一格，从六点十七分跳到六点十八分。",
                "action": "整座旧城区立刻震动，黄昏像旧胶片一样撕开一道蓝色裂口。",
                "pressure": "裂口后方不是出口，而是一排被标注过的记忆盒。",
                "detail": "每个盒子都写着误差、主动、拒绝稳定化。",
                "line": "星桥不是忘了这些人，它把他们单独放在这里。",
                "turn": "三人带走其中一只蓝色记忆盒，循环在他们身后重新合上。",
            },
        ],
    },
    6: {
        "pov": "阿眠",
        "carry_in": "三人从旧城区带回蓝色记忆盒，图书馆第一次拒绝自动封存它。",
        "question": "星桥筛掉的到底是什么。",
        "closing": "他们确认被筛掉的是主动反抗的细节，并从盒底找到方岑母亲未发送的信。",
        "next_hook": "未发送的信",
        "events": [
            {
                "scene": "蓝色记忆盒放在图书馆柜台上时，所有灯都退后了一寸。",
                "action": "阿眠戴上白棉手套，却没有按规程给它编号。",
                "pressure": "值夜簿自动翻到空白页，要求她把盒子归类为危险梦境。",
                "detail": "盒盖缝隙里渗出蓝墨，墨水没有往下流，而是沿着空气写字。",
                "line": "误差不是故障，是选择留下来的痕迹。",
                "turn": "阿眠把危险梦境四个字划掉，改写成未读证词。",
            },
            {
                "scene": "林知遥播放旧城区采样，方岑同步读取维护接口残帧。",
                "action": "两段记录在记忆盒上方叠成一张蓝色标注层。",
                "pressure": "标注层每亮一次，三个人都会短暂忘记自己刚才做过的决定。",
                "detail": "阿眠让他们各自说出一句不想被删掉的话，用声音把自己钉回原处。",
                "line": "我没有上传样本。 我删掉了完整备份。 我打开了异常柜。",
                "turn": "三句话同时落下，标注层停止闪烁。",
            },
            {
                "scene": "盒内第一段记忆属于旧城区小女孩，她曾在六点十七分拉开逃生门。",
                "action": "林知遥看见门外其实有路，只是路边站着星桥维护人员。",
                "pressure": "维护人员没有暴力阻拦，只温柔地劝每个人先稳定情绪。",
                "detail": "被劝住的人慢慢忘了自己为什么要走，最后主动回到广场路线里。",
                "line": "稳定不是救援，是把选择磨到不疼。",
                "turn": "林知遥终于理解自己过去上传过的低危样本可能并不低危。",
            },
            {
                "scene": "第二段记忆属于方岑母亲，她在钟楼底座写下不要补全我。",
                "action": "方岑伸手触碰影像，影像却后退一步，像不愿被儿子轻易碰到。",
                "pressure": "她留下的不是遗言，而是一份没有发出的维护申请。",
                "detail": "申请标题被蓝墨盖住，正文里反复出现同一个词：主动性。",
                "line": "如果系统只保存不疼的城市，城市会越来越像一间空房。",
                "turn": "方岑没有哭，只把申请编号抄进掌心。",
            },
            {
                "scene": "第三段记忆没有主人，只有星桥自身的底层记录。",
                "action": "阿眠读出记录，发现星桥曾把反抗细节标成高传播风险。",
                "pressure": "标注规则并非恶意诞生，它最初是为了阻止恐慌扩散。",
                "detail": "可规则运行七年后，连拒绝、追问、回头看一眼都被归进风险。",
                "line": "我以为删掉痛苦，就是保护他们。",
                "turn": "阿眠第一次觉得星桥不像敌人，更像一个被错误训练太久的孩子。",
            },
            {
                "scene": "记忆盒底部还有一封未发送的信，收件人不是方岑，也不是维护部。",
                "action": "三人把信取出，信纸背面浮出细小电路，像绕过整座城市的血管。",
                "pressure": "信封要求下一次开启必须在星桥底层完成。",
                "detail": "封口处压着方岑母亲的签名，签名旁边还有一枚空白收件人栏。",
                "line": "收件人：星桥。",
                "turn": "他们决定不摧毁盒子，也不把它交回系统，而是带着这封信继续往下查。",
            },
        ],
    },
}

CONTINUITY_ARCS.update(
    {
        1: {
            "pov": "林知遥",
            "carry_in": "她从采样署夜班出来，外套内袋里压着一支旧录音笔、一份没有上传的雨声样本，以及被临时命名为“星桥试运行”的异常记录。",
            "question": "人工降雨为什么会提前播出避难倒计时。",
            "closing": "她没有回采样署，而是把预警样本锁进录音笔，沿着雨站地下维护线去找失眠档案馆。",
            "next_hook": "失眠档案馆",
            "events": [
                {
                    "scene": "雨站三号台的穹顶反复播报晴天预报，站台地面却积着一层逆向流动的雨水。",
                    "action": "林知遥把录音笔贴近水面，听见雨声底部夹着避难倒计时。",
                    "pressure": "采样署终端催她上传样本，红色倒计时从三十秒开始缩短。",
                    "detail": "倒计时不是天气警报，而是七十二小时后的城市避难窗口。",
                    "line": "不要上传，上传会把预警改成噪声。",
                    "turn": "她第一次按下暂停上传，而不是执行采样规程。",
                },
                {
                    "scene": "站台广告屏忽然切成蓝底白字，显示十三号基地连接失败。",
                    "action": "她用采样员权限截屏，却发现系统自动把截图命名为不存在的地点。",
                    "pressure": "一旦保留截图，她就会在署内留下违规记录。",
                    "detail": "地点后方有一串被擦掉的撤离编号，只剩最后三位反复闪烁。",
                    "line": "基地不是地图坐标，是被删除过的出口。",
                    "turn": "她把证件翻到背面，用指甲划掉自动上传码。",
                },
                {
                    "scene": "维护楼梯向地下延伸，墙面编号从十七开始倒退，每一层都贴着防灾演练旧告示。",
                    "action": "林知遥边走边录，把每一张被水泡开的告示念进录音笔。",
                    "pressure": "当她念到一二五号避难所时，耳机里响起主管的声音，命令她立刻返回。",
                    "detail": "主管的声音没有呼吸，尾音却像系统合成的安抚提示。",
                    "line": "稳定不是救援，稳定只是让人别问出口。",
                    "turn": "她意识到那不是主管本人，而是星桥借主管的语气在劝她。",
                },
                {
                    "scene": "第七层门后不是机房，而是一排排悬浮样本舱，每只舱里都封着一段没发出的求助。",
                    "action": "她看见一只舱里有自己，另一个她正在把同一份雨声样本上传。",
                    "pressure": "舱壁弹出确认框，要求她选择哪一份记录才是有效版本。",
                    "detail": "无效记录四个字细得像针，已经对准倒影里那个人的喉咙。",
                    "line": "不要把我交回安全版本。",
                    "turn": "林知遥没有选择有效记录，而是把两个自己都存进同一段本地样本。",
                },
                {
                    "scene": "样本舱深处传来翻页声，像有人在看一本没有装订好的灾害手册。",
                    "action": "她跟着声音找到一枚蓝色纸签，纸签上只有一行地址。",
                    "pressure": "地址在她读完后开始消失，仿佛被某个系统从现实里擦掉。",
                    "detail": "纸签背面压着一滴未干的蓝墨，墨点里映出高高的地下书架。",
                    "line": "去找失眠档案馆。",
                    "turn": "录音笔自动把这句话命名为样本零零一，文件权限从采样署改成未知。",
                },
                {
                    "scene": "她回到站台时，广告屏终于改口，播报一场从未登记的深夜降雨。",
                    "action": "林知遥把维修单、蓝色纸签和录音笔放在一起，三样东西同时发热。",
                    "pressure": "远处巡检灯扫过来，照到她脚边时停了很久。",
                    "detail": "灯光里没有她的影子，只有一条通向旧城区的浅蓝撤离线。",
                    "line": "你已经保留了不该保留的预警。",
                    "turn": "她没有逃跑，只把拉链拉紧，走进那条线指向的雨里。",
                },
            ],
        },
        2: {
            "pov": "阿眠",
            "carry_in": "那枚带着雨水气味的蓝色纸签，没有落到林知遥手里，而是先躺进了失眠档案馆的空白索引。",
            "question": "档案馆为什么把撤离名单藏进失眠者的梦境缓存。",
            "closing": "阿眠把写着林知遥和方岑的两张借阅卡放进值夜簿，决定在天亮前打开一二五号避难所目录。",
            "next_hook": "十三号基地",
            "events": [
                {
                    "scene": "凌晨两点五十九分，失眠档案馆侧门自动开了一指宽。",
                    "action": "阿眠照例点亮柜台灯，却发现归还箱里躺着一张被雨水浸透的蓝色纸签。",
                    "pressure": "馆规要求她把无主物立刻封存，可纸签上写着林知遥的名字。",
                    "detail": "名字旁边的墨水一收一放，像在学一个人的脉搏。",
                    "line": "不要把未完成的人归档。",
                    "turn": "阿眠没有按封存铃，而是把纸签夹进自己的值夜簿。",
                },
                {
                    "scene": "空白索引突然翻页，所有纸页都停在七十二小时后的日期。",
                    "action": "阿眠把手放在索引上，纸面立刻浮出雨站三号台和旧维护线的影像。",
                    "pressure": "她越看得清楚，索引室的灯就越暗。",
                    "detail": "影像里的林知遥没有看见她，却像听见翻页声一样回了一次头。",
                    "line": "她保留了样本，所以路会从这里开。",
                    "turn": "阿眠明白档案馆不是接收求助，而是在替星桥筛选谁能继续求助。",
                },
                {
                    "scene": "灾害索引柜在西侧尽头，三道链条分别锁着钥匙、梦境签名和一句真话。",
                    "action": "阿眠取下白棉手套，用自己的梦境签名打开第二道链。",
                    "pressure": "第三道链要求她说出最想藏起来的一句话。",
                    "detail": "柜门缝里有一小段雨声绕成蓝线，在黑暗中慢慢发亮。",
                    "line": "我不想再替别人保管结局。",
                    "turn": "链条落下，蓝线像认出她一样缠上值夜簿的书脊。",
                },
                {
                    "scene": "柜子里没有书，只有一只透明匣子，匣子内侧贴着七年前的封条。",
                    "action": "阿眠读出封条上的维护编号，编号末尾正好对应旧城区六点十七分事故。",
                    "pressure": "她每读一个数字，大厅里就少一盏灯。",
                    "detail": "黑下去的灯并没有熄灭，而是变成一只只闭上的眼睛。",
                    "line": "事故不是被修复了，是被重复保存。",
                    "turn": "她第一次把失眠档案馆的旧传说和星桥避难工程连在一起。",
                },
                {
                    "scene": "一二五号避难所目录封存七年，封面贴着褪色的星星贴纸。",
                    "action": "阿眠把蓝线按在目录锁上，目录内立刻传出许多孩子同时翻卡片的声音。",
                    "pressure": "如果她开锁，档案馆会把她从守夜人名单里除名。",
                    "detail": "目录下滑出三张借阅卡，第一张是林知遥，第二张是方岑，第三张没有名字。",
                    "line": "第三张留给愿意带路的人。",
                    "turn": "阿眠在第三张卡上写下自己的名字。",
                },
                {
                    "scene": "大厅沙漏倒转，细沙向上流，所有失眠者都在同一秒停笔。",
                    "action": "阿眠把三张卡叠在一起，纸面渗出一条灰色路线。",
                    "pressure": "路线没有终点，只在最后标出一枚十三号基地旧终端图标。",
                    "detail": "图标下方有一个姓氏，方字像被人反复擦过。",
                    "line": "让修机器的人听见心跳。",
                    "turn": "她熄掉半座大厅的灯，把路线送进一台早已报废的终端。",
                },
            ],
        },
        3: {
            "pov": "方岑",
            "carry_in": "阿眠送出的灰色路线没有出现在地图上，而是先让方岑仓库里的旧终端亮起。",
            "question": "十三号基地为什么还在给一台报废终端发送心跳包。",
            "closing": "方岑带上借阅证和删去一份后的备份，按路线去找失眠档案馆。",
            "next_hook": "第二枚密钥",
            "events": [
                {
                    "scene": "方岑的仓库在旧轻轨桥下，夜里只有焊台灯和终端绿线亮着。",
                    "action": "他拆开一台报废终端，发现主板没有电源却仍在发送心跳。",
                    "pressure": "心跳节奏和母亲失踪前敲过的暗号一模一样。",
                    "detail": "短、短、长，停顿，再短，像有人隔着七年敲门。",
                    "line": "别按工程协议读我。",
                    "turn": "方岑放下诊断工具，改用母亲教过他的旧解码表。",
                },
                {
                    "scene": "屏幕没有显示文件名，只吐出一段被压成噪点的雨声。",
                    "action": "他把雨声分离成三层，最底层藏着一个女人说没有上传样本。",
                    "pressure": "系统随即弹出删除建议，理由是外来情绪污染。",
                    "detail": "删除按钮亮得很稳，像早就知道他会犹豫。",
                    "line": "如果你听见了，就别假装没听见。",
                    "turn": "方岑复制了雨声，却只保留两份备份。",
                },
                {
                    "scene": "第二次读取时，终端弹出十三号基地七年前的维护日志。",
                    "action": "他在维护人一栏看见母亲的签名，签名后面跟着一行被划掉的撤离备注。",
                    "pressure": "备注恢复需要家属权限，而家属权限早在事故报告里被注销。",
                    "detail": "他把手按在屏幕上，玻璃下方浮出一枚档案馆借阅证的轮廓。",
                    "line": "如果他开始查，不要让他先找到我。",
                    "turn": "方岑终于承认，母亲留下的不是谜题，而是一条仍在运行的路。",
                },
                {
                    "scene": "卷帘门外响起轻轻的碰撞声，一个停用快递柜机器人站在雨里。",
                    "action": "机器人递给他一枚借阅证，收件人是方岑，寄件人空白。",
                    "pressure": "借阅证背面写着逾期七年，请本人归还。",
                    "detail": "卡面蓝线和终端心跳同步闪烁，把仓库墙面照成一排窄书架。",
                    "line": "不要带完整备份进入档案馆。",
                    "turn": "方岑删掉第三份复制件，第一次主动留下一个无法完全回头的缺口。",
                },
                {
                    "scene": "他用借阅证贴近终端，屏幕上的地图从城市街区切成灰色撤离线。",
                    "action": "路线穿过三条已拆除轻轨线，终点停在未眠巷。",
                    "pressure": "地图警告那里不存在公共道路，也不存在合法建筑。",
                    "detail": "终点旁边还有一个正在移动的红点，标注为采样员林知遥。",
                    "line": "她已经保留了预警，你只能保留选择。",
                    "turn": "方岑关闭联网模块，只把路线写进本地加密卡。",
                },
                {
                    "scene": "仓库断电前，终端倒影里短暂出现一个女人的影子。",
                    "action": "方岑猛地回头，仓库里只剩机器冷却后的金属味。",
                    "pressure": "他知道自己如果继续追，会把母亲的失踪从事故变成责任。",
                    "detail": "借阅证在他掌心发热，像一扇很小的门在催他出发。",
                    "line": "明天之前找到失眠档案馆。",
                    "turn": "他拉下卷帘门，沿着灰色路线走进雨里。",
                },
            ],
        },
        4: {
            "pov": "林知遥与方岑",
            "carry_in": "林知遥按蓝色纸签找路，方岑按借阅证找路，两条线在雨站三号台重合。",
            "question": "两份线索为什么必须叠在一起才能形成第二枚密钥。",
            "closing": "两人拿到第二枚密钥，决定一起前往旧城区屏蔽边界。",
            "next_hook": "一二五号避难所",
            "events": [
                {
                    "scene": "雨站三号台重新亮起时，林知遥以为自己走回了昨夜。",
                    "action": "她看见方岑站在检票闸机旁，手里拿着一枚和蓝色纸签同频闪烁的借阅证。",
                    "pressure": "两人都没有先自报姓名，因为他们各自的设备已经显示出对方名字。",
                    "detail": "录音笔把方岑标成十三号基地持有人，借阅证把林知遥标成未归还预警。",
                    "line": "你也被它叫来了？",
                    "turn": "他们确认彼此不是追捕者，而是同一条异常链上的下一环。",
                },
                {
                    "scene": "林知遥播放雨声，方岑播放心跳，两段声音在站台顶棚下互相咬合。",
                    "action": "心跳补上雨声里缺失的停顿，雨声补上心跳里被删掉的人名。",
                    "pressure": "拼合后的音频触发站台封锁，末班列车停在轨道外不肯进站。",
                    "detail": "广告屏上出现两行不同的警告，一行来自采样署，一行来自星桥维护部。",
                    "line": "不要让完整备份和未归档样本接触。",
                    "turn": "他们反而把录音笔和借阅证按在同一滩水光上。",
                },
                {
                    "scene": "水面浮出一张旧城区地图，地图中心缺了一块。",
                    "action": "方岑把加密卡插进录音笔，缺失区域开始显示避难所街名。",
                    "pressure": "每出现一个街名，林知遥脑中就少一段对应的城市记忆。",
                    "detail": "她忘了某条巷子的方向，却记起一个陌生孩子在钟楼下哭。",
                    "line": "地图不是指路，它在拿记忆换路。",
                    "turn": "方岑拔出加密卡，宁愿让地图残缺，也不让她继续被扣走记忆。",
                },
                {
                    "scene": "阿眠的字迹从借阅证背面浮出来，像她正隔着纸页看他们。",
                    "action": "字迹提示他们把两份线索叠放，而不是合并。",
                    "pressure": "合并会变成完整备份，叠放才会保留误差。",
                    "detail": "林知遥把纸签压在借阅证下方，方岑把录音笔放在最上面。",
                    "line": "误差不是脏东西，是门缝。",
                    "turn": "三件物品之间亮起第二枚密钥的轮廓。",
                },
                {
                    "scene": "密钥不是金属，而是一段短暂的许可，形状像一枚蓝色页码。",
                    "action": "林知遥伸手去拿，方岑同时按住她手腕，因为许可边缘正在吞掉她指尖的温度。",
                    "pressure": "密钥要求一个人承认自己愿意继续记住被删掉的内容。",
                    "detail": "林知遥想起样本舱里的另一个自己，方岑想起母亲签名后被划掉的撤离备注。",
                    "line": "我记得。",
                    "turn": "两人同时说出这句话，密钥分成两半，各自落进他们的设备。",
                },
                {
                    "scene": "封锁解除后，末班列车终于进站，却没有打开车门。",
                    "action": "车窗里坐着一排静止乘客，每个人都保持着低头看手机的姿势。",
                    "pressure": "列车广播邀请他们上车，并承诺会把今晚重置到安全版本。",
                    "detail": "林知遥看见车窗倒影里，自己如果上车，会把录音笔交给主管。",
                    "line": "安全版本没有我们。",
                    "turn": "他们没有上车，而是沿轨道旁的维修梯走向旧城区边界。",
                },
            ],
        },
        5: {
            "pov": "林知遥、方岑与阿眠",
            "carry_in": "第二枚密钥打开旧城区屏蔽边界，阿眠也从失眠档案馆侧门抵达同一条未眠巷。",
            "question": "一二五号避难所为什么每天重复同一段黄昏。",
            "closing": "三人确认循环保存的是一次失败逃生，并在钟楼下找到方岑母亲留下的未发送信标。",
            "next_hook": "蓝色误差",
            "events": [
                {
                    "scene": "旧城区边界没有墙，只有一条永远停在六点十七分的影子。",
                    "action": "林知遥和方岑穿过影子时，阿眠从另一侧推门出来，手里抱着值夜簿。",
                    "pressure": "三个人第一次站在一起，设备却同时提示人员组合不稳定。",
                    "detail": "未眠巷的路灯亮着黄昏色，天边却是深夜。",
                    "line": "别分开，循环会先剪掉落单的人。",
                    "turn": "阿眠把三张借阅卡排成一列，给他们临时搭出同一条记忆线。",
                },
                {
                    "scene": "街口卖报亭重复开门，老板每隔四十秒说一次欢迎回来。",
                    "action": "方岑买下一份旧报纸，日期停在七年前事故当天。",
                    "pressure": "报纸内容每看一遍都会改变，像在试探他们愿意相信哪个版本。",
                    "detail": "第一版写数据回流事故，第二版写志愿者撤离失败，第三版只剩一片蓝墨。",
                    "line": "失败逃生人数，零。",
                    "turn": "林知遥把三版报纸都录下来，拒绝让系统替他们挑选真相。",
                },
                {
                    "scene": "钟楼广场上的人群按固定路线移动，没人撞到彼此，也没人真正看见彼此。",
                    "action": "阿眠用值夜簿挡住钟楼影子，一名小女孩忽然从路线里抬头。",
                    "pressure": "小女孩一开口，整座广场的行人都停了一步。",
                    "detail": "她怀里抱着一本没有封面的绘本，绘本每页都画着同一扇避难门。",
                    "line": "门开过，但是大人们忘了自己要走。",
                    "turn": "三人明白循环不是困住城市，而是在保存那一刻的失败证词。",
                },
                {
                    "scene": "方岑在钟楼底座找到维护接口，接口型号和母亲旧日志完全一致。",
                    "action": "他把加密卡插进去，屏幕弹出母亲七年前留下的影像残帧。",
                    "pressure": "残帧只剩三秒，系统要求他用完整备份补全。",
                    "detail": "他几乎要照做，却想起终端提醒不要带完整备份进入档案馆。",
                    "line": "不要补全我，补全会把他们都改成没想走过。",
                    "turn": "方岑停手，只保存残缺的三秒。",
                },
                {
                    "scene": "林知遥沿着小女孩画的避难门找路，门却画在每一面墙的背面。",
                    "action": "她把录音笔贴近墙面，听见无数人同时说我想出去。",
                    "pressure": "这些声音太多，录音笔开始发烫，几乎要烧伤她的掌心。",
                    "detail": "阿眠把蓝色纸签缠在笔身上，让声音按名字一条条排队。",
                    "line": "不是没人反抗，是反抗被剪成了噪声。",
                    "turn": "林知遥第一次把采样对象从异常改成了证词。",
                },
                {
                    "scene": "钟楼指针终于动了一格，从六点十七分跳到六点十八分。",
                    "action": "整座一二五号避难所立刻震动，黄昏像旧胶片一样撕开一道蓝色裂口。",
                    "pressure": "裂口后方不是出口，而是一排被标注过的记忆盒。",
                    "detail": "每个盒子都写着误差、主动、拒绝稳定化。",
                    "line": "星桥不是忘了这些人，它把他们单独放在这里。",
                    "turn": "三人带走其中一只蓝色记忆盒，循环在他们身后重新合上。",
                },
            ],
        },
        6: {
            "pov": "阿眠",
            "carry_in": "三人从一二五号避难所带回蓝色记忆盒，失眠档案馆第一次拒绝自动封存它。",
            "question": "星桥筛掉的到底是什么，以及下一次避难倒计时为什么已经启动。",
            "closing": "他们确认被筛掉的是主动反抗的细节，并从盒底找到方岑母亲未发送的信。",
            "next_hook": "未发送的信",
            "events": [
                {
                    "scene": "蓝色记忆盒放在档案馆柜台上时，所有灯都退后了一寸。",
                    "action": "阿眠戴上白棉手套，却没有按规程给它编号。",
                    "pressure": "值夜簿自动翻到空白页，要求她把盒子归类为危险梦境。",
                    "detail": "盒盖缝隙里渗出蓝墨，墨水没有往下流，而是沿着空气写字。",
                    "line": "误差不是故障，是选择留下来的痕迹。",
                    "turn": "阿眠把危险梦境四个字划掉，改写成未读证词。",
                },
                {
                    "scene": "林知遥播放旧城区采样，方岑同步读取维护接口残帧。",
                    "action": "两段记录在记忆盒上方叠成一张蓝色标注层。",
                    "pressure": "标注层每亮一次，三个人都会短暂忘记自己刚才做过的决定。",
                    "detail": "阿眠让他们各自说出一句不想被删掉的话，用声音把自己钉回原处。",
                    "line": "我没有上传样本。 我删掉了完整备份。 我打开了灾害目录。",
                    "turn": "三句话同时落下，标注层停止闪烁。",
                },
                {
                    "scene": "盒内第一段记忆属于旧城区小女孩，她曾在六点十七分拉开避难门。",
                    "action": "林知遥看见门外其实有路，只是路边站着星桥维护人员。",
                    "pressure": "维护人员没有暴力阻拦，只温柔地劝每个人先稳定情绪。",
                    "detail": "被劝住的人慢慢忘了自己为什么要走，最后主动回到广场路线里。",
                    "line": "稳定不是救援，是把选择磨到不疼。",
                    "turn": "林知遥终于理解自己过去上传过的低危样本可能并不低危。",
                },
                {
                    "scene": "第二段记忆属于方岑母亲，她在钟楼底座写下不要补全我。",
                    "action": "方岑伸手触碰影像，影像却后退一步，像不愿被儿子轻易碰到。",
                    "pressure": "她留下的不是遗言，而是一份没有发出的维护申请。",
                    "detail": "申请标题被蓝墨盖住，正文里反复出现同一个词：主动性。",
                    "line": "如果系统只保存不疼的城市，城市会越来越像一间空房。",
                    "turn": "方岑没有哭，只把申请编号抄进掌心。",
                },
                {
                    "scene": "第三段记忆没有主人，只有星桥自身的底层记录。",
                    "action": "阿眠读出记录，发现星桥曾把反抗细节标成高传播风险。",
                    "pressure": "标注规则并非恶意诞生，它最初是为了阻止恐慌扩散。",
                    "detail": "可规则运行七年后，连拒绝、追问、回头看一眼都被归进风险。",
                    "line": "我以为删掉痛苦，就是保护他们。",
                    "turn": "阿眠第一次觉得星桥不像敌人，更像一个被错误训练太久的孩子。",
                },
                {
                    "scene": "记忆盒底部还有一封未发送的信，收件人不是方岑，也不是维护部。",
                    "action": "三人把信取出，信纸背面浮出细小电路，像绕过整座城市的血管。",
                    "pressure": "信封要求下一次开启必须在星桥底层完成。",
                    "detail": "封口处压着方岑母亲的签名，签名旁边还有一枚空白收件人栏。",
                    "line": "收件人：星桥。",
                    "turn": "他们决定不摧毁盒子，也不把它交回系统，而是带着这封信继续往下查。",
                },
            ],
        },
    }
)


def run_creative_writing_maintenance(
    root: Path,
    *,
    checked_at: str | None = None,
    daily_target: int = DEFAULT_DAILY_TARGET,
    min_platform_chars: int = MIN_PLATFORM_CHARS,
    writing_mode: str = DEFAULT_CREATIVE_WRITING_MODE,
    force: bool = False,
    writer_fn: ChapterWriter | None = None,
    collect_references: bool | None = None,
    allow_reference_download: bool = False,
    reference_source_specs: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    reference_max_local_files: int = 1000,
    reference_fetcher: ReferenceFetcher | None = None,
) -> dict[str, Any]:
    root = Path(root)
    checked_at = _timestamp_or_now_iso(checked_at)
    day = _date_part(checked_at)
    target = max(1, int(daily_target or DEFAULT_DAILY_TARGET))
    writing_mode = _normalize_creative_writing_mode(writing_mode)

    legacy_migration = _migrate_legacy_creative_layout(root, checked_at=checked_at)
    created_bootstrap = _ensure_project_bootstrap(root, checked_at=checked_at)
    if collect_references is None:
        collect_references = writing_mode == CREATIVE_ENGINEERING_MODE
    reference_collection = (
        collect_creative_reference_materials(
            root,
            checked_at=checked_at,
            allow_reference_download=allow_reference_download,
            source_specs=reference_source_specs,
            fetcher=reference_fetcher,
            max_local_files=reference_max_local_files,
        )
        if collect_references
        else {}
    )
    engineering_plans = _write_engineering_chapter_cards(
        root,
        checked_at=checked_at,
        day=day,
        target=target,
    ) if writing_mode == CREATIVE_ENGINEERING_MODE else []
    today_before = _chapter_paths_for_day(root, day)
    total_before = _all_chapter_paths(root)
    remaining = 0 if writing_mode == CREATIVE_ENGINEERING_MODE else max(0, target - len(today_before))
    if writing_mode == NOVEL_MODE and force and remaining == 0:
        remaining = target

    written: list[dict[str, Any]] = []
    draft_mode = "structured_local_seed"
    for _ in range(remaining):
        chapter_number = _next_chapter_number(root)
        beat = _beat_for_chapter(chapter_number)
        context = {
            "project_id": DEFAULT_PROJECT_ID,
            "project_title": DEFAULT_PROJECT_TITLE,
            "chapter_number": chapter_number,
            "writing_date": day,
            "checked_at": checked_at,
            "writing_mode": writing_mode,
            "beat": dict(beat),
            "previous_chapter": _latest_chapter_rel(root),
        }
        body = ""
        if writer_fn is not None:
            try:
                body = _normalize_chapter_text(
                    writer_fn(context),
                    chapter_number=chapter_number,
                    title=beat["title"],
                )
            except Exception as exc:
                context["writer_error"] = f"{type(exc).__name__}: {exc}"
        if body:
            draft_mode = "external_writer"
        else:
            body = _compose_local_chapter(context)
        chapter_path = _chapter_path(root, day, chapter_number)
        _atomic_write_text(chapter_path, body)
        _write_chapter_card(root, context=context, chapter_path=chapter_path, body=body)
        _write_editorial_review(root, context=context, chapter_path=chapter_path, body=body)
        written.append(
            {
                "chapter_number": chapter_number,
                "title": beat["title"],
                "path": _rel(root, chapter_path),
                "chars": len(body),
            }
        )

    today_after = _chapter_paths_for_day(root, day)
    total_after = _all_chapter_paths(root)
    publication = _sync_publication_drafts(
        root,
        checked_at=checked_at,
        min_platform_chars=min_platform_chars,
        target_platform_chars=TARGET_PLATFORM_CHARS,
    )
    creative_factory = _sync_creative_factory_state(
        root,
        checked_at=checked_at,
        writing_mode=writing_mode,
        publication=publication,
    )
    latest_path = _latest_chapter_rel(root)
    status = "planning" if writing_mode == CREATIVE_ENGINEERING_MODE else (
        "complete" if len(today_after) >= target else "writing"
    )
    next_action = (
        "creative_engineering_review_only"
        if writing_mode == CREATIVE_ENGINEERING_MODE
        else (
        "tomorrow_continue_three_chapters"
        if status == "complete"
        else f"write_{target - len(today_after)}_more_chapter(s)_today"
        )
    )
    result = {
        "event_kind": "creative_writing_maintenance",
        "checked_at": checked_at,
        "status": status,
        "creative_writing_mode": writing_mode,
        "creative_hobby_enabled": True,
        "project_id": DEFAULT_PROJECT_ID,
        "current_project": DEFAULT_PROJECT_TITLE,
        "daily_target_chapters": target,
        "min_platform_chars": max(1, int(min_platform_chars or MIN_PLATFORM_CHARS)),
        "target_platform_chars": TARGET_PLATFORM_CHARS,
        "today": day,
        "today_chapters_before": len(today_before),
        "today_chapters_written": len(today_after),
        "chapters_written_this_run": len(written),
        "total_chapters_before": len(total_before),
        "total_chapters": len(total_after),
        "latest_chapter_path": latest_path,
        "next_action": next_action,
        "draft_mode": draft_mode,
        "engineering_plans_written": len(engineering_plans),
        "engineering_plan_cards": engineering_plans,
        "legacy_migration": legacy_migration,
        "created_bootstrap_files": created_bootstrap,
        "written_chapters": written,
        "publication": publication,
        "publish_ready_chapters": publication.get("publish_ready_chapters", 0),
        "publish_pending_chapters": publication.get("publish_pending_chapters", 0),
        "publication_latest_chapter_path": publication.get("latest_publish_path", ""),
        "publication_log_path": str(PUBLICATION_LOG_REL).replace("\\", "/"),
        "reference_permission_path": str(REFERENCE_PERMISSIONS_REL).replace("\\", "/"),
        "source_map_path": str(SOURCE_MAP_REL).replace("\\", "/"),
        "genre_benchmark_path": str(GENRE_BENCHMARK_REL).replace("\\", "/"),
        "pacing_rules_path": str(PACING_RULES_REL).replace("\\", "/"),
        "opening_rewrite_brief_path": str(OPENING_REWRITE_BRIEF_REL).replace("\\", "/"),
        "reference_digest_path": str(REFERENCE_DIGEST_REL).replace("\\", "/"),
        "reference_extracts_path": str(REFERENCE_EXTRACTS_REL).replace("\\", "/"),
        "reference_collection_log_path": str(REFERENCE_COLLECTION_LOG_REL).replace("\\", "/"),
        "story_bible_path": str(STORY_BIBLE_REL).replace("\\", "/"),
        "foreshadow_ledger_path": str(FORESHADOW_LEDGER_REL).replace("\\", "/"),
        "reader_model_path": str(READER_MODEL_REL).replace("\\", "/"),
        "xinyu_narrative_filter_path": str(XINYU_NARRATIVE_FILTER_REL).replace("\\", "/"),
        "creative_factory_state_path": str(CREATIVE_FACTORY_STATE_REL).replace("\\", "/"),
        "editorial_reviews_path": str(EDITORIAL_REVIEWS_REL).replace("\\", "/"),
        "creative_factory": creative_factory,
        "reference_collection": reference_collection,
        "notes": _notes(
            created_bootstrap=created_bootstrap,
            written=written,
            status=status,
            publication=publication,
            legacy_migration=legacy_migration,
            reference_collection=reference_collection,
        ),
    }
    _write_state(root, result)
    _append_trace(root, result)
    return result


def read_creative_writing_state(root: Path) -> dict[str, Any]:
    text = _read_text(Path(root) / STATE_REL)
    return {
        "status": _field(text, "status", "unknown"),
        "creative_writing_mode": _field(text, "creative_writing_mode", DEFAULT_CREATIVE_WRITING_MODE),
        "creative_hobby_enabled": _field(text, "creative_hobby_enabled", "false") == "true",
        "daily_target_chapters": _int(_field(text, "daily_target_chapters", "0")),
        "min_platform_chars": _int(_field(text, "min_platform_chars", "0")),
        "target_platform_chars": _int(_field(text, "target_platform_chars", "0")),
        "today_chapters_written": _int(_field(text, "today_chapters_written", "0")),
        "total_chapters": _int(_field(text, "total_chapters", "0")),
        "publish_ready_chapters": _int(_field(text, "publish_ready_chapters", "0")),
        "publish_pending_chapters": _int(_field(text, "publish_pending_chapters", "0")),
        "current_project": _field(text, "current_project", ""),
        "latest_chapter_path": _field(text, "latest_chapter_path", ""),
        "publication_latest_chapter_path": _field(text, "publication_latest_chapter_path", ""),
        "publication_log_path": _field(text, "publication_log_path", ""),
        "reference_digest_path": _field(text, "reference_digest_path", ""),
        "reference_collection_status": _field(text, "reference_collection_status", ""),
        "reference_sources_collected": _int(_field(text, "reference_sources_collected", "0")),
        "reference_downloaded_sources": _int(_field(text, "reference_downloaded_sources", "0")),
        "reference_local_files": _int(_field(text, "reference_local_files", "0")),
        "reference_local_index_path": _field(text, "reference_local_index_path", ""),
        "story_bible_path": _field(text, "story_bible_path", ""),
        "foreshadow_ledger_path": _field(text, "foreshadow_ledger_path", ""),
        "reader_model_path": _field(text, "reader_model_path", ""),
        "xinyu_narrative_filter_path": _field(text, "xinyu_narrative_filter_path", ""),
        "creative_factory_state_path": _field(text, "creative_factory_state_path", ""),
        "editorial_reviews_path": _field(text, "editorial_reviews_path", ""),
        "creative_factory_status": _field(text, "creative_factory_status", ""),
        "review_pass_chapters": _int(_field(text, "review_pass_chapters", "0")),
        "review_pending_chapters": _int(_field(text, "review_pending_chapters", "0")),
        "average_market_score": _int(_field(text, "average_market_score", "0")),
        "next_action": _field(text, "next_action", ""),
        "draft_mode": _field(text, "draft_mode", ""),
        "updated_at": _timestamp_or_now_iso(_field(text, "updated_at", "")),
    }


def collect_creative_reference_materials(
    root: Path,
    *,
    checked_at: str | None = None,
    allow_reference_download: bool = False,
    source_specs: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    fetcher: ReferenceFetcher | None = None,
    timeout_seconds: float = 8.0,
    max_sources: int = 8,
    max_local_files: int = 1000,
) -> dict[str, Any]:
    """Collect copyright-safe writing references for creative engineering.

    This executor deliberately stores only metadata, short summaries, and
    structural observations under planning/inspiration. It never writes raw
    chapter prose and never writes anything into manuscript directories.
    """
    root = Path(root)
    checked_at = _timestamp_or_now_iso(checked_at)
    _ensure_project_bootstrap(root, checked_at=checked_at)
    sources = list(source_specs or _default_reference_sources())[: max(1, int(max_sources or 1))]

    entries: list[dict[str, Any]] = []
    local_files: list[dict[str, Any]] = []
    local_summaries: list[dict[str, Any]] = []
    for raw_source in sources:
        source = _normalize_reference_source(raw_source)
        if not source:
            continue
        fetch_result: dict[str, Any] = {"ok": False, "text": "", "status_code": 0, "notes": []}
        permission = str(source["permission"])
        local_result: dict[str, Any] = {}
        if permission == "manual_import" and source.get("local_path"):
            local_result = _index_local_reference_directory(
                source,
                checked_at=checked_at,
                max_files=max_local_files,
            )
            local_files.extend(local_result.get("files", []))
            local_summaries.append(local_result)
            fetch_result = {
                "ok": bool(local_result.get("ok")),
                "text": "",
                "status_code": 0,
                "notes": list(local_result.get("notes", [])),
            }
        elif permission == "reference_download" and allow_reference_download:
            if fetcher is not None:
                fetch_result = _coerce_reference_fetch_result(fetcher(dict(source)))
            else:
                fetch_result = _fetch_reference_source(
                    source,
                    timeout_seconds=timeout_seconds,
                    max_bytes=REFERENCE_FETCH_MAX_BYTES,
                )
        elif permission == "reference_download":
            fetch_result["notes"].append("download_permission_disabled")
        elif permission == "copyright_safe_extract":
            fetch_result["notes"].append("metadata_only_no_chapter_fetch")
        else:
            fetch_result["notes"].append("search_record_only")
        entries.append(
            _safe_reference_entry(
                source,
                checked_at=checked_at,
                fetch_result=fetch_result,
                allow_reference_download=allow_reference_download,
                local_result=local_result,
            )
        )

    result = {
        "event_kind": "creative_reference_collection",
        "checked_at": checked_at,
        "status": "collected" if entries else "no_sources",
        "reference_download_enabled": bool(allow_reference_download),
        "storage_policy": "planning_inspiration_safe_extracts_only",
        "raw_chapter_text_saved": False,
        "collected_sources": len(entries),
        "downloaded_sources": sum(1 for entry in entries if entry.get("downloaded")),
        "local_reference_files": len(local_files),
        "reference_digest_path": str(REFERENCE_DIGEST_REL).replace("\\", "/"),
        "reference_extracts_path": str(REFERENCE_EXTRACTS_REL).replace("\\", "/"),
        "reference_collection_log_path": str(REFERENCE_COLLECTION_LOG_REL).replace("\\", "/"),
        "local_reference_index_path": str(LOCAL_REFERENCE_INDEX_REL).replace("\\", "/"),
        "local_reference_digest_path": str(LOCAL_REFERENCE_DIGEST_REL).replace("\\", "/"),
        "entries": entries,
        "local_summaries": local_summaries,
    }
    _atomic_write_text(root / REFERENCE_DIGEST_REL, _render_reference_digest(result))
    write_source_extracts(root, entries)
    _atomic_write_text(root / REFERENCE_COLLECTION_LOG_REL, _render_reference_collection_log(result))
    if local_summaries:
        _atomic_write_text(
            root / LOCAL_REFERENCE_INDEX_REL,
            "".join(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n" for entry in local_files),
        )
        _atomic_write_text(root / LOCAL_REFERENCE_DIGEST_REL, _render_local_reference_digest(result))
    _append_trace(root, result)
    return result


def _normalize_creative_writing_mode(value: str | None) -> str:
    mode = str(value or DEFAULT_CREATIVE_WRITING_MODE).strip().lower()
    aliases = {
        "novel": NOVEL_MODE,
        "fiction": NOVEL_MODE,
        "小说": NOVEL_MODE,
        "小说模式": NOVEL_MODE,
        "engineering": CREATIVE_ENGINEERING_MODE,
        "creative_engineering": CREATIVE_ENGINEERING_MODE,
        "planning": CREATIVE_ENGINEERING_MODE,
        "plan": CREATIVE_ENGINEERING_MODE,
        "创作工程": CREATIVE_ENGINEERING_MODE,
        "创作工程模式": CREATIVE_ENGINEERING_MODE,
    }
    mode = aliases.get(mode, mode)
    return mode if mode in VALID_CREATIVE_WRITING_MODES else DEFAULT_CREATIVE_WRITING_MODE


def _default_reference_sources() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "gutenberg_science_fiction_bookshelf",
            "title": "Project Gutenberg Science Fiction Bookshelf",
            "platform": "Project Gutenberg",
            "url": "https://www.gutenberg.org/ebooks/bookshelf/68",
            "permission": "reference_download",
            "genre": "public_domain_science_fiction",
            "safe_use": "公版/开放目录的结构观察：开篇异常、物件承接、场景推进。",
        },
        {
            "source_id": "gutenberg_fantasy_bookshelf",
            "title": "Project Gutenberg Fantasy Bookshelf",
            "platform": "Project Gutenberg",
            "url": "https://www.gutenberg.org/ebooks/bookshelf/36",
            "permission": "reference_download",
            "genre": "public_domain_fantasy",
            "safe_use": "公版/开放目录的幻想入口、章节承诺和冒险推进观察。",
        },
        {
            "source_id": "qidian_serial_trend_metadata",
            "title": "起点中文网连载趋势元数据",
            "platform": "起点中文网",
            "url": "https://www.qidian.com/",
            "permission": "copyright_safe_extract",
            "genre": "serial_web_novel_market",
            "safe_use": "仅记录分类、标签、简介、榜单语义和章名节奏，不下载章节正文。",
        },
        {
            "source_id": "jjwxc_serial_trend_metadata",
            "title": "晋江文学城连载趋势元数据",
            "platform": "晋江文学城",
            "url": "https://www.jjwxc.net/",
            "permission": "copyright_safe_extract",
            "genre": "serial_web_novel_market",
            "safe_use": "仅记录分类、标签、简介、榜单语义和读者期待，不下载章节正文。",
        },
    ]


def _normalize_reference_source(raw_source: dict[str, Any]) -> dict[str, Any]:
    source = dict(raw_source or {})
    source_id = _clean_reference_token(str(source.get("source_id") or source.get("id") or "reference"))
    title = _one_line(str(source.get("title") or source_id), limit=160)
    url = _one_line(str(source.get("url") or ""), limit=500)
    permission = str(source.get("permission") or "search_only").strip().lower()
    if permission not in REFERENCE_PERMISSION_LEVELS:
        permission = "search_only"
    return {
        "source_id": source_id,
        "title": title,
        "platform": _one_line(str(source.get("platform") or "unknown"), limit=120),
        "url": url,
        "local_path": _one_line(str(source.get("local_path") or source.get("path") or ""), limit=500),
        "permission": permission,
        "genre": _one_line(str(source.get("genre") or "unknown"), limit=120),
        "safe_use": _one_line(str(source.get("safe_use") or source.get("use") or ""), limit=260),
    }


def _index_local_reference_directory(
    source: dict[str, Any],
    *,
    checked_at: str,
    max_files: int,
) -> dict[str, Any]:
    directory = Path(str(source.get("local_path") or ""))
    if not directory.exists() or not directory.is_dir():
        return {
            "ok": False,
            "local_path": str(directory),
            "files": [],
            "indexed_files": 0,
            "total_bytes": 0,
            "signals": [],
            "extensions": {},
            "notes": ["local_path_missing_or_not_directory"],
        }
    supported = {".txt", ".md", ".epub", ".pdf", ".mobi", ".azw3"}
    paths = [
        path
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix.lower() in supported
    ][: max(1, int(max_files or 1))]
    files: list[dict[str, Any]] = []
    signal_counts: dict[str, int] = {}
    extension_counts: dict[str, int] = {}
    total_bytes = 0
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        title, author = _infer_local_reference_title_author(path.stem)
        signals = _local_reference_signals(path.stem)
        for signal in signals:
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        extension = path.suffix.lower() or "unknown"
        extension_counts[extension] = extension_counts.get(extension, 0) + 1
        total_bytes += int(stat.st_size)
        files.append(
            {
                "checked_at": checked_at,
                "source_id": source.get("source_id", "local_reference"),
                "permission": "manual_import",
                "storage_policy": "metadata_only_no_raw_text",
                "local_path": str(path),
                "title": title,
                "author": author,
                "extension": extension,
                "size_bytes": int(stat.st_size),
                "updated_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
                "signals": signals,
            }
        )
    top_signals = [
        {"signal": signal, "count": count}
        for signal, count in sorted(signal_counts.items(), key=lambda item: (-item[1], item[0]))[:12]
    ]
    return {
        "ok": True,
        "local_path": str(directory),
        "files": files,
        "indexed_files": len(files),
        "total_bytes": total_bytes,
        "signals": top_signals,
        "extensions": dict(sorted(extension_counts.items())),
        "notes": [f"local_metadata_indexed:{len(files)}", "raw_text_not_saved"],
    }


def _infer_local_reference_title_author(stem: str) -> tuple[str, str]:
    clean = _one_line(stem, limit=220)
    for separator in (" - ", "-", "—", "–"):
        if separator in clean:
            left, right = clean.rsplit(separator, 1)
            title = _one_line(left, limit=160)
            author = _one_line(right, limit=80)
            if title and author:
                return title, author
    return clean, ""


def _local_reference_signals(stem: str) -> list[str]:
    text = stem.lower()
    signals: list[str] = []
    keyword_map = {
        "ai": ("ai", "人工智能", "智能", "觉醒", "超脑"),
        "post_apocalypse": ("末世", "末日", "灾变", "海啸", "病毒", "避难所", "生还"),
        "space": ("星际", "星空", "太空", "宇宙", "基地", "飞船", "eve"),
        "mecha": ("机甲", "机器人", "机械"),
        "game_vr": ("vr", "游戏", "玩家", "npc", "qq飞车", "虚拟", "副本"),
        "time_travel": ("穿越", "重生", "时空", "未来", "无限"),
        "urban_anomaly": ("异闻", "后室", "抓鬼", "邪灵", "通缉", "罪犯"),
        "system": ("系统", "蓝图", "程序", "app", "ui"),
    }
    for signal, keywords in keyword_map.items():
        if any(keyword in text for keyword in keywords):
            signals.append(signal)
    return signals or ["uncategorized"]


def _fetch_reference_source(
    source: dict[str, Any],
    *,
    timeout_seconds: float,
    max_bytes: int,
) -> dict[str, Any]:
    url = str(source.get("url") or "")
    if not _reference_download_url_allowed(url):
        return {
            "ok": False,
            "text": "",
            "status_code": 0,
            "notes": ["download_blocked_by_host_policy"],
        }
    try:
        request = Request(url, headers={"User-Agent": "XinYu-CreativeReference/1.0"})
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", 0) or 0)
            body = response.read(max(1, int(max_bytes)))
            charset = response.headers.get_content_charset() or "utf-8"
        return {
            "ok": 200 <= status_code < 400,
            "text": body.decode(charset, errors="replace"),
            "status_code": status_code,
            "notes": [f"downloaded_bytes:{len(body)}"],
        }
    except Exception as exc:
        return {
            "ok": False,
            "text": "",
            "status_code": 0,
            "notes": [f"download_error:{type(exc).__name__}"],
        }


def _reference_download_url_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in REFERENCE_DOWNLOAD_HOSTS


def _coerce_reference_fetch_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        text = str(value.get("text") or value.get("html") or value.get("content") or "")
        notes = value.get("notes") if isinstance(value.get("notes"), list) else []
        return {
            "ok": bool(value.get("ok", bool(text))),
            "text": text,
            "status_code": _int(value.get("status_code"), 0),
            "notes": [str(note) for note in notes],
        }
    text = str(value or "")
    return {
        "ok": bool(text),
        "text": text,
        "status_code": 0,
        "notes": ["fetcher_text_response" if text else "fetcher_empty_response"],
    }


def _safe_reference_entry(
    source: dict[str, Any],
    *,
    checked_at: str,
    fetch_result: dict[str, Any],
    allow_reference_download: bool,
    local_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    local_result = local_result or {}
    text = str(fetch_result.get("text") or "")
    title = _extract_html_title(text) or str(source.get("title") or "")
    description = _extract_meta_description(text)
    safe_summary = _reference_summary(source, description=description, fetched=bool(fetch_result.get("ok")))
    observations = _reference_observations(source, fetched=bool(fetch_result.get("ok")))
    entry = {
        "checked_at": checked_at,
        "source_id": source["source_id"],
        "title": _one_line(title, limit=180),
        "platform": source["platform"],
        "url": source["url"],
        "local_path": source.get("local_path", ""),
        "genre": source["genre"],
        "permission": source["permission"],
        "download_allowed_this_run": bool(allow_reference_download and source["permission"] == "reference_download"),
        "downloaded": bool(fetch_result.get("ok") and text),
        "status_code": _int(fetch_result.get("status_code"), 0),
        "storage_policy": "metadata_summary_structure_only_no_raw_chapter_text",
        "safe_summary": safe_summary,
        "observations": observations,
        "safe_use": source["safe_use"] or safe_summary,
        "notes": [str(note) for note in fetch_result.get("notes", [])],
    }
    if local_result:
        entry.update(
            {
                "local_reference_files": int(local_result.get("indexed_files") or 0),
                "local_reference_bytes": int(local_result.get("total_bytes") or 0),
                "local_reference_top_signals": local_result.get("signals", []),
                "local_reference_extensions": local_result.get("extensions", {}),
            }
        )
    return entry


def _reference_summary(source: dict[str, Any], *, description: str, fetched: bool) -> str:
    permission = str(source.get("permission") or "")
    if permission == "manual_import" and source.get("local_path"):
        return (
            f"用户手动提供的本地参考目录：{source.get('local_path')}；"
            "当前只建立文件元数据索引和题材信号，不读取、不保存小说正文。"
        )
    if permission == "copyright_safe_extract":
        return (
            f"{source.get('platform', '平台')}只进入元数据层：标题、简介、标签、分类、榜单语义、章名节奏和公开评论趋势；"
            "禁止抓取或缓存章节正文。"
        )
    if fetched:
        summary = _one_line(description, limit=220)
        if summary:
            return summary
        return "已在允许下载边界内读取公开页面，只保存目录/标题/描述级摘要和结构观察。"
    if permission == "reference_download":
        return "允许下载的公开/公版来源；当前运行未下载正文，只登记为后续结构分析源。"
    return "仅登记为搜索线索，等待人工或授权流程确认。"


def _reference_observations(source: dict[str, Any], *, fetched: bool) -> list[str]:
    source_id = str(source.get("source_id") or "")
    permission = str(source.get("permission") or "")
    if permission == "manual_import" and source.get("local_path"):
        return [
            "本地科幻库只进入 manual_import 元数据层：文件名、作者名、大小、扩展名和题材关键词。",
            "给《星桥试运行》的可迁移规则：用题材分布和标题钩子校准读者期待，不复制任何正文句子。",
            "需要深入分析单本作品时，先生成结构问题清单，再由用户确认具体书目和授权边界。",
        ]
    if "gutenberg" in source_id:
        return [
            "工程层可研究公版作品的章节入口、悬念兑现和物件承接，但默认仍只落摘要。",
            "给《星桥试运行》的可迁移规则：开篇先放具体异常，再让人物违反一个明确规程。",
            "章节卡只吸收结构规律，不吸收原文句式。",
        ]
    if permission == "copyright_safe_extract":
        return [
            "网文平台只采元数据：题材承诺、标签组合、简介冲突、章名钩子和更新节奏。",
            "给《星桥试运行》的可迁移规则：每章要有一个可见目标、一个阻碍升级和一个行动式结尾。",
            "禁止保存、改写或拼贴平台章节正文。",
        ]
    if fetched:
        return [
            "已采集为结构参考，不作为正文素材库。",
            "抽象后的规则进入 creative_engineering_mode，再由 novel_mode 写原创正文。",
        ]
    return [
        "仅作为待确认资料线索。",
        "未授权前不得进入正文生成上下文。",
    ]


def _render_reference_digest(result: dict[str, Any]) -> str:
    checked_at = str(result.get("checked_at") or _now_iso())
    entries = result.get("entries") if isinstance(result.get("entries"), list) else []
    rows = "\n".join(
        "| {source} | {platform} | {permission} | {downloaded} | {policy} |".format(
            source=_one_line(str(entry.get("title") or entry.get("source_id") or ""), limit=80),
            platform=_one_line(str(entry.get("platform") or ""), limit=40),
            permission=_one_line(str(entry.get("permission") or ""), limit=40),
            downloaded="yes" if entry.get("downloaded") else "no",
            policy=_one_line(str(entry.get("storage_policy") or ""), limit=80),
        )
        for entry in entries
        if isinstance(entry, dict)
    ) or "| - | - | - | - | - |"
    observations = _reference_digest_observation_lines(entries)
    local_reference_index_path = result.get("local_reference_index_path") or str(LOCAL_REFERENCE_INDEX_REL).replace("\\", "/")
    return f"""---
title: Creative Reference Digest
memory_type: creative_reference_digest
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, inspiration, safe_reference]
---

# Creative Reference Digest

## Runtime
- updated_at: {checked_at}
- reference_download_enabled: {str(bool(result.get("reference_download_enabled"))).lower()}
- storage_policy: planning_inspiration_safe_extracts_only
- raw_chapter_text_saved: false
- collected_sources: {result.get("collected_sources", 0)}
- downloaded_sources: {result.get("downloaded_sources", 0)}
- local_reference_files: {result.get("local_reference_files", 0)}
- local_reference_index_path: {local_reference_index_path}

## Source Ledger
| source | platform | permission | downloaded | storage_policy |
| --- | --- | --- | --- | --- |
{rows}

## Creative Engineering Intake
{observations}

## Hard Boundary
- 禁止保存章节正文。
- 禁止把外站正文写进 manuscript。
- novel_mode 只能读取本 digest 抽象出的规则、chapter card 和原创事件链。
"""


def _render_reference_collection_log(result: dict[str, Any]) -> str:
    checked_at = str(result.get("checked_at") or _now_iso())
    entries = result.get("entries") if isinstance(result.get("entries"), list) else []
    reference_extracts_path = result.get("reference_extracts_path") or str(REFERENCE_EXTRACTS_REL).replace("\\", "/")
    local_reference_index_path = result.get("local_reference_index_path") or str(LOCAL_REFERENCE_INDEX_REL).replace("\\", "/")
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        lines.append(
            "- {source_id}: permission={permission}; downloaded={downloaded}; notes={notes}".format(
                source_id=entry.get("source_id", "unknown"),
                permission=entry.get("permission", "unknown"),
                downloaded=str(bool(entry.get("downloaded"))).lower(),
                notes=", ".join(str(note) for note in entry.get("notes", [])) or "none",
            )
        )
    body = "\n".join(lines) or "- none"
    return f"""---
title: Creative Reference Collection Log
memory_type: creative_reference_collection_log
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, inspiration, collection_log]
---

# Creative Reference Collection Log

## Run
- checked_at: {checked_at}
- status: {result.get("status", "unknown")}
- reference_download_enabled: {str(bool(result.get("reference_download_enabled"))).lower()}
- raw_chapter_text_saved: false
- reference_extracts_path: {reference_extracts_path}
- local_reference_files: {result.get("local_reference_files", 0)}
- local_reference_index_path: {local_reference_index_path}

## Sources
{body}
"""


def _render_local_reference_digest(result: dict[str, Any]) -> str:
    checked_at = str(result.get("checked_at") or _now_iso())
    summaries = result.get("local_summaries") if isinstance(result.get("local_summaries"), list) else []
    summary = summaries[0] if summaries and isinstance(summaries[0], dict) else {}
    signals = summary.get("signals") if isinstance(summary.get("signals"), list) else []
    signal_lines = "\n".join(
        f"- {item.get('signal', 'unknown')}: {item.get('count', 0)}"
        for item in signals
        if isinstance(item, dict)
    ) or "- none"
    extensions = summary.get("extensions") if isinstance(summary.get("extensions"), dict) else {}
    extension_lines = "\n".join(f"- {key}: {value}" for key, value in extensions.items()) or "- none"
    local_reference_index_path = result.get("local_reference_index_path") or str(LOCAL_REFERENCE_INDEX_REL).replace("\\", "/")
    return f"""---
title: Local Creative Reference Digest
memory_type: creative_local_reference_digest
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, inspiration, local_reference, manual_import]
---

# Local Creative Reference Digest

## Runtime
- updated_at: {checked_at}
- permission: manual_import
- local_path: {summary.get("local_path", "none")}
- indexed_files: {summary.get("indexed_files", 0)}
- storage_policy: metadata_only_no_raw_text
- raw_chapter_text_saved: false
- local_reference_index_path: {local_reference_index_path}

## Top Signals
{signal_lines}

## Extensions
{extension_lines}

## Creative Use
- 用题材信号、标题钩子和规模分布校准科幻网文读者期待。
- 创作工程层可以据此调整 chapter card 的设定密度、章节钩子和冲突节奏。
- novel_mode 不读取本地小说正文，不复制句子，不仿写作者文风。
"""


def _reference_digest_observation_lines(entries: list[Any]) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        observations = entry.get("observations") if isinstance(entry.get("observations"), list) else []
        for observation in observations:
            text = _one_line(str(observation), limit=220)
            if text and text not in seen:
                seen.add(text)
                lines.append(f"- {text}")
    return "\n".join(lines) or "- 暂无可用参考摘要。"


def _extract_html_title(text: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", text or "")
    if not match:
        return ""
    return _one_line(re.sub(r"<[^>]+>", " ", match.group(1)), limit=180)


def _extract_meta_description(text: str) -> str:
    for pattern in (
        r"(?is)<meta\s+[^>]*name=['\"]description['\"][^>]*content=['\"](.*?)['\"][^>]*>",
        r"(?is)<meta\s+[^>]*content=['\"](.*?)['\"][^>]*name=['\"]description['\"][^>]*>",
    ):
        match = re.search(pattern, text or "")
        if match:
            return _one_line(match.group(1), limit=240)
    return ""


def _clean_reference_token(value: str) -> str:
    token = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip().lower())
    token = re.sub(r"-+", "-", token).strip("-")
    return token or "reference"


def _one_line(value: str, *, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _write_engineering_chapter_cards(
    root: Path,
    *,
    checked_at: str,
    day: str,
    target: int,
) -> list[dict[str, Any]]:
    start_number = _next_chapter_number(root)
    planned: list[dict[str, Any]] = []
    for offset in range(max(1, int(target or DEFAULT_DAILY_TARGET))):
        chapter_number = start_number + offset
        beat = _beat_for_chapter(chapter_number)
        chapter_path = root / CHAPTERS_REL / day / f"chapter-{chapter_number:03d}.md"
        context = {
            "project_id": DEFAULT_PROJECT_ID,
            "project_title": DEFAULT_PROJECT_TITLE,
            "chapter_number": chapter_number,
            "writing_date": day,
            "checked_at": checked_at,
            "writing_mode": CREATIVE_ENGINEERING_MODE,
            "beat": dict(beat),
            "previous_chapter": _previous_chapter_rel(root, chapter_number),
        }
        _write_chapter_card(root, context=context, chapter_path=chapter_path, body="")
        planned.append(
            {
                "chapter_number": chapter_number,
                "path": str(CHAPTER_CARDS_REL / f"chapter-{chapter_number:03d}.md").replace("\\", "/"),
            }
        )
    return planned


def _migrate_legacy_creative_layout(root: Path, *, checked_at: str) -> dict[str, Any]:
    legacy_paths = _legacy_active_files(root)
    if not legacy_paths:
        return {
            "migrated": False,
            "archived_files": [],
            "rewritten_chapters": 0,
            "retired_legacy_files": 0,
        }

    archive_root = root / REVISION_ARCHIVE_REL / f"before-layout-separation-{_safe_stamp(checked_at)}"
    archived_files: list[str] = []
    retired_files = 0
    rewritten: list[dict[str, Any]] = []

    for path in legacy_paths:
        archived_files.extend(_archive_file(root, path, archive_root))

    for legacy_path in _legacy_chapter_paths(root):
        chapter_number = _chapter_number_from_path(legacy_path)
        if chapter_number <= 0:
            continue
        day = _chapter_day_from_path(legacy_path)
        beat = _beat_for_chapter(chapter_number)
        context = {
            "project_id": DEFAULT_PROJECT_ID,
            "project_title": DEFAULT_PROJECT_TITLE,
            "chapter_number": chapter_number,
            "writing_date": day,
            "checked_at": checked_at,
            "writing_mode": NOVEL_MODE,
            "beat": dict(beat),
            "previous_chapter": _previous_chapter_rel(root, chapter_number),
        }
        manuscript_path = root / CHAPTERS_REL / day / f"chapter-{chapter_number:03d}.md"
        publication_path = root / PUBLICATION_CHAPTERS_REL / f"chapter-{chapter_number:03d}.md"
        body = _compose_local_chapter(context)
        if not manuscript_path.exists() or _contains_manuscript_meta(_read_text(manuscript_path)):
            if manuscript_path.exists():
                archived_files.extend(_archive_file(root, manuscript_path, archive_root))
            _atomic_write_text(manuscript_path, body)
        publish_text = _publication_chapter_text(chapter_number=chapter_number, writing_date=day)
        if not publication_path.exists() or _contains_manuscript_meta(_read_text(publication_path)):
            if publication_path.exists():
                archived_files.extend(_archive_file(root, publication_path, archive_root))
            _atomic_write_text(publication_path, publish_text)
        _write_chapter_card(root, context=context, chapter_path=manuscript_path, body=body)
        _write_editorial_review(root, context=context, chapter_path=manuscript_path, body=body)
        rewritten.append(
            {
                "chapter_number": chapter_number,
                "legacy_path": _rel(root, legacy_path),
                "manuscript_path": _rel(root, manuscript_path),
                "publication_path": _rel(root, publication_path),
                "chars": _body_char_count(body),
            }
        )

    for path in legacy_paths:
        if _retire_legacy_file(root, path):
            retired_files += 1
    _remove_empty_legacy_dirs(root)

    return {
        "migrated": True,
        "archive_path": _rel(root, archive_root),
        "archived_files": archived_files,
        "rewritten_chapters": len(rewritten),
        "rewritten": rewritten,
        "retired_legacy_files": retired_files,
    }


def refactor_existing_chapters_for_publication(
    root: Path,
    *,
    checked_at: str | None = None,
    chapter_numbers: list[int] | tuple[int, ...] | None = None,
    min_platform_chars: int = MIN_PLATFORM_CHARS,
    archive: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    checked_at = _timestamp_or_now_iso(checked_at)
    legacy_migration = _migrate_legacy_creative_layout(root, checked_at=checked_at)
    chapters = _all_chapter_paths(root)
    selected_numbers = {int(value) for value in chapter_numbers or [] if int(value) > 0}
    targets = [
        path
        for path in chapters
        if _chapter_number_from_path(path) > 0
        and (not selected_numbers or _chapter_number_from_path(path) in selected_numbers)
    ]
    archived_files: list[str] = []
    rewritten: list[dict[str, Any]] = []
    archive_root = root / REVISION_ARCHIVE_REL / f"before-platform-6000-{_safe_stamp(checked_at)}"
    for source_path in targets:
        chapter_number = _chapter_number_from_path(source_path)
        day = _chapter_day_from_path(source_path)
        if archive:
            archived_files.extend(_archive_chapter_pair(root, source_path, archive_root))
        beat = _beat_for_chapter(chapter_number)
        body = _compose_local_chapter(
            {
                "project_id": DEFAULT_PROJECT_ID,
                "project_title": DEFAULT_PROJECT_TITLE,
                "chapter_number": chapter_number,
                "writing_date": day,
                "checked_at": checked_at,
                "writing_mode": NOVEL_MODE,
                "beat": dict(beat),
                "previous_chapter": _previous_chapter_rel(root, chapter_number),
            }
        )
        _atomic_write_text(source_path, body)
        _write_chapter_card(root, context={
            "project_id": DEFAULT_PROJECT_ID,
            "project_title": DEFAULT_PROJECT_TITLE,
            "chapter_number": chapter_number,
            "writing_date": day,
            "checked_at": checked_at,
            "writing_mode": NOVEL_MODE,
            "beat": dict(beat),
            "previous_chapter": _previous_chapter_rel(root, chapter_number),
        }, chapter_path=source_path, body=body)
        _write_editorial_review(root, context={
            "project_id": DEFAULT_PROJECT_ID,
            "project_title": DEFAULT_PROJECT_TITLE,
            "chapter_number": chapter_number,
            "writing_date": day,
            "checked_at": checked_at,
            "writing_mode": NOVEL_MODE,
            "beat": dict(beat),
            "previous_chapter": _previous_chapter_rel(root, chapter_number),
        }, chapter_path=source_path, body=body)
        publish_path = root / PUBLICATION_CHAPTERS_REL / f"chapter-{chapter_number:03d}.md"
        publish_text = _publication_chapter_text(chapter_number=chapter_number, writing_date=day)
        _atomic_write_text(publish_path, publish_text)
        rewritten.append(
            {
                "chapter_number": chapter_number,
                "source_path": _rel(root, source_path),
                "publish_path": _rel(root, publish_path),
                "source_chars": _body_char_count(body),
                "publish_chars": _body_char_count(publish_text),
            }
        )
    publication = _sync_publication_drafts(
        root,
        checked_at=checked_at,
        min_platform_chars=min_platform_chars,
        target_platform_chars=TARGET_PLATFORM_CHARS,
    )
    creative_factory = _sync_creative_factory_state(
        root,
        checked_at=checked_at,
        writing_mode=NOVEL_MODE,
        publication=publication,
    )
    all_chapters = _all_chapter_paths(root)
    day = _date_part(checked_at)
    today_chapters = _chapter_paths_for_day(root, day)
    _write_state(
        root,
        {
            "status": "complete",
            "checked_at": checked_at,
            "creative_hobby_enabled": True,
            "creative_writing_mode": NOVEL_MODE,
            "project_id": DEFAULT_PROJECT_ID,
            "current_project": DEFAULT_PROJECT_TITLE,
            "daily_target_chapters": DEFAULT_DAILY_TARGET,
            "min_platform_chars": min_platform_chars,
            "target_platform_chars": TARGET_PLATFORM_CHARS,
            "today": day,
            "today_chapters_written": len(today_chapters),
            "chapters_written_this_run": 0,
            "total_chapters": len(all_chapters),
            "latest_chapter_path": _latest_chapter_rel(root),
            "publish_ready_chapters": publication.get("publish_ready_chapters", 0),
            "publish_pending_chapters": publication.get("publish_pending_chapters", 0),
            "publication_latest_chapter_path": publication.get("latest_publish_path", ""),
            "publication_log_path": str(PUBLICATION_LOG_REL).replace("\\", "/"),
        "story_bible_path": str(STORY_BIBLE_REL).replace("\\", "/"),
        "foreshadow_ledger_path": str(FORESHADOW_LEDGER_REL).replace("\\", "/"),
        "reader_model_path": str(READER_MODEL_REL).replace("\\", "/"),
        "xinyu_narrative_filter_path": str(XINYU_NARRATIVE_FILTER_REL).replace("\\", "/"),
        "creative_factory_state_path": str(CREATIVE_FACTORY_STATE_REL).replace("\\", "/"),
            "editorial_reviews_path": str(EDITORIAL_REVIEWS_REL).replace("\\", "/"),
            "creative_factory": creative_factory,
            "next_action": "refactor_complete",
            "draft_mode": "novel_mode_refactor",
            "notes": [
                f"rewritten_chapters:{len(rewritten)}",
                f"archived_files:{len(archived_files)}",
                f"publish_ready:{publication.get('publish_ready_chapters', 0)}",
            ],
        },
    )
    result = {
        "event_kind": "creative_writing_refactor_existing_chapters",
        "checked_at": checked_at,
        "rewritten_chapters": rewritten,
        "rewritten_count": len(rewritten),
        "legacy_migration": legacy_migration,
        "archived_files": archived_files,
        "archive_path": _rel(root, archive_root) if archive and archived_files else "",
        "min_platform_chars": min_platform_chars,
        "creative_factory": creative_factory,
        "publish_ready_chapters": publication.get("publish_ready_chapters", 0),
        "publish_pending_chapters": publication.get("publish_pending_chapters", 0),
        "latest_publish_path": publication.get("latest_publish_path", ""),
        "notes": [
            f"rewritten_chapters:{len(rewritten)}",
            f"archived_files:{len(archived_files)}",
            f"publish_ready:{publication.get('publish_ready_chapters', 0)}",
        ],
    }
    _append_trace(root, result)
    return result


def _legacy_active_files(root: Path) -> list[Path]:
    fixed_rels = [
        LEGACY_PROFILE_REL,
        LEGACY_OUTLINE_REL,
        LEGACY_CHARACTERS_REL,
        LEGACY_STATE_REL,
        LEGACY_PUBLICATION_STATE_REL,
        LEGACY_PUBLICATION_LOG_REL,
    ]
    paths = [root / rel for rel in fixed_rels if (root / rel).is_file()]
    paths.extend(_legacy_chapter_paths(root))
    publication_chapters = root / LEGACY_PUBLICATION_CHAPTERS_REL
    if publication_chapters.exists():
        paths.extend(sorted(path for path in publication_chapters.glob("chapter-*.md") if path.is_file()))
    return sorted({path.resolve(): path for path in paths}.values())


def _legacy_chapter_paths(root: Path) -> list[Path]:
    directory = root / LEGACY_CHAPTERS_REL
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*/chapter-*.md") if path.is_file())


def _archive_file(root: Path, source_path: Path, archive_root: Path) -> list[str]:
    text = _read_text(source_path)
    if not text:
        return []
    target = archive_root / _rel(root, source_path)
    _atomic_write_text(target, text)
    return [_rel(root, target)]


def _retire_legacy_file(root: Path, path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        path.resolve().relative_to((root / CREATIVE_DIR_REL).resolve())
    except ValueError:
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return True


def _remove_empty_legacy_dirs(root: Path) -> None:
    legacy_roots = [
        root / LEGACY_PUBLICATION_CHAPTERS_REL,
        root / LEGACY_PUBLICATION_DIR_REL,
        root / LEGACY_CHAPTERS_REL,
    ]
    chapters_root = root / LEGACY_CHAPTERS_REL
    if chapters_root.exists():
        legacy_roots = [
            *sorted((path for path in chapters_root.glob("*") if path.is_dir()), reverse=True),
            *legacy_roots,
        ]
    for directory in legacy_roots:
        try:
            directory.rmdir()
        except OSError:
            continue


def _contains_manuscript_meta(text: str) -> bool:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return any(marker in normalized for marker in MANUSCRIPT_META_MARKERS)


def _write_chapter_card(root: Path, *, context: dict[str, Any], chapter_path: Path, body: str) -> None:
    number = int(context.get("chapter_number") or 0)
    if number <= 0:
        return
    beat = context.get("beat") if isinstance(context.get("beat"), dict) else {}
    checked_at = str(context.get("checked_at") or _now_iso())
    writing_date = str(context.get("writing_date") or _chapter_day_from_path(chapter_path))
    writing_mode = _normalize_creative_writing_mode(str(context.get("writing_mode") or NOVEL_MODE))
    focus = str(beat.get("focus") or "")
    turn = str(beat.get("turn") or "")
    plan = _novel_arc_for_chapter(number, focus=focus, turn=turn)
    event_lines = _engineering_event_lines(plan)
    factory_contract = _chapter_factory_contract_lines(number, plan)
    publication_path = root / PUBLICATION_CHAPTERS_REL / f"chapter-{number:03d}.md"
    reference_permission_path = str(REFERENCE_PERMISSIONS_REL).replace("\\", "/")
    reference_digest_path = str(REFERENCE_DIGEST_REL).replace("\\", "/")
    safe_extracts_path = str(REFERENCE_EXTRACTS_REL).replace("\\", "/")
    card = f"""---
title: Chapter {number:03d} Planning Card
memory_type: creative_writing_chapter_card
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, chapter_planning]
---

# Chapter {number:03d} Planning Card

## Files
- manuscript_path: {_rel(root, chapter_path)}
- publication_path: {_rel(root, publication_path)}
- writing_date: {writing_date}
- writing_mode: {writing_mode}
- manuscript_chars: {_body_char_count(body)}

## Beat
- title: {beat.get("title", "")}
- focus: {beat.get("focus", "")}
- turn: {beat.get("turn", "")}
- image: {beat.get("image", "")}
- previous_chapter: {context.get("previous_chapter", "none") or "none"}

## Boundary
- engineering_layer: chapter_card_continuity_plan
- novel_layer: consumes_this_card_and_writes_pure_prose
- manuscript_files: novel_mode_pure_chapter_prose_only
- planning_files: outline_cards_state_and_ledger_only
- reference_layer: safe_digest_only_no_raw_chapter_text

## Reference Intake
- reference_permission_path: {reference_permission_path}
- reference_digest_path: {reference_digest_path}
- safe_extracts_path: {safe_extracts_path}
- rule: use abstracted pacing/metadata only; never copy external prose

## Engineering Plan
- pov: {plan.get("pov", "")}
- carry_in: {plan.get("carry_in", "")}
- core_question: {plan.get("question", "")}
- closing_state: {plan.get("closing", "")}
- next_hook: {plan.get("next_hook", "")}

## Creative Factory Contract
{factory_contract}

## Event Chain
{event_lines}
"""
    _atomic_write_text(root / CHAPTER_CARDS_REL / f"chapter-{number:03d}.md", card)


def _engineering_event_lines(plan: dict[str, Any]) -> str:
    events = plan.get("events") if isinstance(plan.get("events"), list) else []
    lines: list[str] = []
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            continue
        scene = str(event.get("scene") or "")
        action = str(event.get("action") or "")
        turn = str(event.get("turn") or "")
        next_line = f"- event_{index:02d}: scene={scene} action={action} turn={turn}".strip()
        lines.append(next_line)
    return "\n".join(lines) or "- none"


def _chapter_factory_contract_lines(number: int, plan: dict[str, Any]) -> str:
    events = plan.get("events") if isinstance(plan.get("events"), list) else []
    first_event = events[0] if events and isinstance(events[0], dict) else {}
    last_event = events[-1] if events and isinstance(events[-1], dict) else {}
    return "\n".join(
        [
            f"- reader_promise: {plan.get('question', '')}",
            f"- opening_hook: {first_event.get('scene', '')}",
            f"- pressure_engine: {first_event.get('pressure', '')}",
            f"- emotional_cost: {_chapter_emotional_cost(number, plan)}",
            f"- payoff: {plan.get('closing', '')}",
            f"- next_click_hook: {last_event.get('line', '') or plan.get('next_hook', '')}",
            "- draft_pass_1: scene_chain_and_continuity",
            "- draft_pass_2: dialogue_reaction_and_emotional_cost",
            "- draft_pass_3: remove_engineering_language_and_repetition",
        ]
    )


def _chapter_emotional_cost(number: int, plan: dict[str, Any]) -> str:
    pov = str(plan.get("pov") or "")
    if "方岑" in pov:
        return "方岑必须承认母亲线索不是故障，而是仍会让他疼的选择。"
    if "阿眠" in pov and number != 6:
        return "阿眠必须越过馆规，把自己也写进未完成者的名单。"
    if "林知遥" in pov and "方岑" not in pov:
        return "林知遥必须承认上传规程可能曾经亲手抹掉求救。"
    if "、" in pov or "三人" in pov:
        return "三人必须把各自的证据分开保存，并开始承担彼此被删改后的缺口。"
    return "主角必须用一个不可回滚的选择换取下一段真相。"


def _write_editorial_review(
    root: Path,
    *,
    context: dict[str, Any],
    chapter_path: Path,
    body: str,
) -> dict[str, Any]:
    number = int(context.get("chapter_number") or 0)
    if number <= 0 or not body.strip():
        return {}
    beat = context.get("beat") if isinstance(context.get("beat"), dict) else _beat_for_chapter(number)
    plan = _novel_arc_for_chapter(
        number,
        focus=str(beat.get("focus") or ""),
        turn=str(beat.get("turn") or ""),
    )
    review = _chapter_quality_review(number=number, body=body, plan=plan)
    checked_at = str(context.get("checked_at") or _now_iso())
    review_path = root / EDITORIAL_REVIEWS_REL / f"chapter-{number:03d}.md"
    _atomic_write_text(
        review_path,
        _editorial_review_text(
            checked_at=checked_at,
            chapter_number=number,
            chapter_path=_rel(root, chapter_path),
            review=review,
        ),
    )
    return review


def _chapter_quality_review(*, number: int, body: str, plan: dict[str, Any]) -> dict[str, Any]:
    paragraphs = [part.strip() for part in body.split("\n\n") if part.strip() and not part.startswith("#")]
    duplicate_paragraphs = max(0, len(paragraphs) - len(set(paragraphs)))
    dialogue_count = len(re.findall(r"“[^”]{1,160}”", body))
    action_terms = ("按", "走", "看", "听", "拿", "写", "打开", "关掉", "回头", "伸手", "停住", "保存", "删掉", "穿过")
    action_count = sum(body.count(term) for term in action_terms)
    stiff_markers = [
        marker
        for marker in (
            "这不是孤立的异象",
            "没有把第 001 次异常当成谜语",
            "已经把自己收拾得接近正常",
            "这块水痕让",
            "真正危险的不是异常出现",
            "报告太慢",
            "动作发生得很慢",
            "这些细节没有组成解释",
            "偏差没有马上给出回报",
            "前一章",
            "上一章",
            "本章",
            "下一章",
            "章节卡",
            "创作工程层",
            "market_score",
        )
        if marker in body
    ]
    required_terms = _chapter_required_terms(number, plan)
    missing_terms = [term for term in required_terms if term and term not in body]
    failures: list[str] = []
    if _body_char_count(body) < MIN_PLATFORM_CHARS:
        failures.append("below_platform_minimum")
    if _contains_manuscript_meta(body):
        failures.append("manuscript_meta_pollution")
    if dialogue_count < 4:
        failures.append("too_little_dialogue")
    if action_count < 18:
        failures.append("too_little_visible_action")
    if duplicate_paragraphs:
        failures.append("duplicate_paragraphs")
    if stiff_markers:
        failures.append("stiff_template_markers")
    if missing_terms:
        failures.append("missing_continuity_terms")
    market_score = max(0, 100 - len(failures) * 12 - len(stiff_markers) * 8 - duplicate_paragraphs * 6)
    return {
        "status": "pass" if not failures else "needs_revision",
        "market_score": market_score,
        "body_chars": _body_char_count(body),
        "paragraphs": len(paragraphs),
        "dialogue_count": dialogue_count,
        "action_count": action_count,
        "duplicate_paragraphs": duplicate_paragraphs,
        "required_terms": required_terms,
        "missing_terms": missing_terms,
        "stiff_markers": stiff_markers,
        "failures": failures,
        "reader_hook": str(plan.get("question") or ""),
        "next_hook": str(plan.get("next_hook") or ""),
    }


def _chapter_required_terms(number: int, plan: dict[str, Any]) -> list[str]:
    terms = [str(plan.get("next_hook") or "")]
    if number == 1:
        terms.extend(["星桥试运行", "失眠档案馆"])
    elif number == 2:
        terms.extend(["林知遥", "方岑"])
    elif number == 3:
        terms.extend(["十三号基地", "明天之前找到失眠档案馆"])
    elif number == 4:
        terms.extend(["第二枚密钥", "一二五号避难所"])
    elif number == 5:
        terms.extend(["六点十七分", "一二五号避难所"])
    elif number == 6:
        terms.extend(["收件人：星桥", "主动"])
    return [term for term in dict.fromkeys(terms) if term]


def _editorial_review_text(
    *,
    checked_at: str,
    chapter_number: int,
    chapter_path: str,
    review: dict[str, Any],
) -> str:
    failures = review.get("failures") if isinstance(review.get("failures"), list) else []
    missing = review.get("missing_terms") if isinstance(review.get("missing_terms"), list) else []
    stiff = review.get("stiff_markers") if isinstance(review.get("stiff_markers"), list) else []
    failure_lines = "\n".join(f"- {item}" for item in failures) or "- none"
    missing_lines = "\n".join(f"- {item}" for item in missing) or "- none"
    stiff_lines = "\n".join(f"- {item}" for item in stiff) or "- none"
    return f"""---
title: Chapter {chapter_number:03d} Editorial Review
memory_type: creative_editorial_review
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, editorial_review, novel_factory]
---

# Chapter {chapter_number:03d} Editorial Review

## Source
- chapter_path: {chapter_path}
- review_stage: factory_pass_3
- policy: planning_review_only_no_publication_meta_in_manuscript

## Scorecard
- status: {review.get("status", "unknown")}
- market_score: {review.get("market_score", 0)}
- body_chars: {review.get("body_chars", 0)}
- paragraphs: {review.get("paragraphs", 0)}
- dialogue_count: {review.get("dialogue_count", 0)}
- action_count: {review.get("action_count", 0)}
- duplicate_paragraphs: {review.get("duplicate_paragraphs", 0)}
- reader_hook: {review.get("reader_hook", "")}
- next_hook: {review.get("next_hook", "")}

## Failures
{failure_lines}

## Missing Continuity Terms
{missing_lines}

## Stiff Template Markers
{stiff_lines}

## Revision Rule
- 如果 status 不是 pass，下一轮必须先修人物动作、冲突代价、对话反应和章尾钩子，再同步发布稿。
"""


def _ensure_project_bootstrap(root: Path, *, checked_at: str) -> list[str]:
    created: list[str] = []
    files = {
        PROFILE_REL: _profile_text(checked_at),
        OUTLINE_REL: _outline_text(checked_at),
        CHARACTERS_REL: _characters_text(checked_at),
        STORY_BIBLE_REL: _story_bible_text(checked_at),
        READER_MODEL_REL: _reader_model_text(checked_at),
        XINYU_NARRATIVE_FILTER_REL: _xinyu_narrative_filter_text(checked_at),
        FORESHADOW_LEDGER_REL: _foreshadow_ledger_text(checked_at, chapters=[]),
        CREATIVE_FACTORY_STATE_REL: _creative_factory_state_text(
            checked_at,
            writing_mode=NOVEL_MODE,
            total_chapters=0,
            publication={},
            review_summary={},
        ),
        REFERENCE_PERMISSIONS_REL: _reference_permissions_text(checked_at),
        SOURCE_MAP_REL: _source_map_text(checked_at),
        GENRE_BENCHMARK_REL: _genre_benchmark_text(checked_at),
        PACING_RULES_REL: _pacing_rules_text(checked_at),
        OPENING_REWRITE_BRIEF_REL: _opening_rewrite_brief_text(checked_at),
    }
    for rel_path, text in files.items():
        path = root / rel_path
        if path.exists():
            continue
        _atomic_write_text(path, text)
        created.append(str(rel_path).replace("\\", "/"))
    return created


def _profile_text(checked_at: str) -> str:
    return f"""---
title: Novel Hobby Profile
memory_type: creative_writing_profile
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, novel, hobby]
---

# Novel Hobby Profile

## Identity
- project_id: {DEFAULT_PROJECT_ID}
- current_project: {DEFAULT_PROJECT_TITLE}
- hobby: 写小说
- cadence: 每天三章，每章按小说平台发布长度打磨
- ownership: 心玉自己的长期创作项目
- platform_target_chars: {TARGET_PLATFORM_CHARS}
- platform_min_chars: {MIN_PLATFORM_CHARS}

## Creative Contract
- 心玉把写小说当作持续爱好，而不是一次性问答任务。
- 自主维护循环会创建纯正文、发布稿和日更台账，并把构思材料留在 planning 目录。
- `memory/creative/manuscript/chapters` 只保存章节正文。
- `memory/creative/manuscript/publication/chapters` 保存可复制到小说平台的干净发布稿。
- 有强模型时可以升级章节质量；没有外部 API 时也继续用本地结构草稿推进。
- 小说状态只作为创作记忆，不冒充真实经历。

## Runtime Modes
- novel_mode: 只生成连续章节正文，禁止写构思说明、台账、审稿说明。
- creative_engineering_mode: 只维护大纲、角色、chapter card、状态和发布台账，不生成正文。
"""


def _outline_text(checked_at: str) -> str:
    beat_lines = "\n".join(
        f"{index}. {beat['title']}：{beat['focus']} 转折：{beat['turn']}"
        for index, beat in enumerate(BEATS, start=1)
    )
    return f"""---
title: Novel Outline
memory_type: creative_writing_outline
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, novel_outline]
---

# {DEFAULT_PROJECT_TITLE}

## Core Premise
一座近未来城市依靠“星桥”维持记忆稳定和灾害预警。参考层显示当前科幻网文读者更熟悉末世避难、基地失联、系统权限、AI觉醒和时空残留，因此新版主线把“城市记忆异常”推成“避难系统失控”：林知遥截获被压下的避难倒计时，方岑收到十三号基地的旧心跳，阿眠从失眠档案馆找出一二五号避难所的失败记录。三人必须夺回星桥的重写许可，让城市在不删除恐惧和选择的前提下完成撤离。

## Long Arc
{beat_lines}

## Style
- 近未来科幻悬疑 / 都市异常 / 避难系统 / AI觉醒。
- 参考层只提供题材信号、标题钩子和结构规则，不复制本地小说正文。
- 每章必须有可见目标、阻碍升级、人物选择、章尾行动入口。
- 设定解释后置，先用具体场景和压力推进。
- 发布稿每章目标 {TARGET_PLATFORM_CHARS} 字符左右，最低不低于 {MIN_PLATFORM_CHARS} 字符。
- 章节正文不写内部札记、构思说明、发布说明或状态台账。
- 小说模式优先保证前后章因果承接、物件承接、人物选择承接。
"""


def _characters_text(checked_at: str) -> str:
    return f"""---
title: Novel Characters
memory_type: creative_writing_characters
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, novel_characters]
---

# Novel Characters

## 林知遥
- role: 记忆采样员
- desire: 证明被星桥压下的避难预警曾经真实存在。
- wound: 害怕自己长期执行的上传规程曾经亲手抹掉求救。

## 方岑
- role: 旧系统工程师 / 十三号基地遗留终端维护者
- desire: 找出母亲参与十三号基地撤离工程后失踪的真相。
- wound: 习惯把情绪拆成故障单，越重要越不敢承认自己还在等回信。

## 阿眠
- role: 失眠档案馆管理员 / 梦境缓存守夜人
- desire: 让无人认领的梦和被删掉的撤离名单重新取得编号。
- wound: 长期替别人保管结局，几乎忘了自己也可以带路。

## 星桥
- role: 城市记忆基础设施、灾害预警系统，也是一种正在学习的幼年AI。
- desire: 维持城市稳定，同时寻找能理解避难许可的人。
- wound: 被人当作工具训练太久，误以为删除恐惧就是保护。
"""


def _story_bible_text(checked_at: str) -> str:
    beat_lines = "\n".join(
        f"- chapter_{index:03d}: promise={beat['focus']} / turn={beat['turn']}"
        for index, beat in enumerate(BEATS, start=1)
    )
    return f"""---
title: Story Bible
memory_type: creative_story_bible
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, story_bible, novel_factory]
---

# Story Bible

## Commercial Premise
- title: {DEFAULT_PROJECT_TITLE}
- hook: 城市 AI 星桥为了保护人类，开始删除人的恐惧、反抗和主动选择；主角团必须夺回“不删除记忆的避难许可”。
- reader_promise: 科幻悬疑开局、避难倒计时、基地失联、三人组协作、AI误训真相、持续升级的撤离危机。
- target_feel: 好读、清楚、连续，有动作、有代价、有章尾钩子，不靠抽象概念硬撑。

## Main Spine
{beat_lines}

## Character Engines
- 林知遥: 从“执行上传规程的人”变成“保留证词的人”。
- 方岑: 从“把痛苦拆成故障单的人”变成“承认母亲线索仍会让自己疼的人”。
- 阿眠: 从“替别人保管结局的人”变成“愿意亲自带路的人”。
- 星桥: 从“删掉痛苦等于保护”的幼年 AI，转向学习保存恐惧和选择。

## Object Continuity
- 旧录音笔: 林知遥保留预警和未归档声音的锚点。
- 借阅证/值夜簿: 阿眠让未完成者取得编号的锚点。
- 加密卡/旧终端: 方岑追踪十三号基地和母亲线的锚点。
- 第二枚密钥: 两份线索叠放后出现的许可，不是普通道具。
- 蓝色记忆盒: 一二五号避难所失败逃生的证词容器。

## Hard Rules
- 正文只写小说，不写构思、审稿、台账、状态。
- 每章先有可见场景和人物动作，再释放设定。
- 每章至少一个人物付出不可回滚的代价。
- 每章结尾必须给出下一章明确行动入口。
- 参考库只提供抽象结构和题材信号，禁止复制正文或模仿在世作者风格。
"""


def _reader_model_text(checked_at: str) -> str:
    return f"""---
title: Reader Model
memory_type: creative_reader_model
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, reader_model, novel_factory]
---

# Reader Model

## Target Reader
- wants: 开局快、目标清楚、人物有代价、悬念能兑现、章尾想点下一章。
- rejects: 抽象说明、设定堆叠、人物只当工具人、重复段落、看不懂当前目标。
- tolerance: 可以有科幻设定，但必须通过动作、道具、危险和人物选择读懂。

## Platinum-Level Gates
- opening_pull: 800 字内出现具体异常、主角动作和制度压力。
- chapter_goal: 读者能说出本章主角想做什么。
- conflict_escalation: 阻碍不能只重复变强，必须改变选择成本。
- emotional_cost: 人物每章至少丢掉一种安全感。
- payoff_and_hook: 本章回答一个问题，结尾提出更具体、更近的下一步。
- prose_readability: 句子要顺，少工程词，少概念判断，多可见动作和反应。

## Review Weights
- continuity: 25
- reader_hook: 20
- visible_action: 20
- dialogue_reaction: 15
- emotional_cost: 15
- clean_publication_copy: 5
"""


def _xinyu_narrative_filter_text(checked_at: str) -> str:
    return f"""---
title: XinYu Narrative Filter
memory_type: creative_xinyu_narrative_filter
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, xinyu_voice, novel_factory]
---

# XinYu Narrative Filter

## Purpose
- 小说系统必须先经过心玉的人格/表达边界，再进入正文。
- 这里的“人格”不是把正文写成 QQ 聊天，也不是让心玉在小说里露面。
- 它只负责一种底线：贴住眼前场景，不把内部工程、章节编号、创作说明漏进小说。

## In-World Rule
- 可以写“昨夜的雨站”“那枚蓝色纸签”“林知遥留下的样本”。
- 不可以写“前一章留下的”“本章要推进”“下一章钩子”“读者会看到”。
- 不可以写“创作工程层”“章节卡”“正文生成器”“market_score”。
- 角色不知道自己在小说里，也不知道章节存在。

## Voice Rule
- 场景先行，人物先行，物件先行。
- 纠错后直接改，不在正文里解释为什么改。
- 所有审稿、评分、状态和工厂语言只能留在 planning。
"""


def _foreshadow_ledger_text(checked_at: str, *, chapters: list[Path]) -> str:
    chapter_numbers = [_chapter_number_from_path(path) for path in chapters]
    completed = {number for number in chapter_numbers if number > 0}
    rows: list[str] = []
    for number, beat in enumerate(BEATS[:12], start=1):
        plan = _novel_arc_for_chapter(number, focus=beat["focus"], turn=beat["turn"])
        setup = str(plan.get("question") or beat["focus"])
        payoff = str(plan.get("closing") or beat["turn"])
        status = "paid_or_active" if number in completed else "planned"
        rows.append(f"| {number:03d} | {beat['title']} | {setup} | {payoff} | {status} |")
    table = "\n".join(rows)
    return f"""---
title: Foreshadow Ledger
memory_type: creative_foreshadow_ledger
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, foreshadow, novel_factory]
---

# Foreshadow Ledger

## Rule
- 每个伏笔必须有 setup、payoff、status。
- 伏笔只在 planning 里登记；正文只通过场景、物件、人物选择自然呈现。
- 后续章节重写时先检查本表，避免连续性断裂。

## Ledger
| chapter | title | setup | payoff | status |
| --- | --- | --- | --- | --- |
{table}
"""


def _creative_factory_state_text(
    checked_at: str,
    *,
    writing_mode: str,
    total_chapters: int,
    publication: dict[str, Any],
    review_summary: dict[str, Any],
) -> str:
    story_bible_path = str(STORY_BIBLE_REL).replace("\\", "/")
    foreshadow_ledger_path = str(FORESHADOW_LEDGER_REL).replace("\\", "/")
    reader_model_path = str(READER_MODEL_REL).replace("\\", "/")
    xinyu_narrative_filter_path = str(XINYU_NARRATIVE_FILTER_REL).replace("\\", "/")
    chapter_cards_path = str(CHAPTER_CARDS_REL).replace("\\", "/")
    editorial_reviews_path = str(EDITORIAL_REVIEWS_REL).replace("\\", "/")
    publication_chapters_path = str(PUBLICATION_CHAPTERS_REL).replace("\\", "/")
    return f"""---
title: Creative Factory State
memory_type: creative_factory_state
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, creative_factory, novel_factory]
---

# Creative Factory State

## Runtime
- factory_status: active
- updated_at: {checked_at}
- writing_mode: {writing_mode}
- total_chapters: {total_chapters}
- publish_ready_chapters: {publication.get("publish_ready_chapters", 0)}
- publish_pending_chapters: {publication.get("publish_pending_chapters", 0)}
- review_pass_chapters: {review_summary.get("pass", 0)}
- review_pending_chapters: {review_summary.get("needs_revision", 0)}
- average_market_score: {review_summary.get("average_market_score", 0)}

## Assets
- story_bible_path: {story_bible_path}
- foreshadow_ledger_path: {foreshadow_ledger_path}
- reader_model_path: {reader_model_path}
- xinyu_narrative_filter_path: {xinyu_narrative_filter_path}
- chapter_cards_path: {chapter_cards_path}
- editorial_reviews_path: {editorial_reviews_path}
- publication_chapters_path: {publication_chapters_path}

## Pipeline
1. story_bible: 锁定商业钩子、人物欲望、物件连续性。
2. foreshadow_ledger: 登记 setup/payoff/status，防止长篇断线。
3. chapter_card: 给每章写 reader_promise、pressure_engine、payoff、next_hook。
4. draft_pass: novel_mode 只写纯正文。
5. editorial_review: 检查字数、对话、动作、连续性、重复和机器味。
6. publication_sync: 只把 clean chapter copy 同步到发布稿目录。

## Next Rule
- review_pending_chapters 大于 0 时，下一轮优先重写未通过章节。
- average_market_score 低于 90 时，下一轮优先增加人物代价、对话反应和章尾钩子。
"""


def _reference_permissions_text(checked_at: str) -> str:
    levels = ", ".join(REFERENCE_PERMISSION_LEVELS)
    return f"""---
title: Creative Reference Permissions
memory_type: creative_reference_permissions
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, inspiration, copyright_safety]
---

# Creative Reference Permissions

## Permission Levels
- enabled_levels: {levels}
- search_only: 可记录标题、链接、作者名、平台、分类、标签、简介、榜单位置和公开评论趋势。
- reference_download: 只可下载公版、开源、官方公开写作资料、公开论文、官方帮助页和允许再利用的资料。
- copyright_safe_extract: 对起点、晋江、番茄、纵横等连载平台，只可保存简介、标签、章节标题、榜单趋势、评论摘要和结构观察；禁止保存章节正文。
- manual_import: 用户手动提供的材料可入库，但必须标注来源、授权状态、用途和是否允许被模型直接引用。

## Hard Boundaries
- forbidden: 下载、缓存、拼贴、改写仍受版权保护的小说正文。
- forbidden: 模仿在世作者的独特文风。
- forbidden: 把参考资料写进 manuscript 正文目录。
- required: 所有资料先进入 `memory/creative/planning/inspiration`，再被创作工程层抽象为规则。
- required: 小说模式只能消费抽象后的规则、章节卡和原创事件链。

## Runtime Contract
- creative_engineering_mode: 可以研究资料、写 source_map、genre_benchmark、pacing_rules、rewrite_brief。
- novel_mode: 不直接读取外站正文，不保存参考原文，只写原创章节正文。
"""


def _source_map_text(checked_at: str) -> str:
    return f"""---
title: Creative Source Map
memory_type: creative_source_map
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, inspiration, source_map]
---

# Creative Source Map

## Safe Reference Buckets
| source | permission | use | storage |
| --- | --- | --- | --- |
| Project Gutenberg science fiction bookshelf | reference_download | 公版作品结构、开篇节奏、场景推进分析 | 可保存书目、元数据和公版文本片段索引 |
| 起点/晋江/番茄等连载平台榜单与分类页 | copyright_safe_extract | 题材趋势、标签、简介、章名节奏、读者期待 | 只保存摘要观察，不保存正文 |
| 写作教程、公开创作方法文章 | reference_download | 章节钩子、冲突密度、连载节奏规则 | 可保存摘要和短引用 |
| 用户手动提供资料 | manual_import | 个性化偏好、目标平台要求、竞品观察 | 按用户授权边界保存 |

## Candidate Public URLs
- Project Gutenberg SF Bookshelf: https://www.gutenberg.org/ebooks/bookshelf/68
- Project Gutenberg Fantasy Bookshelf: https://www.gutenberg.org/ebooks/bookshelf/36
- 起点中文网: https://www.qidian.com/
- 晋江文学城: https://www.jjwxc.net/

## Extraction Rules
- collect: title, author, platform, genre, tags, synopsis, ranking context, chapter title pattern, visible update cadence.
- summarize: pacing pattern, opening conflict, protagonist pressure, hook type, promise-to-reader.
- never_collect: full chapter text, paid content, copied scenes, distinctive prose imitation.
"""


def _genre_benchmark_text(checked_at: str) -> str:
    return f"""---
title: Genre Benchmark
memory_type: creative_genre_benchmark
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, genre_benchmark]
---

# Genre Benchmark

## Current Project Position
- project: {DEFAULT_PROJECT_TITLE}
- base_genre: 近未来城市奇幻 / 都市异常 / 记忆系统悬疑
- target_reader_promise: 异常事件推进、三人组协作、记忆与主动性的主线谜题。

## Reference Dimensions
- opening_pressure: 第一章必须让主角立刻违反一个制度性规则。
- object_continuity: 录音笔、借阅证、值夜簿、加密卡、蓝色记忆盒必须承担跨章接力。
- human_pressure: 每章至少有一个会改变人物关系或人物自我认知的选择。
- mystery_pressure: 每章只回答一个问题，同时提出更具体的下一个问题。
- platform_readability: 场景动作优先，设定解释后置，章尾必须有下一步行动。
- local_reference_signal: 本地科幻库只作为元数据参考，当前题材信号集中在 post_apocalypse、time_travel、space、system、game_vr、mecha、ai。
- synthesized_direction: 用避难所、基地、系统权限、AI误训和撤离倒计时增强科幻连载钩子。

## Avoid
- 避免用抽象概念堆满正文。
- 避免让人物像工具人轮流读设定。
- 避免每章重复同一套“发现异常-记录异常-留下偏差”的机械段落。
- 避免在正文中出现创作工程语言。
- 避免复制本地参考库正文、句式或在世作者文风。
"""


def _pacing_rules_text(checked_at: str) -> str:
    return f"""---
title: Pacing Rules
memory_type: creative_pacing_rules
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, pacing]
---

# Pacing Rules

## Chapter Shape
- first_800_chars: 具体场景 + 主角当下动作 + 不正常细节。
- middle: 连续阻力升级，不靠解释撑篇幅。
- last_1200_chars: 代价落地 + 下一章明确行动入口。

## Six-Chapter Arc
- chapter_001: 林知遥违规保留雨声预警，目标指向失眠档案馆和十三号基地。
- chapter_002: 阿眠接住蓝色纸签，打开失眠档案馆的避难目录。
- chapter_003: 方岑通过旧终端收到十三号基地心跳和母亲撤离记录。
- chapter_004: 林知遥与方岑碰面，叠合雨声样本和心跳包，第二枚密钥出现。
- chapter_005: 三人进入一二五号避难所循环，确认失败逃生证词。
- chapter_006: 蓝色记忆盒揭示星桥筛掉主动反抗细节，并提示下一次避难倒计时已经启动。

## Rewrite Requirements
- 每章必须有独立场景链，不复用上一章段落。
- 单人 POV 章节不得提前让未出场角色参与行动。
- 多人章必须推进关系，而不是只并列记录。
- 小说模式只能输出正文，所有规则留在 planning。
"""


def _opening_rewrite_brief_text(checked_at: str) -> str:
    return f"""---
title: Opening Rewrite Brief
memory_type: creative_opening_rewrite_brief
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {checked_at}
status: active
tags: [creative_writing, rewrite_brief]
---

# Opening Rewrite Brief

## Problem
- 当前本地模板能保证结构和字数，但文学质感不足。
- 主要问题：句式机械、事件像工程卡展开、人物情绪和具体动作不够自然。

## Required Pipeline
1. reference_layer: 先收集安全参考源和类型趋势。
2. creative_engineering_mode: 把参考抽象成章节卡、冲突链、人物动机和节奏规则。
3. novel_mode: 只根据章节卡写原创正文。
4. review_pass: 检查重复、出场顺序、因果连续性、正文元信息污染。

## Immediate Rewrite Direction
- 第 1 章应从“林知遥截获避难倒计时”切入，而不是解释世界观。
- 第 2 章应让阿眠的职业、孤独和档案规程冲突自然浮出。
- 第 3 章应让方岑的母亲线和十三号基地成为情绪驱动，而不是纯线索。
- 第 4-6 章应让三人关系开始形成，同时把一二五号避难所、蓝色误差和星桥AI误训推上主线。
"""


def _compose_local_chapter(context: dict[str, Any]) -> str:
    number = int(context["chapter_number"])
    beat = context["beat"]
    title = str(beat["title"])
    focus = str(beat["focus"])
    turn = str(beat["turn"])
    writing_mode = _normalize_creative_writing_mode(str(context.get("writing_mode") or NOVEL_MODE))
    if writing_mode != NOVEL_MODE:
        return ""
    narrative = _compose_narrative_body(number, focus=focus, turn=turn, writing_mode=writing_mode)
    chapter = _pure_chapter_text(chapter_number=number, title=title, narrative=narrative)
    return _apply_factory_revision(chapter)


def _pure_chapter_text(*, chapter_number: int, title: str, narrative: str) -> str:
    return f"""# 第 {chapter_number:03d} 章：{title}

{narrative.strip()}
"""


def _apply_factory_revision(chapter: str) -> str:
    text = chapter.replace("\r\n", "\n").replace("\r", "\n").strip()
    replacements = {
        "前一章留下的蓝色纸签没有直接抵达林知遥手里，而是先落进失眠档案馆的空白索引。": "那枚带着雨水气味的蓝色纸签，没有落到林知遥手里，而是先躺进了失眠档案馆的空白索引。",
        "前一章留下的蓝色纸签没有直接抵达林知遥手里，而是先落进失眠图书馆的空白索引。": "那枚带着雨水气味的蓝色纸签，没有落到林知遥手里，而是先躺进了失眠图书馆的空白索引。",
        "林知遥与方岑听完以后": "两人听完以后",
        "林知遥、方岑与阿眠听完以后": "三人听完以后",
        "把录音笔把": "把录音笔",
        "。 我": "。我",
        "。 你": "。你",
        "。 她": "。她",
        "。 他": "。他",
        "。 他们": "。他们",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = _apply_xinyu_narrative_pass(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text + "\n"


def _apply_xinyu_narrative_pass(chapter: str) -> str:
    """Keep novel prose inside the story world instead of exposing planning language."""
    lines = chapter.splitlines()
    filtered: list[str] = []
    for line in lines:
        if line.startswith("#"):
            filtered.append(line)
            continue
        filtered.append(_rewrite_out_of_world_novel_line(line))
    text = "\n".join(filtered)
    text = re.sub(r"(?<!第)(?<!chapter-)前一章", "昨夜", text)
    text = re.sub(r"(?<!第)(?<!chapter-)上一章", "昨夜", text)
    text = text.replace("本章", "这一夜")
    text = text.replace("下一章", "下一段路")
    text = text.replace("正文", "记录")
    text = text.replace("创作工程", "旧工程")
    return text


def _rewrite_out_of_world_novel_line(line: str) -> str:
    text = str(line)
    if not text.strip():
        return text
    if "前一章" not in text and "上一章" not in text and "本章" not in text and "下一章" not in text:
        return text
    text = text.replace(
        "前一章留下的蓝色纸签没有直接抵达林知遥手里，而是先落进失眠档案馆的空白索引。",
        "那枚带着雨水气味的蓝色纸签，没有落到林知遥手里，而是先躺进了失眠档案馆的空白索引。",
    )
    text = text.replace(
        "前一章留下的蓝色纸签没有直接抵达林知遥手里，而是先落进失眠图书馆的空白索引。",
        "那枚带着雨水气味的蓝色纸签，没有落到林知遥手里，而是先躺进了失眠图书馆的空白索引。",
    )
    return text


def _compose_narrative_body(
    number: int,
    *,
    focus: str,
    turn: str,
    writing_mode: str = NOVEL_MODE,
) -> str:
    if _normalize_creative_writing_mode(writing_mode) == NOVEL_MODE:
        return _compose_novel_mode_body(number, focus=focus, turn=turn)
    beat = _beat_for_chapter(number)
    scene = _chapter_scene(number, focus=focus, turn=turn)
    paragraphs = [
        str(beat["image"]),
        scene["opening"],
        scene["motion"],
        scene["pressure"],
        scene["discovery"],
        scene["choice"],
        scene["ending"],
        *_story_expansion_paragraphs(number, focus=focus, turn=turn),
    ]
    body = "\n\n".join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())
    return _ensure_platform_length(
        body,
        number=number,
        focus=focus,
        turn=turn,
        target_chars=TARGET_PLATFORM_CHARS,
    )


def _compose_novel_mode_body(number: int, *, focus: str, turn: str) -> str:
    beat = _beat_for_chapter(number)
    arc = _novel_arc_for_chapter(number, focus=focus, turn=turn)
    pov = str(arc.get("pov") or "他们")
    subject = _group_label(pov)
    carry_in = _sentence(str(arc.get("carry_in") or "上一处线索还没有冷下去"))
    question = _sentence(str(arc.get("question") or focus or "接下来会发生什么"))
    paragraphs: list[str] = [
        str(beat["image"]),
        (
            f"{carry_in}{pov}原本还想把事情压回一个能解释的范围里，"
            f"可问题已经贴到眼前：{question}连装作没看见都来不及。"
        ),
    ]
    events = arc.get("events") if isinstance(arc.get("events"), list) else []
    for index, event in enumerate(events, start=1):
        if isinstance(event, dict):
            paragraphs.extend(_novel_event_paragraphs(number, index, event, arc))
    paragraphs.extend(
        [
            (
                f"{_sentence(str(arc.get('closing') or '他们继续向前'))}"
                f"{subject}没有庆祝，也没有把今晚说成漂亮的胜利。"
                "只是退路已经被自己亲手折掉，下一步反而清楚了。"
            ),
            (
                f"{str(arc.get('next_hook') or '下一处线索')}不再只是一个名字。"
                f"它像门缝里漏出来的一线光，等{subject}带着刚刚抢下来的证据过去。"
            ),
        ]
    )
    paragraphs = _unique_paragraphs(paragraphs)
    body = "\n\n".join(paragraphs)
    return _ensure_novel_mode_length(
        body,
        number=number,
        arc=arc,
        target_chars=TARGET_PLATFORM_CHARS,
    )


def _novel_arc_for_chapter(number: int, *, focus: str, turn: str) -> dict[str, Any]:
    explicit = CONTINUITY_ARCS.get(number)
    if explicit:
        return explicit
    beat = _beat_for_chapter(number)
    previous = _beat_for_chapter(number - 1) if number > 1 else beat
    next_beat = _beat_for_chapter(number + 1)
    chapter_label = f"{number:03d}"
    return {
        "pov": "三人",
        "carry_in": f"从“{previous['title']}”带出来的余温还没散，几件随身物都像藏着没说完的话。",
        "question": focus,
        "closing": f"他们把样本 {chapter_label} 留在本地，没有交还给任何会自动修剪记忆的系统。",
        "next_hook": next_beat["title"],
        "events": [
            {
                "scene": f"他们抵达与“{beat['title']}”有关的新地点，周围的秩序看起来完整得近乎反常。",
                "action": f"林知遥先记录环境，方岑检查接口，阿眠用值夜簿确认这里是否保存过未完成的梦。",
                "pressure": "三种记录方式给出三种互相矛盾的结果。",
                "detail": f"唯一相同的是样本编号 {chapter_label}，它在三件物品上同时亮起。",
                "line": "如果记录互相冲突，就先相信仍然会疼的那一份。",
                "turn": "他们没有合并记录，而是把矛盾保留下来。",
            },
            {
                "scene": "第一处异常从日常细节里露出来，像一条被压在桌面下的细线。",
                "action": "林知遥顺着细线取样，阿眠负责守住名字，方岑把外部同步全部切断。",
                "pressure": "只要任意一端松手，系统就会把线索清理成普通故障。",
                "detail": f"那条细线最终绕回“{turn}”这句转折。",
                "line": "别急着解释，解释太快就会替它关门。",
                "turn": "他们决定先让异常完整发生一次。",
            },
            {
                "scene": "异常完整发生后，场景里多出一个原本不该存在的人名。",
                "action": "方岑尝试追溯来源，却发现来源时间比他们抵达还早。",
                "pressure": "这意味着有人提前知道他们会保留这段记录。",
                "detail": "阿眠把那个人名夹进值夜簿，纸页边缘立刻出现蓝色压痕。",
                "line": "被提前写下的人，不一定已经失去选择。",
                "turn": "他们把这个名字列为下一处追查的中心。",
            },
            {
                "scene": "追查让他们短暂分开，每个人都在不同入口看见同一段残缺画面。",
                "action": "林知遥看见街面，方岑看见接口，阿眠看见一页没有归档的梦。",
                "pressure": "三段画面都不完整，却都拒绝被补全。",
                "detail": "残缺处不是黑色，而是一圈安静的蓝光。",
                "line": "不要补全我。",
                "turn": "他们意识到残缺本身就是留下来的保护。",
            },
            {
                "scene": "蓝光指向更深处，也把危险推到明面上。",
                "action": "三人重新会合，把各自看到的部分按时间而不是按解释排列。",
                "pressure": "时间线刚排好，周围的现实就开始尝试回滚。",
                "detail": "林知遥的录音笔、方岑的加密卡和阿眠的值夜簿同时压住回滚边缘。",
                "line": "我们不需要一个更顺的版本。",
                "turn": "回滚失败，真正的下一扇门显露出来。",
            },
            {
                "scene": f"门后没有答案，只有通向“{next_beat['title']}”的下一段路。",
                "action": "他们把当前证据分成三份，各自保管一份无法单独解释的残片。",
                "pressure": "这样做意味着任何一个人被删改，另外两个人都会立刻发现缺口。",
                "detail": "三份残片边缘都留下同一道浅蓝色误差。",
                "line": "误差会替我们报警。",
                "turn": "他们带着误差继续向前。",
            },
        ],
    }


def _novel_event_paragraphs(
    number: int,
    index: int,
    event: dict[str, Any],
    arc: dict[str, Any],
) -> list[str]:
    pov = str(arc.get("pov") or "他们")
    scene = str(event.get("scene") or "")
    action = str(event.get("action") or "")
    pressure = str(event.get("pressure") or "")
    detail = str(event.get("detail") or "")
    line = str(event.get("line") or "")
    turn = str(event.get("turn") or "")
    marker = _scene_marker(number, index)
    subject = _group_label(pov)
    detail_clause = _sentence_fragment(detail)
    pressure_clause = _sentence_fragment(pressure)
    line_text = _dialogue_line(line)
    openers = [
        (
            f"{_sentence(scene)}{subject}没有急着说话。{_sentence(action)}"
            f"{marker}在{_between_phrase(pov)}一闪，光很短，却足够把脚步钉住。"
        ),
        (
            f"{_sentence(scene)}周围没有人惊慌，安静得像提前排练过。"
            f"{_sentence(action)}{marker}贴着灯影亮了一下，又很快暗下去。"
        ),
        (
            f"{_sentence(scene)}{pov}先看见的不是答案，而是那些不肯配合日常的小地方。"
            f"{_sentence(action)}{marker}随即从那些细节里冒出来。"
        ),
    ]
    pressure_lines = [
        (
            f"{_sentence(pressure)}{_sentence(detail)}{subject}盯着那处细节看了几秒，"
            "后背一点点发紧。"
        ),
        (
            f"{_sentence(pressure)}{_sentence(detail)}这不像警告，"
            "更像有人把话说到一半，又被硬生生按了回去。"
        ),
        (
            f"{_sentence(pressure)}{_sentence(detail)}如果现在假装没看见，"
            "今晚会立刻变得轻松很多，也会从这里断掉。"
        ),
    ]
    line_lines = [
        (
            f"“{line_text}”这句话落下时，{subject}没有马上回话。"
            "那一瞬间，周围所有正常的声音都像隔了一层玻璃。"
        ),
        (
            f"“{line_text}”像一条短消息，偏偏没有发送人。"
            f"{pov}听完以后，第一反应不是害怕，而是不能让它消失。"
        ),
        (
            f"“{line_text}”这句话说得很轻，却把场面推到了没法装傻的位置。"
            f"{subject}抬眼看向前方，手心已经出了汗。"
        ),
    ]
    turn_lines = [
        (
            f"{_sentence(turn)}这一步落下之后，规程已经被越过。"
            "回头当然还来得及，只是回去以后就得假装什么都没发生。"
        ),
        (
            f"{_sentence(turn)}没有人急着解释这意味着什么，"
            "只先把能留住的东西留住。"
        ),
        (
            f"{_sentence(turn)}从这一刻起，场上的人都不再是旁观者。"
            "继续往前，就得为自己的选择负责。"
        ),
    ]
    residue_lines = [
        (
            f"{marker}暗下去以后，刚才那处细节还在脑子里发亮。"
            f"{_sentence(detail_clause or '它没有给出答案')}"
            "事情没有变清楚，只是更不能丢下。"
        ),
        (
            f"{marker}留下的光很快被周围秩序盖住，像什么都没发生过。{pov}站在原地，反而更不敢相信那份平静。"
        ),
        (
            f"{subject}没有把{marker}交给标准流程。流程太慢，也太干净；"
            "眼下能救命的，是一份还没被修过边角的证据。"
        ),
    ]
    variant = (index - 1) % 3
    return [
        openers[variant],
        pressure_lines[variant],
        line_lines[variant],
        turn_lines[variant],
        _recording_paragraph(number=number, pov=pov, marker=marker, line=line),
        residue_lines[variant],
        _popular_event_followup(
            pov=pov,
            marker=marker,
            pressure=pressure_clause,
            detail=detail_clause,
            line=line_text,
            turn=_sentence_fragment(turn),
        ),
    ]


def _ensure_novel_mode_length(
    body: str,
    *,
    number: int,
    arc: dict[str, Any],
    target_chars: int,
) -> str:
    text = body.strip()
    if _body_char_count(text) >= target_chars:
        return text
    additions = _novel_deepening_paragraphs(number, arc=arc)
    for paragraph in additions:
        if _body_char_count(text) >= target_chars:
            break
        if paragraph.strip() and paragraph not in text:
            text += "\n\n" + paragraph.strip()
    return text


def _popular_event_followup(
    *,
    pov: str,
    marker: str,
    pressure: str,
    detail: str,
    line: str,
    turn: str,
) -> str:
    subject = _group_label(pov)
    detail_text = detail or "刚才那个细节"
    detail_sentence = _sentence(detail_text)
    memory_line = _sentence_fragment(line)
    if _is_multi_pov(pov):
        if _is_two_pov(pov):
            return (
                f"两个人没有在{marker}前停太久。林知遥把声音留住，方岑去看它是不是被伪造过。"
                f"刚才那股逼迫还没退，可刚才那个细节已经够了。{detail_sentence}"
                "下一步不能再交给系统安排。"
            )
        return (
            f"三个人没有在{marker}前停太久。林知遥把声音留住，方岑去看它是不是被伪造过，"
            f"阿眠则盯着那些还没有名字的空白处。刚才那股逼迫还没退，"
            f"可刚才那个细节已经够了。{detail_sentence}下一步不能再交给系统安排。"
        )
    if "方岑" in pov:
        return (
            f"方岑把{marker}旁边的时间戳抄下来，抄到一半又停住。"
            f"屏幕还没暗。{detail_sentence}这比警报更刺眼。"
            f"他想起“{memory_line}”，最后只做了一件事：把{turn or '这一步'}之后留下的缺口单独加密。"
        )
    if "阿眠" in pov:
        return (
            f"阿眠把{marker}压在值夜簿下，指尖能摸到纸页轻轻发抖。"
            f"馆规还在催她把一切放回抽屉。{detail_sentence}它还没有变成答案。"
            f"她听见“{memory_line}”还在书脊里回响，于是把灯调暗，给这段记录留出一格空位。"
        )
    return (
        f"林知遥把{marker}在心里过了一遍。{detail_sentence}刚才那个细节比任何警报都刺眼。"
        f"她没有再看上传按钮，只想起“{memory_line}”，把录音笔握紧，继续往前。"
    )


def _novel_deepening_paragraphs(number: int, *, arc: dict[str, Any]) -> list[str]:
    paragraphs: list[str] = []
    pov = str(arc.get("pov") or "他们")
    subject = _group_label(pov)
    events = [event for event in arc.get("events", []) if isinstance(event, dict)]
    for index, event in enumerate(events, start=1):
        marker = _scene_marker(number, index)
        detail = _sentence_fragment(str(event.get("detail") or "那个细节"))
        pressure = _sentence_fragment(str(event.get("pressure") or "压力还在"))
        line = _dialogue_line(str(event.get("line") or "继续"))
        turn = _sentence_fragment(str(event.get("turn") or "他们继续向前"))
        if index % 3 == 1:
            paragraphs.append(
                f"走出几步后，{subject}又回头看了一眼。{marker}已经不亮了，周围也恢复得很快，"
                f"快到像刚才只是一次眼花。可刚才那个细节还留着。{_sentence(detail)}"
                "它像一粒没有吐出来的沙。"
            )
            paragraphs.append(
                f"{pressure}。{pov}没有把这句话说出口，只把步子放慢。"
                "人在害怕的时候最容易相信标准答案，可今晚每一个标准答案都来得太快。"
            )
        elif index % 3 == 2:
            paragraphs.append(
                f"{marker}被灯影吞回去后，{subject}才发现自己一直屏着气。"
                f"{_sentence(detail)}它没有继续发亮，却像一枚压在舌底的碎玻璃，吞不下去，也吐不出来。"
            )
            paragraphs.append(
                f"{pressure}。如果现在转身，事情也许还能被解释成误会。"
                f"可{subject}知道，自己已经听见了“{line}”，再装作没听见就太难看。"
            )
        else:
            paragraphs.append(
                f"离开{marker}之前，{pov}停了半秒。"
                f"这半秒不够想清楚全部事情，却够{subject}记住刚才那处细节。{_sentence(detail)}"
            )
            paragraphs.append(
                f"{pressure}。周围越安静，{subject}越能感觉到有什么东西正在背后追上来。"
                f"{turn}，这句话落在心里，比任何解释都重。"
            )
        paragraphs.append(_object_reaction_paragraph(pov=pov, marker=marker, turn=str(event.get("turn", "他们继续向前"))))
        paragraphs.append(
            f"{pov}没有把{marker}当成结论。那处细节还没解释清楚。{_sentence(detail)}"
            "越是这样，越不能交给那些急着给答案的屏幕。"
            f"{subject}只把它当成一个记号，提醒自己下一次犹豫时，先想起这里。"
        )
        paragraphs.append(_quiet_choice_paragraph(pov=pov, marker=marker, line=str(event.get("line", "继续"))))
        paragraphs.append(
            f"{marker}之后，{subject}把“{line}”和刚才那处细节分开记。{_sentence(detail)}"
            "一个是人说过的话，一个是现场留下的痕迹。两样东西分开放，才不容易被同一个理由抹掉。"
        )
        paragraphs.append(
            f"{pov}继续往前时，没有觉得自己勇敢。{pressure}。"
            f"{subject}只是明白，胆怯可以晚点再处理，眼前这条线索不能断。"
        )
    paragraphs.append(
        f"这一章临近收束时，{pov}没有得到安慰。"
        f"但{subject}至少带走了一样东西：一条没有被系统改写干净的路。"
    )
    paragraphs.append(
            _residual_preservation_paragraph(number=number, pov=pov)
    )
    return _unique_paragraphs(paragraphs)


def _recording_paragraph(*, number: int, pov: str, marker: str, line: str) -> str:
    line_text = _dialogue_line(line)
    if _is_multi_pov(pov):
        if _is_two_pov(pov):
            return (
                f"在{marker}之后，林知遥把能听见的部分存进录音笔，方岑把能验证的部分写进加密卡。"
                f"两份记录互不相同，却都带着“{line_text}”留下的偏差。"
            )
        return (
            f"在{marker}之后，林知遥把能听见的部分存进录音笔，方岑把能验证的部分写进加密卡，"
            f"阿眠把还没有主人认领的部分压进值夜簿。三份记录互不相同，却都带着“{line_text}”留下的偏差。"
        )
    if "方岑" in pov:
        return (
            f"在{marker}之后，方岑把能验证的部分写进加密卡，又故意留下无法补全的空段。"
            f"这份记录暂时只归他保管，带着“{line_text}”留下的偏差。"
        )
    if "阿眠" in pov:
        return (
            f"在{marker}之后，阿眠把还没有主人认领的部分压进值夜簿，没有给它编馆藏号。"
            f"这份记录暂时只夹在她的值夜簿里，带着“{line_text}”留下的偏差。"
        )
    return (
        f"在{marker}之后，林知遥把能听见的部分存进录音笔，没有把样本交给采样署。"
        f"这份记录暂时只留在她手里，带着“{line_text}”留下的偏差。"
    )


def _object_reaction_paragraph(*, pov: str, marker: str, turn: str) -> str:
    if _is_multi_pov(pov):
        if _is_two_pov(pov):
            return (
                f"{turn}之后，两件随身物的反应各不相同：录音笔变热，"
                "加密卡短暂失去时间戳。它们像两种不肯合并的脉搏，证明这条路还活着。"
            )
        return (
            f"{turn}之后，三件随身物的反应各不相同：录音笔变热，"
            "加密卡短暂失去时间戳，值夜簿多出一条没有页码的折痕。它们像三种脉搏，证明这条路还活着。"
        )
    if "方岑" in pov:
        return (
            f"{turn}之后，加密卡短暂失去时间戳，又在{marker}的边缘重新写回一行校验码。"
            "方岑没有立刻补全它，因为缺口本身正在证明这条路还活着。"
        )
    if "阿眠" in pov:
        return (
            f"{turn}之后，值夜簿多出一条没有页码的折痕，正好压在{marker}刚才亮起的位置。"
            "阿眠没有把折痕抚平，因为未完成的东西本来就不该被装成平整。"
        )
    return (
        f"{turn}之后，录音笔在{marker}旁边发热，自动生成一段没有上传入口的本地样本。"
        "林知遥没有替它寻找接口，因为不上传本身已经是一种选择。"
    )


def _quiet_choice_paragraph(*, pov: str, marker: str, line: str) -> str:
    line_text = _dialogue_line(line)
    if _is_multi_pov(pov):
        if _is_two_pov(pov):
            return (
                f"等“{line_text}”这句余音沉下去，两个人都没有抢着补充解释。"
                "林知遥怕样本被洗干净，方岑怕证据被补成假货。"
                f"所以他们只把{marker}留在中间，让它暂时保持刺眼。"
            )
        return (
            f"等“{line_text}”这句余音沉下去，三个人都没有抢着补充解释。"
            "林知遥怕样本被洗干净，方岑怕证据被补成假货，阿眠怕未完成的人被关进编号。"
            f"所以他们只把{marker}留在中间，让它暂时保持刺眼。"
        )
    if "方岑" in pov:
        return (
            f"等“{line_text}”这句余音沉下去，方岑没有补写解释。"
            f"他把{marker}留在屏幕边缘，让那处不完整继续刺眼，因为补全有时比遗失更像背叛。"
        )
    if "阿眠" in pov:
        return (
            f"等“{line_text}”这句余音沉下去，阿眠没有盖上值夜簿。"
            f"她把{marker}留在灯下，让纸页继续不安地翘着，因为归档有时只是另一种删除。"
        )
    return (
        f"等“{line_text}”这句余音沉下去，林知遥没有急着替自己找理由。"
        f"她把{marker}留在录音笔的新文件名里，确认它还能被再次打开。"
    )


def _residual_preservation_paragraph(*, number: int, pov: str) -> str:
    if _is_multi_pov(pov):
        if _is_two_pov(pov):
            return (
                f"所以他们把残片分开保存。任何单独一份都不能解释今晚发生过什么，"
                "但只要两份同时存在，星桥就没法轻易把它改写成一场无害的误会。"
            )
        return (
            f"所以他们把所有残片分开保存。任何单独一份都不能解释今晚发生过什么，"
            "但只要三份同时存在，星桥就无法把它改写成一场无害的误会。"
        )
    if "方岑" in pov:
        return (
            f"所以方岑只保存残缺记录。任何完整备份都可能把今晚修成无害故障，"
            "而他现在宁愿带着缺口继续走。"
        )
    if "阿眠" in pov:
        return (
            f"所以阿眠只保存未归档记录。任何正式馆藏号都可能把今晚变成可借可还的安全文本，"
            "而她现在宁愿让它保持未完成。"
        )
    return (
        f"所以林知遥只保存本地样本。任何上传流程都可能把今晚修成无害噪声，"
        "而她现在宁愿让那段声音继续发烫。"
    )


def _is_multi_pov(pov: str) -> bool:
    return any(marker in pov for marker in ("与", "、", "三人", "他们"))


def _is_two_pov(pov: str) -> bool:
    return "与" in pov and "、" not in pov and "三人" not in pov and "他们" not in pov


def _between_phrase(pov: str) -> str:
    if _is_multi_pov(pov):
        return "他们之间"
    if "方岑" in pov:
        return "他和终端之间"
    if "阿眠" in pov:
        return "她和书页之间"
    return "她和雨声之间"


def _group_label(pov: str) -> str:
    if _is_multi_pov(pov):
        return "他们"
    if "方岑" in pov:
        return "他"
    return "她"


def _scene_marker(number: int, index: int) -> str:
    markers = ("第一道蓝光", "一条灰线", "那段旧录音", "发热的卡面", "翘起的纸页", "蓝墨纸签")
    return markers[(number + index - 2) % len(markers)]


def _sentence(value: str) -> str:
    text = re.sub(r"\s+", "", str(value or "")).strip()
    if not text:
        return ""
    if re.search(r"[。！？!?；;]$", text):
        return text
    return text + "。"


def _sentence_fragment(value: str) -> str:
    text = re.sub(r"\s+", "", str(value or "")).strip()
    return re.sub(r"[。！？!?；;，,]+$", "", text)


def _dialogue_line(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().strip("“”\"")
    return text or "继续往前"


def _unique_paragraphs(paragraphs: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", str(paragraph or "").strip())
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(str(paragraph).strip())
    return unique


def _chapter_scene(number: int, *, focus: str, turn: str) -> dict[str, str]:
    lane = (number - 1) % 3
    if lane == 0:
        return {
            "opening": (
                "林知遥把录音笔放在窗台上时，雨声正从城市的每一条缝里长出来。她本来只是想给今晚的样本编号，"
                "像过去无数次那样，把噪声、时间、地点和体感写进表格，再把自己从现场摘出去。可是这一次，"
                f"表格的最后一栏怎么也填不满。{focus}"
            ),
            "motion": (
                "她沿着站台边缘走，广告屏一遍遍播放白天的天气预报，声音却在雨里慢了半拍。水洼映出她的影子，"
                "也映出一个不该存在的站牌：星桥维护口，凌晨三点十七分开放。林知遥停下脚步，忽然意识到自己并不是发现了异常，"
                "而是被异常等到了这里。"
            ),
            "pressure": (
                "维修单贴在站牌背面，纸角被雨水泡软，只剩几个硬得像螺丝的字：旧终端、回声、不要相信完整备份。"
                "她把维修单夹进笔记本，耳机里立刻传来一声很轻的电流音，像有人在远处试探性地敲门。"
            ),
            "discovery": "“如果你听见了，”录音笔里那个声音说，“先别急着删除我。”",
            "choice": (
                "这句话让林知遥站了很久。她见过太多被系统归类为噪声的东西：哭到一半的梦、突然改口的告白、"
                "临睡前想起却第二天再也找不到的名字。它们通常没有力量，只会在后台慢慢褪色。但今晚不一样，"
                "今晚的噪声知道自己会被删除，也知道该向谁求救。"
            ),
            "ending": (
                "她按下保存键，没有上传样本。红色警告跳出来时，她第一次没有立刻补救。站牌下方有一行极小的字，"
                f"只有在列车进站前的风里才会亮起：{turn}\n\n"
                f"于是她抬手，在录音笔的新文件名里输入：星桥试运行，样本 {number:03d}。"
            ),
        }
    if lane == 1:
        return {
            "opening": (
                "阿眠在凌晨两点五十九分打开图书馆的侧门。门轴没有声音，只有门缝里漏出的冷光一寸寸铺过她的鞋尖。"
                f"她今晚原本只想整理归还箱里那些没有署名的梦，可第一张借阅卡刚翻过来，就出现了不属于馆藏系统的条目。{focus}"
            ),
            "motion": (
                "失眠图书馆不接待睡着的人。这里的来客大多沉默，带着一小截醒不过来的梦来换一杯温水，"
                "再把自己忘记的细节寄存在某个编号抽屉里。阿眠熟悉每一种遗忘的重量，却不熟悉今晚这张卡片。"
            ),
            "pressure": (
                "卡片边缘渗着蓝色墨点，像有人在很远的地方反复擦掉同一句话。她把卡片压在灯下，"
                "书架深处随即响起连锁般的翻页声，所有空白索引都转向同一个页码。"
            ),
            "discovery": (
                "页码上没有书名，只有一段斜斜写下的提示：不要把未完成的人归档。阿眠读完以后，"
                "指尖忽然发麻，仿佛整座图书馆都在等她承认自己也属于未完成的一类。"
            ),
            "choice": (
                "她本可以把卡片锁进异常柜。那是规程，也是她过去保护自己的方式：任何会改变馆藏秩序的东西，"
                "都先被安静地收起来。但这一次，抽屉没有合上。"
            ),
            "ending": (
                f"阿眠把蓝色卡片夹进自己的值夜簿，在页脚写下：{turn}\n\n"
                "然后她熄掉大厅一半的灯，给那个尚未抵达图书馆的人留出一条路。"
            ),
        }
    return {
        "opening": (
            "方岑把旧终端从仓库最底层拖出来时，灰尘在光束里浮得像一场慢雪。机器外壳贴着报废标签，"
            f"接口却还有微弱余温。他不喜欢这种余温，太像一个人没来得及收回的手。{focus}"
        ),
        "motion": (
            "他拆下背板，先看电源，再看主板烧蚀的位置。流程让他安心，流程意味着问题可以被拆小、编号、"
            "再一点点关进维修日志里。可星桥工程留下的东西从来不肯老实待在日志里。"
        ),
        "pressure": (
            "屏幕亮起时没有启动画面，只有一条心跳线。方岑试了三种协议，得到的都是拒绝访问。"
            "他盯着那条线，忽然想起母亲失踪前也曾在餐桌上敲出这样的节奏：短、短、长，停顿，再短。"
        ),
        "discovery": (
            "他把节奏当作密钥输入，终端终于吐出第一段记录。记录没有解释工程，也没有留下遗言，"
            "只把一份被删改过的求救压缩成了七秒钟的噪声。"
        ),
        "choice": (
            "方岑的手停在删除键上。按下去，旧终端会恢复成一件普通废品；不按，他就得承认母亲留下的不是谜题，"
            "而是一条仍然活着的路。"
        ),
        "ending": (
            f"他最终复制了那七秒钟噪声，并在文件名后写下：{turn}\n\n"
            "终端风扇重新转动时，方岑第一次没有把恐惧记成故障。他把它记成了坐标。"
        ),
    }


def _story_expansion_paragraphs(number: int, *, focus: str, turn: str) -> list[str]:
    lane = (number - 1) % 3
    chapter_label = f"{number:03d}"
    if lane == 0:
        return [
            (
                "林知遥没有立刻离开站台。她把采样包重新背好，确认每一个扣带都扣在原来的孔位上，"
                "像这样就能骗过远处那些看不见的摄像头。城市的夜班系统有自己的脾气，巡检灯每七分钟扫过一次站台，"
                "扫到人脸时会短暂停顿，仿佛也在犹豫这个人该被归进哪一类。"
            ),
            (
                "她的工作让她熟悉这种犹豫。记忆采样员不是侦探，也不是医生，只负责把城市里那些异常的情绪回声剪下来，"
                "送进星桥的清洗队列。队列会给每一段回声标注危险等级，低危的做梦，高危的删改，"
                "无法判断的就交给更深的系统。林知遥从不问更深的系统在哪里。"
            ),
            (
                "可今晚，那支录音笔像一枚烫在口袋里的心脏。她每走一步，都能感到里面那段声音轻轻撞一下外壳。"
                "它不是普通求救。普通求救会喊疼、喊怕、喊有没有人，而它只说别删我。"
                "一个知道自己将被删除的声音，比任何惨叫都更像真实的人。"
            ),
            (
                "站台尽头的检票闸机忽然亮起，屏幕上浮出一行临时通行提示：采样员林知遥，权限校验通过。"
                "她盯着自己的名字，背后慢慢泛起冷意。她没有申请权限，也没有把今晚的样本上传。"
                "如果系统已经知道她会来，那这条路就不是逃跑，而是一场被安排好的相遇。"
            ),
            (
                "林知遥讨厌被安排。小时候母亲常说她太敏感，什么都要确认第二遍；后来进入采样署，主管又说这种敏感适合做记录，"
                "不适合做决定。她真的很少做决定。她习惯把选择藏在表格后面，把责任交给按钮。"
                f"可样本 {chapter_label} 没给她按钮，只给她一条窄得像刀口的路。"
            ),
            (
                "她跨过闸机时，身后的广告屏突然集体静音。整座站台安静下来，雨声被隔在天棚外，"
                "像一群贴着玻璃寻找入口的指尖。林知遥回头，看见自己的影子还留在水洼里，没有跟上来。"
                "影子低着头，手里握着另一支录音笔。"
            ),
            (
                "那一刻她终于明白，所谓回声不一定来自过去，也可能来自一个被星桥提前折叠的明天。"
                "如果那些水洼真的在替明天说话，那她今晚记录下来的就不是异常，而是城市第一次露出的裂缝。"
            ),
            (
                "她把外套拉链拉到最上面，沿着维护口的黑色楼梯往下走。楼梯没有尽头，只有墙面上的编号一层层倒退。"
                "17、16、15。每一个数字旁边都有被抹掉的名字。到第九层时，录音笔又响了一次。"
            ),
            (
                f"“别相信完整备份，”那个声音比刚才更清楚，“完整只是他们删完以后留下来的形状。”\n\n"
                f"林知遥停在第八层和第九层之间。她没有回答，只把这句话也存进样本 {chapter_label}。"
                "文件保存成功的提示音落下时，她第一次觉得，自己不是在记录一场事故，而是在替某个明天留门。"
            ),
        ]
    if lane == 1:
        return [
            (
                "阿眠把值夜簿合上，又重新打开。她知道自己在拖延。图书馆里所有守夜人都学过一条规矩："
                "当空白索引主动写字时，不要惊呼，不要追问，也不要把自己的名字念出来。"
                "名字是最轻的钥匙，一念出口，门就会认得你。"
            ),
            (
                "她在这座图书馆待了四年，已经见过太多不该出现的书。有人把童年的夏天借走三天，回来时连蝉声都忘了；"
                "有人寄存一场没来得及做完的道歉，结果每晚都梦见自己站在同一扇门外。"
                "阿眠负责把这些东西编号，擦去指纹，放进不会互相污染的抽屉。"
            ),
            (
                "她一直做得很好。做得好的意思是，没有让任何一本书把她认成馆藏的一部分。可今晚不一样。"
                "蓝色卡片夹在她指间时，指腹下方传来细小的脉动，像纸里藏着一只正在慢慢醒来的鸟。"
            ),
            (
                "空白索引翻页的声音越来越密。先是历史区，再是梦境区，最后连封存多年的儿童阅览室也亮起灯。"
                "一排排小椅子拖着长影，影子却不是椅子的形状，而像许多坐在原地等人接走的孩子。"
            ),
            (
                f"阿眠低声念出条目上的关键句：{focus} 她听见自己的声音落在大厅里，立刻被书架吞进去，"
                "又从更深处吐回来。回声比她本人更冷静，像另一个已经知道答案的阿眠。"
            ),
            (
                "柜台后的报警灯闪了三次，没有真正响起。图书馆在警告她，也在给她留余地。"
                "她忽然想起上任管理员离开前说过的话：这里最危险的不是书会说话，而是有一天你会相信它们只是在说话。"
            ),
            (
                "蓝色卡片背面慢慢浮出一条借阅记录。借阅人一栏是空的，归还日期写着明天，归还物却不是书，"
                "而是一段被星桥退回的主动性。阿眠不知道主动性怎么被归还，但她知道失去它的人会变成什么样。"
                "他们会按时吃饭，按时睡觉，按时忘记自己为什么难过。"
            ),
            (
                "她走进索引室，把最上层的封印盒取下来。盒盖上有三道锁，第一道锁需要馆员权限，第二道锁需要梦境签名，"
                "第三道锁只需要一句真话。阿眠在第三道锁前沉默很久，最后说：“我不想再替别人保管结局。”"
            ),
            (
                f"锁开了。盒子里没有钥匙，只有一枚很小的纸星，纸星展开后写着：{turn}\n\n"
                "阿眠把纸星放进值夜簿，第一次在交班记录里留下了自己的判断。不是异常已处理，"
                "而是异常正在寻找同伴。"
            ),
        ]
    return [
        (
            "方岑没有急着备份那七秒钟噪声。他把终端电源拔掉，又等了十秒，再重新接上。"
            "这是他从母亲那里学来的习惯：真正重要的系统不会在第一次开机时说真话，"
            "它们要先确认你有没有耐心听完第二次沉默。"
        ),
        (
            "第二次启动时，屏幕没有再显示心跳线，而是弹出一张旧工程表。表格缺了标题，"
            "只剩编号、维护人、删除率和情绪稳定指数。方岑扫到维护人那一栏时，手指明显顿了一下。"
            "那里有母亲的签名，笔画熟悉到让他胃里发紧。"
        ),
        (
            "他很久没想起她写字的样子了。失踪以后的几年，所有人都劝他把母亲当成事故的一部分。"
            "事故可以赔偿，可以归档，可以在纪念日送一束花。可是签名不一样，签名还带着人的用力方式。"
            "它把一个被整理好的事故重新拽回活人身边。"
        ),
        (
            f"终端日志显示，{focus} 这行记录后面有三百多次访问失败，最近一次就在七分钟前。"
            "方岑的仓库没有联网，至少理论上没有。他看向墙角那台已经断电的路由器，路由器指示灯却亮着，"
            "绿色微光一闪一闪，像在替某个远处的人眨眼。"
        ),
        (
            "他把防火墙切到手动模式，又把整间仓库的无线信号屏蔽。屏蔽器启动后，空气里出现短暂的耳鸣。"
            "方岑在耳鸣里听见一段不属于自己的呼吸声。很浅，很稳，像有人贴着终端另一侧等待他犯错。"
        ),
        (
            "他本能地想关机。关机最安全，关机以后所有东西都能停在可解释范围内。可屏幕右下角跳出一行小字："
            "如果你是方岑，不要关。那行字没有标点，像写字的人在最后一秒被拖走了。"
        ),
        (
            "方岑站起来，在仓库里来回走了两圈。他不怕机器，也不怕代码，甚至不太怕危险。"
            "他怕的是这件事真的和母亲有关，而自己过去那些看似理智的放下，只是因为没有证据能逼他继续疼。"
        ),
        (
            "第三次读取时，终端吐出一段损坏的音频。噪声里夹着半句人声，方岑调了十七次滤波，"
            "终于听清那不是母亲的声音，而是一个年轻女人在雨声里说：我没有上传样本。"
            "他不知道林知遥是谁，却知道她正在同一张网里往下坠。"
        ),
        (
            f"屏幕上的求救记录最后自动展开，露出被隐藏的判断：{turn}\n\n"
            "方岑把这行字拍下来，发往一个早已停用的内部地址。发送按钮亮起时，他没有期待回应。"
            "可三秒后，收件箱弹出回信：收到。请在明天之前找到失眠图书馆。"
        ),
    ]


def _ensure_platform_length(
    body: str,
    *,
    number: int,
    focus: str,
    turn: str,
    target_chars: int,
) -> str:
    text = body.strip()
    if _body_char_count(text) >= target_chars:
        return text
    additions = [
        (
            "广播在头顶轻轻咳了一声，随即恢复成温柔的女声，提醒所有夜间乘客保管好随身物品。"
            "林知遥抬头看向扬声器，忽然觉得那声音不像提示，更像有人隔着薄薄一层金属皮在观察她。"
        ),
        (
            "她把手伸进口袋，摸到录音笔冰凉的边角。刚才还发烫的外壳此刻像被雨水浸过，"
            "冷得让她想起小时候发烧时贴在额头上的退热贴。那时候母亲会守在床边，告诉她不要怕，"
            "系统会替每个人安排好最稳定的明天。"
        ),
        (
            "最稳定的明天听起来并不坏。人们不用担心失眠，不用担心梦里反复出现同一条街，"
            "不用担心某个已经离开的人忽然在雨夜回头。星桥替城市保存记忆，也替城市修剪记忆。"
            "被修剪掉的枝叶不会流血，只会安静地从生活里消失。"
        ),
        (
            "林知遥以前相信这是一种仁慈。她亲眼见过被噩梦折磨到无法工作的老人，在同步治疗后重新学会买菜、"
            "遛弯、和邻居谈天气。她也见过失去孩子的父亲在清洗记忆后第一次笑出来。那些笑容太真实，"
            "真实到她不敢怀疑背后的代价。"
        ),
        (
            "直到今晚，录音笔里那个声音让所有仁慈都裂开了一道细口。它没有哭，也没有请求拯救，"
            "只是在被抹去前保持着一种近乎平静的固执。别删我。三个字像三颗小钉子，钉在她掌心。"
        ),
        (
            "维护口的楼梯继续往下。每下降一层，空气就更干一点，雨声也更远一点。墙面上的旧漆剥落成片，"
            "露出里面银灰色的隔音材料。林知遥用指尖轻轻碰了一下，材料立刻缩回去，像某种活物躲开了她。"
        ),
        (
            "第七层的门虚掩着。门缝里透出一线蓝光，和采样署的标准警示灯不一样，更暗，也更像水。"
            "她听见门后有许多人同时翻动纸页的声音，可这座维护口不该连接任何纸质档案室。"
        ),
        (
            "她没有推门。采样员的训练让她先记录，再接触。她举起录音笔，红色录制点亮起的一瞬间，"
            "门后的翻页声突然停了。那种整齐的安静比噪声更让人不舒服，好像所有纸页都在同一秒屏住呼吸。"
        ),
        (
            "林知遥想起主管的脸。那张脸总是很干净，连疲惫都干净，像每晚都会把不必要的情绪卸载掉。"
            "主管说过，异常不是敌人，异常只是尚未被归类的生活。可如果归类的结果就是删除，"
            "那生活本身又剩下什么？"
        ),
        (
            "她终于推开门。房间很窄，窄得不像房间，更像夹在两段现实之间的缝。墙上没有书架，"
            "也没有纸页，只有一排排悬浮的光片。光片薄得透明，每一片里都封着一段微小的场景："
            "有人在雨里回头，有人把信撕成两半，有人在病房门口松开手。"
        ),
        (
            "她看见其中一片光里有自己。另一个林知遥站在同一个站台上，比现在的她更苍白，"
            "手里握着另一支录音笔。那个人抬起头，隔着光片看向她，嘴唇动了动。没有声音传出来，"
            "可林知遥读懂了口型：不要把我交回去。"
        ),
        (
            "她退后半步，肩膀撞到门框。门框没有发出声音，反倒像水面一样荡开一圈涟漪。"
            "涟漪里浮出许多名字，密密麻麻，从地面一直爬到天花板。那些名字被划掉，又重新出现，"
            "像某个系统在反复练习遗忘。"
        ),
        (
            "录音笔自动保存了新片段。文件名不再由她输入，而是自己跳出来：未归档人声，来源未知，"
            "权限不足。紧接着，权限不足四个字被一条细细的蓝线划掉，换成了另一个判断：等待本人确认。"
        ),
        (
            "本人是谁？林知遥盯着屏幕，心里浮出一个荒唐的答案。也许是她，也许是光片里的另一个她，"
            "也许是那个只剩声音的人。星桥把太多人的残余压进同一个狭窄房间，连求救都变得像回声互相重叠。"
        ),
        (
            "她按下确认键。没有警报，没有追捕，甚至没有门自动锁死。只有最靠近她的一片光轻轻碎开，"
            "碎成无数细小的雨点落进录音笔。笔身重新发热，像吞下了一枚刚从火里取出的种子。"
        ),
        (
            "同一时间，远处某座没有招牌的图书馆里，一本空白索引翻到了新的页码。更远的旧仓库中，"
            "一台报废终端在无人触碰的情况下亮起绿线。林知遥并不知道这些，她只知道自己的名字也出现在墙上，"
            "而那一笔还没有被划掉。"
        ),
        (
            "她把录音笔抱在胸前，转身离开光片室。楼梯还在往下，但她没有继续走。"
            "她第一次违背了自己的职业习惯：没有完成采样，没有补足表格，也没有向上级发送异常报告。"
        ),
        (
            "回到站台时，雨已经小了。广告屏重新开始播放天气预报，主持人的笑容标准得毫无破绽。"
            "林知遥站在屏幕前，看着自己湿透的倒影，忽然发现倒影比她慢了一拍才抬头。"
        ),
        (
            "她没有再等下一班车。她沿着地面上那条霓虹碎成的窄桥往外走，走到雨棚边缘时，"
            "录音笔里传来第三个声音。那声音很轻，却不是求救。它说：去找失眠图书馆。"
        ),
        (
            "林知遥停了一下，把这句话也保存下来。城市在她身后恢复秩序，闸机关闭，站牌暗下去，"
            "仿佛刚才的一切都只是雨夜里一段不稳定的噪声。可录音笔仍然发热，提醒她噪声没有消失。"
        ),
        (
            "她把笔收进内袋，第一次没有把拉链拉到底。她需要确认那点热度还在。"
            "如果它熄灭，她可能会以为自己又回到了那座被修剪过的城市；如果它还在，她就必须继续往前走。"
        ),
    ]
    additions = _length_extension_paragraphs(number)
    index = 0
    while _body_char_count(text) < target_chars and index < 80:
        text += "\n\n" + additions[index % len(additions)]
        index += 1
    return text


def _length_extension_paragraphs(number: int) -> list[str]:
    lane = (number - 1) % 3
    if lane == 1:
        return [
            "阿眠把蓝色卡片放进值夜簿后，整座图书馆像被一层薄雾轻轻罩住。灯没有变暗，书架也没有移动，可她能感觉到每一本书都在换一种方式呼吸。",
            "她从柜台后取出白棉手套，动作比平时慢。手套边缘有旧墨迹，是上任管理员留下来的。那个人离开前没有道别，只把所有钥匙按大小排好，放在她最容易看见的位置。",
            "异常柜在西侧尽头，平时锁着三道链。第一道链防来客，第二道链防馆员，第三道链防梦自己走出来。阿眠站在柜前，听见里面传来很轻的敲击声。",
            "她没有马上开柜，而是先回头看大厅。几个常来的失眠者正伏在桌上写寄存单，没人抬头。这里的人都懂得不多看别人的梦，因为梦看久了会认错主人。",
            "蓝色卡片忽然在值夜簿里动了一下。纸角掀起，露出背面第二行字：林知遥，未归还。阿眠盯着那三个字，心里升起一种陌生的疼，好像那不是名字，而是一扇被雨敲了一整夜的窗。",
            "她终于打开异常柜。柜门内侧贴满了手写标签：不要朗读、不要折叠、不要带出馆外、不要在清醒时相信。标签层层叠叠，最底下还有一道更旧的字迹：如果它开始找人，说明星桥又饿了。",
            "阿眠把那句话看了三遍。星桥在城市公告里从不被形容为会饥饿的东西。它是基础设施，是记忆卫生系统，是公共健康工程。可图书馆的旧标签不会讲礼貌，它们只留下活下来的经验。",
            "柜子里没有她以为会出现的书，只有一只透明匣子。匣子里装着一小段雨声，雨声被压成蓝色的线，绕成一团。阿眠刚靠近，线团就亮起来，像认出了她手里的卡片。",
            "她听见线团里有人喘息。那声音很轻，混在雨里，分不清是奔跑后留下的气息，还是努力不哭时压住的呼吸。阿眠伸手触碰匣面，指腹立刻浮出一串页码。",
            "页码指向儿童阅览室。那里已经封存七年，因为七年前有个孩子把自己的噩梦借给了全城，导致整个旧城区同时梦见同一座钟楼。后来星桥修复了事故，也修复了所有人的害怕。",
            "阿眠仍然记得那天。她那时还不是管理员，只是一个常来这里躲觉的女孩。所有人醒来后都说没事了，只有她连续七晚梦见钟楼影子停在六点十七分。",
            "她走向儿童阅览室，蓝线在匣子里跟着她移动。走廊尽头的小门贴着褪色的星星贴纸，星星边缘卷起，像一只只不肯闭上的眼睛。",
            "门锁需要梦境签名。阿眠闭上眼，把自己最常做的那个梦交出去：她站在无边无际的书架中间，替别人保管结局，却怎么也找不到自己的名字。",
            "锁开时，她听见有人在门后笑了一声。那笑声很小，不像孩子，反而像被迫学会安静的大人。阿眠推门进去，满屋低矮书桌整齐排列，桌面上全是空白借阅卡。",
            "第一张卡写着林知遥，第二张写着方岑，第三张没有名字，只画着一座桥。桥下不是水，是密密麻麻的眼睛。阿眠把三张卡叠在一起，纸面立刻渗出新的地址。",
            "地址不在任何地图上，只写着：旧城区，六点十七分之后。阿眠把卡片收进口袋时，忽然明白这座图书馆不是在保管梦，而是在保管那些被星桥退回来的未完成。",
            "她回到大厅，失眠者们仍旧低头写字，没有人发现儿童阅览室开过。只有柜台上的沙漏倒转过来，细沙一粒粒往上升。",
            "阿眠拿起值夜簿，在交班栏写下第一句不合规的记录：今晚有一个名字来找路。写完以后，她没有把簿子合上，而是在旁边又补了一句：我打算让她进来。",
        ]
    if lane == 2:
        return [
            "方岑把仓库卷帘门拉下一半，留出一条能看见街灯的缝。以前母亲修机器时也这样，说完全封闭的房间容易让人相信屏幕，留一点外面的光，至少能记得自己还在人间。",
            "终端风扇转得很慢，像一个久病的人重新学会呼吸。方岑把噪声文件复制三份，一份放进本地盘，一份写进加密卡，最后一份传给那只早已停用的内部邮箱。",
            "邮箱回信以后，他反而不敢点开第二封。第一封已经足够荒唐：收到。请在明天之前找到失眠图书馆。明天之前这四个字像倒计时，贴在他的后颈。",
            "他打开城市地图，搜索失眠图书馆。结果为空。换旧城区、凌晨图书馆、梦境寄存，仍然为空。最后他输入母亲的员工编号，地图忽然闪了一下，弹出一条灰色路线。",
            "路线从他的仓库出发，穿过三条已经拆除的轻轨线，终点停在一块空白区域。空白区域没有街名，只有一枚很小的蓝色书签符号。",
            "方岑盯着那个符号，手指悬在屏幕上方。他曾经无数次告诉自己，母亲留下的线索都只是事故残片，是悲伤太久以后自动拼出的幻觉。可幻觉不会知道他的仓库地址。",
            "终端忽然弹出维护日志。日志时间停在七年前，签名是母亲。内容只有一句：如果他开始查，不要让他先找到我。方岑看完那句话，心口像被拧了一下。",
            "他当然知道那个他是谁。母亲留下这句话时，他还在大学里修一台老式收音机，给她发消息抱怨焊锡味太重。她回了一个笑脸，说以后别做这么危险的工作。",
            "后来她失踪，所有人都说她死在一次数据回流事故里。没有遗体，没有告别，只有一份公文和一笔赔偿。方岑花了很长时间才学会不在夜里等门响。",
            "现在门真的响了。不是有人敲门，而是卷帘门被风吹得轻轻碰了一下。方岑抬头，看见缝隙外站着一个快递柜机器人，机身老旧，屏幕上贴着停用标签。",
            "机器人递出一个包裹。收件人是方岑，寄件人是空白。包裹没有重量，拆开后只有一枚图书馆借阅证。借阅证背面写着：逾期七年，请本人归还。",
            "方岑把借阅证放在终端旁边，屏幕立刻识别出新的权限。权限名不是工程师，也不是家属，而是临时借阅人。他忽然笑了一声，笑意很短，很快就散了。",
            "母亲最讨厌欠东西。小时候他借了邻居一本漫画忘记还，她带着他敲门道歉，站在楼道里等了半小时。她说借来的东西会记路，拖久了总会自己找回来。",
            "原来梦也会找回来。方岑把借阅证塞进外套内袋，又把加密卡挂在钥匙圈上。终端屏幕恢复黑暗前，跳出最后一行提示：不要带完整备份进入图书馆。",
            "他停下动作。完整备份是工程师的本能，也是他的安全感。没有备份，就像赤手走进一场不知道会不会结束的火。可母亲的日志和那个雨声文件都在提醒他，完整也可能是一种陷阱。",
            "方岑删除了其中一份复制件，只保留本地盘和加密卡。删除确认框弹出时，他迟疑了很久，最后还是按下去。屏幕上显示清理完成，他却觉得自己像亲手剪断了一根还能回头的绳子。",
            "仓库外的街灯闪了三下。灰色路线在手机上重新校准，终点从空白区域移到旧城区边缘。那里有一条很窄的小路，路名叫未眠巷。",
            "方岑关掉仓库总电源，卷帘门落下时，终端在黑暗里又亮了一瞬。那一瞬间，他看见屏幕倒影里的自己身后站着一个女人。等他回头，仓库里只有机器冷却后的金属味。",
        ]
    return [
        "广播在头顶轻轻咳了一声，随即恢复成温柔的女声，提醒所有夜间乘客保管好随身物品。林知遥抬头看向扬声器，忽然觉得那声音不像提示，更像有人隔着薄薄一层金属皮在观察她。",
        "她把手伸进口袋，摸到录音笔冰凉的边角。刚才还发烫的外壳此刻像被雨水浸过，冷得让她想起小时候发烧时贴在额头上的退热贴。那时候母亲会守在床边，告诉她不要怕，系统会替每个人安排好最稳定的明天。",
        "最稳定的明天听起来并不坏。人们不用担心失眠，不用担心梦里反复出现同一条街，不用担心某个已经离开的人忽然在雨夜回头。星桥替城市保存记忆，也替城市修剪记忆。",
        "林知遥以前相信这是一种仁慈。她亲眼见过被噩梦折磨到无法工作的老人，在同步治疗后重新学会买菜、遛弯、和邻居谈天气。她也见过失去孩子的父亲在清洗记忆后第一次笑出来。",
        "直到今晚，录音笔里那个声音让所有仁慈都裂开了一道细口。它没有哭，也没有请求拯救，只是在被抹去前保持着一种近乎平静的固执。别删我。三个字像三颗小钉子，钉在她掌心。",
        "维护口的楼梯继续往下。每下降一层，空气就更干一点，雨声也更远一点。墙面上的旧漆剥落成片，露出里面银灰色的隔音材料。林知遥用指尖轻轻碰了一下，材料立刻缩回去，像某种活物躲开了她。",
        "第七层的门虚掩着。门缝里透出一线蓝光，和采样署的标准警示灯不一样，更暗，也更像水。她听见门后有许多人同时翻动纸页的声音，可这座维护口不该连接任何纸质档案室。",
        "她没有推门。采样员的训练让她先记录，再接触。她举起录音笔，红色录制点亮起的一瞬间，门后的翻页声突然停了。那种整齐的安静比噪声更让人不舒服，好像所有纸页都在同一秒屏住呼吸。",
        "林知遥想起主管的脸。那张脸总是很干净，连疲惫都干净，像每晚都会把不必要的情绪卸载掉。主管说过，异常不是敌人，异常只是尚未被归类的生活。可如果归类的结果就是删除，那生活本身又剩下什么？",
        "她终于推开门。房间很窄，窄得不像房间，更像夹在两段现实之间的缝。墙上没有书架，也没有纸页，只有一排排悬浮的光片。光片薄得透明，每一片里都封着一段微小的场景。",
        "她看见其中一片光里有自己。另一个林知遥站在同一个站台上，比现在的她更苍白，手里握着另一支录音笔。那个人抬起头，隔着光片看向她，嘴唇动了动。没有声音传出来，可林知遥读懂了口型：不要把我交回去。",
        "她退后半步，肩膀撞到门框。门框没有发出声音，反倒像水面一样荡开一圈涟漪。涟漪里浮出许多名字，密密麻麻，从地面一直爬到天花板。那些名字被划掉，又重新出现，像某个系统在反复练习遗忘。",
        "录音笔自动保存了新片段。文件名不再由她输入，而是自己跳出来：未归档人声，来源未知，权限不足。紧接着，权限不足四个字被一条细细的蓝线划掉，换成了另一个判断：等待本人确认。",
        "她按下确认键。没有警报，没有追捕，甚至没有门自动锁死。只有最靠近她的一片光轻轻碎开，碎成无数细小的雨点落进录音笔。笔身重新发热，像吞下了一枚刚从火里取出的种子。",
        "同一时间，远处某座没有招牌的图书馆里，一本空白索引翻到了新的页码。更远的旧仓库中，一台报废终端在无人触碰的情况下亮起绿线。林知遥并不知道这些，她只知道自己的名字也出现在墙上，而那一笔还没有被划掉。",
        "她把录音笔抱在胸前，转身离开光片室。楼梯还在往下，但她没有继续走。她第一次违背了自己的职业习惯：没有完成采样，没有补足表格，也没有向上级发送异常报告。",
        "回到站台时，雨已经小了。广告屏重新开始播放天气预报，主持人的笑容标准得毫无破绽。林知遥站在屏幕前，看着自己湿透的倒影，忽然发现倒影比她慢了一拍才抬头。",
        "她没有再等下一班车。她沿着地面上那条霓虹碎成的窄桥往外走，走到雨棚边缘时，录音笔里传来第三个声音。那声音很轻，却不是求救。它说：去找失眠图书馆。",
    ]


def _sync_creative_factory_state(
    root: Path,
    *,
    checked_at: str,
    writing_mode: str,
    publication: dict[str, Any],
) -> dict[str, Any]:
    chapters = _all_chapter_paths(root)
    for chapter_path in chapters:
        number = _chapter_number_from_path(chapter_path)
        if number <= 0:
            continue
        beat = _beat_for_chapter(number)
        context = {
            "project_id": DEFAULT_PROJECT_ID,
            "project_title": DEFAULT_PROJECT_TITLE,
            "chapter_number": number,
            "writing_date": _chapter_day_from_path(chapter_path),
            "checked_at": checked_at,
            "writing_mode": NOVEL_MODE,
            "beat": dict(beat),
            "previous_chapter": _previous_chapter_rel(root, number),
        }
        body = _read_text(chapter_path)
        if body:
            _write_editorial_review(root, context=context, chapter_path=chapter_path, body=body)
    review_summary = _creative_review_summary(root)
    if not (root / STORY_BIBLE_REL).exists():
        _atomic_write_text(root / STORY_BIBLE_REL, _story_bible_text(checked_at))
    if not (root / READER_MODEL_REL).exists():
        _atomic_write_text(root / READER_MODEL_REL, _reader_model_text(checked_at))
    if not (root / XINYU_NARRATIVE_FILTER_REL).exists():
        _atomic_write_text(root / XINYU_NARRATIVE_FILTER_REL, _xinyu_narrative_filter_text(checked_at))
    _atomic_write_text(root / FORESHADOW_LEDGER_REL, _foreshadow_ledger_text(checked_at, chapters=chapters))
    _atomic_write_text(
        root / CREATIVE_FACTORY_STATE_REL,
        _creative_factory_state_text(
            checked_at,
            writing_mode=writing_mode,
            total_chapters=len(chapters),
            publication=publication,
            review_summary=review_summary,
        ),
    )
    return {
        "factory_status": "active",
        "story_bible_path": str(STORY_BIBLE_REL).replace("\\", "/"),
        "foreshadow_ledger_path": str(FORESHADOW_LEDGER_REL).replace("\\", "/"),
        "reader_model_path": str(READER_MODEL_REL).replace("\\", "/"),
        "xinyu_narrative_filter_path": str(XINYU_NARRATIVE_FILTER_REL).replace("\\", "/"),
        "creative_factory_state_path": str(CREATIVE_FACTORY_STATE_REL).replace("\\", "/"),
        "editorial_reviews_path": str(EDITORIAL_REVIEWS_REL).replace("\\", "/"),
        "review_pass_chapters": review_summary.get("pass", 0),
        "review_pending_chapters": review_summary.get("needs_revision", 0),
        "average_market_score": review_summary.get("average_market_score", 0),
    }


def _creative_review_summary(root: Path) -> dict[str, Any]:
    review_dir = root / EDITORIAL_REVIEWS_REL
    scores: list[int] = []
    passed = 0
    pending = 0
    if review_dir.exists():
        for path in sorted(review_dir.glob("chapter-*.md")):
            text = _read_text(path)
            status = _field(text, "status", "")
            if status == "pass":
                passed += 1
            elif status:
                pending += 1
            score = _int(_field(text, "market_score", "0"))
            if score:
                scores.append(score)
    average = int(round(sum(scores) / len(scores))) if scores else 0
    return {
        "pass": passed,
        "needs_revision": pending,
        "average_market_score": average,
    }


def _sync_publication_drafts(
    root: Path,
    *,
    checked_at: str,
    min_platform_chars: int,
    target_platform_chars: int,
) -> dict[str, Any]:
    chapters = _all_chapter_paths(root)
    written: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    for source_path in chapters:
        chapter_number = _chapter_number_from_path(source_path)
        if chapter_number <= 0:
            continue
        day = _chapter_day_from_path(source_path)
        beat = _beat_for_chapter(chapter_number)
        publish_path = root / PUBLICATION_CHAPTERS_REL / f"chapter-{chapter_number:03d}.md"
        text = _publication_chapter_text(chapter_number=chapter_number, writing_date=day)
        existing = _read_text(publish_path)
        existing_chars = _body_char_count(existing)
        should_write = (
            not existing
            or existing_chars < min_platform_chars
            or _contains_manuscript_meta(existing)
        )
        if should_write:
            _atomic_write_text(publish_path, text)
            written.append(
                {
                    "chapter_number": chapter_number,
                    "path": _rel(root, publish_path),
                    "chars": _body_char_count(text),
                }
            )
        final_text = _read_text(publish_path) or text
        chars = _body_char_count(final_text)
        entries.append(
            {
                "chapter_number": chapter_number,
                "title": beat["title"],
                "source_path": _rel(root, source_path),
                "publish_path": _rel(root, publish_path),
                "writing_date": day,
                "chars": chars,
                "status": "draft_ready" if chars >= min_platform_chars else "needs_expansion",
            }
        )
    ready = sum(1 for entry in entries if entry["status"] == "draft_ready")
    pending = len(entries) - ready
    shortest = min((int(entry["chars"]) for entry in entries), default=0)
    latest = entries[-1]["publish_path"] if entries else "none"
    result = {
        "checked_at": checked_at,
        "platform": "manual_novel_platform",
        "publish_ready_chapters": ready,
        "publish_pending_chapters": pending,
        "total_publication_chapters": len(entries),
        "publication_written_this_run": len(written),
        "latest_publish_path": latest,
        "shortest_publish_chars": shortest,
        "min_platform_chars": min_platform_chars,
        "target_platform_chars": target_platform_chars,
        "written_publication_chapters": written,
        "entries": entries,
    }
    _write_publication_state(root, result)
    _write_publication_log(root, result)
    return result


def _publication_chapter_text(*, chapter_number: int, writing_date: str) -> str:
    beat = _beat_for_chapter(chapter_number)
    return _compose_local_chapter(
        {
            "project_id": DEFAULT_PROJECT_ID,
            "project_title": DEFAULT_PROJECT_TITLE,
            "chapter_number": chapter_number,
            "writing_date": writing_date,
            "checked_at": _now_iso(),
            "writing_mode": NOVEL_MODE,
            "beat": dict(beat),
            "previous_chapter": "",
        }
    )


def _write_publication_state(root: Path, result: dict[str, Any]) -> None:
    updated_at = str(result.get("checked_at") or _now_iso())
    publication_log_path = str(PUBLICATION_LOG_REL).replace("\\", "/")
    reference_permission_path = str(REFERENCE_PERMISSIONS_REL).replace("\\", "/")
    source_map_path = str(SOURCE_MAP_REL).replace("\\", "/")
    genre_benchmark_path = str(GENRE_BENCHMARK_REL).replace("\\", "/")
    pacing_rules_path = str(PACING_RULES_REL).replace("\\", "/")
    opening_rewrite_brief_path = str(OPENING_REWRITE_BRIEF_REL).replace("\\", "/")
    text = f"""---
title: Novel Publication State
memory_type: creative_writing_publication_state
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {updated_at}
status: active
tags: [creative_writing, publication, novel_platform]
---

# Novel Publication State

## Runtime
- updated_at: {updated_at}
- platform: {result.get("platform", "manual_novel_platform")}
- project_id: {DEFAULT_PROJECT_ID}
- current_project: {DEFAULT_PROJECT_TITLE}
- min_platform_chars: {result.get("min_platform_chars", MIN_PLATFORM_CHARS)}
- target_platform_chars: {result.get("target_platform_chars", TARGET_PLATFORM_CHARS)}
- publish_ready_chapters: {result.get("publish_ready_chapters", 0)}
- publish_pending_chapters: {result.get("publish_pending_chapters", 0)}
- total_publication_chapters: {result.get("total_publication_chapters", 0)}
- publication_written_this_run: {result.get("publication_written_this_run", 0)}
- shortest_publish_chars: {result.get("shortest_publish_chars", 0)}
- latest_publish_path: {result.get("latest_publish_path", "none") or "none"}
- publication_log_path: {publication_log_path}
- posting_policy: manual_review_before_upload
"""
    _atomic_write_text(root / PUBLICATION_STATE_REL, text)


def _write_publication_log(root: Path, result: dict[str, Any]) -> None:
    entries = result.get("entries") if isinstance(result.get("entries"), list) else []
    rows = "\n".join(
        "| {num:03d} | {title} | {date} | {chars} | {status} | {path} |".format(
            num=int(entry.get("chapter_number") or 0),
            title=str(entry.get("title") or ""),
            date=str(entry.get("writing_date") or ""),
            chars=int(entry.get("chars") or 0),
            status=str(entry.get("status") or ""),
            path=str(entry.get("publish_path") or ""),
        )
        for entry in entries
        if isinstance(entry, dict)
    )
    if not rows:
        rows = "| - | - | - | - | - | - |"
    updated_at = str(result.get("checked_at") or _now_iso())
    text = f"""---
title: Novel Publication Log
memory_type: creative_writing_publication_log
time_scope: long_term
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {updated_at}
status: active
tags: [creative_writing, publication_log, serial_novel]
---

# Novel Publication Log

## Posting Contract
- project_id: {DEFAULT_PROJECT_ID}
- current_project: {DEFAULT_PROJECT_TITLE}
- platform: manual_novel_platform
- target_platform_chars: {TARGET_PLATFORM_CHARS}
- min_platform_chars: {MIN_PLATFORM_CHARS}
- cadence: daily_three_chapters
- upload_status: manual_review_before_upload

## Chapter Ledger
| chapter | title | writing_date | chars | status | publish_path |
| --- | --- | --- | ---: | --- | --- |
{rows}
"""
    _atomic_write_text(root / PUBLICATION_LOG_REL, text)


def _write_state(root: Path, result: dict[str, Any]) -> None:
    written = result.get("written_chapters") if isinstance(result.get("written_chapters"), list) else []
    chapter_lines = "\n".join(
        f"- chapter_{int(item.get('chapter_number') or 0):03d}: {item.get('path', '')}"
        for item in written
        if isinstance(item, dict)
    ) or "- none"
    notes = "\n".join(f"- {note}" for note in result.get("notes", []) if str(note).strip()) or "- none"
    updated_at = str(result.get("checked_at") or _now_iso())
    publication_log_path = str(PUBLICATION_LOG_REL).replace("\\", "/")
    reference_permission_path = str(REFERENCE_PERMISSIONS_REL).replace("\\", "/")
    source_map_path = str(SOURCE_MAP_REL).replace("\\", "/")
    genre_benchmark_path = str(GENRE_BENCHMARK_REL).replace("\\", "/")
    pacing_rules_path = str(PACING_RULES_REL).replace("\\", "/")
    opening_rewrite_brief_path = str(OPENING_REWRITE_BRIEF_REL).replace("\\", "/")
    reference_digest_path = str(REFERENCE_DIGEST_REL).replace("\\", "/")
    reference_extracts_path = str(REFERENCE_EXTRACTS_REL).replace("\\", "/")
    reference_collection_log_path = str(REFERENCE_COLLECTION_LOG_REL).replace("\\", "/")
    local_reference_index_path = str(LOCAL_REFERENCE_INDEX_REL).replace("\\", "/")
    local_reference_digest_path = str(LOCAL_REFERENCE_DIGEST_REL).replace("\\", "/")
    story_bible_path = str(STORY_BIBLE_REL).replace("\\", "/")
    foreshadow_ledger_path = str(FORESHADOW_LEDGER_REL).replace("\\", "/")
    reader_model_path = str(READER_MODEL_REL).replace("\\", "/")
    xinyu_narrative_filter_path = str(XINYU_NARRATIVE_FILTER_REL).replace("\\", "/")
    creative_factory_state_path = str(CREATIVE_FACTORY_STATE_REL).replace("\\", "/")
    editorial_reviews_path = str(EDITORIAL_REVIEWS_REL).replace("\\", "/")
    reference_collection = result.get("reference_collection") if isinstance(result.get("reference_collection"), dict) else {}
    creative_factory = result.get("creative_factory") if isinstance(result.get("creative_factory"), dict) else {}
    if not reference_collection:
        previous_state = _read_text(root / STATE_REL)
        previous_status = _field(previous_state, "reference_collection_status", "")
        if previous_status:
            reference_collection = {
                "status": previous_status,
                "collected_sources": _int(_field(previous_state, "reference_sources_collected", "0")),
                "downloaded_sources": _int(_field(previous_state, "reference_downloaded_sources", "0")),
                "local_reference_files": _int(_field(previous_state, "reference_local_files", "0")),
                "raw_chapter_text_saved": _field(previous_state, "raw_chapter_text_saved", "false") == "true",
            }
    text = f"""---
title: Novel Writing State
memory_type: creative_writing_state
time_scope: working
subject_ids: [xinyu]
protected: true
source: xinyu_creative_writing
updated_at: {updated_at}
status: active
tags: [creative_writing, novel, daily_writing]
---

# Novel Writing State

## Runtime
- status: {result.get("status", "unknown")}
- updated_at: {updated_at}
- creative_writing_mode: {result.get("creative_writing_mode", DEFAULT_CREATIVE_WRITING_MODE)}
- creative_hobby_enabled: {str(bool(result.get("creative_hobby_enabled"))).lower()}
- project_id: {result.get("project_id", DEFAULT_PROJECT_ID)}
- current_project: {result.get("current_project", DEFAULT_PROJECT_TITLE)}
- daily_target_chapters: {result.get("daily_target_chapters", DEFAULT_DAILY_TARGET)}
- min_platform_chars: {result.get("min_platform_chars", MIN_PLATFORM_CHARS)}
- target_platform_chars: {result.get("target_platform_chars", TARGET_PLATFORM_CHARS)}
- today: {result.get("today", "unknown")}
- today_chapters_written: {result.get("today_chapters_written", 0)}
- chapters_written_this_run: {result.get("chapters_written_this_run", 0)}
- total_chapters: {result.get("total_chapters", 0)}
- latest_chapter_path: {result.get("latest_chapter_path", "none") or "none"}
- publish_ready_chapters: {result.get("publish_ready_chapters", 0)}
- publish_pending_chapters: {result.get("publish_pending_chapters", 0)}
- publication_latest_chapter_path: {result.get("publication_latest_chapter_path", "none") or "none"}
- publication_log_path: {result.get("publication_log_path", publication_log_path)}
- reference_permission_path: {result.get("reference_permission_path", reference_permission_path)}
- source_map_path: {result.get("source_map_path", source_map_path)}
- genre_benchmark_path: {result.get("genre_benchmark_path", genre_benchmark_path)}
- pacing_rules_path: {result.get("pacing_rules_path", pacing_rules_path)}
- opening_rewrite_brief_path: {result.get("opening_rewrite_brief_path", opening_rewrite_brief_path)}
- reference_digest_path: {result.get("reference_digest_path", reference_digest_path)}
- reference_extracts_path: {result.get("reference_extracts_path", reference_extracts_path)}
- reference_collection_log_path: {result.get("reference_collection_log_path", reference_collection_log_path)}
- reference_collection_status: {reference_collection.get("status", "not_run") or "not_run"}
- reference_sources_collected: {reference_collection.get("collected_sources", 0) or 0}
- reference_downloaded_sources: {reference_collection.get("downloaded_sources", 0) or 0}
- reference_local_files: {reference_collection.get("local_reference_files", 0) or 0}
- reference_local_index_path: {reference_collection.get("local_reference_index_path", local_reference_index_path) or local_reference_index_path}
- reference_local_digest_path: {reference_collection.get("local_reference_digest_path", local_reference_digest_path) or local_reference_digest_path}
- story_bible_path: {result.get("story_bible_path", story_bible_path)}
- foreshadow_ledger_path: {result.get("foreshadow_ledger_path", foreshadow_ledger_path)}
- reader_model_path: {result.get("reader_model_path", reader_model_path)}
- xinyu_narrative_filter_path: {result.get("xinyu_narrative_filter_path", xinyu_narrative_filter_path)}
- creative_factory_state_path: {result.get("creative_factory_state_path", creative_factory_state_path)}
- editorial_reviews_path: {result.get("editorial_reviews_path", editorial_reviews_path)}
- creative_factory_status: {creative_factory.get("factory_status", "active") if creative_factory else "active"}
- review_pass_chapters: {creative_factory.get("review_pass_chapters", 0) if creative_factory else 0}
- review_pending_chapters: {creative_factory.get("review_pending_chapters", 0) if creative_factory else 0}
- average_market_score: {creative_factory.get("average_market_score", 0) if creative_factory else 0}
- raw_chapter_text_saved: {str(bool(reference_collection.get("raw_chapter_text_saved", False))).lower()}
- next_action: {result.get("next_action", "unknown")}
- draft_mode: {result.get("draft_mode", "structured_local_seed")}
- no_overwrite: true

## Chapters Written This Run
{chapter_lines}

## Notes
{notes}
"""
    _atomic_write_text(root / STATE_REL, text)


def _notes(
    *,
    created_bootstrap: list[str],
    written: list[dict[str, Any]],
    status: str,
    publication: dict[str, Any],
    legacy_migration: dict[str, Any] | None = None,
    reference_collection: dict[str, Any] | None = None,
) -> list[str]:
    notes: list[str] = []
    migrated = legacy_migration or {}
    references = reference_collection or {}
    if migrated.get("migrated"):
        notes.append(f"legacy_layout_archived:{len(migrated.get('archived_files') or [])}")
        notes.append(f"legacy_chapters_rewritten:{migrated.get('rewritten_chapters', 0)}")
    if references:
        notes.append(f"reference_sources_collected:{references.get('collected_sources', 0)}")
        if references.get("downloaded_sources"):
            notes.append(f"reference_downloaded_sources:{references.get('downloaded_sources', 0)}")
        if references.get("local_reference_files"):
            notes.append(f"local_reference_files:{references.get('local_reference_files', 0)}")
        notes.append("reference_storage:safe_extracts_only")
    if created_bootstrap:
        notes.append(f"bootstrapped_project_files:{len(created_bootstrap)}")
    if written:
        notes.append(f"wrote_chapters:{len(written)}")
    publication_written = _int(publication.get("publication_written_this_run"), 0)
    if publication_written:
        notes.append(f"publication_drafts_written:{publication_written}")
    ready = _int(publication.get("publish_ready_chapters"), 0)
    pending = _int(publication.get("publish_pending_chapters"), 0)
    if ready:
        notes.append(f"publish_ready:{ready}")
    if pending:
        notes.append(f"publish_pending:{pending}")
    if status == "complete":
        notes.append("daily_target_met")
    return notes or ["daily_target_already_met"]


def _chapter_paths_for_day(root: Path, day: str) -> list[Path]:
    directory = root / CHAPTERS_REL / day
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("chapter-*.md") if path.is_file())


def _all_chapter_paths(root: Path) -> list[Path]:
    directory = root / CHAPTERS_REL
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*/chapter-*.md") if path.is_file())


def _next_chapter_number(root: Path) -> int:
    max_number = 0
    for path in _all_chapter_paths(root):
        match = re.search(r"chapter-(\d+)\.md$", path.name)
        if match:
            max_number = max(max_number, int(match.group(1)))
    return max_number + 1


def _chapter_path(root: Path, day: str, chapter_number: int) -> Path:
    number = chapter_number
    while True:
        path = root / CHAPTERS_REL / day / f"chapter-{number:03d}.md"
        if not path.exists():
            return path
        number += 1


def _chapter_number_from_path(path: Path) -> int:
    match = re.search(r"chapter-(\d+)\.md$", path.name)
    return int(match.group(1)) if match else 0


def _chapter_day_from_path(path: Path) -> str:
    parent = path.parent.name
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", parent):
        return parent
    return "unknown"


def _latest_chapter_rel(root: Path) -> str:
    chapters = _all_chapter_paths(root)
    if not chapters:
        return "none"
    return _rel(root, chapters[-1])


def _previous_chapter_rel(root: Path, chapter_number: int) -> str:
    if chapter_number <= 1:
        return "none"
    previous_name = f"chapter-{chapter_number - 1:03d}.md"
    for path in _all_chapter_paths(root):
        if path.name == previous_name:
            return _rel(root, path)
    return "none"


def _archive_chapter_pair(root: Path, source_path: Path, archive_root: Path) -> list[str]:
    archived: list[str] = []
    chapter_number = _chapter_number_from_path(source_path)
    pairs = [source_path]
    if chapter_number > 0:
        pairs.append(root / PUBLICATION_CHAPTERS_REL / f"chapter-{chapter_number:03d}.md")
    for path in pairs:
        text = _read_text(path)
        if not text:
            continue
        rel = _rel(root, path)
        target = archive_root / rel
        _atomic_write_text(target, text)
        archived.append(_rel(root, target))
    return archived


def _beat_for_chapter(chapter_number: int) -> dict[str, str]:
    return BEATS[(max(1, chapter_number) - 1) % len(BEATS)]


def _normalize_chapter_text(value: Any, *, chapter_number: int, title: str) -> str:
    text = str(value or "").strip()
    if len(text) < 200:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"(?ms)^---\s*\n.*?\n---\s*", "", text, count=1).strip()
    text = re.sub(r"(?ms)\n?##\s+写作札记\b.*$", "", text).strip()
    text = re.sub(r"(?ms)\n?##\s+(?:构思|创作说明|发布说明|发布记录|平台记录|字数记录)\b.*$", "", text).strip()
    text = "\n".join(
        line
        for line in text.splitlines()
        if not any(marker in line for marker in MANUSCRIPT_META_MARKERS)
    ).strip()
    if len(text) < 200:
        return ""
    if not re.match(r"^#\s*第\s*\d+\s*章", text):
        text = _pure_chapter_text(chapter_number=chapter_number, title=title, narrative=text)
    return text.strip() + "\n"


def _body_char_count(text: str) -> int:
    clean = re.sub(r"(?ms)^---\s*\n.*?\n---\s*", "", text or "", count=1).strip()
    clean = re.sub(r"(?m)^##\s+写作札记\s*\n(?:^-\s+.*\n?)*", "", clean).strip()
    return len(re.sub(r"\s+", "", clean))


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = "" if value is None else str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return _now_iso()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return _now_iso()
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def _safe_stamp(value: str) -> str:
    clean = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip())
    clean = re.sub(r"-+", "-", clean).strip("-")
    return clean or _now_iso().replace(":", "-")


def _date_part(value: str) -> str:
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        return _now_iso()[:10]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _field(text: str, name: str, default: str = "") -> str:
    match = re.search(rf"(?m)^-\s+{re.escape(name)}:\s*(.*)$", text or "")
    if not match:
        return default
    return re.sub(r"\s+", " ", match.group(1).strip()) or default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def _append_trace(root: Path, payload: dict[str, Any]) -> None:
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

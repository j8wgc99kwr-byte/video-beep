"""中英文脏话词库。

英文词条按"去掉大小写和标点/屏蔽符号后的形态"存储，便于和语音识别结果匹配。
"""

# 中文脏话：按词组做子串匹配（语音识别中文通常不带空格）
# 同时收录简体、繁体、常见同音/谐音变体，提升鲁棒性
PROFANITY_ZH = frozenset([
    # 他妈的 / 妈的 系
    "他妈的", "他媽的", "去你妈的", "去你媽的", "你妈", "你媽", "妈的", "媽的",
    "妈逼", "媽逼", "你麻痹", "你麻痺", "草泥马", "草泥馬", "尼玛", "尼瑪",
    # 操 / 草 系
    "卧槽", "我操", "我靠", "我擦", "操你", "操", "草", "艹",
    # 傻逼 系
    "傻逼", "傻屄", "傻b", "傻x", "煞笔", "傻叉", "白痴", "白癡", "白吃",
    "蠢货", "蠢貨", "蠢猪", "蠢豬", "蠢逼",
    # 骂人名词
    "混蛋", "王八蛋", "王八", "狗东西", "狗東西", "狗日的", "畜生", "贱人",
    "賤人", "婊子", "狗杂种", "狗雜種",
    # 滚 系
    "滚", "滾", "滚蛋", "滾蛋", "滚开", "滾開", "滚犊子", "滾犢子",
    # 其他
    "废物", "廢物", "垃圾", "饭桶", "飯桶", "死胖子", "神经病", "神經病",
    "变态", "變態", "奶奶的", "日你", "日",
    # 用户追加（2026-10）
    "微信", "弱智",          # 多字词
    "妈", "死", "傻", "逼", "勾", "狗", "菜",  # 单字词（注意：会命中所有含该字的词）
])

# 英文脏话：单次 token（已屏蔽形态会先归一化成这种形态）
# 归一化规则：去掉所有非字母字符后整体小写，例如 f*ck -> fck
PROFANITY_EN_TOKENS = frozenset([
    # fuck 系
    "fuck", "fucking", "fucker", "fucks", "fck", "fk", "fuk", "fuxk",
    "motherfucker", "motherfuck", "motherfcker", "mf",
    # shit 系
    "shit", "shits", "shitting", "sht", "shite",
    # bitch 系
    "bitch", "bitches", "btch", "bich",
    # ass 系
    "ass", "asses", "asshole", "assholes", "ahole", "badasse",
    # 其他
    "bastard", "bastards", "bastrd", "bitchass",
    "cunt", "cnt", "pussy", "dick", "dck", "prick", "cock", "cocksucker",
    "whore", "slut", "wanker", "bastard",
    "damn", "damnit", "hell", "crap", "jerk", "moron", "idiot", "stupid",
    "suck", "sucks", "piss", "balls", "jerkoff", "retard",
])

# 英文脏话短语（多词）：匹配时需带词边界
PROFANITY_EN_PHRASES = [
    "son of a bitch",
    "oh my god",   # 若需保留感叹请从词库删除
    "what the hell",
    "go to hell",
    "shut the fuck up",
    "shut up",
    "fuck off",
    "fuck you",
    "piss off",
    "screw you",
    "kick ass",
]

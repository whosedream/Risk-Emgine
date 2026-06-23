"""
角色模板 - 不同风险等级的用户角色故事

创建和加载解耦：
- 本文件定义角色模板（创建）
- role_loader.py 负责加载和随机选择（加载）
"""

# 低风险用户模板（60%）
LOW_RISK_TEMPLATES = [
    {
        "risk_level": 0,
        "user_profile": "30岁，IT从业者，月消费5000-10000元，使用习惯稳定",
        "behavior_pattern": "工作日9-18点活跃，主要使用手机登录，偶尔PC",
        "device_info": "iPhone 15, iOS 17, Safari",
        "ip_pattern": "固定IP，偶尔变化",
        "transaction_pattern": "小额日常消费，单笔<500元"
    },
    {
        "risk_level": 0,
        "user_profile": "25岁，大学生，月消费1000-3000元，学习用品为主",
        "behavior_pattern": "晚间20-23点活跃，周末白天也有活动",
        "device_info": "小米14, Android 14, Chrome",
        "ip_pattern": "校园IP段，稳定",
        "transaction_pattern": "小额消费，单笔<200元"
    },
    {
        "risk_level": 0,
        "user_profile": "35岁，公司职员，月消费8000-15000元，家庭用户",
        "behavior_pattern": "早晚通勤时间活跃，周末全天",
        "device_info": "华为Mate60, HarmonyOS, 华为浏览器",
        "ip_pattern": "家庭和公司IP，规律切换",
        "transaction_pattern": "中等消费，单笔<2000元"
    },
    {
        "risk_level": 0,
        "user_profile": "28岁，自由职业者，月消费3000-8000元，时间灵活",
        "behavior_pattern": "全天分散活跃，无明显规律",
        "device_info": "MacBook Pro, macOS, Chrome",
        "ip_pattern": "咖啡厅/共享办公IP，变化较多但合理",
        "transaction_pattern": "办公设备和咖啡消费，单笔<300元"
    },
    {
        "risk_level": 0,
        "user_profile": "40岁，教师，月消费6000-12000元，注重性价比",
        "behavior_pattern": "晚间和周末活跃，寒暑假全天",
        "device_info": "iPad Pro, iPadOS, Safari",
        "ip_pattern": "家庭和学校IP",
        "transaction_pattern": "教育类和家庭用品，单笔<1500元"
    },
    {
        "risk_level": 0,
        "user_profile": "50岁，退休人员，月消费3000-5000元，生活规律",
        "behavior_pattern": "白天活跃，晚间休息，作息规律",
        "device_info": "华为P60, HarmonyOS, 华为浏览器",
        "ip_pattern": "家庭IP，非常稳定",
        "transaction_pattern": "生活用品和医疗，单笔<800元"
    },
    {
        "risk_level": 0,
        "user_profile": "33岁，医生，月消费10000-20000元，消费能力较强",
        "behavior_pattern": "工作时间活跃，夜班时凌晨也有活动",
        "device_info": "iPhone 14 Pro, iOS 16, Safari",
        "ip_pattern": "医院和家庭IP，规律切换",
        "transaction_pattern": "中高消费，单笔<3000元"
    },
    {
        "risk_level": 0,
        "user_profile": "27岁，设计师，月消费5000-8000元，审美导向",
        "behavior_pattern": "下午和晚间活跃，创意工作时间",
        "device_info": "MacBook Air, macOS, Safari",
        "ip_pattern": "家庭和咖啡厅IP",
        "transaction_pattern": "设计工具和创意产品，单笔<1000元"
    },
    {
        "risk_level": 0,
        "user_profile": "45岁，公务员，月消费6000-10000元，消费稳定",
        "behavior_pattern": "工作日活跃，周末家庭时间",
        "device_info": "小米13, Android 13, Chrome",
        "ip_pattern": "单位和家庭IP，稳定",
        "transaction_pattern": "日常消费，单笔<1500元"
    },
    {
        "risk_level": 0,
        "user_profile": "29岁，外卖骑手，月消费4000-6000元，移动频繁",
        "behavior_pattern": "全天活跃，移动中使用",
        "device_info": "红米Note12, Android 13, Chrome",
        "ip_pattern": "移动IP，变化频繁但合理",
        "transaction_pattern": "小额高频消费，单笔<100元"
    },
    {
        "risk_level": 0,
        "user_profile": "38岁，全职妈妈，月消费5000-8000元，家庭导向",
        "behavior_pattern": "白天活跃，孩子上学后集中使用",
        "device_info": "OPPO Reno10, Android 13, Chrome",
        "ip_pattern": "家庭IP，稳定",
        "transaction_pattern": "母婴用品和家庭消费，单笔<500元"
    },
    {
        "risk_level": 0,
        "user_profile": "42岁，建筑工程师，月消费8000-12000元，经常出差",
        "behavior_pattern": "工作时间活跃，出差时异地登录",
        "device_info": "华为Mate50, HarmonyOS, 华为浏览器",
        "ip_pattern": "项目现场和家庭IP，符合工作性质",
        "transaction_pattern": "差旅和工具消费，单笔<2000元"
    }
]

# 中风险用户模板（30%）
MEDIUM_RISK_TEMPLATES = [
    {
        "risk_level": 1,
        "user_profile": "22岁，刚毕业，收入不稳定，偶尔大额消费",
        "behavior_pattern": "凌晨1-3点偶尔活跃，白天活动不规律",
        "device_info": "多设备切换：手机+PC+平板",
        "ip_pattern": "IP变化较频繁，3-5个不同IP",
        "transaction_pattern": "消费波动大，有时单笔>1000元"
    },
    {
        "risk_level": 1,
        "user_profile": "32岁，销售，经常出差，消费场景多样",
        "behavior_pattern": "不同城市登录，时间跨度大",
        "device_info": "多设备：公司手机+个人手机+笔记本",
        "ip_pattern": "跨省IP变化，符合出差场景",
        "transaction_pattern": "商务消费和娱乐消费混合"
    },
    {
        "risk_level": 1,
        "user_profile": "27岁，网购重度用户，退货率较高",
        "behavior_pattern": "频繁浏览和下单，但也有大量取消",
        "device_info": "手机为主，偶尔PC",
        "ip_pattern": "相对稳定，偶尔用VPN",
        "transaction_pattern": "频繁小额交易，偶尔大额"
    },
    {
        "risk_level": 1,
        "user_profile": "45岁，小商户，资金往来频繁",
        "behavior_pattern": "工作时间活跃，有固定模式",
        "device_info": "固定2-3台设备",
        "ip_pattern": "店铺和家庭IP",
        "transaction_pattern": "大额进账和小额支出交替"
    },
    {
        "risk_level": 1,
        "user_profile": "24岁，游戏玩家，消费集中在游戏和娱乐",
        "behavior_pattern": "深夜活跃，游戏时间长",
        "device_info": "游戏手机+PC，设备较固定",
        "ip_pattern": "家庭IP为主，偶尔网吧",
        "transaction_pattern": "游戏充值和娱乐消费，波动大"
    },
    {
        "risk_level": 1,
        "user_profile": "36岁，个体户，收入波动大",
        "behavior_pattern": "工作时间活跃，周末也有活动",
        "device_info": "手机+平板，设备较固定",
        "ip_pattern": "店铺和家庭IP",
        "transaction_pattern": "生意相关消费，金额波动大"
    },
    {
        "risk_level": 1,
        "user_profile": "29岁，自由撰稿人，收入不稳定",
        "behavior_pattern": "凌晨活跃，写作时间不规律",
        "device_info": "笔记本为主，偶尔手机",
        "ip_pattern": "咖啡厅和家庭IP",
        "transaction_pattern": "文化消费和生活支出，波动中等"
    },
    {
        "risk_level": 1,
        "user_profile": "41岁，中层管理，消费较高但有规律",
        "behavior_pattern": "工作时间活跃，偶尔加班到深夜",
        "device_info": "公司手机+个人手机",
        "ip_pattern": "公司和家庭IP",
        "transaction_pattern": "商务消费和家庭支出，金额较高"
    },
    {
        "risk_level": 1,
        "user_profile": "26岁，留学归国，消费习惯国际化",
        "behavior_pattern": "时差影响，活跃时间不规律",
        "device_info": "iPhone+MacBook，设备固定",
        "ip_pattern": "IP变化较多，符合国际使用习惯",
        "transaction_pattern": "跨境消费和国内消费混合"
    },
    {
        "risk_level": 1,
        "user_profile": "34岁，健身教练，消费集中在健身和健康",
        "behavior_pattern": "早晚活跃，工作时间灵活",
        "device_info": "运动手表+手机，设备固定",
        "ip_pattern": "健身房和家庭IP",
        "transaction_pattern": "健身相关消费，金额中等"
    }
]

# 高风险用户模板（10%）
HIGH_RISK_TEMPLATES = [
    {
        "risk_level": 2,
        "user_profile": "新注册账户，无历史记录，立即大额交易",
        "behavior_pattern": "注册后立即高频操作，凌晨活跃",
        "device_info": "频繁更换设备，5+台不同设备",
        "ip_pattern": "IP频繁变化，使用代理/VPN",
        "transaction_pattern": "注册后24小时内大额交易>5000元"
    },
    {
        "risk_level": 2,
        "user_profile": "账户被盗用，行为模式突变",
        "behavior_pattern": "突然改变登录时间，异地登录",
        "device_info": "新设备登录，与历史不符",
        "ip_pattern": "突然出现异地IP",
        "transaction_pattern": "异常大额转账，与历史不符"
    },
    {
        "risk_level": 2,
        "user_profile": "薅羊毛用户，批量注册",
        "behavior_pattern": "快速完成任务领取奖励，无真实消费",
        "device_info": "同设备多账户，模拟器特征",
        "ip_pattern": "IP段集中，疑似批量注册",
        "transaction_pattern": "只领券不消费，或仅最低消费"
    },
    {
        "risk_level": 2,
        "user_profile": "洗钱嫌疑，资金快进快出",
        "behavior_pattern": "收到转账后立即转出，无浏览行为",
        "device_info": "设备信息简单或伪造",
        "ip_pattern": "IP与注册地不符",
        "transaction_pattern": "大额转入立即转出，金额模式固定"
    },
    {
        "risk_level": 2,
        "user_profile": "信用卡套现，频繁大额交易后退款",
        "behavior_pattern": "短时间内大量交易，随后申请退款",
        "device_info": "设备固定但行为异常",
        "ip_pattern": "IP相对稳定，但行为模式异常",
        "transaction_pattern": "大额交易后立即退款，套取积分或额度"
    },
    {
        "risk_level": 2,
        "user_profile": "赌博网站关联，资金流向异常",
        "behavior_pattern": "深夜活跃，频繁访问特定网站",
        "device_info": "多设备，使用隐私浏览器",
        "ip_pattern": "VPN频繁切换，IP与注册地不符",
        "transaction_pattern": "小额试探后大额充值，资金流向固定"
    },
    {
        "risk_level": 2,
        "user_profile": "虚假交易，刷单嫌疑",
        "behavior_pattern": "固定时间下单，收货后立即好评",
        "device_info": "同设备多账户，行为模式雷同",
        "ip_pattern": "IP段集中，疑似批量操作",
        "transaction_pattern": "固定金额反复交易，无真实消费特征"
    },
    {
        "risk_level": 2,
        "user_profile": "账户出租，他人使用",
        "behavior_pattern": "行为模式突然改变，设备和IP变化",
        "device_info": "新设备登录，与历史不符",
        "ip_pattern": "异地IP，与注册地不符",
        "transaction_pattern": "消费类型与历史不符，金额异常"
    }
]

# 所有模板集合
ALL_TEMPLATES = {
    0: LOW_RISK_TEMPLATES,
    1: MEDIUM_RISK_TEMPLATES,
    2: HIGH_RISK_TEMPLATES
}

# 风险等级分布比例
RISK_DISTRIBUTION = {
    0: 0.6,  # 低风险 60%
    1: 0.3,  # 中风险 30%
    2: 0.1   # 高风险 10%
}

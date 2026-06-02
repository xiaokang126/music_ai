import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app
from app.database import SessionLocal, engine, Base
from app.models import *  # noqa
from app.models.healing_plan import HealingPlan

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Init gifts
from app.models.gift import Gift
existing_gifts = db.query(Gift).count()
if existing_gifts == 0:
    gifts = [
        Gift(name="花束", icon="🌸", type="free"),
        Gift(name="暖灯", icon="🕯️", type="free"),
        Gift(name="星光", icon="⭐", type="free"),
        Gift(name="纸飞机", icon="✈️", type="free"),
        Gift(name="拥抱", icon="🤗", type="free"),
        Gift(name="月亮", icon="🌙", type="free"),
        Gift(name="彩虹", icon="🌈", type="free"),
        Gift(name="四叶草", icon="🍀", type="free"),
    ]
    db.add_all(gifts)
    db.commit()
    print("Gifts initialized")

# Init healing plans
existing_plans = db.query(HealingPlan).count()
if existing_plans == 0:
    plans = [
        HealingPlan(
            name="温柔重启", description="7天，每天用一段旋律记录心情，让音乐帮你梳理情绪的线团",
            duration_days=7, cover_icon="🌅",
            tasks_json=json.dumps([
                {"day": 1, "task": "创作一首表达此刻心情的音乐", "tip": "不用追求完美，真实就好"},
                {"day": 2, "task": "用大调写一段旋律", "tip": "尝试用明亮的调式看看不一样的世界"},
                {"day": 3, "task": "给昨天的自己写一首回信曲", "tip": "用音乐和昨天的自己对话"},
                {"day": 4, "task": "创作一首节奏轻快的曲子", "tip": "试试80BPM以上的速度"},
                {"day": 5, "task": "选一个和弦进行写一段琶音", "tip": "流动的音符能带走烦恼"},
                {"day": 6, "task": "把一周的感受融进一首歌", "tip": "回头看看，你已经走了这么远"},
                {"day": 7, "task": "创作一首送给未来的自己的曲子", "tip": "带着希望走向明天"},
            ])
        ),
        HealingPlan(
            name="愈合之旅", description="14天，系统学习乐理知识并用音乐疗愈自己",
            duration_days=14, cover_icon="🌻",
            tasks_json=json.dumps([
                {"day": 1, "task": "学习音阶基础知识并创作一首C大调曲子", "tip": "从最简单的开始"},
                {"day": 2, "task": "用A小调表达内心的柔软", "tip": "小调更适合表达深沉的情感"},
                {"day": 3, "task": "学习和弦基础——大三和弦，用I-IV-V-I进行创作", "tip": "经典的和弦进行永远不会过时"},
                {"day": 4, "task": "学习小三和弦，创作一首含小调和弦的曲子", "tip": "大小调交替使用会更丰富"},
                {"day": 5, "task": "尝试用七和弦丰富你的和声色彩", "tip": "七和弦多了一层情感维度"},
                {"day": 6, "task": "创作一首给曾经重要的人的曲子", "tip": "感恩相遇，也接纳告别"},
                {"day": 7, "task": "回顾第一周——把本周所有曲子连起来听一遍", "tip": "你的音乐成长已经在发生"},
                {"day": 8, "task": "学习节奏——尝试三拍子的华尔兹节奏", "tip": "旋转的节拍会带来新的感受"},
                {"day": 9, "task": "用琶音(Arpeggio)方式创作一段流动的旋律", "tip": "让音符如水般流淌"},
                {"day": 10, "task": "切换乐器——试试弦乐的温暖音色", "tip": "不同的声音带来不同的心情"},
                {"day": 11, "task": "创作一首表达'放下'的曲子", "tip": "不是忘记，是平静地放在心里"},
                {"day": 12, "task": "用音乐描述一个你向往的地方", "tip": "用旋律画出心中的风景"},
                {"day": 13, "task": "和自己对话——创作一首内心的独白", "tip": "音乐是最诚实的语言"},
                {"day": 14, "task": "毕业创作——一首关于'新生'的曲子", "tip": "恭喜你走完了这段旅程"},
            ])
        ),
        HealingPlan(
            name="新生之路", description="30天深度疗愈，系统掌握音乐创作，用旋律书写全新的自己",
            duration_days=30, cover_icon="🌟",
            tasks_json=json.dumps([
                {"day": 1, "task": "写下此刻最真实的情绪，并创作第一首曲子", "tip": "诚实面对是疗愈的第一步"},
                {"day": 2, "task": "学习自然大调音阶，用钢琴音色创作", "tip": "大调是明亮的基调"},
                {"day": 3, "task": "学习自然小调，感受它与大调的情绪差异", "tip": "小调是我们柔软的那一面"},
                {"day": 4, "task": "尝试多利亚调式(Dorian)——小调中的一抹亮色", "tip": "在忧伤中寻找微光"},
                {"day": 5, "task": "第一周回顾——整理本周创作，给每首写一句感受", "tip": "你已经在用音乐说话了"},
                {"day": 6, "task": "学习基础和弦：大三和弦 I-IV-V 进行", "tip": "三和弦是音乐世界的地基"},
                {"day": 7, "task": "学习小三和弦：加入 ii-iii-vi", "tip": "小和弦带来更丰富的情感层次"},
                {"day": 8, "task": "创作一首使用至少5个不同和弦的曲子", "tip": "和弦越多，故事越丰富"},
                {"day": 9, "task": "学习七和弦——大七和弦的温暖", "tip": "七和弦有种慵懒的温柔"},
                {"day": 10, "task": "第二周回顾——录制一段自己的作品合辑", "tip": "听听半个月的变化"},
                {"day": 11, "task": "学习节奏：基本拍型与速度感", "tip": "节奏是音乐的心跳"},
                {"day": 12, "task": "尝试慢速曲子(50-65BPM)表达平静", "tip": "慢下来，感受呼吸"},
                {"day": 13, "task": "尝试中速曲子(90-110BPM)表达力量", "tip": "节奏能带来能量"},
                {"day": 14, "task": "用三拍子创作一首华尔兹风的曲子", "tip": "旋转会让人忘记烦恼"},
                {"day": 15, "task": "半程回顾——写下15天来的情绪变化", "tip": "你已经走了很远了"},
                {"day": 16, "task": "学习琶音奏法，创作流动的旋律", "tip": "像溪水一样流淌"},
                {"day": 17, "task": "尝试弦乐音色——大提琴般的深沉", "tip": "弦乐是最接近人声的乐器"},
                {"day": 18, "task": "尝试音乐盒音色——找回童心", "tip": "有时候简单的音色最能打动人心"},
                {"day": 19, "task": "用三种不同乐器为同一段旋律编曲", "tip": "每种声音都有独特的温度"},
                {"day": 20, "task": "创作一首'写给过去的信'", "tip": "感谢过去，然后继续前行"},
                {"day": 21, "task": "第三周回顾——选一首最喜欢的作品发布到广场", "tip": "分享让温暖加倍"},
                {"day": 22, "task": "学习情绪映射：调式与情感的对应关系", "tip": "每种调式都有它独特的颜色"},
                {"day": 23, "task": "创作一首表达'感恩'的曲子", "tip": "感恩自己，感恩相遇"},
                {"day": 24, "task": "用音乐对话——回应广场上一位陌生人的作品", "tip": "音乐是最温柔的交流方式"},
                {"day": 25, "task": "创作一首'给自己的情书'", "tip": "学会爱自己"},
                {"day": 26, "task": "尝试用音乐描述一个快乐的场景", "tip": "快乐不需要理由"},
                {"day": 27, "task": "创作一首关于'自由'的曲子", "tip": "自由是发自内心的感觉"},
                {"day": 28, "task": "整理你的创作集，给每首取一个诗意的名字", "tip": "你的作品集就是你的成长日记"},
                {"day": 29, "task": "最后一首——把30天的旅程写成一首歌", "tip": "这是你送给自己的礼物"},
                {"day": 30, "task": "毕业日——在广场发布你的'新生'专辑", "tip": "你值得所有的掌声和拥抱"},
            ])
        ),
    ]
    db.add_all(plans)
    db.commit()
    print("Healing plans initialized")

db.close()
print("Database initialization complete!")

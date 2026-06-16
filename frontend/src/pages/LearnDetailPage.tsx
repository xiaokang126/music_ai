import { useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const CONTENT: Record<string, { title: string; body: string }> = {
  'what-is': {
    title: '什么是音乐配乐导演？',
    body: `MuseCut 的核心理念是**先理解视频结构，再编排声音方案**。

与"输入一个 prompt 直接生成音乐"的 AI 作曲工具不同，MuseCut 会把视频分析成结构化数据：时长、场景变化、关键事件、字幕发现、人声区间和情绪曲线。然后生成一份 **Music Timeline**（音乐时间轴），精确到每一秒该出现什么声音。

这就像是给你的视频请了一位专业的配乐导演：TA 会先完整看一遍你的视频，理解故事节奏，然后再决定每一段用什么音乐、什么音效、什么节奏。`,
  },
  'choose-style': {
    title: '如何选择配乐风格？',
    body: `MuseCut 提供 6 种风格模板：

- **治愈 Vlog**（70-90 BPM）：温暖的钢琴 + 环境音，适合日常记录、旅行日志
- **商品种草**（100-120 BPM）：现代电子 + 强鼓点，适合产品展示和带货视频
- **高燃剪辑**（120-150 BPM）：强鼓点 + 电子乐，适合运动、快节奏混剪
- **校园回忆**（80-100 BPM）：吉他 + 轻鼓，适合毕业视频和校园生活
- **情绪短片**（60-85 BPM）：钢琴 + 弦乐，适合情感表达和故事叙述
- **知识科普**（90-110 BPM）：Lo-fi + 合成器，适合知识内容和教程`,
  },
  'bpm-emotion': {
    title: 'BPM 与情绪的关系',
    body: `BPM（Beats Per Minute）决定了音乐的基础节奏感：

| BPM | 感受 | 适合场景 |
|-----|------|---------|
| 60-80 | 舒缓、沉思 | 情感故事、慢镜头 |
| 80-100 | 温暖、舒适 | 日常 vlog、旅行 |
| 100-120 | 活力、积极 | 产品展示、科普 |
| 120-150 | 兴奋、激烈 | 运动、快节奏混剪 |
| 150+ | 紧张、爆发 | 动作场面、高潮段落 |

选择 BPM 的关键是匹配视频的情感节奏：平静的片头用低 BPM，高潮部分加快节奏，结尾逐渐回落。`,
  },
  'sfx-guide': {
    title: '音效的力量——转场和卡点',
    body: `音效（SFX）是短视频配乐中被严重低估的元素：

- **Whoosh（呼啸声）**：用于场景切换/转场，让画面切换更有"势"
- **Hit（打击声）**：用于字幕弹出、关键信息强调
- **Impact（冲击）**：用于高潮进入、大场景展示
- **Riser（推进）**：用于悬念积累、高潮前的铺垫

好的卡点不是"每一帧都加音效"，而是**在关键节点精准触发**，让观众的注意力跟着声音走。`,
  },
  'voice-ducking': {
    title: '人声避让——让你的旁白更清晰',
    body: `当视频中有人说话时，背景音乐应该自动降低音量——这就是 **Ducking（人声避让）**。

MuseCut 会根据你标记的人声区间，自动在说话时降低 BGM 音量 6-10dB，说话结束后平滑恢复。

**使用技巧**：
1. 在人声标记页面，准确标出每段对话的起止时间
2. Ducking 降低幅度建议 8dB（耳感降到约一半）
3. 过渡时间设置 0.1-0.3 秒，避免音量突变`,
  },
  'chord-basics': {
    title: '和弦进行入门',
    body: `和弦（Chord）是多个音同时发声的组合，决定了音乐的情感色彩：

- **C 大调（C-G-Am-F）**：明亮、温暖、积极——适合治愈 vlog
- **A 小调（Am-F-C-G）**：忧伤、深度、思考——适合情绪短片
- **G 大调（G-D-Em-C）**：活力、向上、青春——适合校园记忆

MuseCut 的 AI 编排引擎会根据你选择的风格自动匹配合适的和弦进行。你不需要懂乐理，AI 会帮你做所有的音乐决策。`,
  },
};

export default function LearnDetailPage() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const lesson = lessonId ? CONTENT[lessonId] : null;

  return (
    <div className="px-4 py-10 max-w-3xl mx-auto">
      <button onClick={() => window.history.back()}
        className="flex items-center gap-2 text-text-muted hover:text-text-main mb-6">
        <ArrowLeft size={18} /> 返回
      </button>
      {lesson ? (
        <>
          <h1 className="text-2xl font-bold text-text-main mb-6">{lesson.title}</h1>
          <div className="glass rounded-2xl p-8">
            <div className="text-text-secondary leading-relaxed whitespace-pre-wrap text-[15px]">
              {lesson.body}
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-20 text-text-muted">内容未找到</div>
      )}
    </div>
  );
}

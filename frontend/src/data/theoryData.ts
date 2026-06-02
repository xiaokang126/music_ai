export interface TheoryChapter {
  id: string;
  title: string;
  lessons: TheoryLesson[];
}

export interface TheoryLesson {
  id: string;
  title: string;
  content: string;
  example?: { label: string; notes: string[]; type: 'scale' | 'chord' };
  quiz?: { question: string; options: string[]; answer: number };
}

export const theoryChapters: TheoryChapter[] = [
  {
    id: 'scale',
    title: '第一章：音阶入门',
    lessons: [
      {
        id: 'scale-1',
        title: '什么是音阶？',
        content: '音阶就是按高低顺序排列的一组音。就像彩虹有七种颜色，音乐也有七个基本音：Do、Re、Mi、Fa、Sol、La、Si。它们循环往复，高一个循环就是高八度。最常见的音阶是大调音阶（听起来明亮、快乐）和小调音阶（听起来柔和、忧伤）。',
        example: { label: 'C大调音阶', notes: ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'], type: 'scale' },
        quiz: { question: '大调音阶通常给人什么感觉？', options: ['明亮、快乐', '忧伤、深沉', '紧张、不安'], answer: 0 }
      },
      {
        id: 'scale-2',
        title: '大调与小调',
        content: '大调音阶（Major Scale）在钢琴上就是从C开始弹所有的白键：C-D-E-F-G-A-B。听起来阳光、明亮。小调音阶（Minor Scale）从A开始弹白键：A-B-C-D-E-F-G。听起来柔和、感性。失恋时的情绪，用小调来表达往往更贴切。',
        example: { label: 'A小调音阶', notes: ['A4', 'B4', 'C5', 'D5', 'E5', 'F5', 'G5', 'A5'], type: 'scale' },
        quiz: { question: 'A小调从哪个音开始？', options: ['C', 'A', 'G'], answer: 1 }
      },
      {
        id: 'scale-3',
        title: '调式与情绪',
        content: '不同的调式就像不同的颜色。D小调深沉而忧郁，C大调纯净明亮，G大调温暖有力。选择不同的调式，就是为你的音乐选择底色。在创作时，你可以根据此刻的心情来选择合适的调式。',
      }
    ],
  },
  {
    id: 'chord',
    title: '第二章：和弦基础',
    lessons: [
      {
        id: 'chord-1',
        title: '什么是和弦？',
        content: '和弦就是三个或更多音同时发声的组合。如果说单音是一个人在说话，和弦就是一群人在合唱。最简单的和弦是三和弦，由根音、三度音、五度音三个音组成。比如C大三和弦就是C-E-G。',
        example: { label: 'C大三和弦', notes: ['C4', 'E4', 'G4'], type: 'chord' },
        quiz: { question: '三和弦由几个音组成？', options: ['2个', '3个', '4个'], answer: 1 }
      },
      {
        id: 'chord-2',
        title: '大三和弦 vs 小三和弦',
        content: '大三和弦听起来明亮、坚定。小三和弦听起来柔和、略带忧伤。区别在于中间那个音（三度音）——大三和弦的三度音比根音高4个半音，小三和弦只高3个半音。就这小小的差距，决定了情绪的基调。',
        example: { label: 'A小三和弦', notes: ['A4', 'C5', 'E5'], type: 'chord' },
      },
      {
        id: 'chord-3',
        title: '七和弦——更丰富的情感',
        content: '在三和弦基础上再加一个音（七度音），就变成了七和弦。大七和弦（maj7）有种温柔梦幻的感觉，小七和弦（m7）带着一丝慵懒和忧郁。七和弦是表达复杂情绪的利器，也是很多治愈系音乐的标配。',
        example: { label: 'Am7和弦', notes: ['A4', 'C5', 'E5', 'G5'], type: 'chord' },
        quiz: { question: '大七和弦的后缀是什么？', options: ['maj7', 'm7', 'dim7'], answer: 0 }
      },
    ],
  },
  {
    id: 'rhythm',
    title: '第三章：节奏感知',
    lessons: [
      {
        id: 'rhythm-1',
        title: '什么是节奏？',
        content: '节奏是音乐的骨架，决定音符出现的时机和长短。心跳是天然的节奏——平静时缓慢而有规律，激动时快而有力。速度用BPM（每分钟节拍数）来衡量：60BPM大约每秒一拍，像缓慢的呼吸；120BPM则是快节奏的律动。',
        quiz: { question: 'BPM 是什么意思？', options: ['每秒节拍数', '每分钟节拍数', '每小时节拍数'], answer: 1 }
      },
      {
        id: 'rhythm-2',
        title: '常用节奏型',
        content: '琶音（Arpeggio）是和弦音一个一个弹出来的温柔流动感；柱式和弦（Block）是和弦音同时弹出来的坚实感；分解和弦（Broken Chord）介于两者之间。表达忧伤情绪时，缓慢的琶音是最常用的手法——像雨滴一样轻柔地落下。',
      },
    ],
  },
  {
    id: 'emotion',
    title: '第四章：情绪映射',
    lessons: [
      {
        id: 'emotion-1',
        title: '音乐与情绪的对应关系',
        content: '悲伤：小调 + 慢速 + 下行旋律 + 钢琴/弦乐\n希望：大调 + 中速 + 上行旋律 + 吉他/钢琴\n平静：大调 + 慢速 + 平稳旋律 + 暖垫/钢琴\n思念：小调 + 中慢速 + 波浪旋律 + 钢琴/音乐盒\n学会用音乐"翻译"情绪，是创作中最美妙的一步。',
      },
      {
        id: 'emotion-2',
        title: '用音乐和自己对话',
        content: '每一段旋律都是内心的独白。不要追求"好听"或"专业"，真实就好。今天的你，无论是伤心、迷茫还是重新燃起希望，都值得被记录成音乐。这也是失恋广场存在的意义——在这里，每一种情绪都值得被听见。',
      },
    ],
  },
];

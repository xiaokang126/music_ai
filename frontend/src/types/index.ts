export interface MusicParams {
  scale: string;
  tempo: number;
  chord_progression: string[];
  rhythm_style: string;
  melody_contour: string;
  instrument: string;
  mood: string;
  description?: string;
}

export interface MusicWork {
  id: number;
  user_id: number;
  title: string;
  mood_tag: string;
  params_json: string;
  reply_to_work_id: number | null;
  is_public: boolean;
  likes_count: number;
  description: string;
  created_at: string;
  username: string;
  avatar: string;
  reply_count: number;
  gift_count: number;
  comment_count: number;
  replies?: MusicWork[];
}

export interface User {
  id: number;
  username: string;
  avatar: string;
  created_at: string;
}

export interface Comment {
  id: number;
  work_id: number;
  user_id: number;
  content: string;
  username: string;
  avatar: string;
  created_at: string;
}

export interface EmotionDiary {
  id: number;
  user_id: number;
  mood_tag: string;
  mood_score: number;
  note: string;
  work_id: number | null;
  created_at: string;
}

export interface HealingPlan {
  id: number;
  name: string;
  description: string;
  duration_days: number;
  cover_icon: string;
  tasks_json: string;
}

export interface UserHealingPlan {
  id: number;
  user_id: number;
  plan_id: number;
  current_day: number;
  start_date: string;
  completed_tasks_json: string;
  is_completed: number;
  plan_name: string;
  duration_days: number;
  tasks_json: string;
}

export interface Gift {
  id: number;
  name: string;
  icon: string;
  type: string;
}

export interface WorkGift {
  id: number;
  work_id: number;
  sender_id: number;
  gift_id: number;
  sender_name: string;
  gift_name: string;
  gift_icon: string;
  created_at: string;
}

export interface ResonanceWork extends MusicWork {
  match_score: number;
}

export interface ChartDataPoint {
  date: string;
  score: number;
  mood_tag: string;
}

export interface MoodOption {
  label: string;
  value: string;
  color: string;
}

export const MOOD_OPTIONS: MoodOption[] = [
  { label: '忧伤', value: 'sad', color: '#6B7DB3' },
  { label: '思念', value: 'nostalgic', color: '#C8A882' },
  { label: '治愈', value: 'healing', color: '#5DB5A4' },
  { label: '希望', value: 'hopeful', color: '#F0C060' },
  { label: '平静', value: 'calm', color: '#7EC8A0' },
  { label: '温暖', value: 'warm', color: '#E8916A' },
  { label: '孤独', value: 'lonely', color: '#9B8EC4' },
  { label: '苦涩', value: 'bittersweet', color: '#C4828C' },
];

export const INSTRUMENTS = [
  { label: '钢琴', value: 'piano', icon: '🎹' },
  { label: '吉他', value: 'guitar', icon: '🎸' },
  { label: '弦乐', value: 'strings', icon: '🎻' },
  { label: '音乐盒', value: 'music_box', icon: '🎵' },
  { label: '暖垫', value: 'warm_pad', icon: '🎧' },
];

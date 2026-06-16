// ========== Enums / Union Types ==========

export type VideoType =
  | 'healing_vlog'
  | 'product_promo'
  | 'hype_edit'
  | 'campus_memory'
  | 'emotional_story'
  | 'knowledge_edu';

export type EmotionType =
  | 'calm'
  | 'warm'
  | 'happy'
  | 'intense'
  | 'sad'
  | 'excited'
  | 'nostalgic'
  | 'mysterious'
  | 'energetic';

export type InstrumentType =
  | 'soft_piano'
  | 'acoustic_guitar'
  | 'pad'
  | 'orchestral'
  | 'lofi_beats'
  | 'synth'
  | 'full_band'
  | 'electronic'
  | 'piano_with_pad'
  | 'piano_with_strings'
  | 'electronic_beat';

export type BeatPattern =
  | 'simple_kick_snare'
  | 'energetic_beat'
  | 'lofi_beat'
  | 'trap_hats';

export type FadeType = 'fade_in' | 'fade_out' | 'fade_out_start';

// ========== Video Analysis Types ==========

export interface VideoProfile {
  id: string;
  duration_seconds: number;
  video_type: VideoType;
  overall_emotion: EmotionType;
  scenes: SceneInfo[];
}

export interface SceneInfo {
  index: number;
  start_time: number;
  end_time: number;
  description: string;
  emotion: EmotionType;
  intensity: number;
}

export interface KeyEvent {
  timestamp: number;
  event_type: string;
  description: string;
  importance: number;
}

export interface SceneChangeCandidate {
  timestamp: number;
  confidence: number;
  change_type: string;
}

export interface VoiceRegion {
  start_time: number;
  end_time: number;
  voice_type: string;
  content_preview: string;
}

export interface CaptionEvent {
  timestamp: number;
  text: string;
  duration: number;
  style: string;
}

export interface EmotionPoint {
  timestamp: number;
  emotion: EmotionType;
  intensity: number;
}

// ========== Music Generation Types ==========

export interface MusicTimeline {
  segments: TimelineSegment[];
  total_duration: number;
  global_key: string;
  global_tempo: number;
}

export interface TimelineSegment {
  start_time: number;
  end_time: number;
  emotion: EmotionType;
  intensity: number;
  instruments: InstrumentType[];
  beat_pattern: BeatPattern;
  chord_progression: string[];
  description: string;
}

export interface SFXNode {
  timestamp: number;
  sfx_type: string;
  description: string;
  duration: number;
  volume: number;
}

export interface DuckingNode {
  start_time: number;
  end_time: number;
  duck_amount_db: number;
  reason: string;
}

// ========== Project Types ==========

export interface VideoProject {
  id: string;
  user_id: number;
  title: string;
  status: 'draft' | 'analyzing' | 'generating' | 'mixing' | 'completed' | 'failed';
  video_url: string;
  video_profile: VideoProfile | null;
  music_timeline: MusicTimeline | null;
  sfx_nodes: SFXNode[];
  ducking_nodes: DuckingNode[];
  final_audio_url: string | null;
  export_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface GenerationSession {
  id: string;
  project_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  current_step: string;
  progress: number;
  error_message: string | null;
  created_at: string;
}

export interface ExportTask {
  id: string;
  project_id: string;
  format: 'mp4' | 'mov' | 'webm';
  quality: '1080p' | '720p' | '480p';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  download_url: string | null;
  created_at: string;
  completed_at: string | null;
}

// ========== Community Types ==========

export interface CommunityPost {
  id: number;
  user_id: number;
  username: string;
  avatar: string;
  project_id: string;
  title: string;
  description: string;
  video_url: string;
  likes_count: number;
  comments_count: number;
  created_at: string;
}

export interface Comment {
  id: number;
  post_id: number;
  user_id: number;
  username: string;
  avatar: string;
  content: string;
  created_at: string;
}

// ========== User Types ==========

export interface User {
  id: string;
  username: string;
  avatar_url?: string;
  avatar?: string;
  created_at: string;
}

export interface LoginForm {
  username: string;
  password: string;
}

export interface RegisterForm {
  username: string;
  password: string;
}

// ========== Video Type Labels ==========

export const VIDEO_TYPE_LABELS: Record<VideoType, string> = {
  healing_vlog: '治愈Vlog',
  product_promo: '产品推广',
  hype_edit: '高燃混剪',
  campus_memory: '校园记忆',
  emotional_story: '情感故事',
  knowledge_edu: '知识教育',
};

export const EMOTION_LABELS: Record<EmotionType, string> = {
  calm: '平静',
  warm: '温暖',
  happy: '快乐',
  intense: '激烈',
  sad: '忧伤',
  excited: '兴奋',
  nostalgic: '怀旧',
  mysterious: '神秘',
  energetic: '活力',
};

export const INSTRUMENT_LABELS: Record<InstrumentType, string> = {
  soft_piano: '柔和钢琴',
  acoustic_guitar: '原声吉他',
  pad: '铺底音色',
  orchestral: '管弦乐',
  lofi_beats: 'LoFi节拍',
  synth: '合成器',
  full_band: '全乐队',
  electronic: '电子乐',
  piano_with_pad: '钢琴+铺底',
  piano_with_strings: '钢琴+弦乐',
  electronic_beat: '电子节拍',
};

export const BEAT_PATTERN_LABELS: Record<BeatPattern, string> = {
  simple_kick_snare: '简易底鼓军鼓',
  energetic_beat: '活力节拍',
  lofi_beat: 'LoFi节拍',
  trap_hats: 'Trap踩镲',
};

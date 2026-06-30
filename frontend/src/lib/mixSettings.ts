export type MixSettingKey = 'original_volume' | 'bgm_volume' | 'beat_volume' | 'sfx_volume' | 'master_volume';

export type MixSettings = Record<MixSettingKey, number>;

export const DEFAULT_MIX_SETTINGS: MixSettings = {
  original_volume: 100,
  bgm_volume: 90,
  beat_volume: 18,
  sfx_volume: 15,
  master_volume: 90,
};

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

const readNumber = (raw: unknown, fallback: number, max: number) => {
  const value = typeof raw === 'number' ? raw : Number(raw);
  return Number.isFinite(value) ? clamp(value, 0, max) : fallback;
};

export const normalizeMixSettings = (raw: unknown): MixSettings => {
  const data = raw && typeof raw === 'object' ? raw as Partial<Record<MixSettingKey, unknown>> : {};
  return {
    original_volume: readNumber(data.original_volume, DEFAULT_MIX_SETTINGS.original_volume, 200),
    bgm_volume: readNumber(data.bgm_volume, DEFAULT_MIX_SETTINGS.bgm_volume, 200),
    beat_volume: readNumber(data.beat_volume, DEFAULT_MIX_SETTINGS.beat_volume, 120),
    sfx_volume: readNumber(data.sfx_volume, DEFAULT_MIX_SETTINGS.sfx_volume, 120),
    master_volume: readNumber(data.master_volume, DEFAULT_MIX_SETTINGS.master_volume, 140),
  };
};

export const sliderToDb = (value: number) => {
  if (value <= 0) return -Infinity;
  return Math.max(-60, 20 * Math.log10(value / 100));
};

export const browserVideoVolume = (value: number) => clamp(value, 0, 100) / 100;

export const sliderFill = (value: number, max: number) => clamp((value / max) * 100, 0, 100);

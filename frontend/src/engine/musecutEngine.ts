import * as Tone from 'tone';

interface DuckingNode { start: number; end: number; reduce_db: number; }

class MuseCutAudioEngine {
  private static instance: MuseCutAudioEngine;
  private bgmPlayer: Tone.Player | null = null;
  private bgmVol: Tone.Volume;
  private beatVol: Tone.Volume;
  private sfxVol: Tone.Volume;
  private masterVol: Tone.Volume;
  private bgmBaseDb = -4;
  private kick: Tone.MembraneSynth;
  private snare: Tone.NoiseSynth;
  private hihat: Tone.MetalSynth;
  private sfxPlayers: Map<string, Tone.Player> = new Map();
  private initialized = false;

  private constructor() {
    this.masterVol = new Tone.Volume(-2).toDestination();
    this.bgmVol = new Tone.Volume(-4).connect(this.masterVol);
    this.beatVol = new Tone.Volume(-26).connect(this.masterVol);
    this.sfxVol = new Tone.Volume(-28).connect(this.masterVol);
    this.kick = new Tone.MembraneSynth({ pitchDecay: 0.05, octaves: 4, volume: -10 }).connect(this.beatVol);
    this.snare = new Tone.NoiseSynth({ noise: { type: 'white' }, envelope: { attack: 0.001, decay: 0.15, sustain: 0 } }).connect(this.beatVol);
    this.hihat = new Tone.MetalSynth({ envelope: { attack: 0.001, decay: 0.05 }, harmonicity: 5.1, modulationIndex: 32, resonance: 4000, volume: -18 }).connect(this.beatVol);
  }

  static getInstance(): MuseCutAudioEngine {
    if (!this.instance) this.instance = new MuseCutAudioEngine();
    return this.instance;
  }

  get isReady() { return this.initialized; }
  get bgmVolume() { return this.bgmVol; }
  get beatVolume() { return this.beatVol; }
  get sfxVolume() { return this.sfxVol; }
  get masterVolume() { return this.masterVol; }

  setBgmVolumeDb(db: number): void {
    this.bgmBaseDb = Number.isFinite(db) ? db : -80;
    this.bgmVol.volume.value = db;
  }

  async init(): Promise<void> {
    if (this.initialized) return;
    await Tone.start();
    Tone.Transport.bpm.value = 120;
    await this.preloadDefaultSFX();
    this.initialized = true;
  }

  async loadBGM(url: string): Promise<void> {
    if (this.bgmPlayer) { this.bgmPlayer.dispose(); this.bgmPlayer = null; }
    return new Promise((resolve, reject) => {
      const player = new Tone.Player({
        url,
        onload: () => {
          this.bgmPlayer = player;
          player.loop = true;
          player.connect(this.bgmVol);
          resolve();
        },
        onerror: () => { reject(new Error('BGM load failed')); },
      });
    });
  }

  async loadSFXBuffer(name: string, url: string): Promise<void> {
    if (this.sfxPlayers.has(name)) return;
    const player = new Tone.Player(url).connect(this.sfxVol);
    await Tone.loaded();
    this.sfxPlayers.set(name, player);
  }

  private async preloadDefaultSFX(): Promise<void> {
    const defaults: Record<string, string> = {
      whoosh: '/sfx/whoosh_short.wav',
      hit: '/sfx/hit_impact.wav',
      impact: '/sfx/impact_cinematic.wav',
      riser: '/sfx/riser_short.wav',
      riser_reverse: '/sfx/riser_reverse.wav',
    };
    await Promise.all(Object.entries(defaults).map(([name, url]) =>
      this.loadSFXBuffer(name, url).catch(() => undefined)
    ));
  }

  scheduleTimeline(timeline: any): void {
    Tone.Transport.cancel();
    const bpm = timeline.bpm || 82;
    Tone.Transport.bpm.value = bpm;

    const segs = timeline.timeline || [];
    segs.forEach((seg: any) => {
      if (seg.beat_pattern) {
        this.scheduleBeat(seg.beat_pattern, seg.start, seg.end, bpm);
      }
      if (seg.sfx && seg.sfx.type) {
        this.scheduleSFX(seg.sfx.type, seg.start);
      }
    });

    (timeline.beat_points || []).slice(0, 260).forEach((point: any) => {
      const t = Number(point.time);
      if (!Number.isFinite(t) || t < 0) return;
      this.scheduleBeatPoint(t, point.type || 'beat', Number(point.confidence) || 0.5);
    });

    (timeline.ducking_schedule || []).forEach((d: DuckingNode) => {
      this.scheduleDucking(d);
    });
  }

  private scheduleBeatPoint(timeSeconds: number, kind: string, confidence: number): void {
    const velocity = Math.max(0.08, Math.min(0.22, 0.08 + confidence * 0.12));
    Tone.Transport.schedule((time) => {
      if (kind === 'onset') {
        this.snare.triggerAttackRelease('32n', time, velocity * 0.7);
      } else {
        this.hihat.triggerAttackRelease('64n', time, velocity);
      }
    }, timeSeconds);
  }

  private scheduleBeat(pattern: string, startT: number, endT: number, bpm: number): void {
    const beatDur = 60 / bpm;
    for (let t = startT; t < endT; t += beatDur) {
      const beatInBar = Math.round((t - startT) / beatDur) % 4;
      Tone.Transport.schedule((time) => {
        this.kick.triggerAttackRelease('C2', '16n', time);
      }, t);
      if (beatInBar === 2) {
        Tone.Transport.schedule((time) => {
          this.snare.triggerAttackRelease('16n', time);
        }, t);
      }
    }
    // Add hi-hat 8th notes
    for (let t = startT; t < endT; t += beatDur / 2) {
      Tone.Transport.schedule((time) => {
        this.hihat.triggerAttackRelease('32n', time);
      }, t);
    }
  }

  private scheduleSFX(type: string, startT: number): void {
    const player = this.sfxPlayers.get(type);
    if (player) {
      Tone.Transport.schedule((time) => {
        player.start(time);
      }, startT);
    }
  }

  private scheduleDucking(d: DuckingNode): void {
    Tone.Transport.schedule(() => {
      const base = Number.isFinite(this.bgmBaseDb) ? this.bgmBaseDb : -80;
      this.bgmVol.volume.rampTo(base - Math.abs(d.reduce_db || 0), 0.12);
    }, d.start);
    Tone.Transport.schedule(() => {
      const base = Number.isFinite(this.bgmBaseDb) ? this.bgmBaseDb : -80;
      this.bgmVol.volume.rampTo(base, 0.35);
    }, d.end);
  }

  async play(fromSeconds = 0): Promise<void> {
    if (!this.initialized) await this.init();
    const offset = Math.max(0, fromSeconds);
    Tone.Transport.stop();
    this.bgmPlayer?.stop();
    this.bgmVol.volume.value = Number.isFinite(this.bgmBaseDb) ? this.bgmBaseDb : -80;
    (Tone.Transport as any).seconds = offset;
    Tone.Transport.start('+0.02', offset);
    if (this.bgmPlayer?.loaded) {
      const duration = this.bgmPlayer.buffer.duration;
      const bgmOffset = duration > 0 ? Math.min(offset % duration, Math.max(0, duration - 0.05)) : 0;
      this.bgmPlayer.start('+0.02', bgmOffset);
    }
  }

  stop(reset = true): void {
    Tone.Transport.stop();
    this.bgmPlayer?.stop();
    this.bgmVol.volume.value = Number.isFinite(this.bgmBaseDb) ? this.bgmBaseDb : -80;
    if (reset) {
      (Tone.Transport as any).seconds = 0;
    }
  }

  setBPM(bpm: number): void {
    Tone.Transport.bpm.value = bpm;
  }

  dispose(): void {
    Tone.Transport.cancel();
    this.bgmPlayer?.dispose();
    this.kick.dispose();
    this.snare.dispose();
    this.hihat.dispose();
    this.sfxPlayers.forEach(p => p.dispose());
    this.masterVol.dispose();
  }
}

export const audioEngine = MuseCutAudioEngine.getInstance();

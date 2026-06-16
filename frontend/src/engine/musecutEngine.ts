import * as Tone from 'tone';

interface DuckingNode { start: number; end: number; reduce_db: number; }

class MuseCutAudioEngine {
  private static instance: MuseCutAudioEngine;
  private bgmPlayer: Tone.Player | null = null;
  private bgmVol: Tone.Volume;
  private beatVol: Tone.Volume;
  private sfxVol: Tone.Volume;
  private masterVol: Tone.Volume;
  private kick: Tone.MembraneSynth;
  private snare: Tone.NoiseSynth;
  private hihat: Tone.MetalSynth;
  private sfxPlayers: Map<string, Tone.Player> = new Map();
  private initialized = false;

  private constructor() {
    this.masterVol = new Tone.Volume(0).toDestination();
    this.bgmVol = new Tone.Volume(0).connect(this.masterVol);
    this.beatVol = new Tone.Volume(-3).connect(this.masterVol);
    this.sfxVol = new Tone.Volume(-3).connect(this.masterVol);
    this.kick = new Tone.MembraneSynth({ pitchDecay: 0.05, octaves: 4, volume: -4 }).connect(this.beatVol);
    this.snare = new Tone.NoiseSynth({ noise: { type: 'white' }, envelope: { attack: 0.001, decay: 0.15, sustain: 0 } }).connect(this.beatVol);
    this.hihat = new Tone.MetalSynth({ envelope: { attack: 0.001, decay: 0.05 }, harmonicity: 5.1, modulationIndex: 32, resonance: 4000, volume: -10 }).connect(this.beatVol);
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
          player.connect(this.bgmVol);
          this.syncBGMStart();
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
    this.syncBGMStart();

    const segs = timeline.timeline || [];
    segs.forEach((seg: any) => {
      if (seg.beat_pattern) {
        this.scheduleBeat(seg.beat_pattern, seg.start, seg.end, bpm);
      }
      if (seg.sfx && seg.sfx.type) {
        this.scheduleSFX(seg.sfx.type, seg.start);
      }
    });

    (timeline.ducking_schedule || []).forEach((d: DuckingNode) => {
      this.scheduleDucking(d);
    });
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
      this.bgmVol.volume.rampTo(-d.reduce_db, 0.1);
    }, d.start);
    Tone.Transport.schedule(() => {
      this.bgmVol.volume.rampTo(0, 0.3);
    }, d.end);
  }

  private syncBGMStart(): void {
    if (!this.bgmPlayer) return;
    try {
      this.bgmPlayer.unsync();
    } catch {
      // Tone versions differ slightly; a fresh player may not be synced yet.
    }
    this.bgmPlayer.sync().start(0);
  }

  async play(fromSeconds = 0): Promise<void> {
    if (!this.initialized) await this.init();
    Tone.Transport.stop();
    (Tone.Transport as any).seconds = Math.max(0, fromSeconds);
    Tone.Transport.start();
  }

  stop(reset = true): void {
    Tone.Transport.stop();
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

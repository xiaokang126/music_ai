import * as Tone from 'tone';
import type { MusicParams } from '../types';

const SCALE_NOTES: Record<string, string[]> = {
  C_major: ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5'],
  D_major: ['D4', 'E4', 'F#4', 'G4', 'A4', 'B4', 'C#5', 'D5'],
  E_major: ['E4', 'F#4', 'G#4', 'A4', 'B4', 'C#5', 'D#5', 'E5'],
  F_major: ['F4', 'G4', 'A4', 'Bb4', 'C5', 'D5', 'E5', 'F5'],
  G_major: ['G4', 'A4', 'B4', 'C5', 'D5', 'E5', 'F#5', 'G5'],
  A_major: ['A4', 'B4', 'C#5', 'D5', 'E5', 'F#5', 'G#5', 'A5'],
  C_minor: ['C4', 'D4', 'Eb4', 'F4', 'G4', 'Ab4', 'Bb4', 'C5'],
  D_minor: ['D4', 'E4', 'F4', 'G4', 'A4', 'Bb4', 'C5', 'D5'],
  E_minor: ['E4', 'F#4', 'G4', 'A4', 'B4', 'C5', 'D5', 'E5'],
  F_minor: ['F4', 'G4', 'Ab4', 'Bb4', 'C5', 'Db5', 'Eb5', 'F5'],
  G_minor: ['G4', 'A4', 'Bb4', 'C5', 'D5', 'Eb5', 'F5', 'G5'],
  A_minor: ['A4', 'B4', 'C5', 'D5', 'E5', 'F5', 'G5', 'A5'],
  B_minor: ['B4', 'C#5', 'D5', 'E5', 'F#5', 'G5', 'A5', 'B5'],
};

const CHORD_MAP: Record<string, string[]> = {
  Am7: ['A4', 'C5', 'E5', 'G5'],
  Dm7: ['D4', 'F4', 'A4', 'C5'],
  Gm7: ['G4', 'Bb4', 'D5', 'F5'],
  Cm7: ['C4', 'Eb4', 'G4', 'Bb4'],
  Fm7: ['F4', 'Ab4', 'C5', 'Eb5'],
  Bbm7: ['Bb4', 'Db5', 'F5', 'Ab5'],
  Em7: ['E4', 'G4', 'B4', 'D5'],
  Bm7: ['B4', 'D5', 'F#5', 'A5'],
  Cmaj7: ['C4', 'E4', 'G4', 'B4'],
  Fmaj7: ['F4', 'A4', 'C5', 'E5'],
  Gmaj7: ['G4', 'B4', 'D5', 'F#5'],
  Amaj7: ['A4', 'C#5', 'E5', 'G#5'],
  Dmaj7: ['D4', 'F#4', 'A4', 'C#5'],
  Emaj7: ['E4', 'G#4', 'B4', 'D#5'],
  Abmaj7: ['Ab4', 'C5', 'Eb5', 'G5'],
  Bbmaj7: ['Bb4', 'D5', 'F5', 'A5'],
  Dbmaj7: ['Db4', 'F4', 'Ab4', 'C5'],
  Ebmaj7: ['Eb4', 'G4', 'Bb4', 'D5'],
  G7: ['G4', 'B4', 'D5', 'F5'],
  C7: ['C4', 'E4', 'G4', 'Bb4'],
  D7: ['D4', 'F#4', 'A4', 'C5'],
  A7: ['A4', 'C#5', 'E5', 'G5'],
  E7: ['E4', 'G#4', 'B4', 'D5'],
  B7: ['B4', 'D#5', 'F#5', 'A5'],
};

class ToneMusicEngine {
  private synth: Tone.PolySynth | null = null;
  private reverb: Tone.Reverb | null = null;
  private delay: Tone.FeedbackDelay | null = null;
  private params: MusicParams | null = null;
  private isPlaying = false;
  private chordIndex = 0;
  private loopId: number | null = null;

  async init() {
    if (this.synth) return;
    await Tone.start();
    this.reverb = new Tone.Reverb({ decay: 2.5, wet: 0.3 }).toDestination();
    this.delay = new Tone.FeedbackDelay({ delayTime: '8n', feedback: 0.15, wet: 0.15 }).connect(this.reverb);
    this.synth = new Tone.PolySynth(Tone.Synth, {
      voice: Tone.Synth as any,
      options: { oscillator: { type: 'triangle' as const }, envelope: { attack: 0.08, decay: 0.4, sustain: 0.3, release: 1.5 } },
    } as any).connect(this.delay);
    this.synth.volume.value = -8;
  }

  loadParams(params: MusicParams) {
    this.stop();
    this.params = params;
    Tone.Transport.bpm.value = params.tempo;
  }

  play() {
    if (!this.params || !this.synth) return;
    this.stop();
    this.isPlaying = true;
    this.chordIndex = 0;

    const playChord = () => {
      if (!this.isPlaying || !this.params || !this.synth) return;
      const chords = this.params.chord_progression;
      const chordName = chords[this.chordIndex % chords.length];
      const notes = CHORD_MAP[chordName] || this.getChordNotes(chordName);
      if (notes.length > 0) {
        const now = Tone.now();
        const duration = this.getChordDuration();
        notes.forEach((note, i) => {
          this.synth?.triggerAttackRelease(note, duration, now + i * 0.02, 0.5 / notes.length);
        });
      }
      this.chordIndex++;
      this.loopId = window.setTimeout(playChord, this.getChordInterval());
    };

    playChord();
    Tone.Transport.start();
  }

  stop() {
    this.isPlaying = false;
    if (this.loopId) {
      clearTimeout(this.loopId);
      this.loopId = null;
    }
    if (this.synth) {
      this.synth.releaseAll();
    }
    Tone.Transport.stop();
  }

  setTempo(bpm: number) {
    if (this.params) this.params.tempo = bpm;
    Tone.Transport.bpm.value = bpm;
  }

  updateChord(index: number, chord: string) {
    if (this.params && index < this.params.chord_progression.length) {
      this.params.chord_progression[index] = chord;
    }
  }

  private getChordDuration(): number {
    const rhythm = this.params?.rhythm_style || 'flowing_arpeggio';
    switch (rhythm) {
      case 'slow_arpeggio': return 2.5;
      case 'steady_waltz': return 1.8;
      case 'soft_block': return 2.0;
      default: return 2.0;
    }
  }

  private getChordInterval(): number {
    const rhythm = this.params?.rhythm_style || 'flowing_arpeggio';
    switch (rhythm) {
      case 'slow_arpeggio': return 4000;
      case 'gentle_broken_chord': return 2500;
      case 'steady_waltz': return 2000;
      case 'soft_block': return 3500;
      default: return 3000;
    }
  }

  private getChordNotes(name: string): string[] {
    const defaults: Record<string, string[]> = {
      Am7: ['A4', 'C5', 'E5', 'G5'], Dm7: ['D4', 'F4', 'A4', 'C5'],
      Gm7: ['G4', 'Bb4', 'D5', 'F5'], Cm7: ['C4', 'Eb4', 'G4', 'Bb4'],
      Fmaj7: ['F4', 'A4', 'C5', 'E5'], Cmaj7: ['C4', 'E4', 'G4', 'B4'],
      Gmaj7: ['G4', 'B4', 'D5', 'F#5'], G7: ['G4', 'B4', 'D5', 'F5'],
      C7: ['C4', 'E4', 'G4', 'Bb4'], D7: ['D4', 'F#4', 'A4', 'C5'],
    };
    return defaults[name] || ['C4', 'E4', 'G4', 'B4'];
  }

  dispose() {
    this.stop();
    this.synth?.dispose();
    this.reverb?.dispose();
    this.delay?.dispose();
    this.synth = null;
    this.reverb = null;
    this.delay = null;
  }
}

export const toneEngine = new ToneMusicEngine();

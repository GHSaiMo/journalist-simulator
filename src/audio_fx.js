/**
 * Procedural Web Audio synthesizer for tactile 2000s photojournalism acoustics:
 * mechanical SLR mirror slap, shutter curtain click, xenon flash capacitor whine,
 * zoom ring detents, cloth rustle, and wool-carpet vs marble footsteps.
 */

export class SoundFX {
  constructor() {
    this.ctx = null;
    this.muted = false;
  }

  _ensure() {
    if (this.muted) return null;
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      this.ctx = new AC();
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
    return this.ctx;
  }

  toggleMute() {
    this.muted = !this.muted;
    return this.muted;
  }

  playShutter(withFlash = true) {
    const ctx = this._ensure();
    if (!ctx) return;
    const now = ctx.currentTime;

    // 1. Mechanical mirror flip-up thud + metallic shutter curtain snap
    const noiseLen = Math.floor(ctx.sampleRate * 0.09);
    const buf = ctx.createBuffer(1, noiseLen, ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < noiseLen; i++) {
      const t = i / ctx.sampleRate;
      // Double transient: mirror up at 0ms, mirror down / second curtain at 38ms
      const env1 = Math.exp(-t * 140);
      const env2 = t > 0.036 ? Math.exp(-(t - 0.036) * 120) * 0.85 : 0;
      data[i] = (Math.random() * 2 - 1) * (env1 + env2);
    }

    const src = ctx.createBufferSource();
    src.buffer = buf;

    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.setValueAtTime(1450, now);
    bp.Q.setValueAtTime(1.4, now);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.55, now);

    src.connect(bp).connect(gain).connect(ctx.destination);
    src.start(now);

    // Subtle mechanical spring ping
    const osc = ctx.createOscillator();
    const og = ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(240, now);
    osc.frequency.exponentialRampToValueAtTime(85, now + 0.045);
    og.gain.setValueAtTime(0.22, now);
    og.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
    osc.connect(og).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.055);

    // 2. Classic Xenon speedlight flash pop + high-pitched capacitor recharge whine
    if (withFlash) {
      const whine = ctx.createOscillator();
      const wg = ctx.createGain();
      whine.type = 'sine';
      whine.frequency.setValueAtTime(2900, now + 0.05);
      whine.frequency.exponentialRampToValueAtTime(7400, now + 0.65);
      wg.gain.setValueAtTime(0.001, now + 0.05);
      wg.gain.linearRampToValueAtTime(0.032, now + 0.12);
      wg.gain.exponentialRampToValueAtTime(0.0005, now + 0.68);
      whine.connect(wg).connect(ctx.destination);
      whine.start(now + 0.05);
      whine.stop(now + 0.70);
    }
  }

  playZoomTick() {
    const ctx = this._ensure();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(680, now);
    osc.frequency.exponentialRampToValueAtTime(260, now + 0.016);
    g.gain.setValueAtTime(0.06, now);
    g.gain.exponentialRampToValueAtTime(0.001, now + 0.018);
    osc.connect(g).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.02);
  }

  playApertureClick() {
    const ctx = this._ensure();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(1180, now);
    osc.frequency.exponentialRampToValueAtTime(420, now + 0.014);
    g.gain.setValueAtTime(0.09, now);
    g.gain.exponentialRampToValueAtTime(0.001, now + 0.016);
    osc.connect(g).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.018);
  }

  playFootstep(onCarpet = true, soft = false) {
    const ctx = this._ensure();
    if (!ctx) return;
    const now = ctx.currentTime;
    const len = Math.floor(ctx.sampleRate * 0.075);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) {
      const t = i / ctx.sampleRate;
      d[i] = (Math.random() * 2 - 1) * Math.exp(-t * (onCarpet ? 65 : 95));
    }
    const src = ctx.createBufferSource();
    src.buffer = buf;

    const flt = ctx.createBiquadFilter();
    flt.type = 'lowpass';
    flt.frequency.setValueAtTime(onCarpet ? 320 : 1150, now);

    const g = ctx.createGain();
    g.gain.setValueAtTime((soft ? 0.08 : 0.16) * (onCarpet ? 0.85 : 1.0), now);
    src.connect(flt).connect(g).connect(ctx.destination);
    src.start(now);
  }

  playClothRustle() {
    const ctx = this._ensure();
    if (!ctx) return;
    const now = ctx.currentTime;
    const len = Math.floor(ctx.sampleRate * 0.12);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) {
      const u = i / len;
      d[i] = (Math.random() * 2 - 1) * Math.sin(u * Math.PI) * 0.5;
    }
    const src = ctx.createBufferSource();
    src.buffer = buf;
    const flt = ctx.createBiquadFilter();
    flt.type = 'bandpass';
    flt.frequency.setValueAtTime(900, now);
    flt.Q.setValueAtTime(0.9, now);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.06, now);
    src.connect(flt).connect(g).connect(ctx.destination);
    src.start(now);
  }

  playDoorOpen() {
    const ctx = this._ensure();
    if (!ctx) return;
    const now = ctx.currentTime;

    // 1. Crisp brass latch release click
    const latch = ctx.createOscillator();
    const lg = ctx.createGain();
    latch.type = 'triangle';
    latch.frequency.setValueAtTime(860, now);
    latch.frequency.exponentialRampToValueAtTime(240, now + 0.035);
    lg.gain.setValueAtTime(0.14, now);
    lg.gain.exponentialRampToValueAtTime(0.001, now + 0.045);
    latch.connect(lg).connect(ctx.destination);
    latch.start(now);
    latch.stop(now + 0.05);

    // 2. Heavy rosewood double-door air/hinge low sweep
    const len = Math.floor(ctx.sampleRate * 0.75);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) {
      const u = i / len;
      d[i] = (Math.random() * 2 - 1) * Math.sin(u * Math.PI) * 0.65;
    }
    const src = ctx.createBufferSource();
    src.buffer = buf;
    const flt = ctx.createBiquadFilter();
    flt.type = 'lowpass';
    flt.frequency.setValueAtTime(190, now + 0.04);
    const sg = ctx.createGain();
    sg.gain.setValueAtTime(0.16, now + 0.04);
    src.connect(flt).connect(sg).connect(ctx.destination);
    src.start(now + 0.04);
  }

  playDoorClose() {
    const ctx = this._ensure();
    if (!ctx) return;
    const now = ctx.currentTime;

    // 1. Deep muffled heavy rosewood door close thud
    const thud = ctx.createOscillator();
    const tg = ctx.createGain();
    thud.type = 'sine';
    thud.frequency.setValueAtTime(98, now);
    thud.frequency.exponentialRampToValueAtTime(34, now + 0.16);
    tg.gain.setValueAtTime(0.34, now);
    tg.gain.exponentialRampToValueAtTime(0.001, now + 0.20);
    thud.connect(tg).connect(ctx.destination);
    thud.start(now);
    thud.stop(now + 0.22);

    // 2. Brass lock tongue clunk
    const lock = ctx.createOscillator();
    const kg = ctx.createGain();
    lock.type = 'triangle';
    lock.frequency.setValueAtTime(620, now + 0.03);
    lock.frequency.exponentialRampToValueAtTime(190, now + 0.075);
    kg.gain.setValueAtTime(0.11, now + 0.03);
    kg.gain.exponentialRampToValueAtTime(0.001, now + 0.085);
    lock.connect(kg).connect(ctx.destination);
    lock.start(now + 0.03);
    lock.stop(now + 0.09);
  }
}

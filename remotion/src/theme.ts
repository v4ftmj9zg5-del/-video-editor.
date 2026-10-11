import {Easing, interpolate, spring} from 'remotion';

export type StyleName = 'dynamic' | 'elegant';

export type Theme = {
  name: StyleName;
  display: string; // big numbers / titles
  text: string; // captions / labels
  bg: string; // card & panel background
  panel: string; // frosted panel
  ink: string; // main text colour on panels
  muted: string;
  accent: string;
  accent2: string;
  good: string;
  bad: string;
  palette: string[]; // default swatches
  inFrames: number; // entrance length
  outFrames: number;
  displayWeight: number;
  textWeight: number;
};

export const THEMES: Record<StyleName, Theme> = {
  dynamic: {
    name: 'dynamic',
    display: 'Rubik',
    text: 'Rubik',
    bg: '#F6F1E7',
    panel: 'rgba(20,20,20,0.78)',
    ink: '#141414',
    muted: '#6B6660',
    accent: '#FFD947',
    accent2: '#FF6B4A',
    good: '#3BB273',
    bad: '#E5484D',
    palette: ['#F4F1EA', '#D9C7A7', '#7C8B6A', '#C06A4B', '#2B2A28'],
    inFrames: 12,
    outFrames: 8,
    displayWeight: 800,
    textWeight: 700,
  },
  elegant: {
    name: 'elegant',
    display: 'Frank Ruhl Libre',
    text: 'Heebo',
    bg: '#F3EEE6',
    panel: 'rgba(243,238,230,0.86)',
    ink: '#2B2A28',
    muted: '#8C8173',
    accent: '#B8735A',
    accent2: '#6E7155',
    good: '#6E7155',
    bad: '#A63D32',
    palette: ['#F3EEE6', '#D8C8B0', '#A89A8A', '#6E7155', '#B8735A'],
    inFrames: 22,
    outFrames: 16,
    displayWeight: 300,
    textWeight: 300,
  },
};

const EDITORIAL = Easing.bezier(0.22, 1, 0.36, 1); // long, soft settle
const SNAP = Easing.bezier(0.2, 0.9, 0.1, 1.0);

/** 0..1 entrance progress, style-appropriate motion curve. */
export const enter = (frame: number, fps: number, t: Theme, delay = 0, len?: number) => {
  const f = frame - delay;
  if (t.name === 'dynamic') {
    return spring({frame: f, fps, config: {damping: 13, stiffness: 170, mass: 0.7}, durationInFrames: len});
  }
  return interpolate(f, [0, len ?? t.inFrames], [0, 1], {easing: EDITORIAL, extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
};

/** 1..0 exit progress near the end of a scene of `dur` frames. */
export const exit = (frame: number, dur: number, t: Theme) =>
  interpolate(frame, [dur - t.outFrames, dur], [1, 0], {
    easing: t.name === 'dynamic' ? SNAP : EDITORIAL,
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

export const ease = (frame: number, range: [number, number], out: [number, number], t: Theme) =>
  interpolate(frame, range, out, {
    easing: t.name === 'dynamic' ? SNAP : EDITORIAL,
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

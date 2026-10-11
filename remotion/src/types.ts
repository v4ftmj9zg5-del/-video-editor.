import {StyleName} from './theme';

export type Word = {w: string; s: number; e: number};
export type Caption = {s: number; e: number; words: Word[]};

export type SceneKind =
  | 'kinetic'
  | 'number'
  | 'mistake'
  | 'furniture'
  | 'lighting'
  | 'palette'
  | 'materials'
  | 'beforeAfter'
  | 'space'
  | 'callout'
  | 'cta';

export type Layout = 'full' | 'card' | 'split';

export type Scene = {
  id: number;
  kind: SceneKind;
  s: number; // seconds, output timeline
  e: number;
  text: string;
  layout: Layout;
  transition: 'flash' | 'whip' | 'leak' | 'fade' | 'none';
  params: Record<string, any>;
};

export type ReelProps = {
  style: StyleName;
  fps: number;
  durationInFrames: number;
  base: string; // file in the public dir
  title?: string;
  captions: Caption[];
  scenes: Scene[];
  punches: {t: number; amount: number}[];
};

import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFonts} from './fonts';
import {GRAPHICS} from './graphics/scenes';
import {H, PatternBg, W} from './graphics/common';
import {THEMES, Theme, clamp01, ease, enter} from './theme';
import {Caption, ReelProps, Scene} from './types';

loadFonts();

const sec = (s: number, fps: number) => Math.round(s * fps);

/** How far each non-full layout is engaged at frame f (0..1, eased in and out). */
const layoutAmount = (scenes: Scene[], layout: string, f: number, fps: number, t: Theme) => {
  let a = 0;
  for (const s of scenes) {
    if (s.layout !== layout) continue;
    const s0 = sec(s.s, fps);
    const s1 = sec(s.e, fps);
    const inLen = t.name === 'dynamic' ? 9 : 16;
    const outLen = t.name === 'dynamic' ? 8 : 14;
    const v = Math.min(ease(f, [s0, s0 + inLen], [0, 1], t), ease(f, [s1 - outLen, s1], [1, 0], t));
    a = Math.max(a, v);
  }
  return a;
};

const BaseLayer: React.FC<ReelProps & {theme: Theme}> = (p) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = p.theme;
  const card = layoutAmount(p.scenes, 'card', f, fps, t);
  const split = layoutAmount(p.scenes, 'split', f, fps, t);
  // punch-ins: fast rise, eased settle (dynamic) / slow breathe (elegant)
  let punch = 0;
  for (const k of p.punches) {
    const k0 = sec(k.t, fps);
    const v =
      t.name === 'dynamic'
        ? Math.min(ease(f, [k0, k0 + 3], [0, 1], t), ease(f, [k0 + 3, k0 + 40], [1, 0.55], t)) * (f < k0 + 90 ? 1 : 0)
        : Math.min(ease(f, [k0, k0 + 24], [0, 1], t), ease(f, [k0 + 50, k0 + 90], [1, 0], t));
    punch = Math.max(punch, v * k.amount);
  }
  // transitions that move the camera
  let shiftX = 0;
  let blur = 0;
  for (const s of p.scenes) {
    const s0 = sec(s.s, fps);
    if (s.transition === 'whip' && f >= s0 - 4 && f < s0 + 6) {
      const k = (f - (s0 - 4)) / 10;
      shiftX = Math.sin(k * Math.PI) * 120;
      blur = Math.sin(k * Math.PI) * 14;
    }
  }
  const scale = (1 + punch) * (1 - 0.44 * card);
  const ty = 430 * card;
  const top = 960 * split;
  return (
    <AbsoluteFill>
      {(card > 0 || split > 0) && <PatternBg theme={t} frame={f} />}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top,
          width: W,
          height: H - top,
          overflow: 'hidden',
          borderRadius: 52 * card + (split > 0 ? 40 * split : 0),
          transform: `translateY(${ty}px) scale(${scale}) translateX(${shiftX}px)`,
          boxShadow: card > 0 ? `0 ${40 * card}px ${90 * card}px rgba(0,0,0,${0.35 * card})` : undefined,
          filter: blur ? `blur(${blur}px)` : undefined,
        }}
      >
        <OffthreadVideo src={staticFile(p.base)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </div>
    </AbsoluteFill>
  );
};

/** Short overlays at scene starts: white flash (dynamic) or warm light-leak sweep (elegant). */
const Transitions: React.FC<{scenes: Scene[]; theme: Theme}> = ({scenes, theme}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {scenes.map((s) => {
        const s0 = sec(s.s, fps);
        if (s.transition === 'flash' && f >= s0 - 1 && f < s0 + 7) {
          return <AbsoluteFill key={s.id} style={{background: '#fff', opacity: interpolate(f, [s0 - 1, s0, s0 + 7], [0, 0.75, 0])}} />;
        }
        if (s.transition === 'leak' && f >= s0 - 6 && f < s0 + 26) {
          const k = (f - (s0 - 6)) / 32;
          const x = 1300 - 1700 * k;
          return (
            <AbsoluteFill key={s.id} style={{mixBlendMode: 'screen', opacity: Math.sin(k * Math.PI) * 0.55,
              background: `radial-gradient(ellipse 520px 1400px at ${x}px 700px, rgba(255,186,120,0.9), rgba(255,120,80,0.35) 55%, rgba(0,0,0,0) 75%)`}} />
          );
        }
        if (s.transition === 'fade' && f >= s0 - 6 && f < s0 + 10) {
          return <AbsoluteFill key={s.id} style={{background: theme.bg, opacity: interpolate(f, [s0 - 6, s0, s0 + 10], [0, 0.35, 0])}} />;
        }
        return null;
      })}
    </AbsoluteFill>
  );
};

/** Captions: dynamic = 1-3 word chunks with a highlight box on the spoken word;
 * elegant = phrase lines that fade and rise. Moves up when a layout needs the space. */
const Captions: React.FC<{captions: Caption[]; scenes: Scene[]; theme: Theme}> = ({captions, scenes, theme}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = f / fps;
  const cap = captions.find((c) => t >= c.s && t < c.e);
  if (!cap) return null;
  const local = f - sec(cap.s, fps);
  const dyn = theme.name === 'dynamic';
  const p = enter(local, fps, theme, 0, dyn ? undefined : 12);
  const out = interpolate(f, [sec(cap.e, fps) - 5, sec(cap.e, fps)], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const takeover = scenes.some((s) => (s.kind === 'beforeAfter' || s.kind === 'cta') && t >= s.s && t < s.e);
  const y = takeover ? 1420 : 1330;
  return (
    <>
    {!dyn && (
      <div style={{position: 'absolute', left: 0, right: 0, top: y - 260, height: 640, opacity: clamp01(p) * out,
        background: 'linear-gradient(180deg, rgba(25,20,15,0) 0%, rgba(25,20,15,0.42) 45%, rgba(25,20,15,0.42) 70%, rgba(25,20,15,0) 100%)'}} />
    )}
    <div style={{position: 'absolute', top: y, left: 70, right: 160, textAlign: 'center', direction: 'rtl',
      opacity: clamp01(dyn ? p * 2 : p) * out, transform: dyn ? `scale(${0.7 + 0.3 * p})` : `translateY(${(1 - p) * 18}px)`}}>
      {cap.words.map((w, i) => {
        const active = t >= w.s && t < w.e;
        if (dyn) {
          return (
            <span key={i} style={{display: 'inline-block', margin: '6px 8px', padding: '2px 16px', borderRadius: 14,
              background: active ? theme.accent : 'transparent', transform: active ? 'scale(1.08) rotate(-1.5deg)' : 'none',
              fontFamily: theme.text, fontWeight: 800, fontSize: 84, lineHeight: 1.15,
              color: active ? theme.ink : '#fff',
              WebkitTextStroke: active ? undefined : '2px #111', textShadow: active ? 'none' : '0 6px 18px rgba(0,0,0,0.55)'}}>
              {w.w}
            </span>
          );
        }
        return (
          <span key={i} style={{fontFamily: theme.text, fontWeight: 400, fontSize: 58, letterSpacing: 2, color: '#FBF8F3',
            textShadow: '0 2px 18px rgba(0,0,0,0.55), 0 0 2px rgba(0,0,0,0.4)', margin: '0 7px',
            opacity: t >= w.s - 0.05 ? 1 : 0.45}}>
            {w.w}
          </span>
        );
      })}
    </div>
    </>
  );
};

const Grain: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{mixBlendMode: 'overlay', opacity: 0.06, pointerEvents: 'none'}}>
      <svg width={W} height={H}>
        <filter id="g">
          <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={f % 9} />
        </filter>
        <rect width={W} height={H} filter="url(#g)" />
      </svg>
    </AbsoluteFill>
  );
};

export const Reel: React.FC<ReelProps> = (props) => {
  const theme = THEMES[props.style];
  const f = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <BaseLayer {...props} theme={theme} />
      {props.scenes.map((s) => {
        const G = GRAPHICS[s.kind];
        const from = sec(s.s, fps);
        const dur = Math.max(1, sec(s.e, fps) - from);
        return G ? (
          <Sequence key={s.id} from={from} durationInFrames={dur} name={`${s.id} ${s.kind}`}>
            <G scene={s} theme={theme} dur={dur} base={props.base} />
          </Sequence>
        ) : null;
      })}
      <Captions captions={props.captions} scenes={props.scenes} theme={theme} />
      <Transitions scenes={props.scenes} theme={theme} />
      {theme.name === 'elegant' && <Grain />}
      {theme.name === 'dynamic' && (
        <div style={{position: 'absolute', top: 226, right: 0, height: 8, borderRadius: 4, background: theme.accent,
          width: (W * (f + 1)) / durationInFrames, boxShadow: '0 2px 8px rgba(0,0,0,0.3)'}} />
      )}
    </AbsoluteFill>
  );
};

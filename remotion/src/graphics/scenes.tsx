import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Scene} from '../types';
import {Theme, clamp01, ease, enter, exit} from '../theme';
import {H, Pill, Stamp, W} from './common';
import {Art, FurnitureArt} from './furnitureArt';

type SP = {scene: Scene; theme: Theme; dur: number; base: string};

const rtl: React.CSSProperties = {direction: 'rtl'};

/* ------------------------------------------------------------------ kinetic */
// Hook / key sentence: words land one by one, the key word gets a marker swipe.
export const Kinetic: React.FC<SP> = ({scene, theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const words: string[] = scene.params.words ?? scene.text.split(/\s+/);
  const key: string = scene.params.key ?? '';
  const out = exit(f, dur, theme);
  const lines: string[][] = [];
  let cur: string[] = [];
  let len = 0;
  for (const w of words) {
    if (len + w.length > (theme.name === 'dynamic' ? 9 : 14) && cur.length) {
      lines.push(cur);
      cur = [];
      len = 0;
    }
    cur.push(w);
    len += w.length + 1;
  }
  if (cur.length) lines.push(cur);
  const size = theme.name === 'dynamic' ? 128 : 104;
  const stagger = theme.name === 'dynamic' ? 3 : 6;
  let idx = 0;
  const scrim = clamp01(enter(f, fps, theme)) * out;
  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          background:
            theme.name === 'dynamic'
              ? 'linear-gradient(180deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.25) 45%, rgba(0,0,0,0) 70%)'
              : `linear-gradient(180deg, ${theme.bg}EE 0%, ${theme.bg}AA 40%, ${theme.bg}00 68%)`,
          opacity: scrim,
        }}
      />
      <div style={{position: 'absolute', top: 330, width: W, textAlign: 'center', ...rtl}}>
        {lines.map((line, li) => (
          <div key={li} style={{marginBottom: theme.name === 'dynamic' ? 6 : 18}}>
            {line.map((w) => {
              const i = idx++;
              const p = enter(f, fps, theme, 2 + i * stagger);
              const isKey = key && w.replace(/[^א-ת0-9]/g, '') === key;
              const mark = ease(f, [8 + i * stagger, 18 + i * stagger], [0, 1], theme);
              return (
                <span
                  key={i}
                  style={{
                    position: 'relative',
                    display: 'inline-block',
                    margin: '0 14px',
                    fontFamily: isKey && theme.name === 'elegant' ? theme.display : theme.text,
                    fontWeight: theme.name === 'dynamic' ? 800 : isKey ? 400 : 300,
                    fontSize: isKey && theme.name === 'elegant' ? size * 1.15 : size,
                    color: theme.name === 'dynamic' ? (isKey ? theme.ink : '#fff') : isKey ? theme.accent : theme.ink,
                    opacity: clamp01(p) * out,
                    transform: `translateY(${(1 - p) * 70}px) rotate(${theme.name === 'dynamic' ? (1 - p) * -8 : 0}deg) scale(${0.85 + 0.15 * p})`,
                    filter: theme.name === 'elegant' ? `blur(${(1 - clamp01(p)) * 10}px)` : undefined,
                    textShadow: theme.name === 'dynamic' && !isKey ? '0 6px 24px rgba(0,0,0,0.45)' : undefined,
                    zIndex: 1,
                  }}
                >
                  {isKey && (
                    <span
                      style={{
                        position: 'absolute',
                        zIndex: -1,
                        right: -14,
                        left: -14,
                        top: theme.name === 'dynamic' ? 8 : size * 1.05,
                        bottom: theme.name === 'dynamic' ? 0 : -6,
                        background: theme.name === 'dynamic' ? theme.accent : theme.accent,
                        transformOrigin: 'right',
                        transform: `scaleX(${mark}) rotate(${theme.name === 'dynamic' ? -2 : 0}deg)`,
                        borderRadius: theme.name === 'dynamic' ? 10 : 2,
                      }}
                    />
                  )}
                  {w}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------- number */
// Big animated number (count-up + ring + label); sits above the video card.
export const BigNumber: React.FC<SP> = ({scene, theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const value: number = scene.params.value ?? 5;
  const label: string = scene.params.label ?? '';
  const out = exit(f, dur, theme);
  const count = ease(f, [4, theme.name === 'dynamic' ? 22 : 34], [0, value], theme);
  const pop = enter(f, fps, theme, 2);
  const ring = ease(f, [4, theme.name === 'dynamic' ? 26 : 40], [0, 1], theme);
  const lab = enter(f, fps, theme, 14);
  const cx = W / 2;
  const cy = 450;
  const dyn = theme.name === 'dynamic';
  return (
    <AbsoluteFill style={{opacity: out}}>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <circle cx={cx} cy={cy} r={210} fill="none" stroke={dyn ? theme.ink : theme.accent} strokeWidth={dyn ? 14 : 2.5}
          pathLength={1} strokeDasharray={1} strokeDashoffset={1 - ring} transform={`rotate(-90 ${cx} ${cy})`} />
        {!dyn && <circle cx={cx} cy={cy} r={230} fill="none" stroke={theme.muted} strokeWidth={1} opacity={ring * 0.6} />}
        {dyn &&
          Array.from({length: 10}).map((_, i) => {
            const a = (i / 10) * Math.PI * 2;
            const r = 240 + ease(f, [20, 34], [0, 120], theme);
            return <circle key={i} cx={cx + Math.cos(a) * r} cy={cy + Math.sin(a) * r} r={12 * (1 - ease(f, [24, 40], [0, 1], theme))} fill={i % 2 ? theme.accent2 : theme.ink} />;
          })}
      </svg>
      <div style={{position: 'absolute', top: cy - 300, width: W, textAlign: 'center'}}>
        <span
          style={{
            display: 'inline-block',
            fontFamily: theme.display,
            fontWeight: dyn ? 900 : 300,
            fontSize: dyn ? 380 : 350,
            lineHeight: '600px',
            color: theme.ink,
            transform: `scale(${0.4 + 0.6 * pop})`,
            textShadow: dyn ? `18px 18px 0 ${theme.accent}` : undefined,
          }}
        >
          {Math.round(count)}
        </span>
      </div>
      <div style={{position: 'absolute', top: cy + 225, width: W, textAlign: 'center', opacity: clamp01(lab), transform: `translateY(${(1 - lab) * 40}px)`}}>
        <span style={{...rtl, fontFamily: dyn ? theme.text : theme.display, fontWeight: dyn ? 800 : 400, fontSize: 84, color: theme.ink, letterSpacing: dyn ? 0 : 6}}>
          {label}
        </span>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ mistake */
// "טעות #n" badge with X stamp and progress dots.
export const Mistake: React.FC<SP> = ({scene, theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const n: number = scene.params.n ?? 1;
  const total: number = scene.params.total ?? Math.max(3, n);
  const word: string = scene.params.word ?? 'טעות';
  const out = exit(f, dur, theme);
  const p = enter(f, fps, theme);
  const stamp = enter(f, fps, theme, 9, 14);
  const dyn = theme.name === 'dynamic';
  return (
    <AbsoluteFill style={{opacity: out}}>
      <div
        style={{
          position: 'absolute',
          top: 260,
          left: 90,
          right: 90,
          height: 300,
          borderRadius: dyn ? 36 : 6,
          background: dyn ? theme.ink : 'rgba(43,42,40,0.9)',
          border: dyn ? 'none' : `1.5px solid ${theme.accent}88`,
          boxShadow: '0 30px 80px rgba(0,0,0,0.25)',
          transform: `translateY(${(1 - p) * -380}px) rotate(${dyn ? (1 - p) * 4 : 0}deg)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 60px',
          ...rtl,
        }}
      >
        <div>
          <div style={{fontFamily: theme.text, fontWeight: dyn ? 800 : 300, fontSize: 110, color: dyn ? '#fff' : theme.bg, lineHeight: 1}}>
            {word} <span style={{fontFamily: theme.display, color: dyn ? theme.accent : theme.accent}}>#{n}</span>
          </div>
          <div style={{display: 'flex', gap: 16, marginTop: 30}}>
            {Array.from({length: total}).map((_, i) => {
              const on = i < n;
              const pi = ease(f, [10 + i * 3, 18 + i * 3], [0, 1], theme);
              return (
                <div key={i} style={{width: on ? 70 : 26, height: 14, borderRadius: 7, transform: `scaleX(${pi})`,
                  background: on ? theme.accent : '#ffffff44'}} />
              );
            })}
          </div>
        </div>
        <Stamp kind={scene.params.good ? 'good' : 'bad'} p={clamp01(stamp)} theme={theme} size={170} />
      </div>
    </AbsoluteFill>
  );
};

/* ---------------------------------------------------------------- furniture */
// Split screen: illustration draws itself on the top half.
export const Furniture: React.FC<SP> = ({scene, theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const art: Art = scene.params.art ?? 'sofa';
  const label: string = scene.params.label ?? '';
  const mark: 'bad' | 'good' | undefined = scene.params.mark;
  const big: boolean = !!scene.params.big;
  const out = exit(f, dur, theme);
  const drawLen = theme.name === 'dynamic' ? 22 : 40;
  const draw = ease(f, [3, drawLen], [0, 1], theme);
  const fillOp = ease(f, [drawLen - 6, drawLen + 10], [0, 1], theme);
  const float = Math.sin(f / 18) * 6;
  const lab = enter(f, fps, theme, drawLen - 4);
  const stamp = enter(f, fps, theme, drawLen + 4, 14);
  const arrow = ease(f, [drawLen, drawLen + 16], [0, 1], theme);
  const shadow = ease(f, [6, drawLen], [0, 1], theme);
  const dyn = theme.name === 'dynamic';
  const scale = big ? 2.05 : 1.7;
  return (
    <AbsoluteFill style={{opacity: out}}>
      <svg width={W} height={960} viewBox={`0 0 ${W} 960`} style={{position: 'absolute', top: 0}}>
        <ellipse cx={W / 2} cy={770} rx={330 * shadow * (big ? 1.2 : 1)} ry={30 * shadow} fill="#000" opacity={0.12} />
        <g transform={`translate(${W / 2 - 200 * scale}, ${270 + float - (big ? 40 : 0)}) scale(${scale})`}>
          <FurnitureArt art={art} stroke={theme.ink} fill={dyn ? theme.accent : '#D8C8B0'} fill2={dyn ? '#FFFFFF' : '#EFE6D8'} draw={draw} fillOp={fillOp} sw={dyn ? 4.5 : 2.6} />
        </g>
        {big && (
          <g opacity={arrow} stroke={theme.bad} strokeWidth={5} fill={theme.bad}>
            <line x1={W / 2 - 400 * arrow} y1={220} x2={W / 2 + 400 * arrow} y2={220} />
            <path d={`M${W / 2 - 400 * arrow} 220 l26 -16 v32 z M${W / 2 + 400 * arrow} 220 l-26 -16 v32 z`} />
          </g>
        )}
      </svg>
      {big && (
        <div style={{position: 'absolute', top: 160, width: W, textAlign: 'center', opacity: arrow}}>
          <Pill theme={theme} text="XL" size={40} style={{background: theme.bad, color: '#fff'}} />
        </div>
      )}
      {label && (
        <div style={{position: 'absolute', top: 830, width: W, textAlign: 'center', opacity: clamp01(lab), transform: `translateY(${(1 - lab) * 30}px)`}}>
          <Pill theme={theme} text={label} dark={!dyn} size={dyn ? 52 : 44} />
        </div>
      )}
      {mark && (
        <div style={{position: 'absolute', top: 330, left: 120}}>
          <Stamp kind={mark} p={clamp01(stamp)} theme={theme} size={150} />
        </div>
      )}
    </AbsoluteFill>
  );
};

/* ----------------------------------------------------------------- lighting */
// The room dims, a pendant swings in and switches on, warm light blooms, kelvin counts down.
export const Lighting: React.FC<SP> = ({scene, theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const label: string = scene.params.label ?? 'אור חם ורך';
  const out = exit(f, dur, theme);
  const onAt = Math.min(Math.round(dur * 0.35), 30);
  const dark = ease(f, [0, 8], [0, 0.62], theme) - ease(f, [onAt, onAt + 14], [0, 0.5], theme);
  const drop = enter(f, fps, theme, 2, 26);
  const swing = Math.sin(f / 6) * 9 * Math.exp(-f / 22);
  const on = ease(f, [onAt, onAt + 18], [0, 1], theme);
  const kelvin = Math.round(interpolate(on, [0, 1], [6500, 2700]) / 100) * 100;
  const lx = 700;
  const ly = 470;
  const cold = [170, 205, 255];
  const warm = [255, 184, 108];
  const mix = (i: number) => Math.round(cold[i] + (warm[i] - cold[i]) * on);
  const chip = `rgb(${mix(0)},${mix(1)},${mix(2)})`;
  const ui = enter(f, fps, theme, 6);
  return (
    <AbsoluteFill style={{opacity: out}}>
      <AbsoluteFill style={{background: '#0b0d14', opacity: Math.max(0, dark)}} />
      <AbsoluteFill
        style={{
          mixBlendMode: 'screen',
          opacity: on,
          background: `radial-gradient(circle at ${lx}px ${ly + 60}px, rgba(255,196,120,0.75) 0px, rgba(255,170,90,0.35) ${260 + 500 * on}px, rgba(255,150,80,0) ${520 + 700 * on}px)`,
        }}
      />
      <AbsoluteFill
        style={{
          mixBlendMode: 'screen',
          opacity: on * 0.35,
          background: `conic-gradient(from ${170 + f * 0.3}deg at ${lx}px ${ly + 70}px, transparent 0deg, rgba(255,210,150,0.5) 12deg, transparent 24deg, transparent 40deg, rgba(255,210,150,0.4) 52deg, transparent 64deg, transparent 360deg)`,
        }}
      />
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <g transform={`translate(${lx - 300}, ${-380 + (ly + 120) * drop}) scale(1.5) rotate(${swing} 200 0)`}>
          <line x1={200} y1={-600} x2={200} y2={0} stroke={theme.name === 'dynamic' ? '#fff' : theme.ink} strokeWidth={3} />
          <FurnitureArt art="pendant" stroke={theme.name === 'dynamic' ? '#fff' : theme.ink} fill={theme.name === 'dynamic' ? theme.accent : '#D8C8B0'} fill2={on > 0.2 ? '#FFE2A8' : '#888'} draw={1} fillOp={1} sw={3} />
          <ellipse cx={200} cy={178} rx={60 * on} ry={18 * on} fill="#FFF3D6" opacity={on} />
        </g>
      </svg>
      <div
        style={{
          position: 'absolute',
          top: 1010,
          left: 90,
          display: 'flex',
          alignItems: 'center',
          gap: 26,
          padding: '22px 34px',
          borderRadius: theme.name === 'dynamic' ? 28 : 6,
          background: theme.name === 'dynamic' ? 'rgba(15,15,15,0.72)' : theme.panel,
          opacity: clamp01(ui),
          transform: `translateX(${(1 - ui) * -80}px)`,
          ...rtl,
        }}
      >
        <div style={{width: 64, height: 64, borderRadius: 32, background: chip, boxShadow: `0 0 ${40 * on}px ${chip}`}} />
        <div>
          <div style={{fontFamily: theme.display, fontWeight: theme.name === 'dynamic' ? 800 : 400, fontSize: 64, color: theme.name === 'dynamic' ? '#fff' : theme.ink, direction: 'ltr', textAlign: 'right'}}>
            {kelvin}K
          </div>
          <div style={{fontFamily: theme.text, fontWeight: theme.name === 'dynamic' ? 600 : 300, fontSize: 38, color: theme.name === 'dynamic' ? '#ffffffcc' : theme.muted}}>{label}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ palette */
// Paint chips unfold one after the other, names + hex type in.
export const Palette: React.FC<SP> = ({scene, theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const colors: {name: string; hex: string}[] = scene.params.colors?.length
    ? scene.params.colors
    : theme.palette.map((hex) => ({name: '', hex}));
  const out = exit(f, dur, theme);
  const band = enter(f, fps, theme);
  const n = colors.length;
  const gap = 24;
  const cw = (W - 180 - gap * (n - 1)) / n;
  const dyn = theme.name === 'dynamic';
  return (
    <AbsoluteFill style={{opacity: out}}>
      <div
        style={{
          position: 'absolute',
          top: 250,
          left: 60,
          right: 60,
          height: 640,
          borderRadius: dyn ? 40 : 4,
          background: dyn ? 'rgba(255,255,255,0.92)' : theme.panel,
          boxShadow: '0 30px 90px rgba(0,0,0,0.22)',
          transform: `scaleY(${band})`,
          transformOrigin: 'top',
        }}
      />
      <div style={{position: 'absolute', top: 285, width: W, textAlign: 'center', opacity: clamp01(band), ...rtl}}>
        <span style={{fontFamily: dyn ? theme.text : theme.display, fontWeight: dyn ? 800 : 400, fontSize: 54, color: theme.ink, letterSpacing: dyn ? 0 : 8}}>
          {scene.params.title ?? 'פלטת צבעים'}
        </span>
      </div>
      {colors.map((c, i) => {
        // RTL: first colour on the right
        const x = W - 90 - (i + 1) * cw - i * gap;
        const p = enter(f, fps, theme, 6 + i * (dyn ? 4 : 7));
        const t = ease(f, [14 + i * 5, 30 + i * 5], [0, 1], theme);
        const hex = c.hex.toUpperCase().slice(0, 1 + Math.round(6 * t));
        return (
          <div key={i} style={{position: 'absolute', left: x, top: 380, width: cw}}>
            <div
              style={{
                height: 360,
                borderRadius: dyn ? 22 : cw / 2,
                background: c.hex,
                boxShadow: 'inset 0 0 0 2px rgba(0,0,0,0.06), 0 16px 40px rgba(0,0,0,0.18)',
                transform: dyn ? `scaleY(${p}) rotate(${(1 - p) * (i % 2 ? 6 : -6)}deg)` : `translateY(${(1 - p) * 60}px) scale(${0.6 + 0.4 * p})`,
                transformOrigin: 'top',
                opacity: clamp01(p * 1.5),
                ...(dyn ? {} : {height: cw, marginTop: 60}),
              }}
            />
            <div style={{textAlign: 'center', marginTop: 22, opacity: clamp01(p), ...rtl}}>
              <div style={{fontFamily: dyn ? theme.text : theme.display, fontWeight: dyn ? 700 : 400, fontSize: Math.min(44, cw / 3.6), color: theme.ink}}>{c.name}</div>
              <div style={{fontFamily: 'Heebo', fontWeight: 400, fontSize: 28, color: theme.muted, direction: 'ltr', letterSpacing: 2}}>{hex}</div>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/* ---------------------------------------------------------------- materials */
const TEX: Record<string, string> = {
  wood: 'repeating-linear-gradient(100deg, #8a5a3b 0 6px, #9c6a47 6px 14px, #7d5034 14px 17px, #a8774f 17px 30px)',
  marble: 'radial-gradient(circle at 30% 30%, #ffffff 0, #ecebe8 40%, #d9d6d0 100%), repeating-linear-gradient(35deg, transparent 0 40px, rgba(120,120,120,0.25) 41px 43px, transparent 44px 90px)',
  linen: 'repeating-linear-gradient(0deg, #e8dfd0 0 3px, #ddd2c0 3px 6px), repeating-linear-gradient(90deg, rgba(255,255,255,0.35) 0 3px, transparent 3px 6px)',
  stone: 'radial-gradient(circle at 40% 35%, #b9b3a9 0, #9c958a 60%, #868076 100%)',
  rattan: 'repeating-linear-gradient(45deg, #c8a46e 0 8px, #b28d58 8px 12px), repeating-linear-gradient(-45deg, rgba(255,255,255,0.25) 0 8px, transparent 8px 16px)',
  velvet: 'radial-gradient(circle at 35% 30%, #7c8b6a 0, #55613f 70%, #3f4a2e 100%)',
};

export const Materials: React.FC<SP> = ({scene, theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const items: {name: string; tex: string}[] = scene.params.items ?? [];
  const out = exit(f, dur, theme);
  const n = Math.max(items.length, 1);
  const r = n > 2 ? 150 : 180;
  return (
    <AbsoluteFill style={{opacity: out}}>
      {items.map((m, i) => {
        const p = enter(f, fps, theme, 4 + i * 6);
        const x = W / 2 + (i - (n - 1) / 2) * (r * 2 + 50) * -1;
        return (
          <div key={i} style={{position: 'absolute', left: x - r, top: 380, width: r * 2, textAlign: 'center',
            transform: `translateY(${(1 - p) * 120}px) rotate(${(1 - p) * 90}deg)`, opacity: clamp01(p)}}>
            <div style={{width: r * 2, height: r * 2, borderRadius: r, background: TEX[m.tex] ?? TEX.linen,
              boxShadow: '0 24px 60px rgba(0,0,0,0.35), inset 0 0 0 6px rgba(255,255,255,0.6)'}} />
            <div style={{marginTop: 26}}>
              <Pill theme={theme} text={m.name} size={44} dark={theme.name === 'elegant'} />
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------- before/after */
// Full-screen comparison with a slider (Hebrew reading order: before on the right).
export const BeforeAfter: React.FC<SP> = ({scene, theme, dur, base}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const out = exit(f, dur, theme);
  const inP = enter(f, fps, theme);
  const slide =
    ease(f, [8, theme.name === 'dynamic' ? 26 : 40], [0, 1], theme) * 0.55 -
    ease(f, [44, 60], [0, 0.12], theme) +
    ease(f, [60, 76], [0, 0.12], theme);
  const x = W * slide; // after (left part) revealed up to x
  const media = (filter?: string, src?: string) =>
    src ? (
      <Img src={staticFile(src)} style={{width: W, height: H, objectFit: 'cover', filter}} />
    ) : (
      <OffthreadVideo src={staticFile(base)} muted style={{width: W, height: H, objectFit: 'cover', filter}} />
    );
  const before = scene.params.before as string | undefined;
  const after = scene.params.after as string | undefined;
  return (
    <AbsoluteFill style={{opacity: out * clamp01(inP * 1.4)}}>
      <AbsoluteFill>{media(before ? undefined : 'grayscale(0.85) brightness(0.72) contrast(0.85)', before)}</AbsoluteFill>
      <AbsoluteFill style={{clipPath: `inset(0 ${W - x}px 0 0)`}}>{media(after ? undefined : 'saturate(1.15) brightness(1.06)', after)}</AbsoluteFill>
      <div style={{position: 'absolute', left: x - 3, top: 0, width: 6, height: H, background: '#fff', boxShadow: '0 0 30px rgba(0,0,0,0.4)'}} />
      <div style={{position: 'absolute', left: x - 55, top: 900, width: 110, height: 110, borderRadius: 55, background: '#fff',
        boxShadow: '0 10px 30px rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'Heebo', fontSize: 52, color: theme.ink}}>‹ ›</div>
      <div style={{position: 'absolute', top: 270, right: 70, opacity: clamp01(inP)}}>
        <Pill theme={theme} text={scene.params.beforeLabel ?? 'לפני'} dark size={48} />
      </div>
      <div style={{position: 'absolute', top: 270, left: 70, opacity: clamp01(ease(f, [16, 26], [0, 1], theme))}}>
        <Pill theme={theme} text={scene.params.afterLabel ?? 'אחרי'} size={48} />
      </div>
    </AbsoluteFill>
  );
};

/* -------------------------------------------------------------------- space */
// Dimension arrows push outward: "small room that feels big".
export const Space: React.FC<SP> = ({scene, theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const out = exit(f, dur, theme);
  const grow = ease(f, [4, theme.name === 'dynamic' ? 24 : 40], [0, 1], theme);
  const lab = enter(f, fps, theme, 12);
  const c = theme.name === 'dynamic' ? theme.accent : '#ffffff';
  const hw = 180 + 300 * grow;
  const hh = 220 + 260 * grow;
  const cx = W / 2;
  const cy = 700;
  const area = scene.params.area as number | undefined;
  return (
    <AbsoluteFill style={{opacity: out}}>
      <svg width={W} height={H} style={{position: 'absolute', filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.45))'}}>
        <rect x={cx - hw} y={cy - hh} width={hw * 2} height={hh * 2} fill="none" stroke={c} strokeWidth={4} strokeDasharray="22 14" opacity={0.9} />
        {[[-1, 0], [1, 0], [0, -1], [0, 1]].map(([dx, dy], i) => {
          const x2 = cx + dx * (hw - 10);
          const y2 = cy + dy * (hh - 10);
          const ang = Math.atan2(dy, dx);
          const a1 = ang + 2.6;
          const a2 = ang - 2.6;
          return (
            <g key={i} stroke={c} strokeWidth={6} fill="none" strokeLinecap="round">
              <line x1={cx + dx * 60} y1={cy + dy * 60} x2={x2} y2={y2} />
              <path d={`M${x2 + Math.cos(a1) * 34} ${y2 + Math.sin(a1) * 34} L${x2} ${y2} L${x2 + Math.cos(a2) * 34} ${y2 + Math.sin(a2) * 34}`} />
            </g>
          );
        })}
      </svg>
      <div style={{position: 'absolute', top: cy - 60, width: W, textAlign: 'center', opacity: clamp01(lab), transform: `scale(${0.7 + 0.3 * lab})`}}>
        <Pill theme={theme} text={area ? `${Math.round(area * grow)} מ״ר` : scene.params.label ?? 'מרגיש גדול'} size={64} />
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ callout */
// Pulsing target + leader line + label (tips, key phrases).
export const Callout: React.FC<SP> = ({scene, theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const out = exit(f, dur, theme);
  const tx: number = scene.params.x ?? 360;
  const ty: number = scene.params.y ?? 900;
  const lx = W - 150;
  const ly = 470;
  const line = ease(f, [4, 18], [0, 1], theme);
  const lab = enter(f, fps, theme, 12);
  const pulse = (f % 30) / 30;
  const c = theme.name === 'dynamic' ? theme.accent : '#ffffff';
  return (
    <AbsoluteFill style={{opacity: out}}>
      <svg width={W} height={H} style={{position: 'absolute', filter: 'drop-shadow(0 3px 10px rgba(0,0,0,0.4))'}}>
        <circle cx={tx} cy={ty} r={18} fill={c} />
        <circle cx={tx} cy={ty} r={18 + 60 * pulse} fill="none" stroke={c} strokeWidth={4} opacity={1 - pulse} />
        <path d={`M${tx} ${ty} L${tx + (lx - 200 - tx) * 0.5} ${ly + 60} L${lx - 200} ${ly + 60}`} fill="none" stroke={c} strokeWidth={4}
          pathLength={1} strokeDasharray={1} strokeDashoffset={1 - line} />
      </svg>
      <div style={{position: 'absolute', top: ly, right: 90, opacity: clamp01(lab), transform: `translateX(${(1 - lab) * 60}px)`, maxWidth: 760}}>
        <div style={{...rtl, padding: '24px 36px', borderRadius: theme.name === 'dynamic' ? 28 : 4,
          background: theme.name === 'dynamic' ? theme.accent : theme.panel, boxShadow: '0 20px 60px rgba(0,0,0,0.25)'}}>
          {scene.params.tag && (
            <div style={{fontFamily: theme.text, fontWeight: 700, fontSize: 34, color: theme.name === 'dynamic' ? theme.ink : theme.accent, letterSpacing: 4}}>{scene.params.tag}</div>
          )}
          <div style={{fontFamily: theme.name === 'dynamic' ? theme.text : theme.display, fontWeight: theme.name === 'dynamic' ? 800 : 400, fontSize: 62, color: theme.ink, lineHeight: 1.15}}>
            {scene.params.label ?? scene.text}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------------------------------------------------------------------- cta */
// Save + follow buttons pop in, a finger taps follow, hearts float up.
export const Cta: React.FC<SP> = ({theme, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const out = exit(f, dur, theme);
  const a = enter(f, fps, theme, 2);
  const b = enter(f, fps, theme, 7);
  const tapAt = 22;
  const tap = ease(f, [tapAt - 10, tapAt], [0, 1], theme);
  const pressed = f >= tapAt;
  const ripple = clamp01((f - tapAt) / 16);
  const dyn = theme.name === 'dynamic';
  const btn = (p: number, filled: boolean, text: string, icon: string): React.CSSProperties => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: 18,
    padding: '26px 52px',
    borderRadius: 999,
    background: filled ? (dyn ? theme.accent : theme.ink) : 'rgba(255,255,255,0.92)',
    color: filled ? (dyn ? theme.ink : theme.bg) : theme.ink,
    fontFamily: theme.text,
    fontWeight: dyn ? 800 : 400,
    fontSize: 58,
    transform: `scale(${(0.3 + 0.7 * p) * (filled && f >= tapAt && f < tapAt + 6 ? 0.92 : 1)})`,
    opacity: clamp01(p),
    boxShadow: '0 18px 50px rgba(0,0,0,0.3)',
  });
  return (
    <AbsoluteFill style={{opacity: out}}>
      {!dyn && (
        <>
          <AbsoluteFill style={{opacity: clamp01(a) * 0.55,
            background: 'radial-gradient(ellipse 900px 700px at 50% 52%, rgba(30,25,20,0.55), rgba(30,25,20,0.85))'}} />
          <div style={{position: 'absolute', top: 600, width: W, textAlign: 'center', ...rtl, fontFamily: theme.display,
            fontWeight: 400, fontSize: 96, color: theme.bg, opacity: clamp01(a), transform: `translateY(${(1 - a) * 30}px)`}}>
            לעוד השראה
          </div>
          <div style={{position: 'absolute', top: 735, left: W / 2 - 160, width: 320, height: 2, background: theme.accent,
            transform: `scaleX(${clamp01(b)})`}} />
        </>
      )}
      <div style={{position: 'absolute', top: 820, width: W, display: 'flex', justifyContent: 'center', gap: 40, ...rtl}}>
        <div style={btn(a, pressed, 'עקבו', '+')}>
          <span>{pressed ? '✓' : '+'}</span>
          <span>{pressed ? 'עוקבים' : 'עקבו'}</span>
        </div>
        <div style={btn(b, false, 'שמרו', '')}>
          <svg width={44} height={52} viewBox="0 0 24 28"><path d="M3 2h18v24l-9-6-9 6z" fill={f > tapAt + 12 ? theme.ink : 'none'} stroke={theme.ink} strokeWidth={2.4} strokeLinejoin="round" /></svg>
          <span>שמרו</span>
        </div>
      </div>
      <svg width={W} height={H} style={{position: 'absolute'}}>
        <circle cx={W / 2 + 220} cy={900} r={30 + 140 * ripple} fill="none" stroke={dyn ? theme.accent : '#fff'} strokeWidth={6} opacity={(1 - ripple) * (pressed ? 1 : 0)} />
        <g transform={`translate(${W / 2 + 230 + (1 - tap) * 160}, ${930 + (1 - tap) * 220})`} opacity={clamp01(tap * 2) * (1 - clamp01((f - tapAt - 14) / 8))}>
          <circle r={34} fill="rgba(255,255,255,0.9)" stroke={theme.ink} strokeWidth={3} />
        </g>
        {dyn &&
          Array.from({length: 7}).map((_, i) => {
            const t = clamp01((f - tapAt - i * 3) / 30);
            if (t <= 0) return null;
            const x = W / 2 + 220 + Math.sin(i * 2.1 + t * 6) * 60;
            const y = 860 - t * 520;
            return (
              <path key={i} transform={`translate(${x}, ${y}) scale(${1.6 * (1 - t * 0.4)})`} opacity={1 - t}
                d="M0 6 C-14 -6 -22 8 0 22 C22 8 14 -6 0 6 Z" fill={i % 2 ? theme.accent2 : '#ff4d6d'} />
            );
          })}
      </svg>
    </AbsoluteFill>
  );
};

export const GRAPHICS: Record<string, React.FC<SP>> = {
  kinetic: Kinetic,
  number: BigNumber,
  mistake: Mistake,
  furniture: Furniture,
  lighting: Lighting,
  palette: Palette,
  materials: Materials,
  beforeAfter: BeforeAfter,
  space: Space,
  callout: Callout,
  cta: Cta,
};

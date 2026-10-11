import React from 'react';
import {Theme} from '../theme';

export const W = 1080;
export const H = 1920;

/** Rounded label used across graphics. */
export const Pill: React.FC<{
  theme: Theme;
  text: string;
  dark?: boolean;
  size?: number;
  style?: React.CSSProperties;
}> = ({theme, text, dark, size = 46, style}) => (
  <div
    style={{
      direction: 'rtl',
      display: 'inline-block',
      padding: `${size * 0.32}px ${size * 0.7}px`,
      borderRadius: 999,
      background: dark ? theme.ink : theme.name === 'dynamic' ? theme.accent : theme.panel,
      color: dark ? theme.bg : theme.ink,
      fontFamily: theme.text,
      fontWeight: theme.name === 'dynamic' ? 700 : 400,
      fontSize: size,
      letterSpacing: theme.name === 'elegant' ? 4 : 0,
      boxShadow: '0 12px 40px rgba(0,0,0,0.18)',
      border: theme.name === 'elegant' ? `1.5px solid ${theme.muted}55` : 'none',
      whiteSpace: 'nowrap',
      ...style,
    }}
  >
    {text}
  </div>
);

/** Red X / green check stamp that slams in. */
export const Stamp: React.FC<{kind: 'bad' | 'good'; p: number; theme: Theme; size?: number}> = ({
  kind,
  p,
  theme,
  size = 180,
}) => {
  const c = kind === 'bad' ? theme.bad : theme.good;
  const s = 2.2 - 1.2 * p;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      style={{transform: `scale(${s}) rotate(${(1 - p) * -25}deg)`, opacity: Math.min(1, p * 1.6)}}
    >
      <circle cx="50" cy="50" r="44" fill={c} />
      {kind === 'bad' ? (
        <path d="M32 32 L68 68 M68 32 L32 68" stroke="#fff" strokeWidth="11" strokeLinecap="round" />
      ) : (
        <path d="M28 52 L44 67 L73 35" stroke="#fff" strokeWidth="11" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
};

/** Moving background behind card / split layouts. */
export const PatternBg: React.FC<{theme: Theme; frame: number}> = ({theme, frame}) => {
  if (theme.name === 'dynamic') {
    const off = (frame * 2) % 80;
    return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: theme.bg,
          backgroundImage: `repeating-linear-gradient(-45deg, ${theme.accent}33 0 18px, transparent 18px 80px)`,
          backgroundPosition: `${off}px 0`,
        }}
      />
    );
  }
  return (
    <div style={{position: 'absolute', inset: 0, background: theme.bg}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 0.5}}>
        {Array.from({length: 13}).map((_, i) => (
          <line key={'v' + i} x1={i * 90} y1={0} x2={i * 90} y2={H} stroke={theme.muted} strokeWidth={0.6} opacity={0.35} />
        ))}
        {Array.from({length: 22}).map((_, i) => (
          <line key={'h' + i} x1={0} y1={i * 90} x2={W} y2={i * 90} stroke={theme.muted} strokeWidth={0.6} opacity={0.35} />
        ))}
        <circle cx={W * 0.78} cy={360 + Math.sin(frame / 40) * 12} r={260} fill={theme.accent} opacity={0.12} />
      </svg>
    </div>
  );
};

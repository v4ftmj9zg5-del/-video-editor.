import React from 'react';

/**
 * Line illustrations (viewBox 0 0 400 300). Every shape carries pathLength=1 so
 * the parent can "draw" it with stroke-dashoffset; `fill` fades in after.
 */
export type Art = 'sofa' | 'armchair' | 'table' | 'lamp' | 'plant' | 'bed' | 'shelf' | 'rug' | 'pendant';

type P = {stroke: string; fill: string; fill2: string; draw: number; fillOp: number; sw?: number};

const shape = (p: P, f: string) => ({
  pathLength: 1,
  stroke: p.stroke,
  strokeWidth: p.sw ?? 4,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  strokeDasharray: 1,
  strokeDashoffset: 1 - p.draw,
  fill: f,
  fillOpacity: p.fillOp,
});

export const FurnitureArt: React.FC<{art: Art} & P> = ({art, ...p}) => {
  const a = (f = p.fill) => shape(p, f);
  switch (art) {
    case 'sofa':
      return (
        <g>
          <rect x="60" y="70" width="280" height="110" rx="26" {...a()} />
          <rect x="30" y="120" width="60" height="120" rx="24" {...a(p.fill2)} />
          <rect x="310" y="120" width="60" height="120" rx="24" {...a(p.fill2)} />
          <rect x="85" y="160" width="115" height="62" rx="14" {...a(p.fill2)} />
          <rect x="200" y="160" width="115" height="62" rx="14" {...a(p.fill2)} />
          <rect x="62" y="225" width="276" height="22" rx="8" {...a()} />
          <path d="M70 247 L66 275 M330 247 L334 275" {...a('none')} />
          <rect x="110" y="96" width="70" height="56" rx="18" transform="rotate(-8 145 124)" {...a('#ffffff')} />
        </g>
      );
    case 'armchair':
      return (
        <g>
          <path d="M110 60 Q200 20 290 60 L285 175 L115 175 Z" {...a()} />
          <rect x="80" y="130" width="55" height="115" rx="24" {...a(p.fill2)} />
          <rect x="265" y="130" width="55" height="115" rx="24" {...a(p.fill2)} />
          <rect x="125" y="170" width="150" height="60" rx="16" {...a(p.fill2)} />
          <path d="M115 245 L105 285 M285 245 L295 285" {...a('none')} />
        </g>
      );
    case 'table':
      return (
        <g>
          <ellipse cx="200" cy="120" rx="170" ry="42" {...a()} />
          <path d="M60 128 Q200 190 340 128" {...a('none')} />
          <path d="M110 155 L95 270 M290 155 L305 270 M200 165 L200 280" {...a('none')} />
          <ellipse cx="160" cy="98" rx="30" ry="9" {...a(p.fill2)} />
          <path d="M240 70 L240 100 M228 100 L252 100 M240 70 Q228 50 240 40 Q252 50 240 70" {...a(p.fill2)} />
        </g>
      );
    case 'lamp':
      return (
        <g>
          <path d="M140 40 L260 40 L295 120 L105 120 Z" {...a()} />
          <path d="M200 120 L200 265" {...a('none')} />
          <ellipse cx="200" cy="272" rx="70" ry="14" {...a(p.fill2)} />
        </g>
      );
    case 'pendant':
      return (
        <g>
          <path d="M200 0 L200 90" {...a('none')} />
          <path d="M120 170 Q200 60 280 170 Z" {...a()} />
          <ellipse cx="200" cy="172" rx="80" ry="12" {...a(p.fill2)} />
        </g>
      );
    case 'plant':
      return (
        <g>
          <path d="M150 190 L250 190 L238 280 L162 280 Z" {...a(p.fill2)} />
          <path d="M200 190 Q190 120 200 40" {...a('none')} />
          <path d="M200 150 Q130 140 110 80 Q170 90 200 150" {...a()} />
          <path d="M200 120 Q270 110 295 50 Q230 60 200 120" {...a()} />
          <path d="M198 175 Q140 185 95 150 Q150 135 198 175" {...a()} />
          <path d="M202 170 Q260 180 305 140 Q250 128 202 170" {...a()} />
          <path d="M200 70 Q170 40 175 10 Q205 30 200 70" {...a()} />
        </g>
      );
    case 'bed':
      return (
        <g>
          <rect x="40" y="60" width="320" height="110" rx="20" {...a(p.fill2)} />
          <rect x="30" y="150" width="340" height="80" rx="16" {...a()} />
          <rect x="70" y="120" width="110" height="45" rx="16" {...a('#ffffff')} />
          <rect x="220" y="120" width="110" height="45" rx="16" {...a('#ffffff')} />
          <path d="M45 230 L45 270 M355 230 L355 270" {...a('none')} />
        </g>
      );
    case 'shelf':
      return (
        <g>
          <path d="M60 80 L340 80 M60 170 L340 170 M60 260 L340 260" {...a("none")} />
          <rect x="90" y="30" width="26" height="50" {...a()} />
          <rect x="120" y="40" width="22" height="40" {...a(p.fill2)} />
          <circle cx="260" cy="58" r="22" {...a()} />
          <rect x="230" y="120" width="70" height="50" rx="8" {...a(p.fill2)} />
          <path d="M100 215 Q130 180 160 215 L150 260 L110 260 Z" {...a()} />
        </g>
      );
    case 'rug':
    default:
      return (
        <g>
          <rect x="40" y="90" width="320" height="150" rx="10" {...a()} />
          <rect x="70" y="115" width="260" height="100" rx="6" {...a(p.fill2)} />
          <path d="M40 100 L25 100 M40 130 L25 130 M40 160 L25 160 M40 190 L25 190 M40 220 L25 220 M360 100 L375 100 M360 130 L375 130 M360 160 L375 160 M360 190 L375 190 M360 220 L375 220" {...a('none')} />
        </g>
      );
  }
};

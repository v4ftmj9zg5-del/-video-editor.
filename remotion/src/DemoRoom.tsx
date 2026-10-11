import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {FurnitureArt} from './graphics/furnitureArt';

/**
 * Stand-in footage for tests and demos only: an illustrated living room with a slow
 * camera drift. variant 'bare' = the "before" room, 'styled' = the "after" room.
 */
export const DemoRoom: React.FC<{variant: 'bare' | 'styled'}> = ({variant}) => {
  const f = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const styled = variant === 'styled';
  const k = durationInFrames > 1 ? f / durationInFrames : 0.5;
  const camX = interpolate(k, [0, 1], [-60, 60]);
  const zoom = interpolate(k, [0, 1], [1.08, 1.16]);
  const wall = styled ? 'linear-gradient(180deg, #E9DFD1 0%, #E2D3C0 100%)' : 'linear-gradient(180deg, #B9BCBF 0%, #A9ACAF 100%)';
  const floor = styled
    ? 'repeating-linear-gradient(90deg, #A9774F 0 150px, #9A6A44 150px 153px, #B0815A 153px 300px, #9A6A44 300px 303px)'
    : 'repeating-linear-gradient(90deg, #8F8B86 0 150px, #7F7B76 150px 153px)';
  const art = (x: number, y: number, s: number, a: any, fill: string, fill2: string) => (
    <g transform={`translate(${x}, ${y}) scale(${s})`}>
      <FurnitureArt art={a} stroke={styled ? '#4A3B30' : '#4B4E52'} fill={fill} fill2={fill2} draw={1} fillOp={1} sw={3} />
    </g>
  );
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `translateX(${camX}px) scale(${zoom})`}}>
        <AbsoluteFill style={{background: wall}} />
        {/* window + daylight */}
        <div style={{position: 'absolute', left: 90, top: 300, width: 380, height: 640, background: styled ? 'linear-gradient(180deg,#CFE3EE,#F4E7D2)' : 'linear-gradient(180deg,#D7DCE0,#C9CED2)',
          border: `18px solid ${styled ? '#F6F1E9' : '#CFD2D4'}`, boxShadow: 'inset 0 0 0 6px rgba(0,0,0,0.05)'}} />
        <div style={{position: 'absolute', left: 270, top: 300, width: 14, height: 640, background: styled ? '#F6F1E9' : '#CFD2D4'}} />
        {styled && <div style={{position: 'absolute', left: 60, top: 260, width: 70, height: 900, background: 'linear-gradient(90deg,#EFE4D3,#E2D2BB)', borderRadius: 8}} />}
        {styled && <div style={{position: 'absolute', left: 440, top: 260, width: 70, height: 900, background: 'linear-gradient(90deg,#E2D2BB,#EFE4D3)', borderRadius: 8}} />}
        {/* wall art */}
        {styled && (
          <>
            <div style={{position: 'absolute', left: 600, top: 420, width: 190, height: 250, background: 'linear-gradient(160deg,#C06A4B,#D9A58A 60%,#EFE6D2)', border: '12px solid #2B2A28'}} />
            <div style={{position: 'absolute', left: 820, top: 470, width: 150, height: 150, background: 'radial-gradient(circle,#707A4E,#9AA37A)', border: '12px solid #2B2A28'}} />
          </>
        )}
        {/* floor */}
        <div style={{position: 'absolute', left: -200, right: -200, top: 1240, bottom: 0, background: floor}} />
        <div style={{position: 'absolute', left: -200, right: -200, top: 1240, height: 30, background: 'rgba(0,0,0,0.12)'}} />
        <svg width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
          {styled && <ellipse cx={560} cy={1520} rx={480} ry={120} fill="#E9DCC6" stroke="#CDB99A" strokeWidth={6} />}
          {art(styled ? 230 : 110, 990, styled ? 1.55 : 2.15, 'sofa', styled ? '#D8C8B0' : '#7D8084', styled ? '#EFE6D8' : '#8C8F93')}
          {styled && art(20, 1180, 0.9, 'armchair', '#707A4E', '#8E9767')}
          {art(styled ? 380 : 420, 1420, 0.85, 'table', styled ? '#2B2A28' : '#5F6266', styled ? '#C06A4B' : '#777')}
          {styled && art(860, 980, 1.0, 'plant', '#6E7F4E', '#C9B79C')}
          {styled && art(560, 820, 1.6, 'lamp', '#F3E3C3', '#2B2A28')}
        </svg>
        {/* ceiling light / warm lamp glow */}
        {styled ? (
          <AbsoluteFill style={{mixBlendMode: 'screen', background: 'radial-gradient(circle at 880px 930px, rgba(255,200,130,0.45), rgba(255,180,110,0.1) 380px, rgba(0,0,0,0) 620px)'}} />
        ) : (
          <AbsoluteFill style={{background: 'radial-gradient(circle at 540px 160px, rgba(255,255,255,0.25), rgba(0,0,0,0.18) 900px)'}} />
        )}
        <AbsoluteFill style={{background: styled ? 'linear-gradient(110deg, rgba(255,240,215,0.28), rgba(0,0,0,0) 45%)' : 'none'}} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

import React from 'react';
import {Composition} from 'remotion';
import {DemoRoom} from './DemoRoom';
import {Reel} from './Reel';
import {ReelProps} from './types';

const defaults: ReelProps = {
  style: 'dynamic',
  fps: 30,
  durationInFrames: 300,
  base: 'base.mp4',
  captions: [],
  scenes: [],
  punches: [],
};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Reel"
      component={Reel as any}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={300}
      defaultProps={defaults as any}
      calculateMetadata={({props}: {props: any}) => ({durationInFrames: props.durationInFrames, fps: props.fps})}
    />
    {/* stand-in footage for tests/demos */}
    <Composition
      id="DemoRoom"
      component={DemoRoom as any}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={600}
      defaultProps={{variant: 'styled', durationInFrames: 600} as any}
      calculateMetadata={({props}: {props: any}) => ({durationInFrames: props.durationInFrames ?? 600})}
    />
  </>
);

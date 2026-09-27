import React from "react";
import {Composition} from "remotion";
import {RenderComposition, type RenderProps} from "./Composition";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ShortAutoProV2"
    component={RenderComposition}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={30}
    defaultProps={{} as RenderProps}
    calculateMetadata={({props}) => {
      const p = props as RenderProps;
      const fps = Number(p.fps || 30);
      const duration = Math.max(1, Math.round(Number(p.duration_target || 1) * fps));
      return {
        fps,
        width: Number(p.width || 1080),
        height: Number(p.height || 1920),
        durationInFrames: duration,
      };
    }}
  />
);

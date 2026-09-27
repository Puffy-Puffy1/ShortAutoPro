import React from "react";
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type TimelineScene = {
  scene_id: string;
  start_time: number;
  end_time: number;
  duration: number;
  asset: string;
  asset_type: "image" | "video";
  transition?: {type?: string; duration?: number};
  effect?: {zoom_start?: number; zoom_end?: number; pan?: string};
};

export type SubtitleCue = {
  start: number;
  end: number;
  text: string;
};

export type RenderProps = {
  width?: number;
  height?: number;
  fps?: number;
  duration_target?: number;
  timeline?: {scenes: TimelineScene[]; subtitles?: SubtitleCue[]};
};

const fit: React.CSSProperties = {
  width: "100%",
  height: "100%",
  objectFit: "cover",
};

const Scene: React.FC<{scene: TimelineScene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = Math.max(0, frame - Math.round(scene.start_time * fps));
  const frames = Math.max(1, Math.round(scene.duration * fps));
  const progress = Math.min(1, local / Math.max(1, frames - 1));
  const z1 = Number(scene.effect?.zoom_start ?? 1);
  const z2 = Number(scene.effect?.zoom_end ?? z1);
  const zoom = interpolate(progress, [0, 1], [z1, z2], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  const pan = String(scene.effect?.pan || "center").toLowerCase();
  const x = pan === "left" ? -1.5 : pan === "right" ? 1.5 : 0;
  const y = 0;
  const opacity = scene.transition?.type === "fade"
    ? Math.min(1, Math.max(0, progress / 0.18))
    : 1;

  const src = staticFile(scene.asset);
  return (
    <AbsoluteFill style={{opacity, transform: `scale(${zoom}) translate(${x}%, ${y}%)`}}>
      {scene.asset_type === "video" ? (
        <OffthreadVideo src={src} muted style={fit} />
      ) : (
        <Img src={src} style={fit} />
      )}
    </AbsoluteFill>
  );
};

const Subtitles: React.FC<{cues: SubtitleCue[]}> = ({cues}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / fps;
  const active = cues.filter((cue) => time >= cue.start && time < cue.end);
  if (!active.length) return null;
  return (
    <AbsoluteFill style={{justifyContent: "flex-end", alignItems: "center", padding: "0 70px 210px", pointerEvents: "none"}}>
      <div style={{
        maxWidth: "92%",
        padding: "14px 22px",
        borderRadius: 16,
        background: "rgba(0,0,0,0.55)",
        color: "white",
        fontFamily: "Arial, sans-serif",
        fontSize: 58,
        fontWeight: 800,
        lineHeight: 1.12,
        textAlign: "center",
        textShadow: "0 3px 8px rgba(0,0,0,0.8)",
      }}>
        {active[active.length - 1].text}
      </div>
    </AbsoluteFill>
  );
};

export const RenderComposition: React.FC<RenderProps> = ({timeline}) => (
  <AbsoluteFill style={{backgroundColor: "#000", overflow: "hidden"}}>
    {(timeline?.scenes || []).map((scene) => (
      <Sequence
        key={scene.scene_id}
        from={Math.max(0, Math.round(scene.start_time * 30))}
        durationInFrames={Math.max(1, Math.round(scene.duration * 30))}
      >
        <Scene scene={scene} />
      </Sequence>
    ))}
    <Subtitles cues={timeline?.subtitles || []} />
  </AbsoluteFill>
);

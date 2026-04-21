import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import { ChaosLines } from "./scenes/ChaosLines";
import { Shockwave } from "./scenes/Shockwave";
import { NetworkTree } from "./scenes/NetworkTree";
import { LogoReveal } from "./scenes/LogoReveal";

/**
 * 主组件：「千人迷途」开场动画
 * 1920×1080, 30fps, 600 帧（20 秒）
 */

export const Opening: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      {/* 场景 1：千线涌入与窒息（0-215 帧）*/}
      <Sequence
        from={0}
        durationInFrames={215}
        layout="none"
      >
        <ChaosLines />
      </Sequence>

      {/* 场景 2：斩断与冲击波（180-240 帧，与场景 1 重叠）*/}
      <Sequence
        from={180}
        durationInFrames={60}
        layout="none"
      >
        <Shockwave />
      </Sequence>

      {/* 场景 3：秩序重建与数据注入（240-510 帧）*/}
      <Sequence
        from={240}
        durationInFrames={270}
        layout="none"
      >
        <NetworkTree />
      </Sequence>

      {/* 场景 4：Logo 定格（510-600 帧）*/}
      <Sequence
        from={510}
        durationInFrames={90}
        layout="none"
      >
        <LogoReveal />
      </Sequence>
    </AbsoluteFill>
  );
};

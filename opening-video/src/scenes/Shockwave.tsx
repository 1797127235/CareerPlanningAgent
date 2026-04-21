import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { lines, CENTER_X, CENTER_Y } from "../utils/generateData";

/**
 * 场景 2：斩断与冲击波（Sequence: 180-240 帧）
 */

export const Shockwave: React.FC = () => {
  const frame = useCurrentFrame();

  // 局部帧 0-60，对应全局 180-240

  // ── 白色闪光灯 ──
  const flashOpacity = interpolate(frame, [15, 17, 18, 35], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── 冲击波圆环 ──
  const shockwaveRadius = interpolate(
    frame,
    [17, 35],
    [0, 1500],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.quad),
    },
  );
  const shockwaveOpacity = interpolate(frame, [17, 25, 35], [1, 0.4, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const shockwaveWidth = interpolate(frame, [17, 35], [8, 2], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── 线条吹散 ──
  const blowProgress = interpolate(frame, [17, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  const blowSegments: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    color: string;
    opacity: number;
  }[] = [];

  // 只渲染冻结在中心附近的线段
  for (const line of lines) {
    const frozenX = CENTER_X + Math.cos(line.blowAngle - Math.PI) * 40;
    const frozenY = CENTER_Y + Math.sin(line.blowAngle - Math.PI) * 40;

    const distance = line.blowSpeed * blowProgress;
    const endX = frozenX + Math.cos(line.blowAngle) * distance;
    const endY = frozenY + Math.sin(line.blowAngle) * distance;

    const opacity = interpolate(blowProgress, [0, 0.5, 1], [0.3, 0.2, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    blowSegments.push({
      x1: frozenX,
      y1: frozenY,
      x2: endX,
      y2: endY,
      color: "#EF4444",
      opacity,
    });
  }

  // ── 中央光点呼吸 ──
  const breathPhase = frame >= 35 ? (frame - 35) / 25 : 0; // 0~1
  const breathScale = 1 + Math.sin(breathPhase * Math.PI * 2) * 0.3;
  const breathOpacity = interpolate(frame, [35, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {/* 吹散的线 */}
      {frame >= 17 && (
        <svg
          width="1920"
          height="1080"
          style={{ position: "absolute", inset: 0 }}
        >
          {blowSegments.map((seg, i) => (
            <line
              key={i}
              x1={seg.x1}
              y1={seg.y1}
              x2={seg.x2}
              y2={seg.y2}
              stroke={seg.color}
              strokeWidth={1.5}
              opacity={seg.opacity}
              strokeLinecap="round"
            />
          ))}
        </svg>
      )}

      {/* 冲击波圆环 */}
      {frame >= 17 && (
        <svg
          width="1920"
          height="1080"
          style={{ position: "absolute", inset: 0 }}
        >
          <circle
            cx={CENTER_X}
            cy={CENTER_Y}
            r={shockwaveRadius}
            fill="none"
            stroke="#FFFFFF"
            strokeWidth={shockwaveWidth}
            opacity={shockwaveOpacity}
          />
        </svg>
      )}

      {/* 中央光点 */}
      {frame >= 35 && (
        <div
          style={{
            position: "absolute",
            left: CENTER_X,
            top: CENTER_Y,
            transform: `translate(-50%, -50%) scale(${breathScale})`,
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: "#FFFFFF",
            opacity: breathOpacity,
            boxShadow: "0 0 40px 20px rgba(255,255,255,0.3)",
          }}
        />
      )}

      {/* 白色闪光灯覆盖层 */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "#FFFFFF",
          opacity: flashOpacity,
          pointerEvents: "none",
        }}
      />
    </div>
  );
};

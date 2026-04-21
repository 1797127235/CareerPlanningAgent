import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { lines, CENTER_X, CENTER_Y, noise2D } from "../utils/generateData";

/**
 * 场景 1：千线涌入与窒息（Sequence: 0-215 帧）
 * 高性能版：path 合并拖尾 + 无 filter
 */

const TRAIL_LENGTH = 24;

function getLinePosition(
  line: (typeof lines)[0],
  progress: number,
): { x: number; y: number } {
  const baseX = interpolate(progress, [0, 1], [line.startX, CENTER_X]);
  const baseY = interpolate(progress, [0, 1], [line.startY, CENTER_Y]);

  const noiseX = noise2D(progress * 4 + line.noiseOffsetX, line.noiseOffsetY);
  const noiseY = noise2D(line.noiseOffsetX, progress * 4 + line.noiseOffsetY);

  const maxOffset = 120;
  return {
    x: baseX + noiseX * maxOffset,
    y: baseY + noiseY * maxOffset,
  };
}

export const ChaosLines: React.FC = () => {
  const frame = useCurrentFrame();

  const paths: { d: string; color: string }[] = [];
  const heads: { x: number; y: number; color: string }[] = [];

  for (const line of lines) {
    const totalFrames = 150 / line.speed;
    const currentProgress = Math.min(frame / totalFrames, 1);

    if (currentProgress <= 0) continue;

    const startFrame = Math.max(0, frame - TRAIL_LENGTH);
    let d = "";

    for (let f = startFrame; f <= frame; f++) {
      const p = Math.min(f / totalFrames, 1);
      const pos = getLinePosition(line, p);
      d += `${f === startFrame ? "M" : "L"} ${pos.x.toFixed(1)} ${pos.y.toFixed(1)} `;
    }

    // 颜色：冷蓝 → 紫红（帧 90~180）
    let color = line.color;
    if (frame >= 90 && frame <= 180) {
      const t = interpolate(frame, [90, 180], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      const r1 = 139 + (239 - 139) * t;
      const g1 = 92 + (68 - 92) * t;
      const b1 = 246 + (68 - 246) * t;
      color = `rgb(${Math.round(r1)},${Math.round(g1)},${Math.round(b1)})`;
    } else if (frame > 180) {
      color = "#EF4444";
    }

    paths.push({ d, color });

    const headPos = getLinePosition(line, currentProgress);
    heads.push({ x: headPos.x, y: headPos.y, color });
  }

  // ── 脉冲震动（心跳式）─-
  const shakeIntensity = interpolate(frame, [120, 180], [0, 8], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const shakeX = Math.sin(frame * 0.8) * shakeIntensity;
  const shakeY = Math.cos(frame * 0.6) * shakeIntensity * 0.5;

  // ── 23% 数字 ──
  const showPercent = frame >= 120;
  const percentOpacity = interpolate(frame, [120, 140], [0, 0.35], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        transform: `translate(${shakeX}px, ${shakeY}px)`,
      }}
    >
      <svg width="1920" height="1080" style={{ position: "absolute", inset: 0 }}>
        {/* 拖尾 path：一条线一个元素 */}
        {paths.map((p, i) => (
          <path
            key={`path-${i}`}
            d={p.d}
            fill="none"
            stroke={p.color}
            strokeWidth={2.2}
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={0.85}
          />
        ))}

        {/* 头部高亮光点 */}
        {heads.map((h, i) => (
          <circle
            key={`head-${i}`}
            cx={h.x}
            cy={h.y}
            r={4}
            fill={h.color}
            opacity={0.95}
          />
        ))}
      </svg>

      {showPercent && (
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%)",
            fontSize: "200px",
            fontWeight: 900,
            color: "#EF4444",
            opacity: percentOpacity,
            fontFamily:
              '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            letterSpacing: "-0.04em",
            userSelect: "none",
            pointerEvents: "none",
            textShadow: "0 0 60px rgba(239,68,68,0.6)",
          }}
        >
          23%
        </div>
      )}
    </div>
  );
};

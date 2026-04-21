import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import {
  CENTER_X,
  CENTER_Y,
  HEX_ANGLES,
  HEX_LABELS,
  getBranchAngles,
} from "../utils/generateData";

/**
 * 场景 3：秩序重建与数据注入（Sequence: 240-510 帧）
 */

const MAIN_LINE_LENGTH = 380;
const BRANCH_LENGTH = 90;

export const NetworkTree: React.FC = () => {
  const frame = useCurrentFrame();

  // ── 六条主线射出 ──
  const mainLineProgress = interpolate(frame, [0, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // ── 末端光圈 ──
  const circleProgress = interpolate(frame, [20, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  // ── 岗位名称 ──
  const labelOpacity = interpolate(frame, [35, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── 分支生长 ──
  const branchProgress = interpolate(frame, [60, 180], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // ── 光粒子 ──
  const particleProgress = interpolate(frame, [180, 270], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── 数据标签 ──
  const tag1Opacity = interpolate(frame, [200, 230], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const tag2Opacity = interpolate(frame, [215, 245], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const tag3Opacity = interpolate(frame, [230, 260], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── 构建 SVG 路径 ──
  const mainLines: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  }[] = [];
  const circles: { cx: number; cy: number }[] = [];
  const branchLines: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  }[] = [];
  const branchDots: { cx: number; cy: number }[] = [];

  for (let i = 0; i < 6; i++) {
    const angle = HEX_ANGLES[i];
    const endX = CENTER_X + Math.cos(angle) * MAIN_LINE_LENGTH * mainLineProgress;
    const endY = CENTER_Y + Math.sin(angle) * MAIN_LINE_LENGTH * mainLineProgress;

    mainLines.push({
      x1: CENTER_X,
      y1: CENTER_Y,
      x2: endX,
      y2: endY,
    });

    // 末端光圈位置（固定终点）
    const finalX = CENTER_X + Math.cos(angle) * MAIN_LINE_LENGTH;
    const finalY = CENTER_Y + Math.sin(angle) * MAIN_LINE_LENGTH;
    circles.push({ cx: finalX, cy: finalY });

    // 分支
    const branchAngles = getBranchAngles(angle);
    for (const ba of branchAngles) {
      const branchStartX = CENTER_X + Math.cos(angle) * MAIN_LINE_LENGTH * 0.65;
      const branchStartY = CENTER_Y + Math.sin(angle) * MAIN_LINE_LENGTH * 0.65;
      const branchEndX = branchStartX + Math.cos(ba) * BRANCH_LENGTH * branchProgress;
      const branchEndY = branchStartY + Math.sin(ba) * BRANCH_LENGTH * branchProgress;

      branchLines.push({
        x1: branchStartX,
        y1: branchStartY,
        x2: branchEndX,
        y2: branchEndY,
      });

      if (branchProgress > 0.9) {
        branchDots.push({ cx: branchEndX, cy: branchEndY });
      }
    }
  }

  // ── 光粒子（沿主线流动）─-
  const particles: { x: number; y: number; opacity: number }[] = [];
  if (particleProgress > 0) {
    for (let i = 0; i < 6; i++) {
      const angle = HEX_ANGLES[i];
      const t = (particleProgress * 1.5) % 1; // 循环流动
      const px = CENTER_X + Math.cos(angle) * MAIN_LINE_LENGTH * t;
      const py = CENTER_Y + Math.sin(angle) * MAIN_LINE_LENGTH * t;
      particles.push({
        x: px,
        y: py,
        opacity: t > 0.9 ? 1 - (t - 0.9) * 10 : 1,
      });
    }
  }

  // ── 数据标签位置 ──
  const tagPositions = [
    { x: 300, y: 200, text: "150万+ 招聘语料" },
    { x: 300, y: 880, text: "409MB AEI 数据" },
    { x: 1620, y: 540, text: "45 节点 · 101 条路径" },
  ];

  // 标签连接线目标节点
  const tagTargets = [
    { x: CENTER_X + Math.cos(HEX_ANGLES[0]) * MAIN_LINE_LENGTH, y: CENTER_Y + Math.sin(HEX_ANGLES[0]) * MAIN_LINE_LENGTH },
    { x: CENTER_X + Math.cos(HEX_ANGLES[3]) * MAIN_LINE_LENGTH, y: CENTER_Y + Math.sin(HEX_ANGLES[3]) * MAIN_LINE_LENGTH },
    { x: CENTER_X + Math.cos(HEX_ANGLES[1]) * MAIN_LINE_LENGTH, y: CENTER_Y + Math.sin(HEX_ANGLES[1]) * MAIN_LINE_LENGTH },
  ];

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <svg width="1920" height="1080" style={{ position: "absolute", inset: 0 }}>
        {/* 主线 */}
        {mainLines.map((line, i) => (
          <line
            key={`main-${i}`}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="#4A9EFF"
            strokeWidth={2}
            strokeLinecap="round"
            opacity={0.8}
          />
        ))}

        {/* 分支 */}
        {branchLines.map((line, i) => (
          <line
            key={`branch-${i}`}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="#4A9EFF"
            strokeWidth={1}
            strokeLinecap="round"
            opacity={0.5}
          />
        ))}

        {/* 末端光圈 */}
        {circles.map((c, i) => (
          <g key={`circle-${i}`}>
            <circle
              cx={c.cx}
              cy={c.cy}
              r={16 * circleProgress}
              fill="none"
              stroke="#4A9EFF"
              strokeWidth={2}
              opacity={circleProgress * 0.8}
            />
            <circle
              cx={c.cx}
              cy={c.cy}
              r={6 * circleProgress}
              fill="#4A9EFF"
              opacity={circleProgress * 0.9}
            />
          </g>
        ))}

        {/* 分支小圆点 */}
        {branchDots.map((d, i) => (
          <circle
            key={`dot-${i}`}
            cx={d.cx}
            cy={d.cy}
            r={3}
            fill="#4A9EFF"
            opacity={0.7}
          />
        ))}

        {/* 光粒子 */}
        {particles.map((p, i) => (
          <circle
            key={`particle-${i}`}
            cx={p.x}
            cy={p.y}
            r={4}
            fill="#FFFFFF"
            opacity={p.opacity}
            filter="url(#glow)"
          />
        ))}

        {/* 发光滤镜 */}
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>

      {/* 岗位名称 */}
      {circles.map((c, i) => (
        <div
          key={`label-${i}`}
          style={{
            position: "absolute",
            left: c.cx,
            top: c.cy - 35,
            transform: "translate(-50%, -100%)",
            color: "#FFFFFF",
            fontSize: "18px",
            fontWeight: 600,
            opacity: labelOpacity,
            fontFamily:
              '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            whiteSpace: "nowrap",
            textShadow: "0 0 20px rgba(74,158,255,0.5)",
            pointerEvents: "none",
          }}
        >
          {HEX_LABELS[i]}
        </div>
      ))}

      {/* 数据标签 */}
      {[
        { opacity: tag1Opacity, idx: 0 },
        { opacity: tag2Opacity, idx: 1 },
        { opacity: tag3Opacity, idx: 2 },
      ].map(({ opacity, idx }) => (
        <React.Fragment key={`tag-${idx}`}>
          {/* 连接线 */}
          <svg
            width="1920"
            height="1080"
            style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
          >
            <line
              x1={tagPositions[idx].x}
              y1={tagPositions[idx].y}
              x2={tagTargets[idx].x}
              y2={tagTargets[idx].y}
              stroke="#FF6B3D"
              strokeWidth={1}
              opacity={opacity * 0.4}
              strokeDasharray="4 4"
            />
          </svg>
          {/* 标签 */}
          <div
            style={{
              position: "absolute",
              left: tagPositions[idx].x,
              top: tagPositions[idx].y,
              transform: "translate(-50%, -50%)",
              border: "1px solid #FF6B3D",
              borderRadius: 6,
              padding: "8px 16px",
              color: "#FF6B3D",
              fontSize: "14px",
              fontWeight: 600,
              opacity,
              fontFamily:
                '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              background: "rgba(0,0,0,0.5)",
              pointerEvents: "none",
              whiteSpace: "nowrap",
            }}
          >
            {tagPositions[idx].text}
          </div>
        </React.Fragment>
      ))}
    </div>
  );
};

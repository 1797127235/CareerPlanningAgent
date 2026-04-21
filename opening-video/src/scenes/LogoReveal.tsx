import React from "react";
import { useCurrentFrame, interpolate, Easing, spring, useVideoConfig } from "remotion";

/**
 * 场景 4：Logo 定格（Sequence: 510-600 帧）
 */

export const LogoReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── 旋转收束 ──
  const rotation = interpolate(frame, [0, 35], [0, 180], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  const networkOpacity = interpolate(frame, [15, 35], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── Logo 出现 ──
  const logoSpring = spring({
    frame: frame - 45,
    fps,
    config: { damping: 15, stiffness: 180 },
  });

  const subtitleSpring = spring({
    frame: frame - 55,
    fps,
    config: { damping: 20, stiffness: 200 },
  });

  // ── 三个标签弹入 ──
  const badges = [
    { text: "百万级数据", delay: 60 },
    { text: "AEI 驱动", delay: 70 },
    { text: "完整闭环", delay: 80 },
  ];

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {/* 网络旋转收束（保持 NetworkTree 的 SVG）*/}
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `rotate(${rotation}deg)`,
          opacity: networkOpacity,
          pointerEvents: "none",
        }}
      />

      {/* Logo */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          opacity: frame >= 45 ? 1 : 0,
        }}
      >
        {/* 主标题 */}
        <h1
          style={{
            fontSize: "96px",
            fontWeight: 900,
            color: "#FFFFFF",
            letterSpacing: "0.08em",
            transform: `scale(${logoSpring})`,
            opacity: logoSpring,
            fontFamily:
              '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif',
            textShadow: "0 0 60px rgba(255,255,255,0.15)",
            margin: 0,
          }}
        >
          职途智析
        </h1>

        {/* 副标题 */}
        <p
          style={{
            fontSize: "28px",
            color: "#FF6B3D",
            marginTop: "24px",
            letterSpacing: "0.04em",
            transform: `translateY(${(1 - subtitleSpring) * 20}px)`,
            opacity: subtitleSpring,
            fontFamily:
              '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif',
            fontWeight: 500,
          }}
        >
          让每一份职业规划都有数据支撑
        </p>

        {/* 标签 */}
        <div
          style={{
            display: "flex",
            gap: "16px",
            marginTop: "48px",
          }}
        >
          {badges.map((badge, i) => {
            const badgeSpring = spring({
              frame: frame - badge.delay,
              fps,
              config: { damping: 18, stiffness: 300 },
            });

            if (frame < badge.delay) return null;

            return (
              <span
                key={i}
                style={{
                  border: "1px solid #FF6B3D",
                  borderRadius: 9999,
                  padding: "8px 20px",
                  color: "#FF6B3D",
                  fontSize: "16px",
                  fontWeight: 500,
                  fontFamily:
                    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                  transform: `scale(${badgeSpring})`,
                  opacity: badgeSpring,
                }}
              >
                {badge.text}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
};

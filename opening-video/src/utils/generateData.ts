/**
 * 数据预生成 — 固定 seed 的伪随机生成器
 * 所有数据在组件外预计算，确保渲染可复现
 */

// ── Seeded PRNG ──
function mulberry32(a: number) {
  return function () {
    let t = (a += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rng = mulberry32(42);

function randomRange(min: number, max: number): number {
  return min + rng() * (max - min);
}

// ── Color helpers ──
function lerpColor(c1: string, c2: string, t: number): string {
  const h1 = parseInt(c1.slice(1), 16);
  const h2 = parseInt(c2.slice(1), 16);
  const r1 = (h1 >> 16) & 0xff, g1 = (h1 >> 8) & 0xff, b1 = h1 & 0xff;
  const r2 = (h2 >> 16) & 0xff, g2 = (h2 >> 8) & 0xff, b2 = h2 & 0xff;
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r},${g},${b})`;
}

function randomBlueColor(): string {
  const t = rng();
  return lerpColor("#1E3A8A", "#60A5FA", t);
}

// ── Perlin-like noise (simple 2D) ──
function fade(t: number): number {
  return t * t * t * (t * (t * 6 - 15) + 10);
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

const perm: number[] = [];
for (let i = 0; i < 256; i++) perm[i] = i;
for (let i = 255; i > 0; i--) {
  const j = Math.floor(rng() * (i + 1));
  [perm[i], perm[j]] = [perm[j], perm[i]];
}
const perm2 = [...perm, ...perm];

function grad(hash: number, x: number, y: number): number {
  const h = hash & 3;
  const u = h < 2 ? x : -x;
  const v = h < 2 ? (h === 0 ? y : -y) : (h === 2 ? y : -y);
  return u + v;
}

export function noise2D(x: number, y: number): number {
  const X = Math.floor(x) & 255;
  const Y = Math.floor(y) & 255;
  const xf = x - Math.floor(x);
  const yf = y - Math.floor(y);
  const u = fade(xf);
  const v = fade(yf);
  const aa = perm2[perm2[X] + Y];
  const ab = perm2[perm2[X] + Y + 1];
  const ba = perm2[perm2[X + 1] + Y];
  const bb = perm2[perm2[X + 1] + Y + 1];
  return lerp(
    lerp(grad(aa, xf, yf), grad(ba, xf - 1, yf), u),
    lerp(grad(ab, xf, yf - 1), grad(bb, xf - 1, yf - 1), u),
    v,
  );
}

// ── Types ──
export type LineData = {
  id: number;
  // 起点在画面边缘 ±100px 范围
  startX: number;
  startY: number;
  // Perlin 噪声参数
  noiseOffsetX: number;
  noiseOffsetY: number;
  // 速度系数
  speed: number;
  // 颜色
  color: string;
  // 吹散方向（弧度，从中心向外的角度 + ±15°偏移）
  blowAngle: number;
  // 吹散速度
  blowSpeed: number;
};

// ── Pre-computed data ──
export const LINE_COUNT = 80;
export const CENTER_X = 960;
export const CENTER_Y = 540;

function pickStartPosition(): { x: number; y: number } {
  const side = Math.floor(rng() * 4); // 0=top, 1=right, 2=bottom, 3=left
  const offset = randomRange(-100, 100);
  switch (side) {
    case 0:
      return { x: randomRange(0, 1920) + offset, y: randomRange(-100, 0) };
    case 1:
      return { x: randomRange(1920, 2020), y: randomRange(0, 1080) + offset };
    case 2:
      return { x: randomRange(0, 1920) + offset, y: randomRange(1080, 1180) };
    default:
      return { x: randomRange(-100, 0), y: randomRange(0, 1080) + offset };
  }
}

export const lines: LineData[] = (() => {
  const result: LineData[] = [];
  for (let i = 0; i < LINE_COUNT; i++) {
    const start = pickStartPosition();
    const dx = CENTER_X - start.x;
    const dy = CENTER_Y - start.y;
    const baseAngle = Math.atan2(dy, dx);
    const blowAngle = baseAngle + randomRange(-0.26, 0.26); // ±15°

    result.push({
      id: i,
      startX: start.x,
      startY: start.y,
      noiseOffsetX: randomRange(0, 100),
      noiseOffsetY: randomRange(0, 100),
      speed: randomRange(0.5, 2.0),
      color: randomBlueColor(),
      blowAngle,
      blowSpeed: randomRange(800, 2000),
    });
  }
  return result;
})();

// ── Hexagon directions ──
export const HEX_ANGLES = [
  -Math.PI / 2, // 12点
  -Math.PI / 6, // 2点
  Math.PI / 6, // 4点
  Math.PI / 2, // 6点
  (5 * Math.PI) / 6, // 8点
  (7 * Math.PI) / 6, // 10点
];

export const HEX_LABELS = [
  "前端开发",
  "Java 后端",
  "算法工程师",
  "C++ 开发",
  "产品经理",
  "测试开发",
];

// 分支角度偏移（主线两侧各3条分支）
export function getBranchAngles(mainAngle: number): number[] {
  return [-0.35, -0.18, 0.18, 0.35].map((off) => mainAngle + off);
}

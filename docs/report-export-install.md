# 报告 PDF 导出 —— 环境安装

## 后端依赖

1. 安装 Playwright Python SDK：
   ```
   pip install playwright>=1.40
   ```

2. 下载 Chromium（一次性，约 150MB）：
   ```
   playwright install chromium
   ```

3. Windows 如遇缺 DLL，装 Visual C++ Redistributable。

## 字体

打印使用中文衬线字体（按系统不同）：
- Windows: Source Han Serif SC / Noto Serif CJK SC（若无需自行下载）
- macOS: Songti SC / PingFang 内置
- Linux: fonts-noto-cjk

字体未安装时会回退，效果会差。建议部署机器安装 Source Han Serif SC。

## 前端依赖

   ```
   cd frontend
   npm install @chenglou/pretext
   ```

## 环境变量

`.env`：
   ```
   FRONTEND_URL=http://localhost:5173
   ```

生产环境按实际前端部署地址填。

## 启动

前端：
   ```
   cd frontend && npm run dev
   ```

后端：
   ```
   python -m uvicorn backend.app:app --reload
   ```

然后前端打开 /report 页面，点"导出 PDF"。

# 前端开发面试重点（浏览器 + JS/TS + 框架 + 工程化 + 性能）

## 浏览器渲染流水线
- 关键渲染路径：HTML→DOM 树、CSS→CSSOM 树、合并→Render 树→布局→绘制→合成。
- DOMContentLoaded vs load：DOM 解析完成 vs 所有资源加载完成，CSS 阻塞 DOM 渲染但不阻塞解析。
- `<script>` 阻塞：默认阻塞 DOM 解析，`async`（下载完立即执行）vs `defer`（DOM 解析后执行）。
- 合成层优化：`transform`/`opacity` 触发 GPU 合成，跳过布局与绘制。
- 重排（Reflow/Layout）与重绘（Repaint）：重排代价更高，批量更新策略（DocumentFragment/虚拟 DOM）。

## 浏览器缓存与网络
- 强缓存：`Cache-Control`（max-age/no-cache/no-store）优先于 `Expires`。
- 协商缓存：`ETag`/`If-None-Match` vs `Last-Modified`/`If-Modified-Since`，304 响应。
- 缓存位置优先级：Service Worker → Memory Cache → Disk Cache → Push Cache。
- HTTP/1.1 持久连接与管线化缺陷；HTTP/2 多路复用、头部压缩（HPACK）、二进制分帧。
- HTTP/3（QUIC）：基于 UDP、0-RTT 连接、解决队头阻塞。
- HTTPS：TLS 握手流程（证书校验→密钥协商→对称加密通信），会话复用。

## 前端安全
- XSS：存储型/反射型/DOM 型，防御（转义、CSP、HttpOnly Cookie）。
- CSRF：伪造请求利用已认证身份，防御（SameSite Cookie、CSRF Token、Referer 校验）。
- CORS：简单请求 vs 预检请求（OPTIONS），`Access-Control-Allow-Origin` 等响应头。
- CSP（Content-Security-Policy）：白名单限制资源加载，`nonce`/`hash` 策略。
- 点击劫持：X-Frame-Options / CSP frame-ancestors 防御。

## JavaScript 类型与作用域
- 8 种数据类型（7 原始 + Object），`typeof null === "object"` 历史遗留。
- `let`/`const` vs `var`：块级作用域、暂时性死区（TDZ）、变量提升差异。
- 作用域链：词法作用域（静态），引擎沿作用域链逐层查找标识符。
- 闭包：函数与其词法环境的绑定，经典场景（防抖/节流/私有变量/柯里化）与内存泄漏风险。
- 隐式类型转换：`==` vs `===`，`[] == ![]` 等经典问题。

## JavaScript 原型与继承
- 原型链：`__proto__` vs `prototype`，属性查找沿原型链向上。
- `Object.create()` vs `new`：直接指定原型 vs 构造函数实例化。
- `class` 语法糖：`extends`/`super` 底层仍基于原型链，`static` 方法不可继承到实例。
- `Object.setPrototypeOf` 性能问题，推荐 `Object.create` 替代。
- `instanceof` 原理：沿原型链查找 constructor.prototype。

## JavaScript 异步编程
- 事件循环：宏任务（setTimeout/setInterval/I/O）与微任务（Promise.then/MutationObserver）执行顺序。
- Promise：状态机（pending→fulfilled/rejected），链式调用与错误冒泡，`Promise.all` vs `Promise.allSettled` vs `Promise.race`。
- `async/await`：语法糖，异常用 `try/catch` 捕获，并行场景仍需 `Promise.all`。
- `async` 函数中的并发陷阱：串行 `await` vs 并行 `Promise.all`，性能差异。
- 任务队列细节：Node.js 的 libuv 事件循环阶段（timers/poll/check/close）。

## ES6+ 核心特性
- 解构赋值（数组/对象/默认值）、展开/剩余运算符。
- 箭头函数：没有 `this`/`arguments`/`prototype`，不适合作为构造函数。
- `Symbol`：唯一标识符，`Symbol.iterator` 与 `for...of` 协议。
- `Map`/`Set`/`WeakMap`/`WeakSet`：与 Object/Array 的适用场景对比。
- `Proxy`/`Reflect`：元编程基础，Vue 3 响应式原理的核心。
- 迭代器协议：`__iter__` + `__next__`，生成器 `yield` 暂停与恢复。

## TypeScript 类型系统
- 接口 vs 类型别名：`interface` 可合并声明，`type` 支持联合/交叉/条件类型。
- 泛型：泛型约束、泛型默认值、泛型在函数/接口/类中的使用。
- 联合类型与类型守卫：`typeof`/`instanceof`/`in`/`自定义类型守卫函数`收窄类型。
- 条件类型与映射类型：`infer` 提取类型参数，`Partial`/`Required`/`Pick`/`Omit`/`Record` 实现原理。
- 协变/逆变/双变/不变：函数参数位置的类型关系。
- `strict` 系列配置：`strictNullChecks`、`noImplicitAny`、`strictFunctionTypes`。

## React 核心机制
- Fiber 架构：链表结构替代递归、可中断渲染、时间切片（Time Slicing）与优先级调度。
- Virtual DOM：Diff 算法（同层比较、key 的作用）、Reconciliation 过程。
- Hooks 规则：调用顺序一致（不能在条件/循环中调用）、闭包陷阱（stale closure）与解决方案。
- 常用 Hooks：`useState`/`useEffect`（依赖数组）/`useCallback`/`useMemo`/`useRef`/`useContext`。
- `useEffect` vs `useLayoutEffect`：异步 vs 同步、绘制前 vs 绘制后。
- React 18 并发特性：`useTransition`（非紧急更新降级）、`useDeferredValue`（延迟重渲染）、Suspense 数据获取。

## Vue 核心机制
- 响应式原理：Vue 2（`Object.defineProperty` 拦截 getter/setter）vs Vue 3（`Proxy` 代理全对象）。
- Composition API：`ref`/`reactive`/`computed`/`watch`/`watchEffect`，逻辑组合 vs Options API 逻辑分散。
- 模板编译：模板→AST→渲染函数→Virtual DOM，静态提升与补丁标记（Patch Flag）。
- 组件更新粒度：Vue 3 基于依赖追踪的精确更新 vs React 整体重渲染（需 memo/shouldComponentUpdate）。
- Vue 3 编译优化：Block Tree、静态提升（hoistStatic）、缓存事件处理器。

## 状态管理
- React：Context API（轻量）、Redux（单向数据流/reducer/middleware）、Zustand（极简 Hook 式）、Jotai/Recoil（原子化）。
- Vue：Pinia（Vue 3 官方推荐，TS 友好、模块化）、Vuex（Vue 2 时代，mutation/action 分离）。
- 状态分层：组件本地状态 vs 全局共享状态 vs 服务端状态（React Query/TanStack Query）。
- 状态管理选型：项目规模、团队熟悉度、TypeScript 支持、 DevTools 生态。

## 组件设计与通信
- 组件通信：props/emit、provide/inject（跨层级）、事件总线、状态管理。
- 组件抽象：高阶组件（HOC）vs Render Props vs Hooks（React）、插槽（Slots）vs 作用域插槽（Vue）。
- 受控 vs 非受控组件：表单管理策略、`ref` 获取 DOM/组件实例。
- 性能优化：`React.memo`/`useMemo`/`useCallback`、Vue `v-once`/`v-memo`、虚拟列表（react-window/vue-virtual-scroller）。

## 路由与 SSR
- React Router：声明式路由、嵌套路由、路由守卫、懒加载（`React.lazy` + `Suspense`）。
- Vue Router：动态路由匹配、导航守卫（beforeEach/afterEach）、路由懒加载。
- SSR vs CSR vs SSG：SEO、首屏速度、服务器成本权衡。
- Next.js：SSR/SSG/ISR/App Router；Nuxt.js：服务端渲染与混合渲染。
- Hydration：SSR HTML + 客户端 JS 绑定事件，注水不匹配（hydration mismatch）排查。

## 前端工程化
- 构建工具：Vite（ESM 开发服务器 + Rollup 构建）vs Webpack（loader/plugin 生态）vs esbuild/swc。
- 代码规范：ESLint + Prettier、Husky + lint-staged（提交前检查）。
- 测试：Jest/Vitest（单元测试）、React Testing Library/Vue Test Utils（组件测试）、Playwright/Cypress（E2E）。
- 微前端：Module Federation、qiankun、single-spa，应用隔离与通信、样式隔离、公共依赖共享。
- 包管理：npm/yarn/pnpm，monorepo 方案（pnpm workspace / nx / Turborepo）。

## 性能优化
- Core Web Vitals：LCP（最大内容绘制 ≤2.5s）、FID/INP（交互延迟 ≤100ms）、CLS（布局偏移 ≤0.1）。
- 代码分割：路由级分割、组件级懒加载、预加载（`<link rel="preload">` / `<link rel="prefetch">`）。
- 图片优化：WebP/AVIF、响应式图片（srcset/sizes）、懒加载（loading="lazy"）、骨架屏。
- 虚拟列表：只渲染视口内元素，滚动时动态替换，适合大数据量列表。
- 内存泄漏排查：Chrome DevTools Memory 面板，堆快照对比、分配时间线、Detached DOM。

## 面试追问模板
- 从输入 URL 到页面渲染完成，中间经历了哪些步骤？
- 你的项目做过哪些性能优化？效果如何量化？
- React 的 Fiber 架构解决了什么问题？调度是怎么实现的？
- Vue 3 的 Proxy 响应式和 Vue 2 的 defineProperty 有什么本质区别？
- 大列表渲染卡顿怎么优化？虚拟列表的原理是什么？
- Promise 链中某个环节没 return，会发生什么？
- 如何定位线上页面的内存泄漏？

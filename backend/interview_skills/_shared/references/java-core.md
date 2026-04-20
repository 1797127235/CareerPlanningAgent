# Java 后端面试重点（Java 核心 + JVM + Spring + MySQL + Redis）

## Java 基础概念
- JVM/JDK/JRE 区别，字节码与"编译+解释"执行模型，AOT vs JIT。
- 8 种基本类型与包装类，自动装箱/拆箱与 Integer Cache（-128~127）。
- `==` vs `equals()`，`hashCode()` 与 `equals()` 一致性约束（重写必须同时重写）。
- 方法重载 vs 重写，静态分派与动态分派。
- 接口 vs 抽象类，Java 8+ default 方法的影响，Java 9+ private 接口方法。
- 深拷贝 vs 浅拷贝，`Cloneable` 接口与 `clone()` 方法，序列化方案。
- `final` 关键字：类（不可继承）、方法（不可重写）、变量（不可重新赋值）。

## String 与不可变性
- 不可变性原理（final byte[]），安全（HashMap key 安全）与性能（字符串常量池复用）影响。
- 字符串常量池：`intern()`、编译期优化、`new String("abc")` 创建对象数。
- `String` vs `StringBuilder` vs `StringBuffer`：不可变 vs 可变 vs 线程安全可变。
- Java 9+ Compact Strings：Latin-1 编码时一个字符占一个字节。

## 集合框架
- List：ArrayList（动态数组、扩容 1.5 倍）vs LinkedList（双向链表），RandomAccess 标记。
- Map：HashMap 底层（数组+链表+红黑树）、负载因子 0.75 与扩容、线程不安全场景。
- HashMap 长度为何是 2 的幂次方（位运算取模），多线程死循环问题（JDK 7 头插法）。
- ConcurrentHashMap：JDK 7 分段锁 vs JDK 8 CAS+synchronized，key/value 不为 null。
- Set：HashSet（基于 HashMap）、LinkedHashSet、TreeSet（红黑树）。
- Queue：BlockingQueue 接口，ArrayBlockingQueue vs LinkedBlockingQueue vs PriorityQueue。
- fail-fast vs fail-safe 机制：`ConcurrentModificationException` vs `CopyOnWriteArrayList`。

## Java 并发
- 线程生命周期与状态转换（NEW→RUNNABLE→BLOCKED/WAITING/TIMED_WAITING→TERMINATED）。
- 死锁：四个必要条件、检测（jstack/arthas）、预防策略（顺序加锁、超时获取）。
- JMM：可见性、有序性、happens-before；volatile 保证可见性+禁止重排序但不保证原子性。
- synchronized 底层原理（Monitor）、锁升级（偏向→轻量→重量）、偏向锁废弃（JDK 15+）。
- ReentrantLock vs synchronized：可中断、公平锁、Condition、超时获取、锁粒度更细。
- CAS 与 ABA 问题，Atomic 原理（Unsafe + CAS），AtomicStampedReference 解决 ABA。
- 线程池：核心参数（corePoolSize/maxPoolSize/queue/handler）、拒绝策略（Abort/CallerRuns/Discard）、动态配置。
- AQS 原理（state + CLH 队列），Semaphore/CountDownLatch/CyclicBarrier 实现与应用。
- ThreadLocal：原理、内存泄漏与弱引用、跨线程传递（TransmittableThreadLocal）。
- CompletableFuture：编排（thenCompose/thenCombine/allOf/anyOf）、异常处理、自定义线程池。
- 虚拟线程（Java 21）：轻量级线程、用途与调度模型、与线程池的区别。

## JVM 内存模型
- 运行时数据区：堆（新生代/老年代）、虚拟机栈、本地方法栈、方法区/元空间、程序计数器、直接内存。
- 对象创建流程：类加载检查→分配内存→初始化零值→设置对象头→执行构造方法。
- 对象内存布局：对象头（Mark Word + Class Pointer）+ 实例数据 + 对齐填充。
- 对象访问定位：句柄 vs 直接指针，HotSpot 使用直接指针。

## GC 垃圾回收
- GC 判断：引用计数 vs 可达性分析；四种引用（强/软/弱/虚）。
- GC 算法：标记-清除（碎片）、复制（Eden→Survivor）、标记-整理（老年代）、分代收集。
- 垃圾收集器：Serial→Parallel→CMS→G1→ZGC/Shenandoah，各自适用场景与演进。
- G1 回收流程（Young GC / Mixed GC / Full GC），ZGC 着色指针与读屏障、STW 时间 < 10ms。
- OOM 排查：Heap Dump、jmap/jstat/arthas、GC 日志分析、MAT 工具。
- GC 调优目标：低延迟（ZGC）vs 高吞吐（Parallel/G1）vs 低内存（Serial）。

## 类加载机制
- 类加载过程：加载→验证→准备→解析→初始化。
- 双亲委派模型：Bootstrap→Extension→Application ClassLoader，避免核心类被篡改。
- 打破双亲委派：SPI（JDBC/JNDI）、OSGi、线程上下文类加载器（Thread.setContextClassLoader）。
- 自定义类加载器：继承 ClassLoader，重写 findClass，实现热部署/类隔离。

## Spring IoC 与 Bean
- IoC 解决什么问题：解耦对象创建与依赖管理，控制反转 vs 依赖注入。
- `@Component` vs `@Bean`：声明方式、代理对象、第三方库集成。
- `@Autowired` vs `@Resource`：按类型 vs 按名称，优先级规则。
- 构造器注入 vs Setter 注入 vs 字段注入：不可变性、循环依赖、测试友好度。
- Bean 作用域（singleton/prototype/request/session），单例 Bean 线程安全分析。
- Bean 生命周期：实例化→属性注入→Aware→初始化（@PostConstruct/InitializingBean）→销毁。

## Spring AOP
- 核心概念：切面/切点/通知/连接点。
- Spring AOP vs AspectJ：JDK 动态代理 vs CGLIB vs 编译期织入，性能与功能差异。
- 通知类型：@Before/@After/@AfterReturning/@AfterThrowing/@Around。
- 同类内部调用 AOP 失效原因与解决方案（AopContext/exposeProxy/注入自身）。

## Spring 事务
- 声明式事务：@Transactional 属性（propagation/isolation/rollbackFor/readOnly/timeout）。
- 七种传播行为：REQUIRED/REQUIRES_NEW/NESTED/SUPPORTS/NOT_SUPPORTED/MANDATORY/NEVER。
- 事务失效场景：同类内部调用、非 public 方法、异常被吞、异步调用、自调用未走代理。
- 隔离级别：READ_UNCOMMITTED/READ_COMMITTED/REPEATABLE_READ/SERIALIZABLE，幻读与 MVCC。

## Spring Boot
- 自动配置原理：@SpringBootApplication→@EnableAutoConfiguration→spring.factories/AutoConfiguration.imports。
- 条件装配：@ConditionalOnClass/@ConditionalOnMissingBean/@ConditionalOnProperty 等。
- 配置文件加载优先级：properties > yaml > 环境变量 > 命令行参数，profile 机制。
- Spring Boot Starter 自定义：META-INF/spring.factories + @Configuration + @Conditional。

## MySQL 索引
- B+ 树为什么适合磁盘索引（有序、范围查询、叶子节点链表）。
- 覆盖索引与回表成本，联合索引最左前缀原则与索引下推（ICP）。
- 索引失效场景：函数转换、隐式类型转换、OR、LIKE 前缀通配、非最左列、!=/<>。
- EXPLAIN 执行计划：type（system→const→eq_ref→ref→range→index→ALL）、key、Extra。

## MySQL 事务与锁
- ACID 含义，事务隔离级别与各自解决的问题。
- InnoDB 默认 RR，通过 MVCC + Next-Key Lock 解决幻读。
- MVCC 原理：隐藏列（trx_id/roll_pointer）、Undo Log 版本链、ReadView 可见性判断。
- 当前读 vs 快照读，RR 下当前读仍加间隙锁。
- 锁机制：表级锁 vs 行级锁，行锁（Record/Gap/Next-Key），意向锁（IS/IX）。
- 死锁检测与避免：按固定顺序加锁、缩短事务、降低隔离级别、死锁超时。

## MySQL 性能优化
- 慢 SQL 定位：slow_query_log、pt-query-digest、EXPLAIN 分析。
- 分库分表策略：垂直拆分（按业务）vs 水平拆分（按 key），ShardingSphere 中间件。
- 深度分页优化：游标分页（where id > ? limit）、延迟关联、子查询先查主键。
- 读写分离：主库写从库读，主从延迟处理（延迟阈值、强制走主库）。

## Redis 数据类型
- 五种基础类型：String/Hash/List/Set/ZSet，各类型底层编码与适用场景。
- 特殊类型：Bitmap（活跃统计）、HyperLogLog（UV 去重）、Stream（消息队列）、GeoHash。
- ZSet 底层为什么用跳表而不是红黑树/B+树（范围查询、实现简单、内存灵活、按 score 排序）。

## Redis 持久化与线程模型
- RDB（fork + COW 快照）vs AOF（写后日志、fsync 策略 always/everysec/no），混合持久化（RDB+AOF）。
- Redis 6.0 前单线程模型（避免锁竞争、IO 多路复用），6.0 后多线程 IO（命令执行仍单线程）。
- 内存淘汰策略：allkeys-lru/volatile-lru/allkeys-random/volatile-ttl/noeviction。

## Redis 生产问题
- 缓存穿透（布隆过滤器/空值缓存）、缓存击穿（互斥锁/逻辑过期）、缓存雪崩（随机过期/多级缓存）。
- 缓存与数据库一致性：延迟双删、Canal 监听 Binlog、最终一致性方案。
- 分布式锁：`SET key value NX EX` 基本实现，误删问题与 Lua 原子释放。
- Redisson 可重入锁原理（Hash 结构 + Lua 脚本），看门狗续期机制。
- BigKey 检测与拆分（redis-cli --bigkeys、UNLINK 异步删除），HotKey 本地缓存 + 热点分散。

## 面试追问模板
- 这个机制底层是怎么实现的？有什么性能代价？
- 多线程环境下会有什么问题？如何保证线程安全？
- 框架（Spring/MyBatis）中哪里用到了这个机制？
- 线上遇到 OOM/GC 频繁怎么排查？参数怎么调？
- @Transactional 标在 private 方法上会生效吗？为什么？
- 如何自定义一个 Spring Boot Starter？
- 这条 SQL 走了什么索引？能否优化？
- 如果 Redis 宕机，业务怎么降级？

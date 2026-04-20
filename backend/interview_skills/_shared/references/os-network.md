# 操作系统与网络面试知识点

### 进程与线程
进程是资源分配单位，线程是调度单位。Linux 中 fork 创建新进程（COW 写时复制），clone 创建线程共享地址空间。上下文切换保存/恢复寄存器、程序计数器、内核栈。线程池避免频繁创建销毁线程，参数设计：核心线程数、最大线程数、队列长度、拒绝策略。线程局部存储（TLS）。

### 内存管理
虚拟内存通过页表映射到物理内存，TLB 缓存近期页表项加速转换。缺页中断处理：分配物理页、磁盘换入、更新页表。内存分配器 ptmalloc/tcmalloc/jemalloc 减少碎片、提高并发分配效率。大页（HugePage）减少 TLB miss。内存映射（mmap）原理与应用。

### 进程间通信 IPC
管道（pipe）半双工，父子进程间；消息队列内核维护，适合小数据；共享内存最快，需配合信号量同步；信号量用于进程/线程同步；Unix Domain Socket 本地高效通信；网络 Socket 跨主机通信。POSIX 共享内存（shm_open）与 System V 共享内存（shmget）对比。

### TCP 三次握手与四次挥手
三次握手：SYN → SYN-ACK → ACK，防止历史连接初始化、同步序列号。四次挥手：FIN → ACK → FIN → ACK，主动关闭方进入 TIME_WAIT（2MSL），确保最后一个 ACK 被收到、避免旧连接报文干扰新连接。SYN 洪水攻击与 SYN Cookie 防御。

### TCP 拥塞控制与流量控制
拥塞控制：慢启动、拥塞避免、快重传、快恢复，拥塞窗口 cwnd 动态调整。流量控制：接收窗口 rwnd，防止发送方淹没接收方。滑动窗口协议实现可靠传输与流水线发送。BBR 拥塞控制算法（基于带宽和 RTT 测量）。

### Socket 编程模型
阻塞 IO：简单但线程数随连接数增长；非阻塞 IO：轮询消耗 CPU；IO 多路复用：select（fd 上限 1024，遍历检查）、poll（无上限，仍需遍历）、epoll（事件驱动，O(1) 注册/触发，LT/ET 模式）。Reactor 同步非阻塞（单线程/多线程/主从多线程），Proactor 异步 IO（Windows IOCP）。

### 高性能网络与零拷贝
零拷贝：sendfile 内核态直接传输文件到 socket，避免用户态内核态来回拷贝；mmap 用户态直接访问内核缓冲区；splice 管道零拷贝；DPDK 用户态轮询网卡绕过内核协议栈；io_uring 异步 IO 接口，批量提交减少系统调用开销。

### 并发同步机制
互斥锁（mutex）保护临界区，自旋锁（spinlock）适合短临界区（避免上下文切换开销）；读写锁（shared_mutex/pthread_rwlock）读并发写独占；条件变量配合 mutex 实现等待/通知；原子操作（atomic）实现无锁算法，内存序（memory_order）控制可见性与重排序。RCU（Read-Copy-Update）读多写少场景。

### 文件系统与 IO
VFS 抽象层统一文件系统接口；页缓存（Page Cache）减少磁盘访问，预读（readahead）策略；fsync/msync 强制刷盘保证持久性；direct IO 绕过页缓存，适合数据库等自管理缓存场景。IO 调度算法（CFQ/Deadline/NOOP）。

### 进程调度
Linux CFS（Completely Fair Scheduler）完全公平调度器，红黑树管理运行队列，vruntime 决定调度顺序。实时调度策略（SCHED_FIFO/SCHED_RR）与普通调度（SCHED_NORMAL）。CPU 亲和性（affinity）绑定进程到特定核心。NUMA 架构下的本地内存访问优化。

### 死锁与排查
死锁四个必要条件：互斥、占有且等待、不可抢占、循环等待。预防策略：破坏任一条件（资源一次性分配、按序申请、允许抢占）。检测：资源分配图、银行家算法。排查工具：pstack、gdb、/proc 文件系统查看线程状态。

### 网络分层模型
OSI 七层 vs TCP/IP 四层。数据链路层（MAC 地址、ARP、MTU/MSS）、网络层（IP、ICMP、路由）、传输层（TCP/UDP）、应用层（HTTP/DNS/FTP）。NAT 网络地址转换原理。iptables/netfilter 防火墙规则链。

### UDP 与可靠 UDP
UDP 无连接、无拥塞控制、低延迟，适合视频流、DNS、游戏状态同步。QUIC 基于 UDP 实现可靠传输（0-RTT、连接迁移、无队头阻塞）。KCP 协议：以牺牲带宽换低延迟，适合实时游戏。

### HTTP 协议演进
HTTP/1.0 短连接、HTTP/1.1 持久连接与管线化（pipelining，存在队头阻塞）、HTTP/2 二进制分帧+多路复用+头部压缩（HPACK）+服务器推送、HTTP/3 QUIC。RESTful API 设计原则。GraphQL 与 REST 对比。

### HTTPS 与安全
TLS/SSL 握手：ClientHello→ServerHello→证书→密钥交换→Finished。证书链验证（根 CA→中间 CA→服务器证书）。前向保密（Forward Secrecy，ECDHE）。TLS 1.3 改进（1-RTT/0-RTT、握手简化）。证书透明度（CT）、OCSP  stapling。

### DNS 解析
递归查询 vs 迭代查询。DNS 缓存层级：浏览器缓存→OS 缓存→hosts→本地 DNS→根 DNS→顶级域 DNS→权威 DNS。DNS 负载均衡（一个域名解析到多个 IP）。DNS 劫持与 DNS over HTTPS（DoH）。CDN 原理：DNS 解析到最近边缘节点。

### 负载均衡
四层负载均衡（LVS：NAT/DR/TUN 模式，基于 IP+端口）vs 七层负载均衡（Nginx/HAProxy，基于 URL/Header/Cookie）。负载均衡算法：轮询、加权轮询、最少连接、源地址哈希、一致性哈希。健康检查机制（主动探测/被动观察）。

### 网络故障排查
ping（ICMP 连通性）、traceroute（路由追踪）、netstat/ss（连接状态）、tcpdump/wireshark（抓包分析）、curl（HTTP 诊断）。MTU 问题、TCP 窗口满、连接数耗尽（TIME_WAIT 过多）排查。SS 命令替代 netstat，更快更全。

### 容器网络
Docker 网络模式：bridge（默认 NAT）、host（共享宿主机网络）、none（无网络）、container（共享另一个容器网络）。veth pair 连接容器与网桥。CNI（Container Network Interface）插件：Flannel（UDP/VXLAN/host-gw）、Calico（BGP）、Cilium（eBPF）。

### eBPF 与网络可观测性
eBPF 内核可编程框架：无需修改内核代码即可注入程序。应用场景：网络过滤（XDP 高性能数据包处理）、跟踪（kprobe/uprobe）、安全（seccomp 增强）。Cilium 基于 eBPF 实现服务网格替代 sidecar 方案。

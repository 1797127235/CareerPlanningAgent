# C++ 语言核心面试知识点

### C++11 右值引用与移动语义
右值引用（`T&&`）允许识别临时对象，移动构造函数/移动赋值运算符转移资源所有权而非拷贝。std::move 将左值转为右值引用，std::forward 实现完美转发。移动语义显著减少大对象的深拷贝开销，是 STL 容器性能提升的关键。

### 智能指针原理
unique_ptr 独占所有权，零开销抽象，支持自定义删除器；shared_ptr 基于引用计数，控制块存储强/弱引用计数，线程安全（原子操作）；weak_ptr 观察但不增加强引用计数，用于打破循环引用。循环引用导致内存泄漏，需用 weak_ptr 断开。make_shared/make_unique 的优势（单次分配、异常安全）。

### RAII 与资源管理
资源获取即初始化，构造函数获取资源，析构函数释放资源。lock_guard/unique_lock 是 RAII 的典型应用。异常安全级别：基本保证、强保证、不抛异常保证。NOEXCEPT 优化与强异常安全的关系。ScopeGuard 模式实现。

### STL 容器原理
vector 连续内存，扩容因子通常 2 倍，涉及重新分配与元素移动；list 双向链表，支持 O(1) 插入删除；deque 分段连续数组，头尾插入 O(1)；unordered_map 开链法处理哈希冲突，负载因子触发 rehash。emplace vs insert 的区别（原地构造避免拷贝）。

### 红黑树与有序容器
map/set 基于红黑树，自平衡二叉搜索树，保证 O(log n) 查找/插入/删除。红黑树性质：根黑、叶黑（NIL）、红节点子必黑、任一节点到叶路径黑节点数相同。与 AVL 树的区别（红黑树插入删除旋转更少，查询稍慢）。

### 模板元编程与 SFINAE
SFINAE（替换失败不是错误）用于编译期条件重载；type traits（is_integral、enable_if 等）在编译期推导类型属性；CRTP（奇异递归模板模式）实现静态多态，避免虚函数开销。C++20 concept 替代 enable_if 的写法。

### 虚函数与多态机制
虚函数通过 vtable（虚函数表）实现动态绑定，每个多态类一个 vtable，每个对象一个 vptr。纯虚函数使类成为抽象类。虚析构函数确保通过基类指针 delete 派生类对象时正确析构。多继承下的虚函数表布局（多个 vptr）。

### C++17/20 新特性
C++17：结构化绑定、if constexpr、折叠表达式、inline variables、std::optional/variant/string_view、并行算法。C++20：concept 约束模板、ranges、coroutine、modules、three-way comparison（<=>）、jthread、std::format。

### 内存模型与对齐
栈自动管理，堆需手动 new/delete 或智能指针；new/delete 调用构造/析构函数，malloc/free 不调用；内存对齐影响 CPU 访问效率，alignas/alignof 控制对齐；内存屏障与原子操作保证多线程内存序。placement new 在已分配内存上构造对象。

### 编译链接过程
预处理（宏展开、头文件包含）、编译（生成汇编）、汇编（生成目标文件）、链接（符号解析与重定位）。模板编译为每个实例化生成独立代码，导致代码膨胀。动态库运行时加载，PIC（位置无关代码）支持共享。静态库 vs 动态库选型。

### Lambda 表达式
捕获列表（值捕获/引用捕获/隐式捕获/初始化捕获）、mutable 修改拷贝、泛型 Lambda（C++14 auto 参数）。Lambda 底层实现（编译器生成匿名类，operator()）。与 std::function 的关系（类型擦除）。

### 类型推导与 auto/decltype
auto 类型推导规则（值退化）、decltype 保留引用和 cv 限定符、decltype(auto)（C++14）。Trailing return type（-> decltype()）用于模板函数返回值推导。auto& 与 auto 的区别（引用折叠）。

### 拷贝控制五法则
拷贝构造函数、拷贝赋值运算符、移动构造函数、移动赋值运算符、析构函数。Rule of Zero（全部默认）vs Rule of Five（自定义任一就定义全部）。=default 与 =delete 的使用场景。

### 多态与 RTTI
dynamic_cast（安全向下转型，运行时检查）、static_cast（编译期检查）、reinterpret_cast、const_cast。typeid 与 type_info，RTTI 开销与禁用（-fno-rtti）。虚继承解决菱形继承问题（重复基类子对象）。

### 异常处理机制
try/catch/throw，栈展开（stack unwinding）过程中调用析构函数。异常规格说明（C++11 起 deprecated）。noexcept 修饰符与移动语义（vector 扩容优先调用 noexcept 移动构造）。std::exception 层次结构。

### 标准库算法
STL 算法分类：非修改式（find/count/for_each）、修改式（copy/transform/replace）、排序（sort/partial_sort/nth_element）、二分搜索（lower_bound/upper_bound/equal_range）、集合操作（set_union/set_intersection）、堆操作（make_heap/push_heap/pop_heap）。

### 迭代器与标签
输入迭代器、输出迭代器、前向迭代器、双向迭代器、随机访问迭代器、连续迭代器（C++17）。迭代器适配器（reverse_iterator、back_insert_iterator、move_iterator）。迭代器失效规则（vector 插入/删除、list/map 删除）。

### 命名空间与 ADL
命名空间嵌套、using 声明 vs using 指令、匿名命名空间（内部链接）。ADL（Argument-Dependent Lookup，Koenig 查找）：根据参数类型所在命名空间查找函数。ADL 在运算符重载中的应用。

### 运算符重载
可重载与不可重载的运算符。运算符重载为成员函数 vs 非成员函数（对称性）。++a 与 a++ 的区别（前置返回引用，后置返回拷贝）。流插入/提取运算符（<<、>>）通常实现为非成员函数。类型转换运算符（operator T()）。

### 对象模型
C++ 对象内存布局：非静态成员变量 + vptr（如有虚函数）+ 填充对齐。空基类优化（Empty Base Optimization，EBO）。POD（Plain Old Data）类型与 trivial 类型。对象切片问题（Object Slicing）。

### 多线程与并发（C++11 起）
std::thread、join/detach、线程 ID。mutex（recursive_mutex/timed_mutex）、lock_guard/unique_lock/scope_lock（C++17）。条件变量（condition_variable）与虚假唤醒（spurious wakeup）。future/promise/async 异步任务模型。原子操作（atomic）与内存序（memory_order_relaxed/acquire/release/seq_cst）。

### 自定义分配器
allocator 接口：allocate/deallocate/construct/destroy。自定义内存池分配器减少碎片、提高缓存局部性。STL 容器支持自定义分配器（模板参数）。pmr（Polymorphic Memory Resources，C++17）多态内存资源。

### 设计模式在 C++ 中的实现
单例模式（Meyer's Singleton、DCL、atomic）、工厂模式、观察者模式（信号槽）、策略模式、RAII/ScopeGuard、PIMPL（Pointer to Implementation，编译防火墙）、CRTP 静态多态。

### 字符串处理
std::string 的 SSO（Short String Optimization，小字符串优化）。string_view（C++17）避免拷贝，但需注意生命周期。C 风格字符串与 std::string 的转换。格式化输出：iostream vs sprintf vs std::format（C++20）。

### 文件与 IO
iostream 体系：istream/ostream/iostream、ifstream/ofstream/fstream。格式化 vs 非格式化 IO。缓冲区刷新（flush/endl/'
' 的区别）。内存流（stringstream/istringstream/ostringstream）。文件系统库（filesystem，C++17）。

### 时间库（C++11 chrono）
steady_clock（单调时钟，适合计时）vs system_clock（系统时钟，可转换到 time_t）。duration 与 time_point 的运算。std::this_thread::sleep_for/sleep_until。C++20 日历和时区支持。

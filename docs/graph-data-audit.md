# Graph 数据审查清单

## 一、计划砍掉的 18 个节点

### 工具/框架节点（14个）— 不是职业方向，是技能
| node_id | label | rp | hal | 当前zone | 砍掉原因 |
|---------|-------|----|-----|----------|----------|
| react | React 工程师 | 48.0 | 61.6 | transition | 被devops/frontend等职业节点覆盖 |
| vue | Vue 工程师 | 48.0 | 61.6 | transition | 被devops/frontend等职业节点覆盖 |
| angular | Angular 工程师 | 48.0 | 61.6 | transition | 被devops/frontend等职业节点覆盖 |
| nodejs | Node.js 工程师 | 36.5 | 70.8 | transition | 被devops/frontend等职业节点覆盖 |
| docker | Docker 工程师 | 33.7 | 83.0 | safe | 被devops/frontend等职业节点覆盖 |
| kubernetes | Kubernetes 工程师 | 29.6 | 86.3 | safe | 被devops/frontend等职业节点覆盖 |
| linux | Linux 工程师 | 32.3 | 84.2 | safe | 被devops/frontend等职业节点覆盖 |
| redis | Redis 工程师 | 31.0 | 75.2 | thrive | 被devops/frontend等职业节点覆盖 |
| terraform | Terraform/IaC 工程师 | 33.7 | 83.0 | safe | 被devops/frontend等职业节点覆盖 |
| aws | 云平台工程师 | 28.2 | 87.4 | safe | 被devops/frontend等职业节点覆盖 |
| spring-boot | Spring Boot 工程师 | 28.8 | 77.0 | thrive | 被devops/frontend等职业节点覆盖 |
| mongodb | MongoDB 工程师 | 31.8 | 74.6 | thrive | 被devops/frontend等职业节点覆盖 |
| elasticsearch | Elasticsearch 工程师 | 31.0 | 75.2 | thrive | 被devops/frontend等职业节点覆盖 |
| graphql | GraphQL 工程师 | 34.6 | 72.3 | thrive | 被devops/frontend等职业节点覆盖 |

### 语言节点（4个）— 被其他职业节点覆盖
| node_id | label | rp | hal | 当前zone | 砍掉原因 |
|---------|-------|----|-----|----------|----------|
| kotlin | Kotlin 工程师 | 28.8 | 77.0 | thrive | → android覆盖 |
| php | PHP 工程师 | 63.9 | 48.9 | danger | 市场萎缩不适合推荐 |
| javascript | JavaScript 工程师 | 40.3 | 67.8 | transition | → frontend覆盖 |
| typescript | TypeScript 工程师 | 38.4 | 69.3 | thrive | → frontend覆盖 |

## 二、保留的 40 个节点（含 zone 重算）

zone 公式: safety_score = (100-rp)*0.5 + hal*0.5, safe>=75 / thrive>=65 / transition>=55 / danger<55

| node_id | label | rp | hal | score | 当前zone | 新zone | 变更? |
|---------|-------|----|-----|-------|----------|--------|-------|
| frontend | 前端工程师 | 48.0 | 61.6 | 56.8 | transition | transition |  |
| full-stack | 全栈工程师 | 38.4 | 69.3 | 65.5 | thrive | thrive |  |
| devops | DevOps 工程师 | 33.7 | 83.0 | 74.7 | safe | thrive | YES |
| devsecops | DevSecOps 工程师 | 41.2 | 77.0 | 67.9 | safe | thrive | YES |
| android | Android 工程师 | 28.8 | 77.0 | 74.1 | thrive | thrive |  |
| ios | iOS 工程师 | 28.8 | 77.0 | 74.1 | thrive | thrive |  |
| flutter | Flutter 工程师 | 28.8 | 77.0 | 74.1 | thrive | thrive |  |
| react-native | React Native 工程师 | 38.4 | 69.3 | 65.5 | transition | thrive | YES |
| game-developer | 游戏客户端工程师 | 28.8 | 77.0 | 74.1 | thrive | thrive |  |
| server-side-game-developer | 游戏服务端工程师 | 28.8 | 87.0 | 79.1 | safe | safe |  |
| ai-engineer | AI 工程师 | 31.4 | 74.9 | 71.8 | thrive | thrive |  |
| machine-learning | 机器学习工程师 | 34.0 | 72.8 | 69.4 | thrive | thrive |  |
| ai-data-scientist | AI 数据科学家 | 46.1 | 63.1 | 58.5 | transition | transition |  |
| ai-agents | AI Agent 工程师 | 32.5 | 84.0 | 75.8 | safe | safe |  |
| mlops | MLOps 工程师 | 33.9 | 82.9 | 74.5 | safe | thrive | YES |
| data-analyst | 数据分析师 | 44.8 | 64.2 | 59.7 | transition | transition |  |
| data-engineer | 数据工程师 | 43.3 | 65.4 | 61.1 | thrive | transition | YES |
| bi-analyst | BI 分析师 | 43.8 | 65.0 | 60.6 | transition | transition |  |
| cyber-security | 网络安全工程师 | 48.6 | 61.1 | 56.2 | transition | transition |  |
| ai-red-teaming | AI 安全工程师 | 41.3 | 77.0 | 67.8 | safe | thrive | YES |
| blockchain | 区块链工程师 | 27.0 | 78.4 | 75.7 | thrive | safe | YES |
| qa | 测试工程师 | 51.9 | 58.5 | 53.3 | danger | danger |  |
| software-architect | 软件架构师 | 24.3 | 90.6 | 83.2 | safe | safe |  |
| engineering-manager | 工程经理 | 15.6 | 95 | 89.7 | safe | safe |  |
| product-manager | 产品经理 | 23.8 | 81.0 | 78.6 | thrive | safe | YES |
| technical-writer | 技术文档工程师 | 31.1 | 75.1 | 72.0 | danger | thrive | YES |
| devrel | 开发者关系工程师 | 31.5 | 74.8 | 71.7 | thrive | thrive |  |
| ux-design | UX 设计师 | 24.9 | 80.1 | 77.6 | thrive | safe | YES |
| cpp | C++ 工程师 | 24.5 | 90.4 | 83.0 | safe | safe |  |
| java | Java 工程师 | 28.8 | 77.0 | 74.1 | thrive | thrive |  |
| python | Python 工程师 | 35.7 | 71.4 | 67.8 | thrive | thrive |  |
| golang | Go 工程师 | 26.1 | 89.1 | 81.5 | safe | safe |  |
| rust | Rust 工程师 | 24.5 | 90.4 | 83.0 | safe | safe |  |
| postgresql-dba | 数据库工程师 | 33.1 | 73.5 | 70.2 | thrive | thrive |  |
| cto | 技术总监/CTO | 13.8 | 95 | 90.6 | safe | safe |  |
| data-architect | 数据架构师 | 57.9 | 53.7 | 47.9 | transition | danger | YES |
| qa-lead | 测试架构师 | 51.9 | 58.5 | 53.3 | transition | danger | YES |
| ml-architect | AI/ML 架构师 | 34.0 | 82.8 | 74.4 | safe | thrive | YES |
| security-architect | 安全架构师 | 48.6 | 71.1 | 61.2 | safe | transition | YES |
| cloud-architect | 云架构师 | 19.9 | 94.1 | 87.1 | safe | safe |  |

## 三、需要人工复核的 AEI 数据

以下节点的 replacement_pressure 看起来不合理：
| node_id | label | rp | 疑点 |
|---------|-------|----|------|
| data-architect | 数据架构师 | 57.9 | 架构师级别应该难被替代，rp偏高，可能O*NET映射到了普通DBA |
| security-architect | 安全架构师 | 48.6 | 安全架构是高级别角色，rp偏高 |
| qa-lead | 测试架构师 | 51.9 | 与qa完全相同的rp，没区分lead和普通 |
| cyber-security | 网络安全工程师 | 48.6 | 安全行业增长快，rp偏高 |

## 四、边的影响
- 当前总边数: 118
- 删除边数: 39
- 保留边数: 79

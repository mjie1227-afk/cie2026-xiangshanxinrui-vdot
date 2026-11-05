# 测试与基准应用

各目录包含实际使用的 C 检查器、汇编和 AM Makefile。将应用放入锁定版本 nexus-am 的 `apps/` 后编译；[源码准备工具](../tools/prepare_sources.py)会执行这一复制步骤。

| 应用 | 用途 | 保存记录中的规模 |
| --- | --- | --- |
| hello-meijie | 个性化 Hello | 固定打印历史 IP 与姓名 |
| vadd4 | 第一阶段向量加法 | [1,2,3,4]+[10,20,30,40] |
| vdot-smoke | 正数、负数、极值与特殊配置 | 7 例 |
| vdot-exceptions | 配置/权限与精确异常 | 64 例，62 陷阱＋2 合法对照 |
| vdot-overlap | 源、目的、掩码寄存器重叠 | 60 例 |
| vdot-deps | 依赖场景 | 48 例 |
| vdot-mixed | 混发场景 | 32 例 |
| vdot-cancel-csr | 分支取消与精确异常 | 40 例 |
| vdot-port-contend-v1 | 发射前共享端口定向程序 | 原记录中的指定实例 |
| vdot-rvv-equiv-v1 | 两条 RVV 基线等价检查 | 144 配置、432 调用 |
| vdot-timing-pilot-v1 | 计时预检 | 6 预热、36 正式样本 |
| vdot-chain-v1 | 完整操作依赖链 | 10 预热、30 正式样本 |
| vdot-throughput-v1 | 八路批处理 | 10 预热、30 正式样本 |
| vdot-e2e-v1 | 逐点完整输出小数组 | 10 预热、30 正式样本 |
| vdot-segment-v1 | G8/G16 分段点积 | 13 预热、39 正式样本 |
| vdot-load-v1 | tu/ta/ta_rr 加载对照 | 35 预热、63 正式样本 |
| vdot-tile-v1 | 2×2 输入复用 | 25 预热、45 正式样本 |

每个程序以自身检查器打印的完整 PASS 标记判定应用结果，并同时核对 DiffTest、GOOD TRAP 和进程退出码。运行方法见[复现步骤](../REPRODUCE.md)，历史日志和统计见[证据索引](../evidence/index.md)。

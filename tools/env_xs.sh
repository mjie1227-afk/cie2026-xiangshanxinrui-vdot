#!/usr/bin/env bash
# 在服务器的作品仓库根目录执行：source tools/env_xs.sh
# 复用 mj/xiangshan 的 Mill、Verilator，以及系统已安装的 Clang 19、JDK 21。
export PATH="/root/private_data/mj/xiangshan/tools/mill-0.12.3:/root/private_data/mj/xiangshan/tools/verilator-5.052/bin:/usr/lib/llvm-19/bin:/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH"

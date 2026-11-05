# 编译环境

评审操作统一见[复现指南](../REPRODUCE.md)。Windows使用Docker Desktop的Linux容器模式，Linux使用Docker Engine；宿主机安装Python 3.9或更新版本。

`Dockerfile`以Ubuntu 24.04为基础，安装JDK 21、Mill 0.12.3、Verilator 5.052、Clang 19、RISC-V GCC 12，以及Flex头文件、GNU time、SQLite开发库等依赖。首次搭建和编译需联网下载，后续可复用缓存。

Windows使用`python tools/container.py`，Linux使用`python3 tools/container.py`，按下列阶段逐步执行：

```text
image → init → check → build → smoke → functional → performance → collect
```

源码复制到独立Linux工作目录后完成编译和仿真，结果通过`collect`导出到宿主机。环境检查会显示工具版本并执行小型编译运行测试。资源要求、操作命令及成功标志见[复现指南](../REPRODUCE.md)。

## 验证材料

- [环境检查与应用编译记录](../evidence/package-checks/docker-20261103/summary.json)
- [已验证环境的软件版本](../evidence/package-checks/docker-20261103/package-versions.txt)
- [环境镜像构建日志](../evidence/package-checks/docker-20261103/image-build.log)
- [整核构建与三组验收记录](../evidence/package-checks/fullcore-local-20261103/summary.json)

基础3/3、功能10/10、性能7/7已实测通过，具体检查范围和原始日志入口见[验证说明](../VALIDATION.md)。

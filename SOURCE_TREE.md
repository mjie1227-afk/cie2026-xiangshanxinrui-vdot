# 完整源码与版本

`src/`提供已应用本项目修改的完整工程源码，以及当前构建使用的依赖。下载作品仓库后可以直接阅读实现；`tools/prepare_sources.py`在仓库的`work/build/`下生成可编译的Linux工作目录，恢复权限与符号链接，不需要下载上游或再应用补丁。

| 工程 | 源码入口 | 锁定基线 |
|---|---|---|
| XiangShan | [src/XiangShan](src/XiangShan/) | `16ae9ddcda54fc9a2fddffad73174cf793ac7814`＋VDot与mtval修复 |
| NEMU | [src/NEMU](src/NEMU/) | `a48a11f208ff81ad765591d83271d1b339fb3861`＋VDot参考模型 |
| nexus-am | [src/nexus-am](src/nexus-am/) | `086a238062fdfb3281b745a537b361983d0154b5` |
| 应用 | [apps](apps/README.md) | 17个Hello/VADD、功能、等价与性能应用 |

源码包含21个锁定版本的工程及依赖目录，共4744个上游/项目源文件条目，另有6个构建信息文件。XiangShan依赖包括coupledL2、DiffTest、fudian、huancun、OpenLLC/OpenNCB、rocket-chip/cde/hardfloat、OpenAIA、utility、YunSuan以及构建资源使用的ready-to-run。NEMU的SoftFloat、nanopb、LibCheckpoint及恢复代码也在仓库内。详细版本见[upstream-lock.json](configs/upstream-lock.json)。

上游部分依赖还登记了供其独立开发或单独测试使用的子模块。这些不参与本项目顶层构建的路径在[source-tree.json](configs/source-tree.json)的`unused_upstream_gitlinks`中列明；本项目实际构建所需的依赖已展开，不执行上游的递归更新命令。

## Windows 与 Linux 的文件形式

为了兼容Windows下载与Git检出，上游`.gitignore`、`.gitattributes`在`src/`内以`.upstream`后缀保存，防止上游忽略规则漏掉提交文件。23个符号链接在可移植目录中保存链接目标文本。准备脚本按[source-tree.json](configs/source-tree.json)恢复原文件名、链接和执行权限，再复制NEMU配置及17个应用。

`src/`是交付源码，`work/build/`是实际编译目录。构建生成的RTL、对象文件、emu和应用镜像均留在`work/`，不与交付源码混在一起。

## 补丁与构建适配

原始实现补丁仍保留：[XiangShan-full.patch](patches/XiangShan-full.patch)、[NEMU.patch](patches/NEMU.patch)。19个实现文件的检查记录保存在[source-snapshots.json](configs/source-snapshots.json)；上述修改已包含在源码中，无需再次应用补丁。

交付目录另有三处构建适配：XiangShan的`build.sc`与`Makefile`改为读取仓库保存的版本和DiffTest文件清单；NEMU的`git.mk`关闭教学模板中的自动Git提交。这样，解压目录在没有嵌套`.git`的情况下也能准备构建。适配不改变VDot或NEMU指令语义，具体差异见[source-package-build.patch](patches/source-package-build.patch)，原文件在[configs/upstream-build](configs/upstream-build/)。

运行工具显式连接`work/build/NEMU/build/riscv64-nemu-interpreter-so`；`ready-to-run`用于上游构建资源打包。

上游版权、许可文件和源码头部说明保留在各工程内。源码准备可以离线执行；编译需要已安装的编译器、JDK、Mill以及Scala/Maven等工具依赖，首次缺少缓存时由构建工具取得依赖。

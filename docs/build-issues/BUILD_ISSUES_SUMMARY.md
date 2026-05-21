# Photonicat2 LEDE Build 问题汇总

> Build 24–35 | LEDE coolsnowwolf 20251001 + RK3576 | Zenbook 本地编译

---

## 目录

1. [问题一览](#问题一览)
2. [根因分析与修复](#根因分析与修复)
3. [修复记录](#修复记录)
4. [关键发现](#关键发现)

---

## 问题一览

| Build | 阶段 | 错误 | 根因 | 状态 |
|-------|------|------|------|------|
| 26–28 | kernel modules | `analogix_dp.ko` 打包找不到 | Photonicat2 RK3576 无 Analogix DP 硬件，DTS 用 HDMI via HDPTX | ✅ 已修复 |
| 29 | kernel modules | `dw-mipi-dsi.ko` 被当作字面路径 | LEDE 不支持 FILES 中的 `@CONFIG_*` 条件语法 | ✅ 已修复 |
| 30 | kernel modules | `drm_dp_aux_bus.ko` 等 DRM 模块缺失 | 版本条件 `@ge6.12` / `@lt5.19` 同样被当字面路径 | ✅ 已修复 |
| 31 | kernel modules | `CONFIG_DRM_DP_AUX_BUS` 丢失 | config symbol 名称错误，应为 `CONFIG_DRM_DISPLAY_DP_AUX_BUS` | ✅ 已修复 |
| 32 | kernel modules | config-6.12 被截断为 860 行 | patch 工具意外将 10677 行配置截断 | ✅ 已恢复 |
| 33 | kernel modules | `hwmon-core` 找不到 `i2c-core.ko` | `hwmon.ko` 运行时依赖 `i2c-core`，但 `hwmon.mk` 未声明 `DEPENDS` | ✅ 已修复 |
| 34 | toolchain | `make dirclean` 后 toolchain 编译失败 | 同上，dirclean 清除缓存后复现 | ✅ 已修复 |
| 34 | uboot | U-Boot patch 3 个 hunk 失败 | board.c / Kconfig / Makefile 的 context 与 U-Boot 2026.01 不匹配 | ✅ 已修复 |

---

## 根因分析与修复

### 1. FILES 条件语法（`@CONFIG_*` / `@ge6.12` / `@lt5.19`）

**问题现象：**

```makefile
# modules.mk 中的写法：
FILES_$(CONFIG_ROCKCHIP_ANALOGIX_DP)+= \
    $(KERNEL_MODULES_PATH)/analogix_dp.ko@CONFIG_ROCKCHIP_ANALOGIX_DP
```

LEDE 构建时将 `analogix_dp.ko@CONFIG_ROCKCHIP_ANALOGIX_DP` 当作字面文件路径，导致报错 "cannot find analogix_dp.ko@CONFIG_ROCKCHIP_ANALOGIX_DP"。

**根因：** LEDE 的 `package-metadata.pl` 中 `@` 条件语法仅用于 `DEPENDS` 和 `PACKAGES` 字段，不适用于 `FILES`。`FILES` 中的 `@` 被原样传递给构建系统，当作路径字面量处理。

**修复：** 直接移除 FILES 中的条件后缀，依赖 `KCONFIG` 行强制设置内核配置选项：

```makefile
# 修复前（不工作）：
FILES_$(CONFIG_FOO) += $(KERNEL_MODULES_PATH)/foo.ko@CONFIG_FOO

# 修复后（正确）：
# 不在 FILES 中使用条件，通过 KCONFIG 强制启用 =y 来确保编译
KCONFIG += CONFIG_FOO=y
```

### 2. config symbol 名称错误

**问题：** 多次遇到 `CONFIG_DRM_DP_AUX_BUS` 在内核 .config 中丢失。

**根因：** 实际的 config symbol 名称是 `CONFIG_DRM_DISPLAY_DP_AUX_BUS`，不是 `CONFIG_DRM_DP_AUX_BUS`。

**修复：** 确认正确的 config symbol 名称后添加到 `target/linux/rockchip/armv8/config-6.12`。

### 3. hwmon-core 依赖 i2c-core 但未声明

**问题现象：**

```
ERROR: module 'hwmon-core' depends on 'i2c-core'
Hint: kmod-i2c-core is missing from kernel dependencies in kmod cache
```

文件存在：`build_dir/.../hwmon.ko`，但 LEDE 的 provides/missing 检查失败。

**根因：** `hwmon.ko` 的 `.modinfo` 显示 `depends=i2c-core`（运行时依赖），但 `package/kernel/linux/modules/hwmon.mk` 的 `KernelPackage/hwmon-core` 定义中没有 `DEPENDS+=+kmod-i2c-core`。

LEDE 的打包脚本会检查 kmod provides/missing 链条，缺少声明会导致 missing 文件列表出现 `i2c-core`。

**修复：**

```makefile
# hwmon.mk 修复：
define KernelPackage/hwmon-core
  ...
  DEPENDS:=+kmod-i2c-core   # 添加此行
  ...
endef
```

### 4. config-6.12 被意外截断

**问题：** patch 操作将 10677 行的 config 文件截断为 860 行。

**修复：** 从 git 恢复被截断的文件。

### 5. U-Boot patch hunk context 失效

**问题：** `package/boot/uboot-rockchip/patches/319-rockchip-rk3576-Add-support-for-photonicat2.patch` 中 3 个 hunk（board.c × 2，Kconfig × 1，Makefile × 1）应用失败：

```
Hunk #1 FAILED at 61.
Hunk #2 FAILED at 480.
```

**根因：** 原始 patch 是针对早期 U-Boot 版本编写的。U-Boot 2026.01 中：

- `board.c` 的 `board_late_init()` 结构已改变，不再有 `rockchip_eink_show_uboot_logo()` 调用，上下文行不匹配
- `drivers/video/Kconfig` 的 `endmenu` 位置已从 ~652 行移到 1413 行
- `drivers/video/Makefile` 的末尾结构也已变化

**修复方法：**

1. 下载原始 U-Boot 2026.01 tarball
2. 在 build 目录中手动应用所需的源码修改
3. 用 `diff -u` 生成正确的 hunk
4. 替换原 patch 文件中损坏的 3 个 hunk
5. 在干净 U-Boot 源码上验证全部 8 个 hunk 应用成功

---

## 修复记录

### Commit 历史

| Commit | 内容 |
|--------|------|
| `a4baa0ed85` | target/linux/rockchip/armv8/config-6.12: 恢复完整内核配置，添加 DRM display helper 选项 |
| `cff6d844a6` | package/kernel/linux/modules/hwmon.mk: 添加缺失的 DEPENDS on kmod-i2c-core |
| `44c992d7d1` | uboot-rockchip: 修复 Photonicat2 patch context for U-Boot 2026.01 |

### 修复的文件

| 文件 | 修改内容 |
|------|----------|
| `target/linux/rockchip/modules.mk` | 移除 FILES 中的 `@CONFIG_*` 和 `@版本条件` 后缀；添加 KCONFIG DRM 选项 |
| `target/linux/rockchip/armv8/config-6.12` | 恢复完整 10677 行内核配置；添加 DRM/显示/PHY 相关选项 |
| `package/kernel/linux/modules/hwmon.mk` | 添加 `DEPENDS:=+kmod-i2c-core` |
| `package/boot/uboot-rockchip/patches/319-*.patch` | 修复 board.c/Kconfig/Makefile 的 hunk context |

---

## 关键发现

### LEDE kmod 打包机制

1. **FILES 条件语法**：仅 `DEPENDS` / `PACKAGES` 支持条件表达式，`FILES` 不支持任何 `@` 条件
2. **KCONFIG override**：在 `modules.mk` 中使用 `KCONFIG += CONFIG_XXX=y` 可强制设置内核配置，但 `=n` 优先于其他来源的 `=y`
3. **运行时依赖**：`.ko` 文件的 `depends=`（来自 `.modinfo`）是运行时依赖，需要在 LEDE 的 `DEPENDS` 中显式声明，否则 provides/missing 检查失败
4. **config-6.12 合并**：LEDE kernel 配置合并流程会自动重置部分配置，通过 KCONFIG 行强制覆盖是更可靠的方式

### U-Boot 补丁维护

- U-Boot 上游代码变动会导致 patch hunk 失效
- 修复方法：从 dl/ 目录解压原始 tarball → 手动应用修改 → 生成新的 unified diff
- 验证：每次修改后在新解压的源码上 `patch -p1 < xxx.patch` 确认全部 hunk 通过

### 硬件配置确认

- **Photonicat2 RK3576** 使用 HDMI via **HDPTX PHY**，无 Analogix DP 控制器
- SPI display driver (`pcat-spi-display.c`) 在 U-Boot 中通过 `CONFIG_PCAT_SPI_DISPLAY` 控制
- GMAC 使用 RGMII 模式，双网口配置

---

*文档生成时间：Build 35 开始后*
*LEDE 版本：coolsnowwolf/lede branch photonicat2_lede*

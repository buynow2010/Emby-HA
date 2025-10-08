# Emby for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/buynow2010/Emby-HA)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.1%2B-green.svg)](https://www.home-assistant.io/)

将 Emby 媒体服务器完美集成到 Home Assistant，实时监控服务器状态、播放活动和媒体库统计。

## 🚀 快速开始

<table>
<tr>
<td align="center">
<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=buynow2010&repository=Emby-HA&category=integration">
<img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="添加HACS仓库" />
</a>
<br />
<strong>添加到 HACS</strong>
</td>
<td align="center">
<a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=emby">
<img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="添加集成" />
</a>
<br />
<strong>添加集成</strong>
</td>
</tr>
</table>

## 功能特性

### 📊 实体说明

集成提供 **6 个服务器级别实体** + **每个监控设备 5 个实体**

**服务器传感器 (4个)**
- 🎬 电影数量 - 媒体库中的电影总数
- 📺 剧集数量 - 媒体库中的剧集总数
- 📹 集数 - 媒体库中的集数总数
- 🆕 最近添加 - 最近7天添加的媒体

**二进制传感器 (2个)**
- ✅ 服务器在线状态 - 实时监控服务器连接
- ▶️ 有活动播放 - 检测是否有设备正在播放（支持设备过滤）

**设备级实体（每个监控设备）**

为每个监控设备自动创建以下实体：
- 🎵 **当前播放传感器** - 显示正在播放的内容名称和详情
- ⏯️ **播放状态传感器** - 显示播放/暂停/空闲状态
- 📊 **播放进度传感器** - 显示播放进度百分比
- ⏱️ **剩余时间传感器** - 显示剩余播放时间
- 🎮 **媒体播放器** - 提供播放状态和媒体信息（仅显示，不支持控制）

### 🎯 设备过滤功能

选择要监控的特定设备，避免多设备干扰：
- 只监控指定设备的播放状态
- 适合自动化场景（如客厅灯光控制）
- 精准的播放状态检测

## 安装方式

### 方法一：通过 HACS 安装（推荐）

[![添加HACS仓库](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=buynow2010&repository=Emby-HA&category=integration)

**一键安装（推荐）**：点击上方徽章，直接在 HACS 中添加此仓库

**手动添加**：
1. 确保已安装 [HACS](https://hacs.xyz/)
2. 在 HACS 中点击右上角菜单 → **自定义存储库**
3. 添加仓库地址：`https://github.com/buynow2010/Emby-HA`
4. 类别选择：**Integration**
5. 点击 **添加**
6. 在 HACS 中搜索 "**Emby**"
7. 点击 **下载**
8. 重启 Home Assistant

### 方法二：手动安装

1. 下载本仓库
2. 将 `custom_components/emby` 文件夹复制到你的 Home Assistant 配置目录下的 `custom_components/` 目录
3. 重启 Home Assistant

## 配置

### 1. 获取 Emby API 密钥

登录 Emby 管理界面：
```
设置 → 高级 → API密钥 → 新建
```

### 2. 添加集成

[![添加集成](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=emby)

**一键添加（推荐）**：点击上方徽章，直接跳转到添加集成页面

**手动添加**：
```
设置 → 设备与服务 → 添加集成 → 搜索 "Emby"
```

### 3. 填写配置信息

- **主机**: Emby 服务器地址（如：`192.168.1.100` 或 `emby.example.com`）
- **端口**: `8096`（默认）或自定义端口
- **API密钥**: 刚才生成的 API 密钥
- **监控设备**（可选）: 选择要监控的特定设备或选择"所有设备"

## 使用示例

### Lovelace 卡片

```yaml
type: entities
title: Emby 服务器
entities:
  - binary_sensor.emby_online
  - sensor.emby_movie_count
  - sensor.emby_series_count
  - sensor.emby_episode_count
  - sensor.emby_recently_added
  - binary_sensor.emby_has_active_streams
  # 设备级实体（根据你监控的设备动态创建）
  # 将 device_name 替换为你的实际设备名称
  - sensor.emby_device_name_now_playing
  - sensor.emby_device_name_playback_state
  - sensor.emby_device_name_progress_percent
  - media_player.emby_device_name
```

### 自动化示例

**播放开始通知**
```yaml
automation:
  - alias: "Emby 播放通知"
    trigger:
      - platform: state
        entity_id: binary_sensor.emby_has_active_streams
        from: "off"
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "有人开始在 Emby 上播放内容"
```

**服务器离线警告**
```yaml
automation:
  - alias: "Emby 离线警告"
    trigger:
      - platform: state
        entity_id: binary_sensor.emby_online
        to: "off"
        for:
          minutes: 5
    action:
      - service: notify.mobile_app
        data:
          title: "Emby 警告"
          message: "Emby 服务器已离线超过 5 分钟"
```

**播放时调暗灯光**
```yaml
automation:
  - alias: "播放时调暗客厅灯光"
    trigger:
      - platform: state
        entity_id: binary_sensor.emby_has_active_streams
        to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 20
```

## 系统要求

### Emby Server
- 版本：4.7+
- 已启用 API 并生成密钥

### Home Assistant
- 版本：2023.1.0+
- Python：3.10+

## 故障排除

### 无法找到集成
检查集成是否正确安装：
```bash
ls ~/.homeassistant/custom_components/emby/manifest.json
```

### 认证失败
- 在 Emby 中重新生成 API 密钥
- 确保密钥正确复制（无空格）
- 检查 Emby 服务器地址和端口是否正确

### 实体无数据
- 确认 Emby 服务正在运行
- 点击 `button.emby_test_connection` 测试连接
- 查看 HA 日志：`设置 → 系统 → 日志`

### 启用调试日志
在 `configuration.yaml` 中添加：
```yaml
logger:
  default: info
  logs:
    custom_components.emby: debug
```

## 技术特性

- ✅ 并发 API 请求，性能优化
- ✅ 完善的错误处理机制
- ✅ 30 秒自动更新（可配置）
- ✅ 为每个监控设备动态创建传感器和媒体播放器
- ✅ 设备过滤功能
- ✅ 支持 HTTPS/SSL 连接

## 更新日志

### v1.0.0 (2025-10-07)
- 🎉 初始版本发布
- ✅ 6 个服务器级别实体 + 每个监控设备 5 个实体（4个传感器 + 1个媒体播放器）
- 🚀 并发 API 请求优化
- 🎯 设备过滤功能
- 📖 完整的文档

## 支持与反馈

- **问题反馈**: [GitHub Issues](https://github.com/buynow2010/Emby-HA/issues)
- **功能请求**: [GitHub Issues](https://github.com/buynow2010/Emby-HA/issues)
- **讨论交流**: [GitHub Discussions](https://github.com/buynow2010/Emby-HA/discussions)

## 友情链接

### 🏠 Home Assistant 中文网

[![Home Assistant 中文网](https://img.shields.io/badge/Home%20Assistant-中文网-blue?style=for-the-badge&logo=home-assistant)](https://www.hasscn.top)

[**Home Assistant 中文网 (hasscn.top)**](https://www.hasscn.top) - 最全面的免费 Home Assistant 中文站点，提供：
- 🚀 **Home Assistant OS 极速版** - 专为中国优化的加速版系统
- ⚡ **HACS 极速版** - 使用国内镜像加速插件下载
- 📚 **中文文档教程** - 详细的安装配置指南
- 💬 **社区支持** - 微信公众号：老王杂谈说

**特别适合国内用户使用，解决下载慢、连接困难等问题！**

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 致谢

- [Emby](https://emby.media/) - 优秀的媒体服务器
- [Home Assistant](https://www.home-assistant.io/) - 开源智能家居平台
- [HACS](https://hacs.xyz/) - Home Assistant 社区商店

---

**享受您的 Emby + Home Assistant 集成体验！** 🎬🏠

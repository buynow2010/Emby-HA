# Emby for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/buynow2010/Emby-HA)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.1%2B-green.svg)](https://www.home-assistant.io/)

将 Emby 媒体服务器完美集成到 Home Assistant，实时监控服务器状态、播放活动和媒体库统计。

## 功能特性

### 📊 20+ 个实体

**传感器 (13个)**
- 🎬 电影/剧集/集数统计
- 📚 媒体库数量
- 👥 用户和会话监控
- 📱 设备管理
- ⚙️ 系统活动和任务
- 🎵 当前播放（显示播放内容、类型、进度、状态）

**二进制传感器 (5个)**
- ✅ 服务器在线状态
- ▶️ 活动播放检测
- ⚡ 任务运行状态
- 🔄 待重启提醒
- 🌐 网络连接状态

**按钮 (2个)**
- 🔄 刷新数据
- 🔗 测试连接

**媒体播放器**
- 🎮 自动为活动会话创建媒体播放器实体
- 📊 显示播放内容和进度

### 🎯 设备过滤功能

选择要监控的特定设备，避免多设备干扰：
- 只监控指定设备的播放状态
- 适合自动化场景（如客厅灯光控制）
- 精准的播放状态检测

## 安装方式

### 方法一：通过 HACS 安装（推荐）

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

在 Home Assistant 中：
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
  - sensor.emby_version
  - sensor.emby_movie_count
  - sensor.emby_series_count
  - sensor.emby_episode_count
  - sensor.emby_active_sessions
  - binary_sensor.emby_has_active_streams
  - sensor.emby_now_playing
  - button.emby_refresh
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
- ✅ 动态创建媒体播放器实体
- ✅ 设备过滤功能
- ✅ 支持 HTTPS/SSL 连接

## 更新日志

### v1.0.0 (2025-10-06)
- 🎉 初始版本发布
- ✅ 20 个实体（传感器+二进制传感器+按钮+媒体播放器）
- 🚀 并发 API 请求优化
- 🎯 设备过滤功能
- 📖 完整的文档

## 支持

- **问题反馈**: [GitHub Issues](https://github.com/buynow2010/Emby-HA/issues)
- **功能请求**: [GitHub Issues](https://github.com/buynow2010/Emby-HA/issues)

## 许可证

MIT License

## 致谢

- [Emby](https://emby.media/) - 优秀的媒体服务器
- [Home Assistant](https://www.home-assistant.io/) - 开源智能家居平台

---

**享受您的 Emby + Home Assistant 集成体验！** 🎬🏠

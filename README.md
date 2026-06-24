# PSAs - 中国经典公益广告索引

收集中国经典公益广告，按主题分类整理。最终目标是将公益广告插入动画片中，让小朋友学习中华民族的传统美德。

## 工作方式

- **仓库只存索引**（链接+元数据），不存视频文件
- 通过 GitHub Actions **每6小时自动收集**一次，增量更新
- 收集到的视频先进入**待审核区**，人工确认后入正式库
- 需要使用时，用 `yt-dlp` 按需下载视频

## 质量过滤

自动收集经过三层过滤：

1. **标题过滤** — 必须包含"公益"、"广告"、"传统美德"等核心词，排除"搞笑"、"鬼畜"等
2. **时长过滤** — 仅保留 10秒-5分钟的视频
3. **来源过滤** — 央视、人民日报等权威来源标记为高可信度

过滤后的视频标记为 `pending` 状态，等待人工审核。

## 使用方法

### 可视化审核（推荐）

```bash
python scripts/review.py
```

浏览器自动打开审核页面，可直接观看视频，点击"批准/拒绝/跳过"按钮。

### 命令行审核

```bash
python scripts/approve.py list              # 查看待审核项
python scripts/approve.py approve 0         # 批准第0条
python scripts/approve.py approve all       # 批准全部
python scripts/approve.py reject 1          # 拒绝第1条
```

### 下载视频

```bash
pip install yt-dlp
python scripts/download.py 文明礼貌
```

## 项目结构

```
PSAs/
├── .github/workflows/collect.yml   # GitHub Actions 定时收集
├── scripts/
│   ├── collect.py                  # 自动收集 + 质量过滤
│   ├── review.py                   # 可视化审核页面
│   ├── approve.py                  # 命令行审核
│   └── download.py                 # 按分类批量下载
├── index.json                      # 视频索引数据
└── README.md
```

## 分类

文明礼貌 | 孝道 | 节约 | 环保 | 交通安全 | 禁烟 | 诚信 | 友善 | 爱国 | 助人为乐

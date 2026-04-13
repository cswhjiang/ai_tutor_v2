
# manim 笔记

Manim 现在常见的其实是两条分支：Manim（Community Edition） 和 ManimGL。它们名字很像，但定位、技术路线差别很大。

## 区别
| 维度     | **Manim（Community）** | **ManimGL**   |
| ------ | -------------------- | ------------- |
| 官方定位   | 社区维护、稳定主线            | 原作者个人分支       |
| 渲染方式   | 🎞 离线渲染（逐帧）          | ⚡ OpenGL 实时渲染 |
| 预览方式   | `manim -p`（生成视频）     | 窗口实时播放        |
| 稳定性    | ⭐⭐⭐⭐⭐（生产级）           | ⭐⭐⭐（开发向）      |
| 上手难度   | 较低                   | 较高            |
| 中文资料   | 非常多                  | 很少            |
| 适合用途   | 讲解视频、课程、投稿           | 实验、演示、交互      |
| 是否推荐新人 | ✅ 强烈推荐               | ❌ 不推荐         |


👀 看起来几乎一样，但底层完全不同：

Community：生成帧 → 合成视频

GL：OpenGL 实时画

而且：

一些类名、参数、效果在两边 不完全兼容

新教程 几乎都以 Community 为准

### 3b1b 版 （manimgl）
https://github.com/3b1b/manim


### 社区版 (manim)
https://github.com/ManimCommunity/manim/
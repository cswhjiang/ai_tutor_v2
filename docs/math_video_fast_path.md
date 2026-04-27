# 数学视频生成加速记录

## 背景

当前数学视频链路原来是四段式：

1. `SolutionAgent` 生成解题过程。
2. `ShotAgent` 生成分镜。
3. `CodeGenerationAgent` 生成完整 Manim 代码。
4. `RenderAgent` 执行 Manim 渲染并保存视频。

从现有日志抽样看，一次成功请求大约耗时 9 分钟，其中代码生成约 6 分 40 秒，Manim/TTS 渲染约 1 分钟。主要瓶颈不是 Manim CE 本身，而是“让 LLM 生成完整 Manim 程序”这一步。

## 本次优化

新增快速链路：让 LLM 只输出结构化讲解脚本 JSON，本地固定 Manim 模板负责渲染。

相关文件：

- `src/agents/experts/math_video/fast_math_video_agent.py`
- `src/agents/experts/math_video/fast_template_renderer.py`
- `src/agents/experts/math_video/math_video_generation_agent.py`
- `src/llm/model_factory.py`
- `test_manim/test_fast_template_renderer.py`
- `test_adk/test_model_factory.py`

核心变化：

- 默认 `MathVideoGenerationAgent` 改为 `FastMathVideoGenerationAgent`。
- LLM 调用从“解题 + 分镜 + 代码生成”缩短为一次结构化脚本生成。
- 快速脚本 Agent 显式使用低推理档；`model_factory` 会把 `reasoning_effort="low"` 映射到 Gemini 的 `LOW` thinking level，避免沿用全局 high thinking。
- 渲染模板固定为 `854x480@15fps`，降低 Manim 渲染压力。
- 不再执行 LLM 生成的任意 Manim 代码，减少失败重试和安全风险。
- 语音为自动模式：有火山 TTS 环境变量和 `ffmpeg/ffprobe` 时并发合成并混音；否则生成无语音字幕式视频。
- 旧四段式链路仍保留，可用 `math_video_mode="legacy"` 或 `use_legacy=True` 回退。

## 使用方式

默认不需要改调用方，继续使用 `MathVideoGenerationAgent` 即可走快速链路。

如果需要回退旧链路，在当前步骤参数中传入：

```json
{
  "math_video_mode": "legacy"
}
```

或：

```json
{
  "use_legacy": true
}
```

语音控制：

- 默认：`MATH_VIDEO_FAST_VOICEOVER=auto`
- 强制静音：`MATH_VIDEO_FAST_VOICEOVER=0`
- 自动语音需要 `VOLCENGINE_APPID`、`VOLCENGINE_ACCESS_TOKEN`、`ffmpeg`、`ffprobe`

## 预期速度

在原链路中，最大耗时来自完整 Manim 代码生成。新链路删掉这一步后，典型路径变成：

1. 入口编排和计划生成。
2. 一次脚本 LLM 调用。
3. 本地模板低分辨率渲染。

按已有日志中的 9 分钟样本估算，如果入口编排耗时不变，端到端目标可以从分钟级降到几十秒级。实际能否稳定达到 10 倍，取决于上游 `Orchestrator` 的计划耗时、LLM API 延迟、TTS 是否命中缓存、机器渲染性能。

## 验证

已增加不依赖外部 LLM 的单元测试，覆盖脚本归一化、旁白顺序、时长估计、Manim 代码关键参数。

建议验证命令：

```bash
python -m pytest test_manim/test_fast_template_renderer.py
python -m pytest test_adk/test_model_factory.py
python -m py_compile src/llm/model_factory.py src/agents/experts/math_video/fast_template_renderer.py src/agents/experts/math_video/fast_math_video_agent.py src/agents/experts/math_video/math_video_generation_agent.py
```

后续如果要继续提速，可以再做两件事：

1. 在路由层对明确的视频任务跳过通用 `Orchestrator` 的全局计划和单步计划。
2. 优化 `ByteDanceService`，避免 WAV 转 MP3 的中间步骤，进一步减少语音生成耗时。

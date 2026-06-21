数学问题生成视频

## 路线

当前有三条生成路线，默认路线由 `conf/jsons/system.json` 中的 `math_video_generation_route` 控制，修改配置并重启服务后生效。

- `manimce`: `ManimCESolutionAgent -> ManimCEShotAgent -> CodeGenerationAgent -> RenderAgent`，使用 Manim CE 和 `manim_voiceover`。
- `fast`: 单次脚本生成 + 固定 Manim CE 模板，速度快，但表达能力较弱。
- `manimgl`: `ManimGLSolutionAgent -> ManimGLShotAgent -> ManimGLCodeGenerationAgent -> ManimGLRenderAgent`，使用 `reference-projects/manim` 中的 ManimGL 源码，通过 Volcengine TTS 合成旁白，并用 ManimGL 的 `add_sound` 合成到视频中。

`manimce` 和 `manimgl` 不共享解题或分镜 agent。两条路线分别使用独立的 state key 和 per-agent LLM 配置，后续可以单独优化 prompt、模型和 reasoning level。

## 配置

```json
{
  "math_video_generation_route": "manimgl",
  "manimgl_project_path": "../reference-projects/manim",
  "manimgl_render_quality": "low"
}
```

`math_video_generation_route` 可选值为 `manimce`、`fast`、`manimgl`。

## ManimGL 运行要求

- 需要安装 ManimGL reference 项目的运行依赖。
- 需要本机有可用 OpenGL/WindowServer 环境；在受限沙箱里可能无法创建 OpenGL pixel format。
- 需要设置 `VOLCENGINE_APPID` 和 `VOLCENGINE_ACCESS_TOKEN`，否则 ManimGL 路线无法生成带旁白的视频。

# Local Manim Voiceover Services

这里放项目内自定义的 Manim voiceover 服务，不再复制到 `.venv`。

生成的 Manim 代码应使用项目内 import：

```python
from src.local_manim_voiceover_services.bytedance import ByteDanceService
```

`RenderAgent` 会在执行 `manim` 子进程时把项目根目录加入 `PYTHONPATH`，因此临时目录中的渲染脚本也能 import 到这里的服务。

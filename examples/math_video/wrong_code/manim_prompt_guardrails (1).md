# 防止智能体生成 Manim 不兼容代码的 Prompt 增补（建议直接粘贴到系统/开发者提示词中）

> 目标：避免生成“某个 Manim 版本不存在的方法/参数”导致的运行时错误（例如 `Text.get_parts_by_text()` 在部分版本中不存在）。

---

## 1) 明确运行环境与版本锁定（必须写进 Prompt）

请在生成代码前**先声明并遵守**以下环境约束：

- **Manim 版本**：`manim==<你的版本号>`（例如 `0.18.0` / `0.19.0` 等）
- **manim-voiceover 版本**：`manim-voiceover==<你的版本号>`
- Python 版本：`3.11`（或你的实际版本）
- 平台：macOS / Windows / Linux（可选）

并要求智能体：
- **只能使用上述版本文档/API中存在的类与方法**。
- 遇到不确定的 API（比如 `get_parts_by_text`、`substrings_to_isolate` 等）必须**采用“通用兼容写法”**或给出**版本条件分支**。

你可以这样写在 Prompt 里（示例）：

- “你生成的 Manim 代码必须兼容 `manim==0.18.0` 与 `manim-voiceover==0.3.x`。禁止使用这些版本中不存在的方法。若不确定 API 是否存在，必须用更通用的实现（例如用 `Text` 的字符切片索引而非 `get_parts_by_text`）。”

---

## 2) 强制“API 存在性自检”规则（写进 Prompt）

在 Prompt 中加入硬性规则，让智能体在输出前进行自检（即使它不能真的运行，也要按规则推导）：

- **规则 A：不要对 `Text` 调用按文本匹配的 `get_parts_by_text()`**
  - 对 `Text` 高亮子串时，优先用：
    - `t2c`/`t2w`/`t2s`（按字符串着色）
    - 或用 `find()` + `Text` 的**字符切片**（兼容性强）
- **规则 B：若要按字符串定位子对象，必须写出定位策略**
  - 例如：`idx = s.find("40"); mobj = text[idx:idx+len("40")]`
- **规则 C：每个“可能不稳定的 API”必须给出替代方案**
  - 例如：`get_parts_by_text` → 用 `find + slice` 或 `t2c` + `Indicate(slice)`

建议直接写入 Prompt 的强制句式（可复制）：

- “输出前请检查所有调用的方法是否属于该类在指定版本 Manim 中的公开 API。若不确定，改用更通用的写法（例如对 `Text` 使用索引切片来定位字符子物体，而不是调用 `get_parts_by_text`）。”

---

## 3) 要求智能体在关键处添加“兼容性注释 + 防呆代码”

让智能体在容易出错的位置加注释和防呆：

- 对需要高亮的数字，统一用一个小工具函数（可复用）：
  - 输入：原字符串、目标子串
  - 输出：`Text` 的切片对象
- 加入断言/兜底：
  - 找不到子串时，不要崩溃：跳过高亮或改为 `Indicate(text)`。

---

## 4) 可直接粘贴的 Prompt 增补片段（推荐）

把下面这段加到你现有的 prompt（越靠前越好）：

```text
【Manim 兼容性硬约束】
- 运行环境：Python 3.11；manim==<填写你的版本>；manim-voiceover==<填写你的版本>
- 只能使用上述版本中确实存在的 API。不要假设某类有某方法。
- 特别注意：对 Text/MarkupText 的子串定位不要使用不确定的方法（如 get_parts_by_text）。对 Text 高亮子串请用：
  1) 先在原字符串中用 find() 找到子串起始索引；
  2) 再用 text[idx:idx+len(substr)] 取切片；
  3) Indicate/SurroundingRectangle 等作用于该切片。
- 如果 find() 返回 -1，必须提供兜底（例如跳过高亮或改为 Indicate 整个 Text），避免运行时异常。
- 对任何你不确定是否存在的 Manim API，都必须给出“通用替代实现”，并优先选择替代实现。
```

---

## 5) 为什么这能避免这次错误（对应你的报错点）

本次错误来自：`Text` 对象上调用了 `get_parts_by_text("40")`，而你的 Manim 版本中 `Text` 没有该方法。

按上述 prompt 约束后，智能体会被迫采用**更稳定的做法**：

- `idx = problem_str.find("40")`
- `mobj_40 = problem[idx:idx+2]`
- `Indicate(mobj_40)`

从而避免“调用不存在的方法”导致的崩溃。

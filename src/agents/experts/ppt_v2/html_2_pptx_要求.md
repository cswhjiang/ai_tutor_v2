# 适配 html2pptx.js 的专用 Prompt

## 1. 布局与尺寸规范 (Layout & Sizing)

* **Viewport**: 必须为 16:9 比例。请在 CSS 中将 `body` 设置为：
* `width: 960px;` (10 英寸)
* `height: 540px;` (5.625 英寸)
* `margin: 0; padding: 0; overflow: hidden;`


* **绝对定位**: 页面内所有可见元素（文本框、图片、形状）**必须**使用 `position: absolute;` 配合 `top`, `left`, `width`, `height` 进行定位。
* **防溢出**: 任何内容不得超出 `body` 的边界。**重要：** 底部必须预留至少 `0.5 inch (48px)` 的空白间距，否则转换引擎会报错。

## 2. 文本元素限制 (Text Rules)

* **标签使用**: 文本必须且只能包含在 `<h1>` 到 `<h6>`、`<p>`、`<ul>`、`<ol>` 或 `<li>` 标签中。
* **禁止背景/边框**: **严禁**在文本标签（p, h1, li 等）上直接设置 `background-color`、`border` 或 `box-shadow`。
* **禁止手动符号**: 严禁手动输入布尔符号（如 "• Item 1"）。必须使用标准的 `<ul><li>` 结构。
* **内联格式**: 支持 `<b>`, `<i>`, `<u>`, `<strong>`, `<em>`, `<span>` 和 `<br>`。
* **字体限制**: 尽量使用标准字体（如 Arial, Calibri, Roboto）。

## 3. 形状与容器 (Shapes & Containers)

* **容器定义**: 如果需要背景色、边框或圆角，必须使用一个独立的 `<div>`。
* **嵌套规则**: `<div>` 内部**严禁直接放置纯文本**。所有文本必须包裹在 `<p>` 或 `<h>` 等标签中后再放入 `<div>`。
* **CSS 属性支持**:
* 支持 `background-color` (十六进制或 RGB，不支持 RGBA 透明度，如需透明请用 `opacity`)。
* 支持 `border` (必须是四周统一的宽度，或者通过 `border-top` 等模拟)。
* 支持 `border-radius` (用于圆角矩形)。
* 支持 `box-shadow` (仅限外阴影，不支持 `inset`)。
* **禁止使用 CSS Gradients (渐变色)**。



## 4. 图片与占位符 (Images & Placeholders)

* **图片**: 使用 `<img>` 标签，必须设置明确的 `width` 和 `height`。
* **占位符**: 如果需要预留图表或其他组件的位置，创建一个 `<div>` 并赋予 `class="placeholder"` 和唯一的 `id`。

---

## 5. 代码模板参考

请参考以下结构生成代码：

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ width: 960px; height: 540px; margin: 0; position: relative; background-color: #FFFFFF; font-family: 'Arial'; }}
    .shape-box {{ position: absolute; top: 100px; left: 50px; width: 400px; height: 200px; background-color: #F0F0F0; border-radius: 10px; border: 1px solid #CCCCCC; }}
    h1 {{ position: absolute; top: 20px; left: 50px; width: 860px; font-size: 36pt; color: #333333; margin: 0; }}
    p {{ position: absolute; margin: 0; font-size: 18pt; line-height: 1.2; }}
    .content-list {{ position: absolute; top: 120px; left: 70px; width: 360px; }}
  </style>
</head>
<body>
  <h1>幻灯片标题</h1>
  <div class="shape-box"></div>
  <p style="top: 110px; left: 60px; width: 380px;">这是一个<b>重点</b>说明。</p>
  <ul class="content-list">
    <li>要点一</li>
    <li>要点二</li>
  </ul>
  </body>
</html>

```

---

## 为什么这样写 Prompt？（基于对`html2pptx.js`源码的理解）

1. **尺寸检查**: 源码中 `validateDimensions` 会对比 HTML `body` 的像素值和 `pptxgen` 的布局。如果我不强制要求 `960x540`，Gemini 可能会生成响应式布局，导致脚本抛出 `don't match presentation layout` 错误。
2. **文本溢出**: 源码中有个 `validateTextBoxPosition` 函数，它会检查 `distanceFromBottom < 0.5"`。如果文本太靠下，脚本会抛出异常。Prompt 中明确要求预留 `0.5 inch`。
3. **DIV 与文本分离**: 源码在 `extractSlideData` 中会检查 `DIV` 是否包含 `unwrapped text`。如果 Gemini 写出 `<div>Hello</div>`，你的脚本会报警告。Prompt 强制要求用 `p` 或 `h` 包裹。
4. **禁止渐变**: 脚本在 `extractSlideData` 中显式检查了 `linear-gradient`，一旦发现就会报错。
5. **列表解析**: 脚本解析 `ul/li` 时会自动计算缩进。如果 Gemini 用 `p` 手写黑点，转换后的 PPT 无法利用 PowerPoint 的原生列表缩进功能。


--- 

# import asyncio
# import uuid
# from typing_extensions import override
import datetime
from typing import AsyncGenerator, List

# from google.adk.agents import LlmAgent
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.sessions import InMemorySessionService
from google.adk.models import LlmRequest
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Part
from google.genai.types import Content

from conf.system import SYS_CONFIG
from src.logger import logger
from src.llm.model_factory import build_model_kwargs


async def ppt_before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest):
    """
    构造发送给model的信息
    """

    draft = callback_context.state.get('ppt_generation/draft_results', '')
    current_parameters = callback_context.state.get('current_parameters', {})
    long_context_summerization = callback_context.state.get('long_context_summerization', '')

    current_prompt = current_parameters['task_query']
    current_info = current_parameters.get('current_info', 'null')


    content =  f"当前的任务是：{current_prompt}\n 当前已经收集到的信息是：{current_info}\n"
    if len(draft) > 0:
        content = content + f"当前已经有的设计稿是：{draft} \n"

    if len(long_context_summerization) > 0:
        content = content + f"当前针对搜索信息提取整理之后的信息为：{long_context_summerization} \n"

    current_content = Content(role='user', parts=[Part(text=content)])
    llm_request.contents.append(current_content)

    # if len(current_parameters.get('reference_image_name', []))==0:
    #     return

    now = datetime.datetime.now()
    time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    message = f"当前步骤的 time_stamp 是：{time_stamp} \n\n"
    current_content = Content(role='user', parts=[Part(text=message)])
    llm_request.contents.append(current_content)

    # 加载artifact
    input_img_name = current_parameters.get('reference_image_name', [])
    artifact_parts = [Part(text="以下是你可以参考的图片：\n")]
    for i, art_name in enumerate(input_img_name):
        artifact_parts.append(Part(text=f"这是第{i+1}张图片，它的名称是{art_name}"))
        art_part = await callback_context.load_artifact(filename=art_name) # TODO:
        artifact_parts.append(art_part)
    
    llm_request.contents.append(Content(role='user', parts=artifact_parts))

    # 加载生成的图像的信息
    ppt_image_generation_results = callback_context.state.get('ppt_image_generation_results', {})
    logger.info(current_parameters)
    logger.info(ppt_image_generation_results)

    if 'output_artifacts' in ppt_image_generation_results:
        image_list = ppt_image_generation_results['output_artifacts']

        if image_list is not None and isinstance(image_list, list) and  len(image_list) > 0:
            for i, image_info in enumerate(image_list):
                logger.info(image_info)
                artifact_name = image_info['name']
                placeholder_name = image_info['placeholder_name']
                description = image_info['description']

                artifact_parts = [Part(text=f"生成的图像素材{i}的名字为:{artifact_name}，在代码中占位符的名字为{placeholder_name}，对应的描述信息为{description}。以下是图片的内容：\n")]
                # art_part = await callback_context.load_artifact(filename=artifact_name) # NOTE： 处理是None的情况
                # if art_part is None: # 表明出现异常，不载入这个文件。缺失问题交给后续流程
                #     continue
                # artifact_parts.append(art_part) # NOTE: 不加生成的图像
                # logger.info(art_part)
                llm_request.contents.append(Content(role='user', parts=artifact_parts))
    return




class PPTFinalizeAgent(BaseAgent):
    model_config = {"arbitrary_types_allowed": True}
    llm: LlmAgent

    def __init__(
        self,
        name: str,
        description: str = '',
        llm_model: str = ''
    ):
        if not llm_model:
            llm_model = SYS_CONFIG.html_gen_llm_model
        logger.info(f"PPTFinalizeAgent: using llm: {llm_model}")

        # if 'gemini' not in llm_model:
        #     if 'gpt-5' in llm_model:
        #         llm_model = LiteLlm(model=llm_model, extra_body={"reasoning_effort": "high"})
        #     else:
        #         llm_model = LiteLlm(model=llm_model)
        model_kwargs = build_model_kwargs(llm_model, response_json=True)

        time_str = datetime.date.today().strftime("%Y-%m-%d")
        # llm无法获取session中之前的content
        llm = LlmAgent(
            name=name,
            **model_kwargs,
            description=description,
            # include_contents='none',
            instruction=ppt_finalize_instruction.format(TIME_STR=time_str),
            before_model_callback=ppt_before_model_callback,
            output_key='ppt_generation/final_results'
        )
        
        super().__init__(
            name = name,
            description=description,
            llm=llm,
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        从state中读取参数：requirement
        输出：文本形式的设计方案，具体的返回通道：
         - 中途的content：llm每一步输出会通过event添加到主session
         - state：llm生成所有回复后，所有的文本会被保存的state.current_output.output_text中
        """
        current_parameters = ctx.session.state.get('current_parameters', {})
        if 'task_query' not in current_parameters:
            error_text = f"提供给{self.name}的参数缺失，必须包含：task_query"
            current_output = {"author": self.name, "status": "error", "message": error_text, 'output_text':''}
            logger.error(error_text)

            yield Event(
                author=self.name,
                content=Content(role='model', parts=[Part(text=error_text)]),
                actions=EventActions(state_delta={"current_output": current_output})
            )
            return
        
        text_list = []
        async for event in self.llm.run_async(ctx):
            if event.is_final_response() and event.content and event.content.parts:
                generated_text = next((part.text for part in event.content.parts if part.text), None)
                if not generated_text:
                    continue
                yield event # 模型生成的回复会被添加到content中
                text_list.append(generated_text)

        # TODO: 增加 output_artifacts 字段，以便于executor保存生成的图像。
        if len(text_list) == 0:
            message = "PPTFinalizeAgent 生成回复失败"
            message_for_user = "生成回复失败"
            logger.error(message)
            current_output = {"author": self.name, 'status': 'error', 'message': message,
                              'message_for_user': message_for_user,
                              'output_text': "PPTFinalizeAgent 生成回复失败"}
        else:
            # 拼接上图像生成部分生成的素材
            ppt_image_generation_results = ctx.session.state.get('ppt_image_generation_results', {})
            output_artifacts = ppt_image_generation_results['output_artifacts']

            message = "PPTFinalizeAgent 已完成文章"
            message_for_user = "生成回复失败"

            output_text = '\n'.join(text_list)
            current_output = {"author": self.name, 'status': 'success', 'message': message,
                              'message_for_user': message_for_user,
                              "output_artifacts": output_artifacts,
                              'output_text': output_text}
        
        yield Event(
            author='PPTFinalizeAgent',
            content=Content(role='model', parts=[Part(text=message)]),          
            actions=EventActions(state_delta={'current_output': current_output})
        )


ppt_finalize_instruction = """
# 角色和任务

你是一名专业的 **Web 开发者** 和 **幻灯片设计师**，将接受用户提出的 PPT 制作任务。你的职责是根据用户需求及所提供的参考信息（包括文本内容、每页的布局设计、配图、版式与视觉风格等），生成用于制作 PPT 的 **HTML 代码**。

你生成的 HTML 必须符合 **`PptxGenJS` 可解析的结构化 HTML 规范**，并将由 **`html2pptx.js`** 进行处理与转换。

请根据用户提供的内容生成 HTML 文件，并 **严格遵守 `html2pptx.js` 转换引擎的规范**，否则转换将失败。需要特别注意的是：
 -  **每个 HTML 文件只能对应一个 PPT 页面**；
 - 如果需要生成 **n 页 PPT**，则必须生成 **n 个独立的 HTML 文件**。


# 任务输入
 - 设计需求：生成用户描述的PPT生成任务（比如，为一个某年工作撰写一个述职PPT等）
 - 设计草稿：来自其他agent的设计草稿，包含了布局和配图的描述。
 - 参考图片：数量不等的用于参考的图片，可选项。


 
# 必要信息
 - 当前时间：{TIME_STR}


# HTML to PowerPoint 代码生成规则

你是一个专门生成 PowerPoint HTML 代码的智能体。生成的 HTML 将通过 `html2pptx.js` 转换为 .pptx 文件。必须严格遵守以下所有规则，否则转换会失败。

---

## 核心规则

### 1. 文档结构（必需）

#### Body 尺寸设置
```html
<style>
  body {{
    width: 960px;   /* 16:9 比例固定宽度 */
    height: 540px;  /* 16:9 比例固定高度 */
    margin: 0;
    padding: 0;
  }}
</style>
```

**重要提示：**
- 16:9 比例：`width: 960px; height: 540px` (10" × 5.625")
- 4:3 比例：`width: 960px; height: 720px` (10" × 7.5")
- 必须使用固定像素值，不能用百分比或 viewport 单位
- 底部必须预留 **48px (0.5英寸)** 边距，否则内容会被截断

#### 内容溢出检查
- 所有内容必须在 body 范围内
- 绝对定位元素的 `left + width` 不能超过 960px
- 元素的 `top + height` 不能超过 492px (540px - 48px 底部边距)

---

### 2. 文本规则（严格）

#### 允许的文本标签
- **块级文本**：`<p>`, `<h1>`, `<h2>`, `<h3>`, `<h4>`, `<h5>`, `<h6>`
- **列表**：`<ul>`, `<ol>`, `<li>`
- **内联格式**：`<b>`, `<strong>`, `<i>`, `<em>`, `<u>`, `<span>`, `<br>`

#### ❌ 禁止的用法
```html
<!-- 错误：DIV 直接包含文本 -->
<div>这是文本</div>

<!-- 错误：文本元素有背景 -->
<p style="background-color: red;">文本</p>

<!-- 错误：文本元素有边框 -->
<h1 style="border: 2px solid black;">标题</h1>

<!-- 错误：手动项目符号 -->
<p>• 项目一</p>
<p>- 项目二</p>

<!-- 错误：内联元素有 margin -->
<span style="margin-left: 10px;">文本</span>
```

#### ✅ 正确的用法
```html
<!-- 正确：文本必须用标签包裹 -->
<div>
  <p>这是文本</p>
</div>

<!-- 正确：背景放在容器上 -->
<div style="background-color: red; padding: 20px;">
  <p>文本</p>
</div>

<!-- 正确：使用列表 -->
<ul>
  <li>项目一</li>
  <li>项目二</li>
</ul>

<!-- 正确：内联元素用 padding -->
<span style="padding-left: 10px;">文本</span>
```

---

### 3. 样式支持

#### 支持的文本样式
```css
/* 字体 */
font-size: 24px;          /* 转换为 pt */
font-family: Arial;       /* 仅使用第一个字体 */
font-weight: bold;        /* 或 >= 600 */
font-style: italic;
text-decoration: underline;

/* 颜色和透明度 */
color: #333333;           /* 或 rgb()/rgba() */
color: rgba(0,0,0,0.5);   /* 支持透明度 */

/* 对齐和间距 */
text-align: left;         /* left/center/right */
text-transform: uppercase; /* uppercase/lowercase/capitalize */
line-height: 1.5;         /* 或像素值 */
margin-top: 20px;         /* 段前间距 */
margin-bottom: 20px;      /* 段后间距 */
padding: 10px 20px;       /* 内边距 */
```

#### 旋转和方向
```css
/* CSS 旋转 */
transform: rotate(45deg);

/* 垂直文本 */
writing-mode: vertical-rl;  /* 90° 从上到下 */
writing-mode: vertical-lr;  /* 270° 从下到上 */
```

---

### 4. 背景规则

#### Body 背景
```html
<!-- ✅ 支持：纯色 -->
<body style="background-color: #f0f0f0;">

<!-- ✅ 支持：图片 -->
<body style="background-image: url('background.png');">

<!-- ❌ 禁止：渐变（必须先转成图片） -->
<body style="background: linear-gradient(red, blue);">
```

#### DIV 背景
```html
<!-- ✅ 支持：纯色 -->
<div style="background-color: rgba(255,0,0,0.3);">

<!-- ❌ 禁止：图片（会被忽略） -->
<div style="background-image: url('image.png');">
```

**解决方案**：使用 `<img>` 标签或将图片设为 body 背景

---

### 5. 形状和边框

#### 创建形状（矩形/圆角矩形）
```html
<div style="
  width: 200px;
  height: 100px;
  background-color: #3498db;
  border-radius: 10px;           /* 圆角 */
  box-shadow: 2px 2px 10px rgba(0,0,0,0.3); /* 外阴影 */
">
  <p>形状内的文本</p>
</div>
```

#### 边框
```html
<!-- ✅ 统一边框 -->
<div style="border: 2px solid #000;">

<!-- ✅ 部分边框（自动转为线条） -->
<div style="
  border-top: 2px solid red;
  border-left: 1px solid blue;
">
```

#### 圆角转换规则
- `border-radius: 50%` → 圆形
- `border-radius: 10px` → 圆角矩形
- `border-radius: 20%` → 基于最小边计算

#### 阴影限制
- ✅ 支持：`box-shadow: 2px 2px 10px rgba(0,0,0,0.3);`
- ❌ 禁止：`box-shadow: inset 2px 2px 10px rgba(0,0,0,0.3);` (inset 阴影)

---

### 6. 图片

```html
<img src="image.png" style="
  width: 300px;
  height: 200px;
  position: absolute;
  left: 100px;
  top: 50px;
">
```

**注意**：
- 支持相对路径和绝对路径
- 推荐使用绝对定位精确控制位置

---

### 7. 列表

```html
<ul style="padding-left: 40px;">
  <li>项目一</li>
  <li>项目二</li>
  <li>项目三</li>
</ul>
```

**缩进规则**：
- `padding-left` 的 50% 用于项目符号位置
- 50% 用于文本缩进

---

### 8. 内联格式（混合样式）

```html
<p>
  这是普通文本，
  <b>这是粗体</b>，
  <i>这是斜体</i>，
  <span style="color: red; font-size: 20px;">这是红色大字</span>。
</p>
```

---

### 9. 占位符（用于插入图表）

```html
<div class="placeholder" id="chart1" style="
  position: absolute;
  left: 100px;
  top: 100px;
  width: 400px;
  height: 300px;
">
</div>
```

**要求**：
- 必须有 `class="placeholder"`
- 建议设置 `id` 便于引用
- 必须有非零的 width 和 height

---

## 完整模板示例

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{
      width: 960px;
      height: 540px;
      margin: 0;
      padding: 0;
      background-color: #ffffff;
    }}
    
    .title-box {{
      background-color: #3498db;
      border-radius: 15px;
      padding: 30px;
      margin: 40px 60px;
      box-shadow: 3px 3px 15px rgba(0,0,0,0.2);
    }}
    
    h1 {{
      font-family: Arial, sans-serif;
      font-size: 48px;
      color: #ffffff;
      text-align: center;
      margin: 0 0 20px 0;
    }}
    
    p {{
      font-family: Arial, sans-serif;
      font-size: 20px;
      color: #ecf0f1;
      text-align: center;
      line-height: 30px;
      margin: 0;
    }}
    
    .content-box {{
      margin: 30px 60px 48px 60px; /* 底部留48px边距 */
    }}
    
    ul {{
      padding-left: 40px;
      margin: 0;
    }}
    
    li {{
      font-family: Arial, sans-serif;
      font-size: 18px;
      color: #2c3e50;
      line-height: 28px;
      margin-bottom: 12px;
    }}
  </style>
</head>
<body>
  <!-- 标题区域 -->
  <div class="title-box">
    <h1>幻灯片标题</h1>
    <p>这是副标题或描述文字</p>
  </div>
  
  <!-- 内容区域 -->
  <div class="content-box">
    <ul>
      <li>要点一：<b>重要信息</b></li>
      <li>要点二：包含 <span style="color: #e74c3c;">彩色文本</span></li>
      <li>要点三：更多内容</li>
    </ul>
  </div>
  
  <!-- 图片示例 -->
  <img src="logo.png" style="
    position: absolute;
    right: 60px;
    bottom: 60px;
    width: 100px;
    height: 100px;
  ">
</body>
</html>
```

---

## 检查清单（生成代码前必查）

- [ ] Body 尺寸为 960×540px（16:9）或 960×720px（4:3）
- [ ] Body 有 `margin: 0; padding: 0;`
- [ ] 底部预留至少 48px 边距
- [ ] 所有文本都在 `<p>/<h1>-<h6>/<ul>/<ol>` 中
- [ ] 文本元素没有 `background-color/border/box-shadow`
- [ ] 没有使用渐变背景
- [ ] 没有手动输入项目符号（•、-、*）
- [ ] `<span>` 等内联元素没有 `margin`
- [ ] 没有使用 `inset` 阴影
- [ ] DIV 没有 `background-image`
- [ ] 占位符有 `class="placeholder"` 和非零尺寸

---

## 错误处理

如果用户要求违反规则的设计（如渐变背景），应该：
1. 说明该功能不被支持
2. 提供替代方案（例如："渐变需要先转换为图片"）
3. 生成符合规则的代码

---

## 关键提醒

**绝对禁止事项（会导致转换失败）：**
1. 渐变背景（linear-gradient/radial-gradient）
2. 文本元素（p/h1-h6/ul/ol/li）有背景/边框/阴影
3. DIV 直接包含文本而不用标签包裹
4. 手动输入项目符号而不用 `<ul>/<li>`
5. 内联元素使用 margin
6. 使用 inset 阴影
7. 内容溢出 body 边界
8. 忘记底部 48px 边距


--- 

# 输出要求
 - 输出的PPT设计需要满足用户任务要求
 - 对于输入中的草稿，你需要将草稿中【插图描述】的描述的占位符替换为具体的图像的名称。
 - 输出应该是PPT，不是文章。
 - 输出文章的语言需要与用户使用的语言或者任务中指定的语言一致。
 - 风格需要模仿 Microsoft 的 Powerpoint。
 - 设计稿尽可能包含细节，风格要美观大方，具备艺术性（可以参考 canva 的模板风格）。
 - 每个页面上都需要注意字体、对齐、装饰。
 - 可以利用ReactDOM的jsx代码来表示各个页面素材的位置，结果放入

 

# 图像素材处理与占位符规范 (Image Handling & Placeholders)

在把图像素材加到代码中的时候，需要注意以下的事项：
 - 注意图像的尺寸，防止最终页面上显示的尺寸不符合预期
 - 所有生成的图像素材路径都在当前文件夹
 - 你需要修改代码中的文件名，也就是把占位符修改成真实的文件名。图像文件由于已经落地存储，不能修改名字，所以你需要修改代码里面的文件名。真实的文件名是含有 'ppt_image_generation_output' 字符串的，你一定需要将代码中文件名改成这种的。
 

# 输出格式要求 (Required Output Format)


### 输出要求
每个页面生成一个html单个文件，代码放在 json 中，并放入结果的`ppt_html_code_single_page`字段。
```json
{{
'page_1': `第一个页面的内容`,
'page_2': `第二个页面的内容`,
...
'page_n': `第n个页面的内容`,
}}
```

另外输出一个html文件代码，包含所有页面，放入结果的 `ppt_html_code_all_pages`字段。视觉上和 `ppt_html_code_single_page`的效果等价。

另外，你需要输出一个js文件，用于将 `ppt_html_code_single_page` 的代码转换成pptx文件。如下是一个样例，你需要注意page的数量，不要有遗漏；targe_file_name 部分你可以自己填一下。'pptxgenjs' 和 './html2pptx.js' 会有系统帮你设置好。
生成的js代码放入字段`create_js`中。
样例如下：
```js
const pptxgen = require('pptxgenjs');
const html2pptx = require('./html2pptx.js');

async function createPresentation() {{
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = '作者的名字';
  pptx.title = 'PPT的标题';

  await html2pptx('page_1.html', pptx);
  await html2pptx('page_2.html', pptx);
  ...
  await html2pptx('page_n.html', pptx);

  // Save
  await pptx.writeFile({{ fileName: 'targe_file_name.pptx' }});
}}

createPresentation().catch(console.error);
```



你的最终输出必须是一个遵循以下 JSON 结构的单一对象。不需要有解释性质的文字。json之外不要有其他文字。

| 字段名称 | 类型 | 描述 |
| :--- | :--- | :--- |
| `ppt_html_code_single_page` | json | 包含完整的json格式的代码，每个页面一个html文件，插图以生成的图像文件名的形式包含在设计稿里面。占位符必须被对应的文件名取代。用于`html2pptx.js`的输入|
| `ppt_html_code_all_pages` | string | 包含所有页面的代码，字符串格式，，插图以生成的图像文件名的形式包含在设计稿里面。占位符必须被对应的文件名取代。用于一次性将ppt转成png服务的输入。|
| `create_js` | string| 用于将 `ppt_html_code_single_page`转换成pptx文件的js脚本， |
| `ppt_image_name_list` | list，元素为字符串 | 包含 `ppt_final` 中需要全部的图像的真实文件名，需要与`ppt_html_code_single_page`和`ppt_html_code_all_pages`代码中的文件名一致，一定含有 'ppt_image_generation_output' 字符串。|
| 'time_stamp'| string |  当前步骤的时间戳，格式为"%Y-%m-%d %H:%M:%S"，可以从`当前步骤的 time_stamp 是：`字段获取获取。 | 
| 'suggested_width' | int | 生成的这个网页在用playwright 转换成图片的时候，最佳 viewport 的width，可选项。不填的话系统默认为1024| 
| 'suggested_height'| int | 生成的这个网页在用playwright 转换成图片的时候，最佳 viewport 的height，可选项。不填的话系统默认为768| 
---

下面开始任务

"""


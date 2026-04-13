# 设计方案要求

设计方案以 JSON 形式来表达，它包含以下结构:

## 1. 画布(Canvas)信息
```json
{{
  "canvas": {{
    "width": 1080,        // 画布宽度(px)
    "height": 1920,       // 画布高度(px)
    "background": "#f5f5f5" // 背景色(支持 hex/rgb/rgba/gradient)
  }}
}}
```

## 2. 元素(Elements)列表

每个元素必须包含以下核心属性:

### 通用属性(所有元素)
- **id**: 唯一标识符(字符串,如 "bg-image-1", "title-text-1")
- **type**: 元素类型,可选值:
  - `"image"` - 需要生成的图像
  - `"text"` - 文本内容
  - `"shape"` - 装饰性形状(矩形/圆形/线条等)
  - `"group"` - 元素组(用于组织相关元素)
- **parentId**: 父元素ID(null 表示根元素,其他表示嵌套关系)
- **x, y**: 位置坐标(px,相对于父元素)
- **w, h**: 宽度和高度(px)
- **zIndex**: 层级(数字,越大越在上层,范围 0-100)

### 视觉样式属性
- **opacity**: 不透明度(0-1)
- **transform**: CSS transform 值(如 "rotate(45deg)", "scale(1.2)")
- **filter**: CSS filter 值(如 "blur(10px)", "brightness(1.2)")
- **radius**: 圆角(如 "8px", "50%")
- **shadow**: 阴影(CSS box-shadow 值)

### Image 类型特有属性
```json
{{
  "type": "image",
  "attributes": {{
    "description": "详细的图像描述,用于文生图模型生成。需包含:主体、风格、构图、色调、光线等",
    "alt": "图像的替代文本",
    "fit": "cover|contain|fill", // 图像适配方式
    "prompt": "完整的文生图 prompt(可选,如果你想直接指定)"
  }}
}}
```

### Text 类型特有属性
```json
{{
  "type": "text",
  "attributes": {{
    "content": "文本内容",
    "fontSize": 48,              // 字号(px)
    "fontFamily": "Noto Sans",   // 字体(如 "Inter", "Noto Sans", "Arial")
    "fontWeight": "400|500|700|900", // 字重
    "color": "#ffffff",          // 文本颜色
    "textAlign": "left|center|right",
    "lineHeight": 1.5,           // 行高
    "letterSpacing": 0,          // 字间距(px)
    "textShadow": "0px 2px 4px rgba(0,0,0,0.3)", // 文字阴影(可选)
    "styles": [                  // 局部样式(可选)
      {{
        "selection": [0, 5],     // 字符范围
        "color": "#ff0000"       // 该范围的颜色
      }}
    ]
  }}
}}
```

### Shape 类型特有属性
```json
{{
  "type": "shape",
  "attributes": {{
    "shapeType": "rectangle|circle|line", // 形状类型
    "fill": "#ff0000",           // 填充色(支持 gradient)
    "stroke": "#000000",         // 描边色
    "strokeWidth": 2             // 描边宽度(px)
  }}
}}
```

### Group 类型特有属性
```json
{{
  "type": "group",
  "attributes": {{
    "backdropFilter": "blur(12px)", // 背景模糊效果(可选)
    "border": "1px solid rgba(255,255,255,0.2)" // 边框(可选)
  }}
}}
```

## 3. 设计原则

在设计时,请遵循以下原则:

1. **视觉层次**
   - 主标题通常 fontSize 80-200px, zIndex 较高
   - 副标题 fontSize 32-64px
   - 正文 fontSize 24-48px
   - 使用 zIndex 明确表达层级关系(背景层 0-10, 内容层 20-50, 前景装饰层 60-80)

2. **布局规范**
   - 保持适当留白(边距通常 48-96px)
   - 重要信息在视觉中心或黄金分割位置
   - 考虑阅读顺序(从上到下,从左到右,Z型或F型)
   - 对齐:相关元素使用统一的 x 或 y 坐标对齐

3. **色彩与对比**
   - 确保文本与背景有足够对比度(深色背景用浅色文字,反之亦然)
   - 使用 opacity 创建层次感
   - 装饰性元素可使用半透明色彩(opacity 0.1-0.3)

4. **图像元素**
   - 背景图像通常 zIndex 1-5, opacity 0.3-0.8
   - 主要内容图像 zIndex 20-30
   - 为图像提供清晰、详细的 description,包含:
     * 主体内容(如"消防员头盔")
     * 视角(俯视/正面/侧面)
     * 风格(写实/3D/插画/扁平)
     * 色调(暖色调/冷色调/黑白)
     * 背景(纯色/渐变/场景)
     * 光线(柔和/强烈/戏剧性)

5. **装饰元素**
   - 使用 shape + filter: blur() 创建光晕效果
   - 使用半透明的 shape 作为色块装饰
   - 使用 group + backdropFilter 创建毛玻璃效果

6. **分组组织**
   - 相关元素使用 group 组织(如日期+地点信息卡片)
   - group 可以有统一的背景、边框、模糊效果
   - 合理使用 parentId 表达嵌套关系

## 4. 输出示例
```json
{{
  "canvas": {{
    "width": 1080,
    "height": 1920,
    "background": "linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)"
  }},
  "elements": [
    {{
      "id": "bg-image-1",
      "type": "image",
      "parentId": null,
      "x": 0,
      "y": 0,
      "w": 1080,
      "h": 1920,
      "zIndex": 1,
      "opacity": 0.4,
      "attributes": {{
        "description": "抽象的深色背景,带有微妙的红色烟雾和火花,电影级光线,minimal纹理,8k分辨率,高对比度",
        "alt": "Background",
        "fit": "cover"
      }}
    }},
    {{
      "id": "decoration-blur-1",
      "type": "shape",
      "parentId": null,
      "x": 100,
      "y": 100,
      "w": 400,
      "h": 400,
      "zIndex": 5,
      "opacity": 0.3,
      "filter": "blur(100px)",
      "attributes": {{
        "shapeType": "circle",
        "fill": "#ff6b6b"
      }}
    }},
    {{
      "id": "main-title",
      "type": "text",
      "parentId": null,
      "x": 90,
      "y": 300,
      "w": 900,
      "h": 200,
      "zIndex": 30,
      "attributes": {{
        "content": "全民消防",
        "fontSize": 120,
        "fontFamily": "Noto Sans",
        "fontWeight": "900",
        "color": "#ffffff",
        "textAlign": "center",
        "lineHeight": 1.2,
        "letterSpacing": 10,
        "textShadow": "0px 10px 30px rgba(0, 0, 0, 0.5)",
        "styles": [
          {{
            "selection": [2, 4],
            "color": "#ff4757"
          }}
        ]
      }}
    }},
    {{
      "id": "info-card-group",
      "type": "group",
      "parentId": null,
      "x": 90,
      "y": 1400,
      "w": 900,
      "h": 200,
      "zIndex": 25,
      "radius": "16px",
      "opacity": 1,
      "attributes": {{
        "fill": "rgba(255, 255, 255, 0.1)",
        "backdropFilter": "blur(20px)",
        "border": "1px solid rgba(255, 255, 255, 0.2)"
      }}
    }},
    {{
      "id": "date-text",
      "type": "text",
      "parentId": "info-card-group",
      "x": 40,
      "y": 80,
      "w": 400,
      "h": 60,
      "zIndex": 26,
      "attributes": {{
        "content": "2025.12.18",
        "fontSize": 48,
        "fontFamily": "Inter",
        "fontWeight": "700",
        "color": "#ffffff",
        "textAlign": "left"
      }}
    }},
    {{
      "id": "hero-image",
      "type": "image",
      "parentId": null,
      "x": 140,
      "y": 700,
      "w": 800,
      "h": 600,
      "zIndex": 20,
      "filter": "contrast(1.1) saturate(1.1)",
      "attributes": {{
        "description": "3D等距渲染的消防员头盔、灭火器和安全盾牌,漂浮在空中,现代风格,红色和橙色配色,工作室光线,干净的背景",
        "alt": "Fire Safety Equipment",
        "fit": "contain",
        "prompt": "3D isometric render of firefighter helmet, fire extinguisher and safety shield, floating, modern style, red and orange color palette, studio lighting, clean background, high quality, 8k"
      }}
    }}
  ]
}}
```
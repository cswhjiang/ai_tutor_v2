from manim import *
import math

# ==========================================================================
# 旁白脚本配置 (Narration Script)
# RenderAgent 可读取此结构用于后期合成，同时代码内部也尝试使用 manim_voiceover
# ==========================================================================
NARRATION = [
    {
        "id": "S1_hook",
        "text": "如果一个班里有25个人，你能不能保证：至少有几个人的属相一定相同？",
        "hint": "标题展示"
    },
    {
        "id": "S2_drawers",
        "text": "把12个生肖想象成12个抽屉：鼠、牛、虎一直到猪。每个人都会被分到其中一个抽屉里。",
        "hint": "绘制12个方格和生肖标签"
    },
    {
        "id": "S3_people",
        "text": "现在我们用25个小圆点代表25个人。接下来做一件事：把他们一个个放进这12个生肖抽屉里。",
        "hint": "左侧显示25个圆点"
    },
    {
        "id": "S4_distribute_24",
        "text": "先看一种最平均的放法：让每个抽屉最多放2个人。12个抽屉如果每个装2个人，总共只能装下24个人。",
        "hint": "前24个点移动到抽屉"
    },
    {
        "id": "S5_distribute_25th",
        "text": "关键来了：现在还有第25个人。无论你把他放进哪个抽屉，都会让某个抽屉从2个人变成3个人。也就是说，至少有3个人属相相同。",
        "hint": "第25个点移动，高亮抽屉"
    },
    {
        "id": "S6_math",
        "text": "用抽屉原理写成算式就是：25除以12，商是2，还余1。前面的2表示每个抽屉平均装2个；多出来的1必然挤进某个抽屉，形成第3个人。",
        "hint": "右侧显示公式"
    },
    {
        "id": "S7_conclusion",
        "text": "这就是抽屉原理：当物体数超过抽屉能平均容纳的数量时，必然有某个抽屉装得更多。在这个问题里，答案就是：至少3个人属相相同。",
        "hint": "总结文字"
    }
]

# ==========================================================================
# 尝试导入 TTS 库，若失败则使用伪造类以保证代码不报错
# ==========================================================================
USE_VOICEOVER = False
try:
    from manim_voiceover import VoiceoverScene
    from manim_voiceover.services.gtts import GTTSService
    from manim_voiceover.services.pyttsx3 import PyTTSX3Service
    USE_VOICEOVER = True
except ImportError:
    # 如果没有安装 manim_voiceover，定义一个兼容的空类
    class VoiceoverScene(Scene):
        def construct(self):
            pass
        
        # 定义一个简单的上下文管理器来模拟 voiceover
        class FakeVoiceoverContext:
            def __init__(self, scene, text=None):
                self.scene = scene
                self.text = text
            def __enter__(self):
                if self.text:
                    print(f"[模拟旁白] {self.text}")
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.scene.wait(0.5)

        def voiceover(self, text=None, **kwargs):
            return self.FakeVoiceoverContext(self, text)

# ==========================================================================
# 主场景类
# ==========================================================================
class ZodiacPigeonhole(VoiceoverScene):
    def construct(self):
        # --- TTS 配置 ---
        if USE_VOICEOVER:
            # 优先尝试 pyttsx3 (离线)，若失败或为了效果可用 GTTSService (需网络)
            try:
                self.set_speech_service(PyTTSX3Service(voice=None, lang="zh")) # 系统默认中文
            except:
                self.set_speech_service(GTTSService(lang="zh-CN"))

        # ==================== S1: 引入问题 ====================
        # 旁白：如果一个班里有25个人...
        with self.voiceover(text=NARRATION[0]["text"]):
            title = Text("25个人里至少有几个人属相相同？", font_size=36)
            self.play(Write(title))
            self.wait(1)
            self.play(title.animate.to_edge(UP))

        # ==================== S2: 展示抽屉 ====================
        # 旁白：把12个生肖想象成12个抽屉...
        labels = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
        
        # 创建抽屉组
        drawers = VGroup()
        drawer_labels = VGroup()
        
        # 抽屉样式
        drawer_w, drawer_h = 1.6, 1.2
        
        for i in range(12):
            box = RoundedRectangle(
                width=drawer_w,
                height=drawer_h,
                corner_radius=0.15,
                stroke_width=3,
                color=BLUE_C
            )
            # 生肖文字 (注意：MathTex不支持中文，必须用Text)
            lab = Text(labels[i], font_size=24, color=WHITE)
            # 暂存，稍后统一布局
            drawers.add(box)
            drawer_labels.add(lab)

        # 布局：3行4列
        drawers.arrange_in_grid(rows=3, cols=4, buff=0.25)
        drawers.move_to(UP * 0.5) # 稍微靠上，留出底部给字幕
        
        # 关键修复：逐个对齐标签到抽屉中心
        for i, lab in enumerate(drawer_labels):
            lab.move_to(drawers[i].get_center())

        with self.voiceover(text=NARRATION[1]["text"]):
            self.play(LaggedStartMap(Create, drawers, lag_ratio=0.1), run_time=2)
            self.play(LaggedStartMap(FadeIn, drawer_labels, lag_ratio=0.1), run_time=1.5)
        
        self.wait(0.5)

        # ==================== S3: 展示25个人 ====================
        # 旁白：现在我们用25个小圆点代表25个人...
        people = VGroup()
        for k in range(25):
            # 使用 Circle 而非 SVG 保证兼容性
            p = Circle(radius=0.08, stroke_width=0, fill_opacity=1, fill_color=YELLOW)
            people.add(p)

        # 5x5 排列在左侧
        people.arrange_in_grid(rows=5, cols=5, buff=0.15)
        people.to_edge(LEFT, buff=0.8).shift(DOWN * 0.5)
        
        people_label = Text("25个人", font_size=24, color=YELLOW)
        people_label.next_to(people, UP, buff=0.2)

        with self.voiceover(text=NARRATION[2]["text"]):
            self.play(FadeIn(people, shift=RIGHT*0.5), Write(people_label))
        
        self.wait(0.5)

        # ==================== S4: 分配前24个人 ====================
        # 旁白：先看一种“最平均”的放法...
        
        # 底部提示条
        tip = Text("把25个人分到12个生肖抽屉里…", font_size=24, color=GRAY_A)
        tip.to_edge(DOWN, buff=0.8)
        
        with self.voiceover(text=NARRATION[3]["text"]):
            self.play(Write(tip))
            
            # 计算槽位偏移
            # 每个抽屉放3个槽位的相对位置：左上，右上，正下
            offsets = [
                LEFT * 0.35 + UP * 0.25,
                RIGHT * 0.35 + UP * 0.25,
                DOWN * 0.3
            ]
            
            # 记录每个抽屉当前的计数
            counts = [0] * 12
            
            anims = []
            # 分配前24个人 (indices 0 to 23)
            for i in range(24):
                drawer_idx = i % 12
                slot_idx = counts[drawer_idx]
                counts[drawer_idx] += 1
                
                target_pos = drawers[drawer_idx].get_center() + offsets[slot_idx]
                anims.append(people[i].animate.move_to(target_pos))

            # 分批播放动画，避免卡顿，每批6个
            batch_size = 6
            for i in range(0, 24, batch_size):
                batch_anims = anims[i : i+batch_size]
                # 播放这批动画
                self.play(*batch_anims, run_time=1.0, rate_func=smooth)
            
            self.wait(0.5)

        # ==================== S5: 第25个人与高亮 ====================
        # 旁白：关键来了：现在还有第25个人...
        
        tip2 = Text("必然有某个抽屉出现第3个人！", font_size=24, color=YELLOW)
        tip2.to_edge(DOWN, buff=0.8)

        with self.voiceover(text=NARRATION[4]["text"]):
            self.play(ReplacementTransform(tip, tip2))
            
            # 第25个人 (index 24) 放入第一个抽屉 (idx 0)
            last_person = people[24]
            target_drawer_idx = 0
            target_slot_idx = counts[target_drawer_idx] # 应该是 2
            
            target_pos = drawers[target_drawer_idx].get_center() + offsets[target_slot_idx]
            
            self.play(last_person.animate.move_to(target_pos).scale(1.5).set_color(RED), run_time=1.5)
            
            # 高亮该抽屉
            highlight_rect = SurroundingRectangle(drawers[target_drawer_idx], color=RED, buff=0.1, stroke_width=4)
            self.play(Create(highlight_rect))
            self.wait(0.5)

        # ==================== S6: 公式结论 ====================
        # 旁白：用抽屉原理写成算式就是...
        
        # 准备公式文本
        # 注意：MathTex不含中文
        eq1 = MathTex(r"25 \div 12 = 2 \cdots 1", font_size=36)
        
        # 结论行拆分：Text(中文) + MathTex(公式)
        # "至少有 2+1=3 人属相相同"
        line2_pre = Text("至少有 ", font_size=30)
        line2_math = MathTex(r"2 + 1 = 3", font_size=36)
        line2_post = Text(" 人属相相同", font_size=30)
        
        line2_group = VGroup(line2_pre, line2_math, line2_post).arrange(RIGHT, buff=0.1)
        
        formula_group = VGroup(eq1, line2_group).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        formula_group.to_edge(RIGHT, buff=1.0).shift(DOWN * 1.5)
        
        # 加上背景板增加可读性
        bg = BackgroundRectangle(formula_group, fill_opacity=0.8, buff=0.2)

        with self.voiceover(text=NARRATION[5]["text"]):
            self.play(FadeIn(bg), Write(eq1))
            self.wait(0.5)
            self.play(Write(line2_group))
        
        self.wait(1)

        # ==================== S7: 总结 ====================
        # 旁白：这就是抽屉原理...
        
        end_text = Text("抽屉原理：物体数 > 抽屉数 → 必有抽屉 > 1", font_size=28, color=WHITE)
        end_text.to_edge(DOWN, buff=0.8)

        with self.voiceover(text=NARRATION[6]["text"]):
            self.play(ReplacementTransform(tip2, end_text))
            # 强调最后的结论
            self.play(Indicate(line2_group, color=YELLOW))
            self.wait(2)
        
        # 清理画面（可选）
        self.play(FadeOut(Group(*self.mobjects)))

# 运行提示
# manim -pqh your_script.py ZodiacPigeonhole
# Execution result: agent 1 视频生成失败Invalid \escape: line 2 column 6138 (char 6139)
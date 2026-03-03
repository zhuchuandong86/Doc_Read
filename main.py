import os
from concurrent.futures import ThreadPoolExecutor
from api_client import call_api
from parsers.image_parser import encode_and_compress_image
from config import MODEL_BLUE, MODEL_RED, MODEL_EDITOR, MODEL_TEXT



def process_single_page(image_path, page_num):
    """视觉引擎：负责单张图片的解析与数据清洗"""
    print(f"👉 正在深度解析并清洗页面 {page_num}: {os.path.basename(image_path)}...")
    try:
        base64_img = encode_and_compress_image(image_path)
    except Exception as e:
        return f"--- ⚠️ 图片预处理失败: {e} ---"
    
    messages = [{
        "role": "user",
        "content": [
            {
                "type": "text", 
                "text": f"这是电信运营商经营分析/网络分析报告的第 {page_num} 页。\n你现在的角色是严谨的『数据清洗与提取专家』。\n\n【提取与清洗规则】：\n1. 🛑 自动过滤噪音：绝对不要提取无意义的页眉、页脚、单纯的页码、背景水印、版权声明或无法识别的乱码。\n2. 📊 表格规范化：将所有财报表格、饼图、折线图转化为格式极其干净、对齐的标准 Markdown 表格。\n3. 📝 文本结构化：正文请保持清爽的排版，多用无序列表('- ')，去除原文中为了排版而产生的多余换行。\n4. 🚫 严禁主观加工：不要对数据进行任何评价或总结，只需忠实、干净地还原核心有效信息。"
            },
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
        ]
    }]
    from config import MODEL_VISION
    result = call_api(messages, model_name=MODEL_VISION, stream=False)
    return result.strip()


def get_safe_text_for_model(text, model_name):
    """【新增功能】：根据不同模型的真实上下文上限，动态截断文本"""
    limit = 40000  # 默认基准线
    name_lower = model_name.lower()
    
    if "deepseek-v3-0324" in name_lower:
        limit = 38000   # 明确已知 32k 限制，严格掐断防 400 报错
    elif "deepseek-r1" in name_lower:
        limit = 60000   # R1 通常部署 64k 左右的上下文
    elif "72b" in name_lower or "30b" in name_lower or "256k" in name_lower:
        limit = 120000  # Qwen 大家族原生 128k 起步，放宽限制
        
    if len(text) > limit:
        print(f"✂️ [安全管控] {model_name} 触发阈值，已动态截断至 {limit} 字符...")
        return text[:limit] + f"\n\n...[警告：由于 {model_name} 算力限制，尾部内容已安全截断]..."
    return text


def _call_specialist_agent(role_prompt, full_text, model_name, agent_name):
    """用于调用红/蓝军专家的内部并发函数"""
    print(f"[{agent_name}] 正在独立阅卷分析中...")
    
    # 【改动点】：获取当前模型能安全吃下的文本长度
    safe_text = get_safe_text_for_model(full_text, model_name)
    
    messages = [
        {"role": "system", "content": role_prompt},
        {"role": "user", "content": f"以下是完整的财报或者经营分析、网络分析报告提取数据，请严格按照你的角色设定，指出具体问题（必须标明来源页码）：\n\n{safe_text}"}
    ]
    # 【改动点】：开启 stream=True 防 504，同时开启 silent_stream=True 防止控制台字体重叠打架
    return call_api(messages, model_name=model_name, stream=True, silent_stream=True)


def generate_final_summary(full_text):
    """大脑引擎升级：Multi-Agent 红蓝对抗工作流 (带专家底稿保留)"""
    
    # 【改动点】：删除了原先死板的 MAX_CHAR_LIMIT = 20000 全局截断

    print("\n🤖 [Multi-Agent 启动] 正在唤醒虚拟专家团队进行红蓝对抗...")
    
    # ---------------------------------------------------------
    # 第一阶段：红蓝两军并发独立看报告
    # ---------------------------------------------------------
    blue_prompt = "你是一位极其严苛的『蓝军风控官』。你的唯一任务是：只找问题，不看成绩。请穿透字面意思，找出所有隐性风险、成本压力、业务下滑迹象等负面信号。必须极其犀利，并在每一条风险后标注 [来源文件：X页]。"
    
    red_prompt = "你是一位极具商业嗅觉的『红军战略官』。你的唯一任务是：寻找增长引擎。请专注发掘业务亮点、第二曲线潜力、高增长板块等积极信号。请保持客观乐观，并在每一个亮点后标注 [来源文件：X页]。"
    
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as executor:
        # 注意：这里会把你的 full_text 传进函数，在函数内部进行动态截断
        future_blue = executor.submit(_call_specialist_agent, blue_prompt, full_text, MODEL_BLUE, "🔵 蓝军风控官")
        future_red = executor.submit(_call_specialist_agent, red_prompt, full_text, MODEL_RED, "🔴 红军战略官")
        
        blue_report = future_blue.result()
        red_report = future_red.result()
        
    print("✅ 红蓝两军辩论完毕！正在交由 [👨‍⚖️ 首席主编] 融合并输出最终报告...")

    # ---------------------------------------------------------
    # 第二阶段：主编 Agent 汇总输出
    # ---------------------------------------------------------
    # 【改动点】：为主编模型单独进行一次安全文本截断
    editor_safe_text = get_safe_text_for_model(full_text, MODEL_EDITOR)
    
    editor_messages = [
        {
            "role": "system", 
            "content": "你现在是一位供职于顶级投行与战略咨询公司的【首席电信行业商业分析师兼资深行业专家】。你极其擅长穿透数据，从枯燥的经营数据中推演出企业的真实战略走向、业务健康度和潜在危机。你的最高原则是【数据驱动】和【绝对客观】。"
        },
        {
            "role": "user", 
            "content": f"""你现在拥有三份核心输入资料。请结合红蓝双方的意见，对原始数据进行最终判决。

【资料一：原始提取数据】：
{editor_safe_text}
---
【资料二：蓝军风控专家意见】：
{blue_report}
---
【资料三：红军战略专家意见】：
{red_report}

【最高执行指令（铁律）】：
1. **尽力而为与客观免责**：无论数据多么残缺，只要包含业务/财务数字，都请基于这些【仅有】的数据进行深度逻辑推演。对于缺失维度，请以专业口吻客观注明“受限于披露口径，原文件未见相关数据”，**绝不允许靠常识瞎编**。
2. **强制精准溯源与排版（极其重要）**：
   - 你在报告中引用的**每一个**具体数据、结论、风险，**必须在句子末尾精确标注来源页码，并严格使用 HTML 的 span 标签包裹**。
   - 格式标准：`*<span style="color: gray;">[来源：第X页]</span>*`
   - **排版要求：在输出无序列表（使用 `- ` 开头）时，每一个列表项必须独立成行，末尾必须带有回车换行符，绝不能将多个列表项挤在同一行。**
   - 示例示范：
     - 政企DICT业务收入同比增长15% *<span style="color: gray;">[来源：第4页]</span>*
     - 整体毛利率出现下滑迹象 *<span style="color: gray;">[来源：第5页]</span>*
3. **零幻觉容忍**：如果在原始数据中找不到对应的页码支撑，请直接在你的脑海中删掉这句话，严禁泛泛而谈。

请严格基于原文数据，按照以下五大专业维度输出《深度商业经营研判报告》：
            
1. **📊 经营成果与财务/网络体检 (Financial & Operational Results)**
- **数据透视**：梳理核心指标，如营收、利润、EBITDA、ARPU、用户规模等，如果没有就退而求其次，不要罗列没有的数据。（包含同比/环比增速、横向其他省分对比情况）,。
- **质量评估**：不仅要看绝对值，还要分析增长质量,如果没有就退而求其次，不要罗列没有的数据。（例如：是否存在“增收不增利”的剪刀差？各项成本（如网络运维、折旧、营销费用）的管控效率如何？）

2. **🎯 战略演进与增长引擎 (Strategy & Growth Engines)**
- **战略解码**：基于管理层的表述与实际资源倾斜，研判企业当前的核心战略方向。
- **第二曲线**：深度分析新业务（如云算力、AI、政企大客户、低空经济等）的营收占比与增速贡献。这些新业务是否已经大到足以弥补传统业务的衰退？

3. **⚠️ 风险穿透与压力洞察 (Risk & Pressure Penetration)**
- **显性风险**：直接点出报告中承认的下滑指标和受挫业务。
- **隐性风控**：拿着放大镜寻找可能的隐藏危机。（不超过3-5条，没有不要硬编；例如：应收账款周期是否拉长？资本开支（CAPEX）是否对现金流造成重压？是否有激进的价格战迹象？传统基本盘是否面临见顶失速风险？）

4. **💡 首席分析师战略谏言 (Analyst's Strategic Recommendations)**
- **行动指南**：基于上述暴露的问题，给出犀利、可落地的管理层建议（不超过3-5条，没有不要硬编；例如：剥离某项低效资产、优化定价策略、收缩某项资本开支、调整组织阵型等）。拒绝“假大空”的废话。

5. **📈 核心数据资产总表 (Master Data Table)**
- 将提取到的最重要的核心KPI整合为一张格式极简、对齐完美的 Markdown 表格。
- 表格必须包含：指标名称、当前数值/表现、同环比变化、横向其他省分对比。
- **表格最后一列必须是“数据来源”，且标注具体的页码。**

以下是完整的原文件提取内容：

"""
        }
    ]
    
    # 首席主编流式输出打字机效果
    final_summary = call_api(editor_messages, model_name=MODEL_EDITOR, stream=True)
    
    if "⚠️ 本次提取彻底失败" in final_summary:
        print(f"\n🚨 警告：主编模型 {MODEL_EDITOR} 调用失败！")
        return final_summary
        
    # ---------------------------------------------------------
    # 第三阶段：【新增】缝合红蓝军原始底稿，作为附录保留
    # ---------------------------------------------------------
    preserved_agent_reports = f"""

---

## 🗂️ 专家组独立研判底稿 (Multi-Agent 视角)

<details markdown="1">
<summary>🔵 点击展开【蓝军风控官】的原始挑刺报告</summary>

{blue_report}

</details>

<details markdown="1">
<summary>🔴 点击展开【红军战略官】的原始增长报告</summary>

{red_report}

</details>
"""
    # 将底稿拼接到主编最终报告的尾部返回给 WebUI
    return final_summary + preserved_agent_reports

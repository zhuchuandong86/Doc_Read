import streamlit as st
import os
import time
from datetime import datetime
from renderers.excel_builder import export_tables_to_excel  # 👈 【新增这一行】

# ==========================================
# 1. 核心路径防呆设计 (彻底解决目录混乱)
# ==========================================
# 获取 webui.py 当前所在的绝对路径（即 06_文件总结 文件夹）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 规范化所有的输出目录，强制建在 06_文件总结 里面
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
UPLOAD_DIR = os.path.join(OUTPUT_DIR, "uploads")             # 存放所有上传的原文件
TEMP_IMG_DIR = os.path.join(OUTPUT_DIR, "pdf_temp_images")   # 存放 PDF 拆解图

# 确保目录永远存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_IMG_DIR, exist_ok=True)

# 导入底层核心模块
from utils import natural_sort_key
from parsers.pdf_parser import convert_pdf_to_images
from main import process_single_page, generate_final_summary
from renderers.html_builder import export_to_html

# 华为内网代理设置
os.environ['NO_PROXY'] = 'api.openai.rnd.huawei.com'

# ==========================================
# 2. 页面基本设置
# ==========================================
st.set_page_config(
    page_title="AI 经营分析工作台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/combo-chart--v1.png", width=60)
    st.title("系统面板")
    st.markdown("---")
    max_pages = st.number_input("最大解析页数 (防超载)", min_value=1, max_value=500, value=50)
    st.markdown("---")
    st.success(f"📁 **数据存储路径已锁定:**\n\n所有的原文件和报告都会自动保存在:\n`{OUTPUT_DIR}`")

st.markdown("### 📊 AI 材料深度解读工作台")  # 两个 # 号，大小刚刚好，不突兀
st.markdown("基于 Qwen-VL 与 DeepSeek 多模型引擎，自动读取图文并进行红蓝军对抗生成商业洞察。")

# ==========================================
# 3. 双轨工作流（标签页设计）
# ==========================================
tab1, tab2 = st.tabs(["🚀 全流程智能解析 (传 PDF / 图片)", "⚡ 断点续传与重新生成 (直接传 MD)"])

# ---------------------------------------------------------
# 工作流 A：全流程解析 (看图 -> 提取 -> 总结 -> 网页)
# ---------------------------------------------------------
with tab1:
    st.markdown("###### 📥 步骤一：上传原始文件")
    uploaded_files = st.file_uploader(
        "请将需要分析的 PDF 报告或 PPT 截图拖拽至此", 
        type=["pdf", "png", "jpg", "jpeg"], 
        accept_multiple_files=True,
        key="full_pipeline"
    )

    if st.button("🚀 开始全流程深度研判", type="primary", key="btn_full"):
        if not uploaded_files:
            st.warning("⚠️ 请先上传至少一个文件！")
            st.stop()
            
        status_text = st.empty()
        progress_bar = st.progress(0)
        image_paths = []
        
        # 1. 接收文件并永久保存到 uploads 目录
        status_text.info("📦 正在接收并备份上传的文件...")
        timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S_") # 时间戳前缀防覆盖
        
        for file in uploaded_files:
            # 文件名加上时间戳，存入 uploads 文件夹
            safe_filename = timestamp_prefix + file.name
            file_path = os.path.join(UPLOAD_DIR, safe_filename)
            
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
                
            # 解析刚才保存的本地文件
            if file.name.lower().endswith('.pdf'):
                pdf_imgs = convert_pdf_to_images(file_path, TEMP_IMG_DIR, max_pages)
                image_paths.extend(pdf_imgs)
            else:
                image_paths.append(file_path)
                
        if max_pages: image_paths = image_paths[:max_pages]
            
        total_pages = len(image_paths)
        if total_pages == 0:
            st.error("❌ 未能成功提取任何页面，请检查文件格式。")
            st.stop()

        # 2. 视觉解析
        all_content = ""
        st.markdown("###### 👁️ 步骤二：视觉引擎解析监控")
        with st.expander("👉 点击展开查看各页提取明细", expanded=False):
            log_placeholder = st.empty()
            log_text = ""
            for i, path in enumerate(image_paths):
                status_text.warning(f"👁️ 视觉引擎正在解析第 {i+1}/{total_pages} 页...")
                result = process_single_page(path, i + 1)
                
                filename_raw = os.path.basename(path)
                source_name = filename_raw.split('_page_')[0] if '_page_' in filename_raw else filename_raw
                page_block = f"\n\n> 📁 **[来源文件：{source_name}]** - 第 {i+1} 页提取内容\n{result}\n"
                all_content += page_block
                
                log_text += f"**✅ 第 {i+1} 页提取完成**\n\n"
                log_placeholder.markdown(log_text)
                progress_bar.progress((i + 1) / total_pages)
                
        # 实时保存一份最新的 MD 提取底稿 (覆盖式，方便断点续传快速找)
        temp_md_path = os.path.join(OUTPUT_DIR, "最新提取缓存底稿.md")
        with open(temp_md_path, "w", encoding="utf-8") as f:
            f.write(all_content)
                
        # 3. 大脑深度总结
        status_text.success("✅ 视觉提取完毕！即将进入大脑深度研判...")
        progress_bar.empty()
        st.markdown("###### 🧠 步骤三：深度研判报告生成中")
        with st.spinner('DeepSeek 正在进行交叉比对与财务推演 (请查看命令行后台的打字机输出)...'):
            summary = generate_final_summary(all_content)
            
        st.success("🎉 研判报告已生成！")
        st.markdown("---")
        st.markdown(summary)
        
# ---------- 替换开始 ----------
        # 生成带时间戳的最终持久化文件
        final_md_content = f"# AI 深度洞察与业务研判报告\n\n{summary}\n\n---\n## 📚 附录：已清洗的分页底层数据\n<details markdown=\"1\">\n<summary>👉 点击展开查看各页原始核心数据 (已过滤噪音)</summary>\n\n{all_content}\n</details>"
        
        final_md_file = os.path.join(OUTPUT_DIR, f"AI研判报告_{timestamp_prefix[:-1]}.md")
        with open(final_md_file, "w", encoding="utf-8") as f:
            f.write(final_md_content)
            
        final_html_file = os.path.join(OUTPUT_DIR, f"AI研判网页版_{timestamp_prefix[:-1]}.html")
        export_to_html(final_md_content, final_html_file)

        # 【新增：生成 Excel 文件】
        final_excel_file = os.path.join(OUTPUT_DIR, f"提取数据表_{timestamp_prefix[:-1]}.xlsx")
        has_excel = export_tables_to_excel(final_md_content, final_excel_file)
        
        # 提供下载 (动态判断：如果有表格，就显示 3 个按钮；没有表格，就只显示 2 个)
        st.markdown("### 💾 导出报告")
        cols = st.columns(3 if has_excel else 2)
        
        with cols[0]:
            with open(final_md_file, "r", encoding="utf-8") as f:
                st.download_button("⬇️ 下载 Markdown 归档版", f, file_name=f"AI研判报告_{timestamp_prefix[:-1]}.md")
        with cols[1]:
            with open(final_html_file, "r", encoding="utf-8") as f:
                st.download_button("🌐 下载精美 HTML 网页版", f, file_name=f"AI研判网页版_{timestamp_prefix[:-1]}.html")
                
        # 如果成功提取到了 Excel，渲染第三个按钮
        if has_excel:
            with cols[2]:
                with open(final_excel_file, "rb") as f:
                    st.download_button(
                        "📊 下载 Excel 数据表", 
                        f, 
                        file_name=f"提取数据表_{timestamp_prefix[:-1]}.xlsx", 
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        # ---------- 替换结束 ----------


# ---------------------------------------------------------
# 工作流 B：断点续传 (直接吃 MD -> 总结 -> 网页)
# ---------------------------------------------------------
with tab2:
    st.markdown("###### 📥 步骤一：上传已有的 Markdown 数据文件")
    st.info("如果你之前提取的文本保存为了 `.md` 文件，将它传到这里，将直接跳过看图环节。")
    
    uploaded_md = st.file_uploader(
        "请将带有提取文本的 .md 文件拖拽至此", 
        type=["md"],
        key="md_pipeline"
    )
    
    if st.button("⚡ 直接生成深度分析与 HTML", type="primary", key="btn_md"):
        if not uploaded_md:
            st.warning("⚠️ 请先上传 .md 文件！")
            st.stop()
            
        # 1. 永久备份上传的 MD 文件
        timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S_")
        safe_md_filename = timestamp_prefix + uploaded_md.name
        md_save_path = os.path.join(UPLOAD_DIR, safe_md_filename)
        
        all_content = uploaded_md.getvalue().decode("utf-8")
        with open(md_save_path, "w", encoding="utf-8") as f:
            f.write(all_content)
            
        if not all_content.strip():
            st.error("❌ 文件内容为空！")
            st.stop()
            
        # 2. 开始总结
        st.markdown("###### 🧠 步骤二：大脑深度研判报告生成中")
        with st.spinner('正在直接读取文本并进行研判分析...'):
            summary = generate_final_summary(all_content)
            
        st.success("🎉 基于 MD 的研判报告已极速生成！")
        st.markdown("---")
        st.markdown(summary)
        
        # 3. 生成带时间戳的持久化文件
        final_md_content = f"# AI 深度洞察与业务研判报告\n\n{summary}\n\n---\n## 📚 附录：已清洗的分页底层数据\n<details markdown=\"1\">\n<summary>👉 点击展开查看各页原始核心数据 (已过滤噪音)</summary>\n\n{all_content}\n</details>"
        
        final_md_file = os.path.join(OUTPUT_DIR, f"极速直出报告_{timestamp_prefix[:-1]}.md")
        with open(final_md_file, "w", encoding="utf-8") as f:
            f.write(final_md_content)
            
        final_html_file = os.path.join(OUTPUT_DIR, f"极速直出网页版_{timestamp_prefix[:-1]}.html")
        export_to_html(final_md_content, final_html_file)
        
        # 4. 提供下载
        st.markdown("###### 💾 导出报告")
        col1, col2 = st.columns(2)
        with col1:
            with open(final_md_file, "r", encoding="utf-8") as f:
                st.download_button("⬇️ 下载 Markdown 归档版", f, file_name=f"极速直出报告_{timestamp_prefix[:-1]}.md")
        with col2:
            with open(final_html_file, "r", encoding="utf-8") as f:
                st.download_button("⬇️ 下载精美 HTML 网页版", f, file_name=f"极速直出网页版_{timestamp_prefix[:-1]}.html")


    #streamlit run 06_文件总结/webui.py

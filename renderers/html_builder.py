import markdown

def export_to_html(markdown_text, output_html_path):
    """将 Markdown 渲染为带有商用 CSS 样式的精美 HTML"""
    # 【修复点 1】：在 extensions 里加上 'md_in_html'，这是让 details 标签内支持表格的核心！
    html_body = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code', 'md_in_html'])
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI文档分析报告</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 40px 20px; background-color: #f9f9fa; }}
            .report-container {{ background-color: #ffffff; padding: 40px 50px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            h1 {{ font-size: 2.2em; text-align: center; color: #2563eb; border-bottom: none; }}
            h2, h3 {{ color: #1a202c; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; margin-top: 1.5em; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 0.95em; }}
            th, td {{ border: 1px solid #dfe2e5; padding: 12px 16px; text-align: left; }}
            th {{ background-color: #f6f8fa; font-weight: 600; }}
            tr:nth-child(even) {{ background-color: #fafbfc; }}
            blockquote {{ margin: 0; padding: 15px 20px; background-color: #f0f7ff; border-left: 5px solid #2563eb; color: #4b5563; border-radius: 0 8px 8px 0; }}
            details {{ margin-top: 20px; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fafafa; }}
            summary {{ font-weight: bold; cursor: pointer; outline: none; color: #4b5563; }}
        </style>
    </head>
    <body>
        <div class="report-container">
            {html_body}
        </div>
    </body>
    </html>
    """
    
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_template)

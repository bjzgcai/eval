#!/usr/bin/env python3
"""
维度HTML详情页面生成器
生成美观的维度分析详情HTML页面
"""

import json
from typing import Dict, Any
from pathlib import Path


class DimensionHtmlGenerator:
    """维度HTML详情页面生成器"""
    
    def __init__(self):
        self.dimension_names = {
            1: "代码结构与可维护性",
            2: "测试覆盖与质量保障", 
            3: "构建与工程可重复性",
            4: "依赖与许可证合规",
            5: "安全性与敏感信息防护",
            6: "CI/CD 自动化保障",
            7: "使用文档与复现性",
            8: "接口与平台兼容性",
            9: "协作流程与代码规范",
            10: "开源协议与法律合规",
            11: "社区治理与贡献机制",
            12: "舆情与风险监控",
            13: "数据与算法合规审核",
            14: "IP（知识产权）"
        }
    
    def generate_dimension_html(self, dimension_data: Dict[str, Any]) -> str:
        """
        生成维度分析HTML页面
        
        Args:
            dimension_data: 维度JSON数据
            
        Returns:
            HTML页面内容
        """
        try:
            dimension_info = dimension_data.get('dimension_info', {})
            analysis_summary = dimension_data.get('analysis_summary', {})
            metrics = dimension_data.get('metrics', {})
            tools_analysis = dimension_data.get('tools_analysis', {})
            insights = dimension_data.get('insights', [])
            project_context = dimension_data.get('project_context', {})
            
            # 基本信息
            dimension_name = dimension_info.get('dimension_name', '未知维度')
            score = dimension_info.get('score', 0)
            status = dimension_info.get('status', 'UNKNOWN')
            analysis_level = dimension_info.get('analysis_level', 'basic')
            
            # 状态颜色
            status_colors = {
                'EXCELLENT': '#28a745',
                'GOOD': '#27ae60', 
                'WARN': '#ffc107',
                'FAIL': '#dc3545',
                'UNKNOWN': '#6c757d'
            }
            status_color = status_colors.get(status, '#6c757d')
            
            html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dimension_name} - 维度详情分析</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: #f8f9fa; 
            color: #212529;
        }}
        .container {{ 
            max-width: 1000px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.1); 
        }}
        .header {{ 
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
            color: white; 
            padding: 30px; 
            border-radius: 12px 12px 0 0; 
        }}
        .content {{ padding: 30px; }}
        .overview-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin: 20px 0; 
        }}
        .overview-card {{ 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 8px; 
            text-align: center;
            border-left: 4px solid #27ae60;
        }}
        .overview-card h3 {{ margin: 0 0 10px 0; color: #495057; font-size: 14px; }}
        .overview-card .value {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
        .section {{ 
            margin: 30px 0; 
            padding: 20px; 
            border-radius: 8px; 
            background: #f8f9fa; 
        }}
        .section h2 {{ 
            color: #495057; 
            margin: 0 0 20px 0; 
            padding-bottom: 10px; 
            border-bottom: 2px solid #27ae60; 
        }}
        .tool-grid {{ 
            display: grid; 
            gap: 15px; 
            margin: 15px 0; 
        }}
        .tool-card {{ 
            background: white; 
            padding: 15px; 
            border-radius: 6px; 
            border-left: 4px solid #27ae60; 
        }}
        .tool-card.failed {{ border-left-color: #dc3545; }}
        .tool-card.success {{ border-left-color: #28a745; }}
        .tool-name {{ font-weight: bold; color: #495057; }}
        .tool-status {{ 
            display: inline-block; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-size: 12px; 
            color: white; 
            margin-left: 10px;
        }}
        .tool-status.success {{ background-color: #28a745; }}
        .tool-status.failed {{ background-color: #dc3545; }}
        .tool-details {{ margin-top: 10px; font-size: 14px; color: #6c757d; }}
        .ai-analysis {{ 
            background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%); 
            padding: 20px; 
            border-radius: 8px; 
            margin: 20px 0;
            border-left: 4px solid #27ae60;
        }}
        .insight-card {{ 
            background: white; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 6px; 
            border-left: 4px solid #27ae60; 
        }}
        .insight-title {{ font-weight: bold; color: #495057; margin-bottom: 8px; }}
        .insight-description {{ color: #6c757d; margin-bottom: 10px; }}
        .suggestion-list {{ list-style: none; padding: 0; margin: 0; }}
        .suggestion-list li {{ 
            padding: 4px 0; 
            position: relative; 
            padding-left: 20px;
        }}
        .suggestion-list li::before {{ 
            content: "•"; 
            color: #27ae60; 
            position: absolute; 
            left: 0; 
        }}
        .back-link {{ 
            display: inline-block; 
            padding: 10px 20px; 
            background: #27ae60; 
            color: white; 
            text-decoration: none; 
            border-radius: 4px; 
            margin-bottom: 20px;
        }}
        .back-link:hover {{ background: #1e8449; }}
        .score-badge {{ 
            display: inline-block; 
            padding: 8px 16px; 
            background: {status_color}; 
            color: white; 
            border-radius: 20px; 
            font-weight: bold; 
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="../{project_context.get('project_name', 'unknown')}_audit_report.html" class="back-link">← 返回总览</a>
            <h1>{dimension_name}</h1>
            <p>分析时间: {dimension_info.get('analysis_timestamp', 'N/A')}</p>
            <p>分析级别: {self._format_analysis_level(analysis_level)}</p>
        </div>
        
        <div class="content">
            <!-- 评估概览 -->
            <div class="section">
                <h2>评估概览</h2>
                <div class="overview-grid">
                    <div class="overview-card">
                        <h3>综合得分</h3>
                        <div class="value">{score:.1f}/100</div>
                    </div>
                    <div class="overview-card">
                        <h3>评估状态</h3>
                        <div class="score-badge">{self._format_status(status)}</div>
                    </div>
                    <div class="overview-card">
                        <h3>问题总数</h3>
                        <div class="value">{metrics.get('total_issues', 0)}</div>
                    </div>
                    <div class="overview-card">
                        <h3>工具覆盖率</h3>
                        <div class="value">{metrics.get('coverage_percentage', 0):.1f}%</div>
                    </div>
                </div>
            </div>
            
            <!-- 项目上下文 -->"""
            
            if project_context:
                html += f"""
            <div class="section">
                <h2>项目上下文</h2>
                <div class="overview-grid">
                    <div class="overview-card">
                        <h3>项目名称</h3>
                        <div class="value" style="font-size: 16px;">{project_context.get('project_name', 'N/A')}</div>
                    </div>
                    <div class="overview-card">
                        <h3>主要语言</h3>
                        <div class="value" style="font-size: 16px;">{project_context.get('primary_language', 'N/A')}</div>
                    </div>
                    <div class="overview-card">
                        <h3>项目类型</h3>
                        <div class="value" style="font-size: 16px;">{project_context.get('project_type', 'N/A').replace('ProjectType.', '')}</div>
                    </div>
                    <div class="overview-card">
                        <h3>项目规模</h3>
                        <div class="value" style="font-size: 16px;">{project_context.get('size_category', 'N/A')}</div>
                    </div>
                </div>
            </div>"""
            
            # 工具分析
            if tools_analysis and 'tools_used' in tools_analysis:
                html += f"""
            <div class="section">
                <h2>工具执行分析</h2>
                <p><strong>使用工具:</strong> {', '.join(tools_analysis.get('tools_used', []))}</p>
                <div class="tool-grid">"""
                
                tool_results = tools_analysis.get('tool_results_summary', {})
                for tool_name, result in tool_results.items():
                    if result:
                        status_class = "success" if result.get('success', False) else "failed"
                        status_text = "成功" if result.get('success', False) else "失败"
                        
                        html += f"""
                    <div class="tool-card {status_class}">
                        <div class="tool-name">
                            {tool_name}
                            <span class="tool-status {status_class}">{status_text}</span>
                        </div>
                        <div class="tool-details">
                            <strong>执行时间:</strong> {result.get('execution_time', 0):.2f}秒 | 
                            <strong>发现问题:</strong> {result.get('issues_count', 0)}个 | 
                            <strong>评分:</strong> {result.get('score', 0)}
                        </div>
                        {f'<div class="tool-details"><strong>总结:</strong> {result["summary"]}</div>' if result.get('summary') else ''}
                    </div>"""
                
                html += """
                </div>
            </div>"""
            
            # AI智能分析
            ai_analysis = analysis_summary.get('ai_analysis')
            ai_recommendations = analysis_summary.get('ai_recommendations', [])
            
            if ai_analysis and ai_analysis.strip() and "基于规则分析" not in ai_analysis:
                html += f"""
            <div class="ai-analysis">
                <h2>AI智能分析</h2>
                <div style="line-height: 1.6;">
                    {self._format_ai_content(ai_analysis)}
                </div>
                """
                
                if ai_recommendations:
                    html += """
                <h3 style="margin-top: 20px;">改进建议</h3>
                <ul class="suggestion-list">"""
                    for recommendation in ai_recommendations[:5]:
                        if recommendation.strip():
                            html += f"<li>{recommendation.strip()}</li>"
                    html += "</ul>"
                
                html += "</div>"
            
            # 专业洞察
            if insights:
                html += """
            <div class="section">
                <h2>专业洞察</h2>"""
                
                for insight in insights:
                    insight_type = insight.get('insight_type', 'general')
                    title = insight.get('title', '未知洞察')
                    description = insight.get('description', '')
                    impact = insight.get('impact', 'medium')
                    suggestions = insight.get('suggestions', [])
                    
                    impact_text = {
                        'high': '高影响',
                        'medium': '中等影响', 
                        'low': '低影响'
                    }.get(impact, impact)
                    
                    html += f"""
                <div class="insight-card">
                    <div class="insight-title">{title} ({impact_text})</div>
                    <div class="insight-description">{description}</div>"""
                    
                    if suggestions:
                        html += """
                    <div><strong>建议措施:</strong></div>
                    <ul class="suggestion-list">"""
                        for suggestion in suggestions:
                            html += f"<li>{suggestion}</li>"
                        html += "</ul>"
                    
                    html += "</div>"
                
                html += "</div>"
            
            # 分析总结
            summary = analysis_summary.get('summary', '')
            key_findings = analysis_summary.get('key_findings', [])
            
            if summary or key_findings:
                html += """
            <div class="section">
                <h2>分析总结</h2>"""
                
                if summary:
                    html += f"<p>{summary}</p>"
                
                if key_findings:
                    html += """
                <h3>关键发现</h3>
                <ul class="suggestion-list">"""
                    for finding in key_findings:
                        if finding.strip():
                            html += f"<li>{finding.strip()}</li>"
                    html += "</ul>"
                
                html += "</div>"
            
            html += f"""
        </div>
        
        <div style="text-align: center; padding: 20px; color: #6c757d; border-top: 1px solid #dee2e6;">
            <p>报告生成时间: {dimension_info.get('analysis_timestamp', 'N/A')}</p>
            <p>本报告由 OSS Audit 2.0 自动生成</p>
        </div>
    </div>
</body>
</html>
"""
            
            return html
            
        except Exception as e:
            return f"""
<html>
<head><title>报告生成错误</title></head>
<body>
    <h1>维度报告生成失败</h1>
    <p>错误: {str(e)}</p>
    <pre>{json.dumps(dimension_data, ensure_ascii=False, indent=2)}</pre>
</body>
</html>
"""
    
    def _format_status(self, status: str) -> str:
        """格式化状态显示"""
        status_map = {
            'EXCELLENT': '优秀',
            'GOOD': '良好',
            'WARN': '警告',
            'FAIL': '失败',
            'UNKNOWN': '未知'
        }
        return status_map.get(status, status)
    
    def _format_analysis_level(self, level: str) -> str:
        """格式化分析级别显示"""
        level_map = {
            'basic': '基础分析',
            'enhanced': '增强分析', 
            'ai': 'AI智能分析',
            'collaborative': '协同分析'
        }
        return level_map.get(level, level)
    
    def _format_ai_content(self, content: str) -> str:
        """格式化AI分析内容"""
        # 简单的段落分割和格式化
        paragraphs = content.split('\n\n')
        formatted = ""
        
        for paragraph in paragraphs:
            if paragraph.strip():
                # 检查是否是标题
                if any(keyword in paragraph for keyword in ['状态评估', '风险点', '改进方向', '当前状态', '主要风险', '核心改进']):
                    formatted += f"<h4 style='color: #495057; margin: 15px 0 10px 0;'>{paragraph.strip()}</h4>"
                else:
                    formatted += f"<p>{paragraph.strip()}</p>"
        
        return formatted


def generate_dimension_html_file(input_file: str, output_file: str = None) -> str:
    """
    生成维度HTML文件
    
    Args:
        input_file: 输入的JSON文件路径
        output_file: 输出的HTML文件路径（可选）
        
    Returns:
        生成的HTML内容
    """
    try:
        # 读取JSON文件
        with open(input_file, 'r', encoding='utf-8') as f:
            dimension_data = json.load(f)
        
        # 生成HTML
        generator = DimensionHtmlGenerator()
        html_content = generator.generate_dimension_html(dimension_data)
        
        # 保存到文件（如果指定了输出文件）
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        return html_content
        
    except Exception as e:
        return f"处理文件失败: {str(e)}"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python dimension_html_generator.py <input_json_file> [output_html_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = generate_dimension_html_file(input_file, output_file)
    
    if output_file:
        print(f"HTML报告已保存到: {output_file}")
    else:
        print(result[:500] + "..." if len(result) > 500 else result)
#!/usr/bin/env python3
"""
HTML Report Generator - HTML报告生成器

生成美观的HTML格式的审计报告。
"""

import logging

logger = logging.getLogger(__name__)

import pathlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_generator import BaseReportGenerator, ReportData


class HTMLReportGenerator(BaseReportGenerator):
    """HTML报告生成器"""

    def __init__(self, i18n_manager=None):
        super().__init__(i18n_manager)

    def generate_report(self,
            report_data: ReportData,
            output_path: pathlib.Path) -> pathlib.Path:
        """生成HTML报告"""
        html_content = self._generate_html_content(report_data)

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入HTML文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return output_path

    def generate_overview_report(
            self,
            report_data: ReportData,
            output_path: pathlib.Path) -> pathlib.Path:
        """生成概览报告"""
        # 确保传递的是文件路径而不是目录路径
        if output_path.is_dir():
            output_path = output_path / "overview" / "index.html"
        return self.generate_report(report_data, output_path)

    def generate_dimension_report(
            self,
            dimension_result,
            output_dir: pathlib.Path) -> pathlib.Path:
        """生成维度详细报告"""
        # 确保输出目录存在
        dimension_name = dimension_result.get('dimension_name', 'Unknown')
        dimension_dir = output_dir / "dimensions" / \
            self._sanitize_filename(dimension_name)
        dimension_dir.mkdir(parents=True, exist_ok=True)

        # 标记这是维度详细报告页面
        dimension_result['is_dimension_detail_page'] = True

        # 创建简化的报告数据
        report_data = ReportData(
            project_name=dimension_result.get('project_name', 'Unknown Project'),
            project_path="",
            analysis_results=[dimension_result],
            total_score=dimension_result.get('score', 0),
            average_score=dimension_result.get('score', 0),
            passed_dimensions=1 if dimension_result.get('status') == 'PASS' else 0,
            total_dimensions=1,
            generation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            language=self.i18n.language
        )

        # 生成维度报告文件
        output_path = dimension_dir / "index.html"
        return self.generate_report(report_data, output_path)

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        import re
        return re.sub(r'[^\w\-_.]', '_', filename)

    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """将Markdown文本转换为HTML"""
        import re

        if not markdown_text:
            return ""

        # 基本的Markdown转换
        html = markdown_text

        # 转换标题
        html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # 转换粗体
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html)

        # 转换斜体
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        html = re.sub(r'_(.*?)_', r'<em>\1</em>', html)

        # 转换代码块
        html = re.sub(
            r'```(.*?)```',
            r'<pre><code>\1</code></pre>',
            html,
            flags=re.DOTALL)
        html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)

        # 转换列表
        html = re.sub(
            r'^\d+\. (.*?)$',
            r'<li>\1</li>',
            html,
            flags=re.MULTILINE)
        html = re.sub(r'^- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # 转换段落
        html = re.sub(r'\n\n', r'</p><p>', html)
        html = f'<p>{html}</p>'

        # 清理多余的段落标签
        html = re.sub(r'<p>\s*</p>', '', html)
        html = re.sub(r'<p>\s*<(h[1-6]|pre|ul|ol)>', r'<\1', html)
        html = re.sub(r'</(h[1-6]|pre|ul|ol)>\s*</p>', r'</\1>', html)

        return html

    def _generate_html_content(self, report_data: ReportData) -> str:
        """生成HTML内容"""
        return f"""<!DOCTYPE html>
<html lang="{self.i18n.language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.i18n.get_text('reports', 'overview_title')} - {report_data.project_name}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        {self._generate_header_html(report_data)}
        {self._generate_summary_html(report_data)}
        {self._generate_dimensions_html(report_data)}
        {self._generate_ai_analysis_html(report_data)}
        {self._generate_footer_html(report_data)}
    </div>
    
    <script>
    function toggleToolDetails(toolName) {{
        const detailsElement = document.getElementById(toolName + '-details');
        const button = event.target;
        
        if (detailsElement) {{
            if (detailsElement.style.display === 'none' || detailsElement.style.display === '') {{
                detailsElement.style.display = 'block';
                button.textContent = '收起';
            }} else {{
                detailsElement.style.display = 'none';
                button.textContent = '详情';
            }}
        }}
    }}

    // Add smooth transitions
    document.addEventListener('DOMContentLoaded', function() {{
        const detailsElements = document.querySelectorAll('.tool-details-content');
        detailsElements.forEach(element => {{
            element.style.transition = 'all 0.3s ease-in-out';
        }});
    }});
    </script>
</body>
</html>"""

    def _generate_header_html(self, report_data: ReportData) -> str:
        """生成头部HTML"""
        return f"""
        <header>
            <h1>{self.i18n.get_text('reports', 'overview_title')}</h1>
            <div class="project-info">
                <p><strong>{self.i18n.get_text('reports', 'project_name')}:</strong> {report_data.project_name}</p>
                <p><strong>{self.i18n.get_text('reports', 'assessment_time')}:</strong> {report_data.generation_time}</p>
                <p><strong>{self.i18n.get_text('reports', 'comprehensive_score')}:</strong> {report_data.total_score:.1f}/100</p>
            </div>
        </header>
        """

    def _generate_summary_html(self, report_data: ReportData) -> str:
        """生成摘要HTML"""
        quality_level = self._get_quality_level(report_data.total_score)

        return f"""
        <div class="summary">
            <div class="score-card">
                <div class="score">{report_data.total_score:.1f}</div>
                <div class="quality-level">{quality_level}</div>
            </div>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-label">{self.i18n.get_text('reports', 'dimensions_count')}</span>
                    <div class="stat-value">{len(report_data.analysis_results)}</div>
                </div>
                <div class="stat-item">
                    <span class="stat-label">{self.i18n.get_text('reports', 'passed_dimensions')}</span>
                    <div class="stat-value">{sum(1 for r in report_data.analysis_results if r.get('status') == 'PASS')}</div>
                </div>
                <div class="stat-item">
                    <span class="stat-label">{self.i18n.get_text('reports', 'failed_dimensions')}</span>
                    <div class="stat-value">{sum(1 for r in report_data.analysis_results if r.get('status') == 'FAIL')}</div>
                </div>
            </div>
        </div>
        """

    def _generate_dimensions_html(self, report_data: ReportData) -> str:
        """生成维度HTML"""
        dimensions_html = f"""
        <div class="dimensions">
            <h2>{self.i18n.get_text('reports', 'dimensions_analysis')}</h2>
            <div class="dimensions-grid">
        """

        for result in report_data.analysis_results:
            dimensions_html += self._generate_dimension_card_html(result)

        dimensions_html += """
            </div>
        </div>
        """

        return dimensions_html

    def _generate_dimension_card_html(self, result) -> str:
        """生成维度卡片HTML"""
        status_class = result.get('status', 'UNKNOWN')
        status_text = self.i18n.get_status_text(
            result.get('status', 'UNKNOWN'))

        # 生成工具信息HTML
        tools_html = self._generate_tools_info_html(
            result.get('details', {}).get('tools_used', {}),
            result.get('details', {}),
            result.get('dimension_name', 'Unknown'),
            result.get('is_dimension_detail_page', False)
        )

        # 生成AI分析HTML
        ai_html = self._generate_ai_analysis_item_html(result)

        # 检查是否在维度详细报告页面中
        # 如果是维度详细报告页面，则不显示"查看详情"链接
        # 如果是总览页面，则显示链接到维度详细报告
        view_details_html = ""
        if not result.get('is_dimension_detail_page', False):
            view_details_html = f"""
            <div class="dimension-actions">
                <a href="../dimensions/{self._sanitize_filename(result.get('dimension_name', 'Unknown'))}/index.html" class="btn btn-primary">
                    {self.i18n.get_text('reports', 'view_details')}
                </a>
            </div>
            """

        return f"""
        <div class="dimension-card">
            <div class="dimension-header">
                <div class="dimension-name">{result.get('dimension_name', 'Unknown')}</div>
                <div class="dimension-score">{result.get('score', 0):.1f}</div>
                <div class="dimension-status status {status_class}">{status_text}</div>
            </div>
            {tools_html}
            {ai_html}
            {view_details_html}
        </div>
        """

    def _generate_tools_info_html(
            self,
            tools_used: Dict,
            details: Dict,
            dimension_name: str,
            is_detail_page: bool) -> str:
        """生成工具信息HTML（优化显示格式）"""
        if not tools_used:
            return ""

        # 获取工具结果和选择信息 - 兼容多种数据结构
        tools_results = details.get('tools_results', {})
        
        # 如果没有找到tools_results，尝试从老的结构获取
        if not tools_results:
            # 检查是否有老的工具结果结构
            for key, value in details.items():
                if key.endswith('_raw_output') and value:
                    # 根据key推断工具名称
                    tool_name = key.replace('_raw_output', '')
                    if tool_name not in tools_results:
                        # 尝试解析JSON输出来获取详细数据
                        parsed_data = {}
                        try:
                            if tool_name == 'safety' and value.strip():
                                # 解析safety JSON输出
                                json_start = value.find('{')
                                if json_start >= 0:
                                    json_end = value.rfind('}') + 1
                                    if json_end > json_start:
                                        json_text = value[json_start:json_end]
                                        import json
                                        parsed_data = json.loads(json_text)
                        except:
                            pass
                        
                        tools_results[tool_name] = {
                            'success': True,
                            'score': details.get(f'{tool_name}_score', 0),
                            'issues_count': details.get(f'{tool_name}_issues_count', 0),
                            'raw_output': value,
                            'raw_error': details.get(f'{tool_name}_raw_error', ''),
                            'parsed_output': parsed_data
                        }
                        
                        # 为safety工具添加详细数据
                        if tool_name == 'safety' and parsed_data:
                            vulnerabilities = []
                            scanned_packages = parsed_data.get('scanned_packages', {})
                            packages_found = parsed_data.get('report_meta', {}).get('packages_found', 0)
                            
                            # 添加扫描统计信息
                            tools_results[tool_name].update({
                                'total_packages_scanned': packages_found,
                                'vulnerabilities': vulnerabilities,
                                'scanned_packages': list(scanned_packages.keys()) if scanned_packages else []
                            })
        
        tool_summary = details.get('tool_summary', {})
        tool_selection_info = details.get('tool_selection_info', {})

        # 生成HTML
        tools_html = f"""
        <div class="tools-info">
            <div class="tools-header">
                <span class="tools-icon">🔧</span>
                <span class="tools-title">工具分析结果</span>
                <span class="tools-summary">({tool_summary.get('successful_tools', 0)}/{tool_summary.get('total_tools', 0)} 成功)</span>
            </div>

            <!-- 工具选择策略 -->
            <div class="tools-strategy">
                <div class="strategy-title">📋 工具选择策略</div>
                <div class="strategy-content">
                    <span class="strategy-text">{tool_selection_info.get('selection_strategy', '基于可用性选择')}</span>
                </div>
            </div>

            <div class="tools-list">
        """

        # 显示工具详细信息
        tool_details = tool_selection_info.get('tool_details', {})
        for tool_name, tool_info in tool_details.items():
            tools_html += f"""
            <div class="tool-detail">
                <div class="tool-name">{tool_info['name']}</div>
                <div class="tool-description">{tool_info['description']}</div>
                <div class="tool-strengths">
                    <span class="strength-label">💪 优势:</span>
                    <span class="strength-text">{', '.join(tool_info['strengths'])}</span>
                </div>
                <div class="tool-best-for">
                    <span class="best-for-label">🎯 适用:</span>
                    <span class="best-for-text">{', '.join(tool_info['best_for'])}</span>
                </div>
            </div>
            """

        # 维度目录（用于链接原始输出和工具报告）
        dimension_dir_rel = "." if is_detail_page else f"../dimensions/{self._sanitize_filename(dimension_name)}"
        
        try:
            # 构建工具报告文件路径
            tools_report_path = f"{dimension_dir_rel}/tools_report.md"
            # 移除相对路径部分以检查文件是否存在
            actual_path = pathlib.Path(tools_report_path.replace("../", ""))
            logger.debug(f"Checking for tools report at path: {actual_path}")
        except Exception as e:
            logger.error(f"Error building tool report path for dimension {dimension_name}: {e}")
            tools_report_path = None

        # 显示工具执行结果
        for tool_name, is_used in tools_used.items():
            if is_used:
                tool_result = tools_results.get(tool_name, {})
                score = tool_result.get('score', 0)
                issues_count = tool_result.get('issues_count', 0)
                execution_time = tool_result.get('execution_time', 0)
                success = tool_result.get('success', False)

                # 确定状态图标和颜色
                if success:
                    if score >= 80:
                        status_icon = "✅"
                        status_class = "tool-success"
                    elif score >= 60:
                        status_icon = "⚠️"
                        status_class = "tool-warning"
                    else:
                        status_icon = "❌"
                        status_class = "tool-error"
                else:
                    status_icon = "❌"
                    status_class = "tool-error"

                # 获取工具显示名称
                tool_display_name = tool_details.get(
                    tool_name, {}).get('name', tool_name)

                # 生成工具结果文本
                if tool_name == 'pylint':
                    tool_text = f"{tool_display_name}: {score}/100 ({issues_count}个问题, {
                        execution_time:.1f}s)"
                elif tool_name == 'flake8':
                    tool_text = f"{tool_display_name}: {score}/100 ({issues_count}个问题, {
                        execution_time:.1f}s)"
                elif tool_name == 'mypy':
                    tool_text = f"{tool_display_name}: {score}/100 ({issues_count}个类型问题, {
                        execution_time:.1f}s)"
                elif tool_name == 'black':
                    files_reformatted = tool_result.get('files_reformatted', 0)
                    tool_text = f"{tool_display_name}: {score}/100 ({files_reformatted}个文件需格式化, {
                        execution_time:.1f}s)"
                elif tool_name == 'isort':
                    files_reformatted = tool_result.get('files_reformatted', 0)
                    tool_text = f"{tool_display_name}: {score}/100 ({files_reformatted}个文件需整理, {
                        execution_time:.1f}s)"
                elif tool_name == 'coverage':
                    percentage = tool_result.get('percentage', 0)
                    tool_text = f"{tool_display_name}: {percentage}% ({
                        execution_time:.1f}s)"
                elif tool_name == 'pytest':
                    test_count = tool_result.get('test_count', 0)
                    passed_count = tool_result.get('passed_count', 0)
                    failed_count = tool_result.get('failed_count', 0)
                    tool_text = f"{tool_display_name}: {passed_count}/{test_count}通过 ({failed_count}个失败, {
                        execution_time:.1f}s)"
                elif tool_name == 'bandit':
                    tool_text = f"{tool_display_name}: {score}/100 ({issues_count}个安全问题, {
                        execution_time:.1f}s)"
                elif tool_name == 'safety':
                    tool_text = f"{tool_display_name}: {score}/100 ({issues_count}个依赖问题, {
                        execution_time:.1f}s)"
                else:
                    tool_text = f"{tool_display_name}: {score}/100 ({issues_count}个问题, {
                        execution_time:.1f}s)"

                # 可选链接到原始输出
                raw_link_html = ""
                raw_txt = f"{tool_name}_output.txt"
                raw_err = f"{tool_name}_output.err.txt"
                has_raw = False
                
                # 根据是否在详细页面确定文件路径
                raw_txt_path = f"{dimension_dir_rel}/{raw_txt}"
                raw_err_path = f"{dimension_dir_rel}/{raw_err}"
                
                # 构建文件路径对象用于检查文件是否存在
                txt_file_path = pathlib.Path(f"{dimension_dir_rel}/{raw_txt}".replace("../", ""))
                err_file_path = pathlib.Path(f"{dimension_dir_rel}/{raw_err}".replace("../", ""))
                
                if tool_result.get('raw_output') is not None and txt_file_path.exists():
                    raw_link_html += f' <a class="tool-raw-link" href="{raw_txt_path}" target="_blank">原始输出</a>'
                    has_raw = True
                    
                if tool_result.get('raw_error') and err_file_path.exists():
                    raw_link_html += f' <a class="tool-raw-link" href="{raw_err_path}" target="_blank">错误输出</a>'
                    has_raw = True

                # 添加工具详细结果展开按钮
                tool_details_html = self._generate_tool_details_html(tool_name, tool_result)
                detail_button = ""
                if tool_details_html:
                    detail_button = f' <button class="tool-details-btn" onclick="toggleToolDetails(\'{tool_name}\')">详情</button>'
                
                link_suffix = f"{raw_link_html}{detail_button}" if (has_raw or detail_button) else ""
                tools_html += f'<div class="tool-item {status_class}">{status_icon} {tool_text}{link_suffix}</div>'
                
                # 添加隐藏的详细结果区域
                if tool_details_html:
                    tools_html += f'<div class="tool-details-content" id="{tool_name}-details" style="display:none;">{tool_details_html}</div>'

        # 添加工具摘要
        if tool_summary:
            avg_score = tool_summary.get('average_score', 0)
            total_time = tool_summary.get('execution_time', 0)
            total_issues = tool_summary.get('total_issues', 0)

            # 总体评估状态
            if avg_score >= 80:
                overall_status = "🟢 优秀"
                overall_class = "overall-excellent"
            elif avg_score >= 60:
                overall_status = "🟡 良好"
                overall_class = "overall-good"
            else:
                overall_status = "🔴 需改进"
                overall_class = "overall-poor"

            tools_html += f"""
            <div class="tools-summary-info {overall_class}">
                <div class="summary-header">
                    <span class="overall-status">{overall_status}</span>
                    <span class="summary-title">工具分析摘要</span>
                </div>
                <div class="summary-details">
                    <span class="summary-item">平均分数: {avg_score:.1f}/100</span>
                    <span class="summary-item">总耗时: {total_time:.1f}s</span>
                    <span class="summary-item">总问题: {total_issues}个</span>
                </div>
            </div>
            """

        # 在维度总览中添加“查看工具报告(聚合)”链接（如果存在）
        if is_detail_page:
            tools_report_path = "tools_report.md"
        else:
            tools_report_path = f"../dimensions/{self._sanitize_filename(dimension_name)}/tools_report.md"
        tools_html += f"""
            </div>
        """
        
        # Get the tools report path and check if it exists
        try:
            # First, determine the paths based on whether we're in detail or overview mode
            if is_detail_page:
                display_path = "tools_report.md"
                check_path = pathlib.Path(display_path)
            else:
                display_path = f"../dimensions/{self._sanitize_filename(dimension_name)}/tools_report.md"
                # Construct the path for existence check relative to overview directory
                check_path = pathlib.Path(display_path)

            # Check if the file exists at the expected location
            if check_path.exists():
                tools_html += f"""
                    <div class="tools-footer" style="margin-top:8px;"> 
                        <a class="btn btn-primary" href="{display_path}" target="_blank">查看工具扫描报告</a>
                    </div>
                """
        except Exception as e:
            logger.error(f"Error checking tools report path: {e}")

        tools_html += """
        </div>
        """

        return tools_html

    def _generate_tool_details_html(self, tool_name: str, tool_result: Dict[str, Any]) -> str:
        """生成工具详细结果HTML"""
        if not tool_result.get('success', False):
            return ""
        
        details_html = []
        
        if tool_name == 'bandit':
            # 安全扫描详细结果
            security_findings = tool_result.get('security_findings', [])
            if security_findings:
                details_html.append('<div class="tool-detail-section">')
                details_html.append(f'<h4>安全发现 ({len(security_findings)} 项)</h4>')
                
                # 按严重程度分组
                by_severity = {}
                for finding in security_findings[:15]:  # 限制显示数量
                    severity = finding.get('issue_severity', 'LOW')
                    if severity not in by_severity:
                        by_severity[severity] = []
                    by_severity[severity].append(finding)
                
                for severity in ['HIGH', 'MEDIUM', 'LOW']:
                    if severity in by_severity:
                        details_html.append(f'<div class="severity-group severity-{severity.lower()}">')
                        details_html.append(f'<h5>{severity} ({len(by_severity[severity])} 项)</h5>')
                        details_html.append('<ul class="findings-list">')
                        
                        for finding in by_severity[severity][:5]:  # 每个严重程度最多显示5个
                            filename = finding.get('filename', 'unknown')
                            line_number = finding.get('line_number', 0)
                            test_name = finding.get('test_name', '')
                            issue_text = finding.get('issue_text', '')[:120]
                            
                            details_html.append(f'''
                            <li class="finding-item">
                                <div class="finding-location">{filename}:{line_number}</div>
                                <div class="finding-test">{test_name}</div>
                                <div class="finding-description">{issue_text}...</div>
                            </li>
                            ''')
                        
                        if len(by_severity[severity]) > 5:
                            details_html.append(f'<li class="more-items">... 还有 {len(by_severity[severity]) - 5} 个发现</li>')
                        
                        details_html.append('</ul></div>')
                
                details_html.append('</div>')
        
        elif tool_name == 'safety':
            # 依赖漏洞详细结果
            vulnerabilities = tool_result.get('vulnerabilities', [])
            parsed_output = tool_result.get('parsed_output', {})
            total_packages = tool_result.get('total_packages_scanned', 0)
            scanned_packages = tool_result.get('scanned_packages', [])
            
            # 显示扫描统计信息
            if parsed_output or total_packages > 0:
                details_html.append('<div class="tool-detail-section">')
                details_html.append('<h4>安全扫描详情</h4>')
                details_html.append('<div class="coverage-stats">')
                details_html.append(f'<div class="coverage-percentage">扫描包数量: {total_packages}</div>')
                if vulnerabilities:
                    details_html.append(f'<div class="coverage-lines">发现漏洞: {len(vulnerabilities)} 个</div>')
                else:
                    details_html.append('<div class="coverage-lines">✅ 未发现安全漏洞</div>')
                
                # 显示扫描的包示例
                if scanned_packages:
                    sample_packages = scanned_packages[:10]  # 显示前10个包
                    packages_text = ', '.join(sample_packages)
                    if len(scanned_packages) > 10:
                        packages_text += f' 等{len(scanned_packages)}个包'
                    details_html.append(f'<div class="coverage-lines">扫描包: {packages_text}</div>')
                
                details_html.append('</div>')
                details_html.append('</div>')
            
            # 显示漏洞详情（如果有）
            if vulnerabilities:
                details_html.append('<div class="tool-detail-section">')
                details_html.append(f'<h4>发现的漏洞 ({len(vulnerabilities)} 项)</h4>')
                details_html.append('<ul class="vulnerabilities-list">')
                
                for vuln in vulnerabilities[:8]:  # 最多显示8个漏洞
                    package = vuln.get('package', 'unknown')
                    cve = vuln.get('cve', vuln.get('CVE', ''))
                    advisory = vuln.get('advisory', '')[:150]
                    more_info_url = vuln.get('more_info_url', '')
                    
                    details_html.append(f'''
                    <li class="vulnerability-item">
                        <div class="vuln-package"><strong>{package}</strong></div>
                        <div class="vuln-cve">{cve}</div>
                        <div class="vuln-description">{advisory}...</div>
                        {f'<div class="vuln-link"><a href="{more_info_url}" target="_blank">详细信息</a></div>' if more_info_url else ''}
                    </li>
                    ''')
                
                if len(vulnerabilities) > 8:
                    details_html.append(f'<li class="more-items">... 还有 {len(vulnerabilities) - 8} 个漏洞</li>')
                
                details_html.append('</ul></div>')
        
        elif tool_name in ['pylint', 'flake8', 'mypy']:
            # 代码质量问题详细结果
            issues = tool_result.get('issues', [])
            by_severity = tool_result.get('by_severity', {})
            
            if issues or by_severity:
                details_html.append('<div class="tool-detail-section">')
                details_html.append(f'<h4>代码质量问题 ({len(issues)} 项)</h4>')
                
                # 显示严重程度统计
                if by_severity:
                    details_html.append('<div class="severity-stats">')
                    for severity, count in by_severity.items():
                        details_html.append(f'<span class="severity-badge severity-{severity}">{severity}: {count}</span>')
                    details_html.append('</div>')
                
                # 显示具体问题
                if issues:
                    details_html.append('<ul class="issues-list">')
                    for issue in issues[:10]:  # 最多显示10个问题
                        file_path = issue.get('file', 'unknown')
                        line = issue.get('line', 0)
                        severity = issue.get('severity', 'info')
                        message = issue.get('message', '')[:100]
                        symbol = issue.get('symbol') or issue.get('code', '')
                        
                        details_html.append(f'''
                        <li class="issue-item severity-{severity}">
                            <div class="issue-location">{file_path}:{line}</div>
                            <div class="issue-rule">{symbol}</div>
                            <div class="issue-message">{message}</div>
                        </li>
                        ''')
                    
                    if len(issues) > 10:
                        details_html.append(f'<li class="more-items">... 还有 {len(issues) - 10} 个问题</li>')
                    
                    details_html.append('</ul>')
                
                details_html.append('</div>')
        
        elif tool_name == 'coverage':
            # 测试覆盖率详细结果
            percentage = tool_result.get('percentage', 0)
            lines_total = tool_result.get('lines_total', 0)
            lines_covered = tool_result.get('lines_covered', 0)
            
            if percentage > 0:
                details_html.append('<div class="tool-detail-section">')
                details_html.append('<h4>测试覆盖率详情</h4>')
                details_html.append('<div class="coverage-stats">')
                details_html.append(f'<div class="coverage-percentage">覆盖率: {percentage:.1f}%</div>')
                details_html.append(f'<div class="coverage-lines">覆盖行数: {lines_covered}/{lines_total}</div>')
                details_html.append('</div>')
                details_html.append('</div>')
        
        return ''.join(details_html) if details_html else ""

    def _generate_ai_analysis_item_html(self, result) -> str:
        """生成AI分析项HTML"""
        ai_analysis = result.get('details', {}).get('ai_analysis', {})
        if not ai_analysis:
            return ""

        content = ai_analysis.get('content', '')
        model = ai_analysis.get('model', '')
        confidence = ai_analysis.get('confidence', 0)

        # 转换Markdown为HTML
        formatted_content = self._convert_markdown_to_html(content)

        return f"""
        <div class="ai-analysis-item">
            <div class="ai-header">
                <div class="ai-meta">
                    <span class="ai-model">🤖 {model}</span>
                    <span class="ai-confidence">置信度: {confidence}%</span>
                </div>
            </div>
            <div class="ai-summary">{formatted_content}</div>
        </div>
        """

    def _generate_ai_analysis_html(self, report_data: ReportData) -> str:
        """生成AI分析HTML"""
        # 从analysis_results中查找AI分析
        ai_analysis = None
        for result in report_data.analysis_results:
            if result.get('ai_analysis'):
                ai_analysis = result.get('ai_analysis')
                break

        if not ai_analysis:
            return ""
        content = ai_analysis.get('content', '')
        model = ai_analysis.get('model', '')
        confidence = ai_analysis.get('confidence', 0)

        return f"""
        <div class="ai-analysis">
            <h2>{self.i18n.get_text('reports', 'ai_analysis')}</h2>
            <div class="ai-analysis-content">
                <div class="ai-header">
                    <div class="ai-meta">
                        <span class="ai-model">🤖 {model}</span>
                        <span class="ai-confidence">置信度: {confidence}%</span>
                    </div>
                </div>
                <div class="ai-content">{self._convert_markdown_to_html(content)}</div>
            </div>
        </div>
        """

    def _generate_footer_html(self, report_data: ReportData) -> str:
        """生成底部HTML"""
        return f"""
        <footer>
            <p>{self.i18n.get_text('reports', 'generated_by')} OSS Audit</p>
            <p>{self.i18n.get_text('reports', 'generated_time')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
        """

    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 90:
            return self.i18n.get_text('reports', 'quality_excellent')
        elif score >= 80:
            return self.i18n.get_text('reports', 'quality_good')
        elif score >= 70:
            return self.i18n.get_text('reports', 'quality_fair')
        elif score >= 50:
            return self.i18n.get_text('reports', 'quality_poor')
        else:
            return self.i18n.get_text('reports', 'quality_critical')

    def _get_css_styles(self) -> str:
        """获取CSS样式"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }

        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
        }

        .project-info {
            color: #666;
        }

        .summary {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 30px;
            margin-bottom: 30px;
        }

        .score-card {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }

        .score {
            font-size: 3em;
            font-weight: bold;
            color: #2c3e50;
            margin: 10px 0;
        }

        .quality-level {
            font-size: 1.2em;
            color: #27ae60;
            font-weight: 500;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }

        .stat-item {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }

        .stat-label {
            display: block;
            color: #666;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }

        .dimensions {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }

        .dimensions h2 {
            color: #2c3e50;
            margin-bottom: 20px;
        }

        .dimensions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }

        .dimension-card {
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .dimension-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }

        .dimension-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #e9ecef;
        }

        .dimension-name {
            font-weight: 700;
            font-size: 1.1em;
            color: #2c3e50;
        }

        .dimension-score {
            font-size: 1.4em;
            font-weight: 700;
            color: #2c3e50;
        }

        .dimension-status {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .status.pass {
            background: linear-gradient(135deg, #d5f4e6 0%, #a8e6cf 100%);
            color: #27ae60;
            border: 1px solid #27ae60;
        }

        .status.warn {
            background: linear-gradient(135deg, #fef9e7 0%, #fdeaa7 100%);
            color: #f39c12;
            border: 1px solid #f39c12;
        }

        .status.fail {
            background: linear-gradient(135deg, #fadbd8 0%, #f5b7b1 100%);
            color: #e74c3c;
            border: 1px solid #e74c3c;
        }

        .tools-info {
            margin: 15px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }

        .tools-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
            font-weight: 600;
            color: #495057;
        }

        .tools-icon {
            margin-right: 8px;
            font-size: 1.1em;
        }

        .tools-title {
            font-size: 0.95em;
            font-weight: 600;
        }

        .tools-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .tool-item {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            color: #1565c0;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
            border: 1px solid #90caf9;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .tools-summary {
            margin-left: auto;
            font-size: 0.8em;
            color: #666;
            font-weight: 500;
        }

        .tools-summary-info {
            margin-top: 10px;
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid #28a745;
        }

        .summary-item {
            display: inline-block;
            margin-right: 15px;
            font-size: 0.85em;
            color: #495057;
            font-weight: 500;
        }

        /* 工具选择策略样式 */
        .tools-strategy {
            margin: 10px 0;
            padding: 12px 15px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }

        .strategy-title {
            font-weight: 600;
            color: #495057;
            margin-bottom: 5px;
            font-size: 0.9em;
        }

        .strategy-content {
            margin-top: 5px;
        }

        .strategy-text {
            font-size: 0.85em;
            color: #6c757d;
            font-style: italic;
        }

        /* 工具详细信息样式 */
        .tool-detail {
            margin: 12px 0;
            padding: 15px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }

        .tool-name {
            font-weight: 600;
            color: #495057;
            font-size: 1em;
            margin-bottom: 5px;
        }

        .tool-description {
            font-size: 0.85em;
            color: #6c757d;
            margin-bottom: 8px;
            line-height: 1.4;
        }

        .tool-strengths, .tool-best-for {
            margin: 5px 0;
            font-size: 0.8em;
        }

        .strength-label, .best-for-label {
            font-weight: 600;
            color: #495057;
            margin-right: 5px;
        }

        .strength-text, .best-for-text {
            color: #6c757d;
        }

        /* 工具状态样式 */
        .tool-success {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .tool-warning {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            color: #856404;
            border: 1px solid #ffeaa7;
        }

        .tool-error {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        /* 总体评估样式 */
        .overall-excellent {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            border-left: 4px solid #28a745;
        }

        .overall-good {
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            border-left: 4px solid #ffc107;
        }

        .overall-poor {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border-left: 4px solid #dc3545;
        }

        .summary-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }

        .overall-status {
            font-weight: 600;
            font-size: 0.9em;
        }

        .summary-title {
            font-weight: 600;
            color: #495057;
            font-size: 0.9em;
        }

        .summary-details {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .ai-analysis-item {
            margin: 15px 0;
            padding: 15px;
            background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf1 100%);
            border: 1px solid #bee5eb;
            border-radius: 10px;
            position: relative;
        }

        .ai-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .ai-meta {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .ai-model {
            font-weight: 600;
            color: #3498db;
        }

        .ai-confidence {
            font-size: 0.85em;
            color: #6c757d;
        }

        .ai-summary {
            color: #495057;
            line-height: 1.6;
            white-space: pre-line;
        }

        .dimension-actions {
            margin-top: 15px;
            text-align: center;
        }

        .btn {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #3498db;
            color: white;
        }

        .btn-primary:hover {
            background: #2980b9;
            transform: translateY(-1px);
        }

        .ai-analysis {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }

        .ai-analysis h2 {
            color: #2c3e50;
            margin-bottom: 20px;
        }

        .ai-analysis-content {
            background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf1 100%);
            border: 1px solid #bee5eb;
            border-radius: 10px;
            padding: 20px;
        }

        .ai-content {
            color: #495057;
            line-height: 1.6;
            white-space: pre-line;
        }

        /* 工具详细结果样式 */
        .tool-details-btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            cursor: pointer;
            margin-left: 8px;
            transition: background-color 0.2s;
        }

        .tool-details-btn:hover {
            background: #0056b3;
        }

        .tool-details-content {
            margin-top: 10px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }

        .tool-detail-section {
            margin-bottom: 20px;
        }

        .tool-detail-section h4 {
            color: #495057;
            margin-bottom: 10px;
            font-size: 1.1em;
        }

        .tool-detail-section h5 {
            color: #6c757d;
            margin: 10px 0 5px 0;
            font-size: 0.9em;
        }

        .severity-group {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 6px;
        }

        .severity-high {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
        }

        .severity-medium {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
        }

        .severity-low {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
        }

        .severity-stats {
            margin-bottom: 10px;
        }

        .severity-badge {
            display: inline-block;
            padding: 3px 8px;
            margin-right: 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 500;
        }

        .severity-badge.severity-error,
        .severity-badge.severity-fatal {
            background: #f8d7da;
            color: #721c24;
        }

        .severity-badge.severity-warning {
            background: #fff3cd;
            color: #856404;
        }

        .severity-badge.severity-convention,
        .severity-badge.severity-refactor,
        .severity-badge.severity-note {
            background: #d1ecf1;
            color: #0c5460;
        }

        .findings-list,
        .vulnerabilities-list,
        .issues-list {
            list-style: none;
            padding: 0;
            margin: 10px 0;
        }

        .finding-item,
        .vulnerability-item,
        .issue-item {
            background: white;
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 4px;
            border: 1px solid #dee2e6;
        }

        .finding-location,
        .issue-location {
            font-family: monospace;
            color: #6c757d;
            font-size: 0.85em;
        }

        .finding-test,
        .issue-rule {
            color: #007bff;
            font-size: 0.8em;
            font-weight: 500;
        }

        .finding-description,
        .issue-message {
            color: #495057;
            font-size: 0.9em;
            margin-top: 4px;
        }

        .vuln-package {
            color: #dc3545;
            font-size: 1em;
        }

        .vuln-cve {
            color: #6c757d;
            font-size: 0.85em;
            font-family: monospace;
        }

        .vuln-description {
            color: #495057;
            font-size: 0.9em;
            margin: 5px 0;
        }

        .vuln-link {
            margin-top: 5px;
        }

        .vuln-link a {
            color: #007bff;
            text-decoration: none;
            font-size: 0.85em;
        }

        .vuln-link a:hover {
            text-decoration: underline;
        }

        .more-items {
            color: #6c757d;
            font-style: italic;
            padding: 8px;
            text-align: center;
        }

        .coverage-stats {
            background: white;
            padding: 10px;
            border-radius: 4px;
            border: 1px solid #dee2e6;
        }

        .coverage-percentage {
            font-size: 1.2em;
            font-weight: 600;
            color: #28a745;
        }

        .coverage-lines {
            font-size: 0.9em;
            color: #6c757d;
            margin-top: 4px;
        }

        footer {
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding: 20px;
        }
        """

#!/usr/bin/env python3
"""
维度分析报告格式化器
将JSON格式的维度数据转换为可读性强的结构化报告
"""

import json
from typing import Dict, Any, List
from pathlib import Path


class DimensionFormatter:
    """维度分析报告格式化器"""
    
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
    
    def format_dimension_report(self, dimension_data: Dict[str, Any]) -> str:
        """
        格式化维度分析报告为可读文本
        
        Args:
            dimension_data: 维度JSON数据
            
        Returns:
            格式化后的可读报告
        """
        try:
            # 基本信息
            dimension_info = dimension_data.get('dimension_info', {})
            analysis_summary = dimension_data.get('analysis_summary', {})
            metrics = dimension_data.get('metrics', {})
            tools_analysis = dimension_data.get('tools_analysis', {})
            insights = dimension_data.get('insights', [])
            project_context = dimension_data.get('project_context', {})
            
            report = []
            
            # 标题和基本信息
            dimension_name = dimension_info.get('dimension_name', '未知维度')
            score = dimension_info.get('score', 0)
            status = dimension_info.get('status', 'UNKNOWN')
            analysis_level = dimension_info.get('analysis_level', 'basic')
            
            report.append("=" * 80)
            report.append(f"维度分析报告: {dimension_name}")
            report.append("=" * 80)
            report.append("")
            
            # 评估概览
            report.append("[评估概览]")
            report.append("-" * 40)
            report.append(f"维度ID:       {dimension_info.get('dimension_id', 'N/A')}")
            report.append(f"综合得分:     {score:.1f}/100")
            report.append(f"评估状态:     {self._format_status(status)}")
            report.append(f"分析级别:     {self._format_analysis_level(analysis_level)}")
            report.append(f"分析时间:     {dimension_info.get('analysis_timestamp', 'N/A')}")
            report.append(f"分析耗时:     {dimension_info.get('analysis_duration', 0):.3f} 秒")
            report.append("")
            
            # 项目上下文
            if project_context:
                report.append("[项目上下文]")
                report.append("-" * 40)
                report.append(f"项目名称:     {project_context.get('project_name', 'N/A')}")
                report.append(f"主要语言:     {project_context.get('primary_language', 'N/A')}")
                report.append(f"项目类型:     {project_context.get('project_type', 'N/A')}")
                report.append(f"项目规模:     {project_context.get('size_category', 'N/A')}")
                report.append("")
            
            # 问题统计
            report.append("[问题统计]")
            report.append("-" * 40)
            report.append(f"问题总数:     {metrics.get('total_issues', 0)}")
            report.append(f"关键问题:     {metrics.get('critical_issues', 0)}")
            report.append(f"高优先级:     {metrics.get('high_issues', 0)}")
            report.append(f"中优先级:     {metrics.get('medium_issues', 0)}")
            report.append(f"低优先级:     {metrics.get('low_issues', 0)}")
            report.append("")
            
            # 工具执行统计
            report.append("[工具执行统计]")
            report.append("-" * 40)
            report.append(f"执行工具数:   {metrics.get('tools_executed', 0)}")
            report.append(f"成功执行:     {metrics.get('tools_successful', 0)}")
            report.append(f"工具覆盖率:   {metrics.get('coverage_percentage', 0):.1f}%")
            report.append(f"质量趋势:     {metrics.get('quality_trend', 'N/A')}")
            report.append("")
            
            # 工具详细分析
            if tools_analysis and 'tools_used' in tools_analysis:
                report.append("[工具详细分析]")
                report.append("-" * 40)
                
                tools_used = tools_analysis.get('tools_used', [])
                tool_results = tools_analysis.get('tool_results_summary', {})
                
                if tools_used:
                    report.append(f"使用工具:     {', '.join(tools_used)}")
                    report.append("")
                    
                    # 每个工具的详细结果
                    for tool_name, result in tool_results.items():
                        if result:
                            status_icon = "[成功]" if result.get('success', False) else "[失败]"
                            report.append(f"{status_icon} {tool_name}")
                            report.append(f"   状态: {result.get('status', 'N/A')}")
                            report.append(f"   耗时: {result.get('execution_time', 0):.2f}秒")
                            report.append(f"   问题: {result.get('issues_count', 0)}个")
                            report.append(f"   评分: {result.get('score', 0)}")
                            if result.get('summary'):
                                report.append(f"   总结: {result['summary']}")
                            report.append("")
                else:
                    report.append("未使用任何工具进行分析")
                    report.append("")
            
            # AI智能分析
            ai_analysis = analysis_summary.get('ai_analysis')
            ai_recommendations = analysis_summary.get('ai_recommendations', [])
            
            if ai_analysis and ai_analysis.strip() and "基于规则分析" not in ai_analysis:
                report.append("[AI智能分析]")
                report.append("-" * 40)
                
                # 分段显示AI分析内容
                analysis_sections = ai_analysis.split('\n\n')
                for section in analysis_sections:
                    if section.strip():
                        # 检查是否是标题行
                        if any(keyword in section for keyword in ['状态评估', '风险点', '改进方向', '当前状态', '主要风险', '核心改进']):
                            lines = section.strip().split('\n')
                            for line in lines:
                                if line.strip():
                                    if any(keyword in line for keyword in ['状态评估', '风险点', '改进方向']):
                                        report.append(f"【{line.strip()}】")
                                    else:
                                        report.append(f"  {line.strip()}")
                        else:
                            # 普通内容，适当换行
                            wrapped_lines = self._wrap_text(section.strip(), 60)
                            for line in wrapped_lines:
                                report.append(f"  {line}")
                        report.append("")
                
                # AI建议
                if ai_recommendations:
                    report.append("[AI改进建议]")
                    report.append("-" * 40)
                    for i, recommendation in enumerate(ai_recommendations[:5], 1):
                        if recommendation.strip():
                            wrapped_lines = self._wrap_text(f"{i}. {recommendation.strip()}", 60)
                            for j, line in enumerate(wrapped_lines):
                                if j == 0:
                                    report.append(f"  {line}")
                                else:
                                    report.append(f"     {line}")
                    report.append("")
            
            # 分析总结
            summary = analysis_summary.get('summary', '')
            key_findings = analysis_summary.get('key_findings', [])
            
            if summary or key_findings:
                report.append("[分析总结]")
                report.append("-" * 40)
                
                if summary:
                    wrapped_lines = self._wrap_text(summary, 60)
                    for line in wrapped_lines:
                        report.append(f"  {line}")
                    report.append("")
                
                if key_findings:
                    report.append("关键发现:")
                    for finding in key_findings:
                        if finding.strip():
                            wrapped_lines = self._wrap_text(f"- {finding.strip()}", 60)
                            for j, line in enumerate(wrapped_lines):
                                if j == 0:
                                    report.append(f"  {line}")
                                else:
                                    report.append(f"    {line}")
                    report.append("")
            
            # 洞察与建议
            if insights:
                report.append("[专业洞察]")
                report.append("-" * 40)
                
                for insight in insights:
                    insight_type = insight.get('insight_type', 'general')
                    title = insight.get('title', '未知洞察')
                    description = insight.get('description', '')
                    impact = insight.get('impact', 'medium')
                    suggestions = insight.get('suggestions', [])
                    
                    type_icon = {
                        'recommendation': '[建议]',
                        'warning': '[警告]',
                        'info': '[信息]',
                        'success': '[成功]'
                    }.get(insight_type, '[洞察]')
                    
                    impact_text = {
                        'high': '高影响',
                        'medium': '中等影响', 
                        'low': '低影响'
                    }.get(impact, impact)
                    
                    report.append(f"{type_icon} {title} ({impact_text})")
                    if description:
                        wrapped_lines = self._wrap_text(description, 60)
                        for line in wrapped_lines:
                            report.append(f"   {line}")
                    
                    if suggestions:
                        report.append("   建议措施:")
                        for suggestion in suggestions:
                            wrapped_lines = self._wrap_text(f"- {suggestion}", 56)
                            for j, line in enumerate(wrapped_lines):
                                if j == 0:
                                    report.append(f"     {line}")
                                else:
                                    report.append(f"       {line}")
                    report.append("")
            
            # 报告结尾
            report.append("=" * 80)
            report.append(f"报告生成时间: {dimension_info.get('analysis_timestamp', 'N/A')}")
            report.append("本报告由 OSS Audit 2.0 自动生成")
            report.append("=" * 80)
            
            return '\n'.join(report)
            
        except Exception as e:
            return f"报告生成失败: {str(e)}\n\n原始数据:\n{json.dumps(dimension_data, ensure_ascii=False, indent=2)}"
    
    def _format_status(self, status: str) -> str:
        """格式化状态显示"""
        status_map = {
            'EXCELLENT': '[优秀]',
            'GOOD': '[良好]',
            'WARN': '[警告]',
            'FAIL': '[失败]',
            'UNKNOWN': '[未知]'
        }
        return status_map.get(status, f"[{status}]")
    
    def _format_analysis_level(self, level: str) -> str:
        """格式化分析级别显示"""
        level_map = {
            'basic': '基础分析',
            'enhanced': '增强分析', 
            'ai': 'AI智能分析',
            'collaborative': '协同分析'
        }
        return level_map.get(level, level)
    
    def _wrap_text(self, text: str, width: int) -> List[str]:
        """文本换行处理"""
        if not text:
            return []
            
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            # 估算中文字符宽度（中文字符按2个字符计算）
            word_length = sum(2 if ord(c) > 127 else 1 for c in word)
            
            if current_length + word_length + len(current_line) <= width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else ['']


def format_dimension_file(input_file: str, output_file: str = None) -> str:
    """
    格式化维度文件为可读报告
    
    Args:
        input_file: 输入的JSON文件路径
        output_file: 输出的文本文件路径（可选）
        
    Returns:
        格式化后的报告文本
    """
    try:
        # 读取JSON文件
        with open(input_file, 'r', encoding='utf-8') as f:
            dimension_data = json.load(f)
        
        # 格式化报告
        formatter = DimensionFormatter()
        formatted_report = formatter.format_dimension_report(dimension_data)
        
        # 保存到文件（如果指定了输出文件）
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_report)
        
        return formatted_report
        
    except Exception as e:
        return f"处理文件失败: {str(e)}"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python dimension_formatter.py <input_json_file> [output_txt_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = format_dimension_file(input_file, output_file)
    
    if output_file:
        print(f"报告已保存到: {output_file}")
    else:
        print(result)
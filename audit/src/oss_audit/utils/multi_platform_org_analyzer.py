"""
多平台Git组织分析器 - 统一入口
"""

import logging
from typing import Optional

from .git_platform_analyzer import GitPlatformAnalyzerFactory
# 导入所有平台分析器以注册它们
from .github_analyzer import GitHubAnalyzer
from .gitlab_analyzer import GitLabAnalyzer  
from .gitee_analyzer import GiteeAnalyzer
from .gitea_analyzer import GiteaAnalyzer

logger = logging.getLogger(__name__)


class MultiPlatformOrgAnalyzer:
    """多平台Git组织分析器"""
    
    def __init__(self):
        """初始化多平台分析器"""
        # 确保所有分析器都已注册
        self._ensure_analyzers_registered()
    
    def _ensure_analyzers_registered(self):
        """确保所有分析器都已注册到工厂"""
        # 这些导入会自动执行注册
        pass
    
    def is_supported_org_url(self, url: str) -> bool:
        """检查是否为支持的组织URL"""
        return GitPlatformAnalyzerFactory.is_supported_org_url(url)
    
    def get_supported_platforms(self) -> list:
        """获取支持的平台列表"""
        return GitPlatformAnalyzerFactory.get_supported_platforms()
    
    def create_analyzer(self, url: str, **kwargs) -> Optional[object]:
        """根据URL创建相应的平台分析器"""
        return GitPlatformAnalyzerFactory.create_analyzer(url, **kwargs)
    
    def extract_platform_name(self, url: str) -> Optional[str]:
        """从URL提取平台名称"""
        analyzer = self.create_analyzer(url)
        if analyzer:
            return analyzer.get_platform_name()
        return None
    
    def extract_org_name(self, url: str) -> Optional[str]:
        """从URL提取组织名"""
        analyzer = self.create_analyzer(url)
        if analyzer:
            return analyzer.extract_org_name(url)
        return None
    
    def analyze_organization(self, org_url: str, 
                           audit_runner_class,
                           output_dir: Optional[str] = None,
                           **kwargs):
        """分析指定平台的组织"""
        analyzer = self.create_analyzer(org_url, **kwargs)
        if not analyzer:
            supported_platforms = ', '.join(self.get_supported_platforms())
            raise ValueError(f"不支持的平台URL: {org_url}。支持的平台: {supported_platforms}")
        
        logger.info(f"使用 {analyzer.get_platform_name()} 分析器分析组织")
        return analyzer.analyze_organization(org_url, audit_runner_class, output_dir, **kwargs)
"""
Gitee组织分析器 - 支持Gitee组织级别的项目分析
"""

import logging
import os
from typing import List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

from .git_platform_analyzer import GitPlatformAnalyzer, PlatformRepoInfo, GitPlatformAnalyzerFactory

logger = logging.getLogger(__name__)


@dataclass
class GiteeRepoInfo(PlatformRepoInfo):
    """Gitee仓库信息"""
    def __init__(self, name: str, full_name: str, clone_url: str, web_url: str,
                 description: Optional[str], language: Optional[str], size: int,
                 stars: int, forks: int, updated_at: str, archived: bool, private: bool):
        super().__init__(
            name=name,
            full_name=full_name,
            clone_url=clone_url,
            web_url=web_url,
            description=description,
            language=language,
            size=size,
            stars=stars,
            forks=forks,
            updated_at=updated_at,
            archived=archived,
            private=private,
            platform="Gitee"
        )


class GiteeAnalyzer(GitPlatformAnalyzer):
    """Gitee组织级别分析器"""
    
    def __init__(self, access_token: Optional[str] = None, max_workers: int = 3):
        """
        初始化Gitee组织分析器
        
        Args:
            access_token: Gitee访问令牌（可选）
            max_workers: 最大并发工作线程数
        """
        gitee_token = access_token or os.getenv('GITEE_TOKEN')
        super().__init__(access_token=gitee_token, max_workers=max_workers)
        
    def _setup_authentication(self, session):
        """设置Gitee认证"""
        # Gitee使用查询参数而不是头部认证
        pass
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return "Gitee"
    
    def is_platform_org_url(self, url: str) -> bool:
        """检查是否为Gitee组织URL"""
        if not url.startswith(('http://', 'https://')):
            return False
            
        parsed = urlparse(url)
        if parsed.hostname != 'gitee.com':
            return False
            
        # 解析路径，组织URL格式: /org_name 或 /org_name/
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        
        # 只有组织名，没有仓库名
        return len(path_parts) == 1
    
    def extract_org_name(self, url: str) -> Optional[str]:
        """从URL提取组织名"""
        if not self.is_platform_org_url(url):
            return None
            
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        return path_parts[0] if path_parts else None
    
    def _fetch_org_repositories_impl(self, org_name: str, 
                                    include_archived: bool = False,
                                    include_private: bool = False,
                                    min_size_kb: int = 1,
                                    exclude_forks: bool = True) -> List[PlatformRepoInfo]:
        """
        获取Gitee组织的所有仓库
        """
        repos = []
        page = 1
        per_page = 100
        
        while True:
            url = f"https://gitee.com/api/v5/orgs/{org_name}/repos"
            params = {
                'page': page,
                'per_page': per_page,
                'sort': 'updated',
                'direction': 'desc'
            }
            
            # 如果有访问令牌，添加到参数中
            if self.access_token:
                params['access_token'] = self.access_token
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                repo_data = response.json()
                if not repo_data:
                    break
                    
                for repo in repo_data:
                    # 应用过滤条件
                    if not include_private and repo.get('private', False):
                        continue
                    
                    # Gitee没有归档状态，跳过这个过滤
                    
                    # 仓库大小过滤
                    repo_size = repo.get('size', 0)  # Gitee返回KB为单位
                    if repo_size < min_size_kb:
                        continue
                    
                    if exclude_forks and repo.get('fork', False):
                        continue
                        
                    repo_info = GiteeRepoInfo(
                        name=repo['name'],
                        full_name=repo['full_name'],
                        clone_url=repo['clone_url'],
                        web_url=repo['html_url'],
                        description=repo.get('description'),
                        language=repo.get('language'),
                        size=repo_size,
                        stars=repo.get('stargazers_count', 0),
                        forks=repo.get('forks_count', 0),
                        updated_at=repo.get('updated_at', ''),
                        archived=False,  # Gitee没有归档状态
                        private=repo.get('private', False)
                    )
                    repos.append(repo_info)
                
                # Gitee分页检查
                if len(repo_data) < per_page:
                    break
                    
                page += 1
                logger.info(f"已获取 {len(repos)} 个仓库...")
                
            except Exception as e:
                logger.error(f"获取仓库列表失败: {e}")
                if page == 1:
                    raise
                break
        
        return repos


# 注册Gitee分析器
GitPlatformAnalyzerFactory.register_analyzer("gitee", GiteeAnalyzer)
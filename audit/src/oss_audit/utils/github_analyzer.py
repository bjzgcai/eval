"""
GitHub组织分析器 - 继承自通用Git平台分析器
"""

import logging
import os
from typing import List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

from .git_platform_analyzer import GitPlatformAnalyzer, PlatformRepoInfo, GitPlatformAnalyzerFactory

logger = logging.getLogger(__name__)


@dataclass
class GitHubRepoInfo(PlatformRepoInfo):
    """GitHub仓库信息"""
    def __init__(self, name: str, full_name: str, clone_url: str, html_url: str,
                 description: Optional[str], language: Optional[str], size: int,
                 stars: int, forks: int, updated_at: str, archived: bool, private: bool):
        super().__init__(
            name=name,
            full_name=full_name,
            clone_url=clone_url,
            web_url=html_url,
            description=description,
            language=language,
            size=size,
            stars=stars,
            forks=forks,
            updated_at=updated_at,
            archived=archived,
            private=private,
            platform="GitHub"
        )
        # 保持向后兼容性
        self.html_url = html_url


class GitHubAnalyzer(GitPlatformAnalyzer):
    """GitHub组织级别分析器"""
    
    def __init__(self, access_token: Optional[str] = None, max_workers: int = 3):
        """
        初始化GitHub组织分析器
        
        Args:
            access_token: GitHub访问令牌（可选，但建议提供以避免速率限制）
            max_workers: 最大并发工作线程数
        """
        github_token = access_token or os.getenv('GITHUB_TOKEN')
        super().__init__(access_token=github_token, max_workers=max_workers)
        
    def _setup_authentication(self, session):
        """设置GitHub认证"""
        if self.access_token:
            session.headers.update({
                'Authorization': f'token {self.access_token}'
            })
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return "GitHub"
    
    def is_platform_org_url(self, url: str) -> bool:
        """检查是否为GitHub组织URL"""
        if not url.startswith(('http://', 'https://')):
            return False
            
        parsed = urlparse(url)
        if parsed.hostname != 'github.com':
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
        获取GitHub组织的所有仓库
        """
        repos = []
        page = 1
        per_page = 100
        
        while True:
            url = f"https://api.github.com/orgs/{org_name}/repos"
            params = {
                'page': page,
                'per_page': per_page,
                'sort': 'updated',
                'direction': 'desc'
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                repo_data = response.json()
                if not repo_data:
                    break
                    
                for repo in repo_data:
                    # 应用过滤条件
                    if not include_archived and repo.get('archived', False):
                        continue
                    if not include_private and repo.get('private', False):
                        continue
                    if repo.get('size', 0) < min_size_kb:
                        continue
                    if exclude_forks and repo.get('fork', False):
                        continue
                        
                    repo_info = GitHubRepoInfo(
                        name=repo['name'],
                        full_name=repo['full_name'],
                        clone_url=repo['clone_url'],
                        html_url=repo['html_url'],
                        description=repo.get('description'),
                        language=repo.get('language'),
                        size=repo.get('size', 0),
                        stars=repo.get('stargazers_count', 0),
                        forks=repo.get('forks_count', 0),
                        updated_at=repo.get('updated_at', ''),
                        archived=repo.get('archived', False),
                        private=repo.get('private', False)
                    )
                    repos.append(repo_info)
                
                # 检查是否还有更多页面
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


# 注册GitHub分析器
GitPlatformAnalyzerFactory.register_analyzer("github", GitHubAnalyzer)
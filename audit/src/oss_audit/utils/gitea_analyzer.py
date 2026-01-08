"""
Gitea组织分析器 - 支持Gitea组织级别的项目分析
"""

import logging
import os
from typing import List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

from .git_platform_analyzer import GitPlatformAnalyzer, PlatformRepoInfo, GitPlatformAnalyzerFactory

logger = logging.getLogger(__name__)


@dataclass
class GiteaRepoInfo(PlatformRepoInfo):
    """Gitea仓库信息"""
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
            platform="Gitea"
        )


class GiteaAnalyzer(GitPlatformAnalyzer):
    """Gitea组织级别分析器"""
    
    def __init__(self, access_token: Optional[str] = None, gitea_url: str = None, max_workers: int = 3):
        """
        初始化Gitea组织分析器
        
        Args:
            access_token: Gitea访问令牌（可选）
            gitea_url: Gitea实例URL（必需，因为Gitea通常是自建的）
            max_workers: 最大并发工作线程数
        """
        self.gitea_url = gitea_url or os.getenv('GITEA_URL', 'https://gitea.io')
        self.gitea_url = self.gitea_url.rstrip('/')
        gitea_token = access_token or os.getenv('GITEA_TOKEN')
        super().__init__(access_token=gitea_token, max_workers=max_workers)
        
    def _setup_authentication(self, session):
        """设置Gitea认证"""
        if self.access_token:
            session.headers.update({
                'Authorization': f'token {self.access_token}'
            })
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return "Gitea"
    
    def is_platform_org_url(self, url: str) -> bool:
        """检查是否为Gitea组织URL"""
        if not url.startswith(('http://', 'https://')):
            return False
            
        parsed = urlparse(url)
        gitea_hostname = urlparse(self.gitea_url).hostname
        
        # 检查是否匹配配置的Gitea实例
        if parsed.hostname != gitea_hostname:
            # 也检查常见的Gitea实例
            common_gitea_hosts = ['gitea.io', 'gitea.com', 'codeberg.org']
            if parsed.hostname not in common_gitea_hosts:
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
        
        # 如果URL不是配置的Gitea实例，更新实例URL
        if parsed.hostname != urlparse(self.gitea_url).hostname:
            self.gitea_url = f"{parsed.scheme}://{parsed.hostname}"
            if parsed.port:
                self.gitea_url += f":{parsed.port}"
        
        return path_parts[0] if path_parts else None
    
    def _fetch_org_repositories_impl(self, org_name: str, 
                                    include_archived: bool = False,
                                    include_private: bool = False,
                                    min_size_kb: int = 1,
                                    exclude_forks: bool = True) -> List[PlatformRepoInfo]:
        """
        获取Gitea组织的所有仓库
        """
        repos = []
        page = 1
        limit = 50  # Gitea默认限制
        
        while True:
            url = f"{self.gitea_url}/api/v1/orgs/{org_name}/repos"
            params = {
                'page': page,
                'limit': limit
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
                    
                    # 仓库大小过滤（Gitea返回字节，转换为KB）
                    repo_size = repo.get('size', 0) / 1024
                    if repo_size < min_size_kb and repo_size > 0:
                        continue
                    
                    if exclude_forks and repo.get('fork', False):
                        continue
                        
                    repo_info = GiteaRepoInfo(
                        name=repo['name'],
                        full_name=repo['full_name'],
                        clone_url=repo['clone_url'],
                        web_url=repo['html_url'],
                        description=repo.get('description'),
                        language=repo.get('language'),
                        size=int(repo_size),
                        stars=repo.get('stars_count', 0),
                        forks=repo.get('forks_count', 0),
                        updated_at=repo.get('updated_at', ''),
                        archived=repo.get('archived', False),
                        private=repo.get('private', False)
                    )
                    repos.append(repo_info)
                
                # Gitea分页检查
                if len(repo_data) < limit:
                    break
                    
                page += 1
                logger.info(f"已获取 {len(repos)} 个仓库...")
                
            except Exception as e:
                logger.error(f"获取仓库列表失败: {e}")
                if page == 1:
                    raise
                break
        
        return repos


# 注册Gitea分析器
GitPlatformAnalyzerFactory.register_analyzer("gitea", GiteaAnalyzer)
"""
GitLab组织分析器 - 支持GitLab组织级别的项目分析
"""

import logging
import os
from typing import List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

from .git_platform_analyzer import GitPlatformAnalyzer, PlatformRepoInfo, GitPlatformAnalyzerFactory

logger = logging.getLogger(__name__)


@dataclass
class GitLabRepoInfo(PlatformRepoInfo):
    """GitLab仓库信息"""
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
            platform="GitLab"
        )


class GitLabAnalyzer(GitPlatformAnalyzer):
    """GitLab组织级别分析器"""
    
    def __init__(self, access_token: Optional[str] = None, gitlab_url: str = "https://gitlab.com", max_workers: int = 3):
        """
        初始化GitLab组织分析器
        
        Args:
            access_token: GitLab访问令牌（可选）
            gitlab_url: GitLab实例URL（默认为gitlab.com）
            max_workers: 最大并发工作线程数
        """
        self.gitlab_url = gitlab_url.rstrip('/')
        gitlab_token = access_token or os.getenv('GITLAB_TOKEN')
        super().__init__(access_token=gitlab_token, max_workers=max_workers)
        
    def _setup_authentication(self, session):
        """设置GitLab认证"""
        if self.access_token:
            session.headers.update({
                'Authorization': f'Bearer {self.access_token}'
            })
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return "GitLab"
    
    def is_platform_org_url(self, url: str) -> bool:
        """检查是否为GitLab组织/群组URL"""
        if not url.startswith(('http://', 'https://')):
            return False
            
        parsed = urlparse(url)
        
        # 支持gitlab.com和自建GitLab实例
        gitlab_hostname = urlparse(self.gitlab_url).hostname
        if parsed.hostname != gitlab_hostname and parsed.hostname != 'gitlab.com':
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
        获取GitLab组织/群组的所有项目
        """
        repos = []
        page = 1
        per_page = 100
        
        # 首先获取群组ID
        group_url = f"{self.gitlab_url}/api/v4/groups/{org_name}"
        try:
            group_response = self.session.get(group_url, timeout=30)
            group_response.raise_for_status()
            group_data = group_response.json()
            group_id = group_data['id']
        except Exception as e:
            logger.error(f"无法找到GitLab群组 {org_name}: {e}")
            raise
        
        while True:
            # 获取群组项目
            url = f"{self.gitlab_url}/api/v4/groups/{group_id}/projects"
            params = {
                'page': page,
                'per_page': per_page,
                'order_by': 'updated_at',
                'sort': 'desc',
                'include_subgroups': True  # 包含子群组的项目
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                project_data = response.json()
                if not project_data:
                    break
                    
                for project in project_data:
                    # 应用过滤条件
                    if not include_archived and project.get('archived', False):
                        continue
                    if not include_private and project.get('visibility') == 'private':
                        continue
                    
                    # GitLab没有直接提供仓库大小，估算或跳过
                    estimated_size = project.get('repository_size', 0) / 1024  # 转换为KB
                    if estimated_size < min_size_kb and estimated_size > 0:
                        continue
                    
                    if exclude_forks and project.get('forked_from_project'):
                        continue
                        
                    repo_info = GitLabRepoInfo(
                        name=project['name'],
                        full_name=project['path_with_namespace'],
                        clone_url=project['http_url_to_repo'],
                        web_url=project['web_url'],
                        description=project.get('description'),
                        language=None,  # GitLab API需要额外调用获取主要语言
                        size=int(estimated_size),
                        stars=project.get('star_count', 0),
                        forks=project.get('forks_count', 0),
                        updated_at=project.get('last_activity_at', ''),
                        archived=project.get('archived', False),
                        private=project.get('visibility') == 'private'
                    )
                    repos.append(repo_info)
                
                # 检查是否还有更多页面
                if len(project_data) < per_page:
                    break
                    
                page += 1
                logger.info(f"已获取 {len(repos)} 个项目...")
                
            except Exception as e:
                logger.error(f"获取项目列表失败: {e}")
                if page == 1:
                    raise
                break
        
        return repos


# 注册GitLab分析器
GitPlatformAnalyzerFactory.register_analyzer("gitlab", GitLabAnalyzer)
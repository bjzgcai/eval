"""
测试多平台Git组织分析器
"""

import pytest
from unittest.mock import Mock, patch

from src.oss_audit.utils.multi_platform_org_analyzer import MultiPlatformOrgAnalyzer


class TestMultiPlatformOrgAnalyzer:
    """多平台Git组织分析器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.analyzer = MultiPlatformOrgAnalyzer()

    def test_github_org_url_support(self):
        """测试GitHub组织URL支持"""
        github_urls = [
            "https://github.com/Netflix",
            "https://github.com/microsoft",
            "https://github.com/google",
        ]
        
        for url in github_urls:
            assert self.analyzer.is_supported_org_url(url), f"应该支持GitHub URL: {url}"
            assert self.analyzer.extract_platform_name(url) == "GitHub"
            assert self.analyzer.extract_org_name(url) in ["Netflix", "microsoft", "google"]

    def test_gitlab_org_url_support(self):
        """测试GitLab组织URL支持"""
        gitlab_urls = [
            "https://gitlab.com/gitlab-org",
            "https://gitlab.com/fdroid",
        ]
        
        for url in gitlab_urls:
            assert self.analyzer.is_supported_org_url(url), f"应该支持GitLab URL: {url}"
            assert self.analyzer.extract_platform_name(url) == "GitLab"
            
    def test_gitee_org_url_support(self):
        """测试Gitee组织URL支持"""
        gitee_urls = [
            "https://gitee.com/openharmony",
            "https://gitee.com/mindspore",
        ]
        
        for url in gitee_urls:
            assert self.analyzer.is_supported_org_url(url), f"应该支持Gitee URL: {url}"
            assert self.analyzer.extract_platform_name(url) == "Gitee"

    def test_gitea_org_url_support(self):
        """测试Gitea组织URL支持"""
        gitea_urls = [
            "https://gitea.io/gitea-org",
            "https://codeberg.org/forgejo",
        ]
        
        for url in gitea_urls:
            assert self.analyzer.is_supported_org_url(url), f"应该支持Gitea URL: {url}"
            assert self.analyzer.extract_platform_name(url) == "Gitea"

    def test_unsupported_urls(self):
        """测试不支持的URL"""
        unsupported_urls = [
            "https://bitbucket.org/atlassian",  # Bitbucket暂不支持
            "https://sourceforge.net/u/user",   # SourceForge暂不支持
            "not-a-url",
            "https://example.com/org",
        ]
        
        for url in unsupported_urls:
            assert not self.analyzer.is_supported_org_url(url), f"不应该支持URL: {url}"
            assert self.analyzer.extract_platform_name(url) is None

    def test_repo_urls_not_supported(self):
        """测试仓库URL不被识别为组织URL"""
        repo_urls = [
            "https://github.com/user/repo",
            "https://gitlab.com/group/project",
            "https://gitee.com/user/repo",
        ]
        
        for url in repo_urls:
            assert not self.analyzer.is_supported_org_url(url), f"仓库URL不应该被识别为组织URL: {url}"

    def test_supported_platforms_list(self):
        """测试获取支持的平台列表"""
        platforms = self.analyzer.get_supported_platforms()
        
        expected_platforms = {"github", "gitlab", "gitee", "gitea"}
        actual_platforms = set(platforms)
        
        assert expected_platforms.issubset(actual_platforms), f"应该支持这些平台: {expected_platforms}"

    @patch('src.oss_audit.utils.github_analyzer.GitHubAnalyzer.analyze_organization')
    def test_create_github_analyzer(self, mock_analyze):
        """测试创建GitHub分析器"""
        url = "https://github.com/Netflix"
        analyzer = self.analyzer.create_analyzer(url)
        
        assert analyzer is not None
        assert analyzer.get_platform_name() == "GitHub"

    @patch('src.oss_audit.utils.gitlab_analyzer.GitLabAnalyzer.analyze_organization')
    def test_create_gitlab_analyzer(self, mock_analyze):
        """测试创建GitLab分析器"""
        url = "https://gitlab.com/gitlab-org"
        analyzer = self.analyzer.create_analyzer(url)
        
        assert analyzer is not None
        assert analyzer.get_platform_name() == "GitLab"

    @patch('src.oss_audit.utils.gitee_analyzer.GiteeAnalyzer.analyze_organization')  
    def test_create_gitee_analyzer(self, mock_analyze):
        """测试创建Gitee分析器"""
        url = "https://gitee.com/openharmony"
        analyzer = self.analyzer.create_analyzer(url)
        
        assert analyzer is not None
        assert analyzer.get_platform_name() == "Gitee"

    @patch('src.oss_audit.utils.gitea_analyzer.GiteaAnalyzer.analyze_organization')
    def test_create_gitea_analyzer(self, mock_analyze):
        """测试创建Gitea分析器"""
        url = "https://gitea.io/gitea-org"
        analyzer = self.analyzer.create_analyzer(url)
        
        assert analyzer is not None
        assert analyzer.get_platform_name() == "Gitea"

    def test_create_analyzer_for_unsupported_url(self):
        """测试为不支持的URL创建分析器"""
        url = "https://bitbucket.org/atlassian"
        analyzer = self.analyzer.create_analyzer(url)
        
        assert analyzer is None

    @patch('src.oss_audit.utils.github_analyzer.GitHubAnalyzer.analyze_organization')
    def test_analyze_organization_success(self, mock_analyze):
        """测试成功分析组织"""
        url = "https://github.com/Netflix"
        
        # 模拟分析结果
        mock_context = Mock()
        mock_context.platform = "GitHub"
        mock_context.org_name = "Netflix"
        mock_analyze.return_value = mock_context
        
        result = self.analyzer.analyze_organization(url, Mock())
        
        assert result is not None
        mock_analyze.assert_called_once()

    def test_analyze_unsupported_organization(self):
        """测试分析不支持的组织URL"""
        url = "https://bitbucket.org/atlassian"
        
        with pytest.raises(ValueError, match="不支持的平台URL"):
            self.analyzer.analyze_organization(url, Mock())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
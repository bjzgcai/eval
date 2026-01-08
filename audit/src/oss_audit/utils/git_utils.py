"""
Git工具类 - 处理Git仓库克隆和管理
"""

import os
import subprocess
import tempfile
import shutil
import logging
from typing import Tuple, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitUtils:
    """Git工具类"""
    
    @staticmethod
    def is_git_url(url: str) -> bool:
        """检查是否为Git URL"""
        if not url:
            return False
        
        # HTTP/HTTPS Git URLs
        if url.startswith(('https://github.com/', 'https://gitlab.com/', 'https://gitee.com/')):
            return True
        
        # SSH Git URLs
        if url.startswith(('git@', 'ssh://')):
            return True
        
        # Git protocol
        if url.startswith('git://'):
            return True
        
        return False
    
    @staticmethod
    def clone_repository(git_url: str, target_dir: Optional[str] = None, shallow: bool = True) -> str:
        """
        克隆Git仓库到本地目录
        
        Args:
            git_url: Git仓库URL
            target_dir: 目标目录，如果为None则创建临时目录
            shallow: 是否使用浅克隆（默认True）
            
        Returns:
            本地仓库路径
        """
        if not target_dir:
            target_dir = tempfile.mkdtemp(prefix="oss_audit_")
        
        try:
            # 构建git clone命令
            cmd = ['git', 'clone']
            if shallow:
                cmd.extend(['--depth', '1'])
            cmd.extend([git_url, target_dir])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise RuntimeError(f"Git clone失败: {result.stderr}")
            
            logger.info(f"成功克隆仓库: {git_url} -> {target_dir}")
            return target_dir
            
        except Exception as e:
            # 清理失败的克隆目录
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            raise RuntimeError(f"克隆仓库失败 {git_url}: {e}")
    
    @staticmethod
    def cleanup_temp_repo(temp_dir: str):
        """清理临时仓库目录"""
        if temp_dir and os.path.exists(temp_dir):
            try:
                # Windows下需要特殊处理.git目录的只读文件
                if os.name == 'nt':  # Windows
                    import stat
                    def handle_remove_readonly(func, path, exc):
                        if exc[1].errno == 13:  # Permission denied
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        else:
                            raise
                    
                    shutil.rmtree(temp_dir, onerror=handle_remove_readonly)
                else:
                    shutil.rmtree(temp_dir)
                logger.debug(f"已清理临时目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败 {temp_dir}: {e}")
                # 尝试强制清理（最后手段）
                try:
                    if os.name == 'nt':
                        subprocess.run(['rmdir', '/s', '/q', temp_dir], 
                                     shell=True, check=False, capture_output=True)
                except:
                    pass
    
    @staticmethod
    def cleanup_temp_dir(temp_dir: str):
        """清理临时目录（别名方法）"""
        GitUtils.cleanup_temp_repo(temp_dir)


def resolve_project_path(project_path: str) -> Tuple[str, bool]:
    """
    解析项目路径，支持Git URL
    
    Args:
        project_path: 项目路径或Git URL
        
    Returns:
        (actual_path, is_temp) - 实际路径和是否为临时目录的标志
    """
    if GitUtils.is_git_url(project_path):
        # 克隆Git仓库到临时目录
        temp_dir = GitUtils.clone_repository(project_path)
        return temp_dir, True
    else:
        # 本地路径，直接返回
        return project_path, False
#!/usr/bin/env python3
"""
确定性缓存系统 - 用于缓存AI分析和工具执行结果
确保相同输入产生相同输出，提高分析一致性
"""

import os
import json
import hashlib
import pickle
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    content: Any
    timestamp: datetime
    content_hash: str
    metadata: Dict[str, Any]
    version: str = "1.0"


class DeterministicCache:
    """确定性缓存系统"""
    
    def __init__(self, cache_dir: Optional[str] = None, expire_hours: int = 168):  # 7天过期
        """
        初始化缓存系统
        
        Args:
            cache_dir: 缓存目录，默认为 ~/.oss-audit-cache
            expire_hours: 缓存过期时间（小时），默认7天
        """
        self.cache_dir = Path(cache_dir or os.path.expanduser("~/.oss-audit-cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.expire_hours = expire_hours
        
        # 创建子目录
        self.ai_cache_dir = self.cache_dir / "ai_results"
        self.tool_cache_dir = self.cache_dir / "tool_results"
        self.project_cache_dir = self.cache_dir / "project_analysis"
        
        for subdir in [self.ai_cache_dir, self.tool_cache_dir, self.project_cache_dir]:
            subdir.mkdir(exist_ok=True)
    
    def _generate_key(self, content: Union[str, dict], context: Optional[Dict] = None) -> str:
        """
        生成确定性缓存键
        
        Args:
            content: 要缓存的内容
            context: 额外的上下文信息
            
        Returns:
            16进制哈希键
        """
        if isinstance(content, dict):
            # 确保字典键按字母顺序排序
            content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        else:
            content_str = str(content)
        
        if context:
            context_str = json.dumps(context, sort_keys=True, ensure_ascii=False)
            content_str += context_str
        
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    def _get_cache_path(self, cache_type: str, key: str) -> Path:
        """获取缓存文件路径"""
        type_dir_map = {
            'ai': self.ai_cache_dir,
            'tool': self.tool_cache_dir,
            'project': self.project_cache_dir
        }
        
        cache_dir = type_dir_map.get(cache_type, self.cache_dir)
        return cache_dir / f"{key}.cache"
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """检查缓存是否过期"""
        expire_time = entry.timestamp + timedelta(hours=self.expire_hours)
        return datetime.now() > expire_time
    
    def get(self, cache_type: str, content: Union[str, dict], 
            context: Optional[Dict] = None) -> Optional[Any]:
        """
        获取缓存内容
        
        Args:
            cache_type: 缓存类型 ('ai', 'tool', 'project')
            content: 缓存键内容
            context: 额外上下文
            
        Returns:
            缓存的内容，如果不存在或已过期返回None
        """
        try:
            key = self._generate_key(content, context)
            cache_path = self._get_cache_path(cache_type, key)
            
            if not cache_path.exists():
                logger.debug(f"缓存未命中: {cache_type}:{key[:8]}")
                return None
            
            with open(cache_path, 'rb') as f:
                entry: CacheEntry = pickle.load(f)
            
            if self._is_expired(entry):
                logger.debug(f"缓存已过期: {cache_type}:{key[:8]}")
                cache_path.unlink()  # 删除过期缓存
                return None
            
            logger.debug(f"缓存命中: {cache_type}:{key[:8]}")
            return entry.content
            
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")
            return None
    
    def set(self, cache_type: str, content: Union[str, dict], result: Any,
            context: Optional[Dict] = None, metadata: Optional[Dict] = None) -> str:
        """
        设置缓存内容
        
        Args:
            cache_type: 缓存类型 ('ai', 'tool', 'project')
            content: 缓存键内容
            result: 要缓存的结果
            context: 额外上下文
            metadata: 元数据
            
        Returns:
            缓存键
        """
        try:
            key = self._generate_key(content, context)
            cache_path = self._get_cache_path(cache_type, key)
            
            entry = CacheEntry(
                content=result,
                timestamp=datetime.now(),
                content_hash=key,
                metadata=metadata or {}
            )
            
            with open(cache_path, 'wb') as f:
                pickle.dump(entry, f)
            
            logger.debug(f"缓存已保存: {cache_type}:{key[:8]}")
            return key
            
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")
            return ""
    
    def invalidate(self, cache_type: str, content: Union[str, dict],
                   context: Optional[Dict] = None) -> bool:
        """
        使指定缓存失效
        
        Args:
            cache_type: 缓存类型
            content: 缓存键内容
            context: 额外上下文
            
        Returns:
            是否成功删除
        """
        try:
            key = self._generate_key(content, context)
            cache_path = self._get_cache_path(cache_type, key)
            
            if cache_path.exists():
                cache_path.unlink()
                logger.debug(f"缓存已删除: {cache_type}:{key[:8]}")
                return True
            return False
            
        except Exception as e:
            logger.warning(f"缓存删除失败: {e}")
            return False
    
    def clear_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存文件数量
        """
        cleared_count = 0
        
        for cache_dir in [self.ai_cache_dir, self.tool_cache_dir, self.project_cache_dir]:
            for cache_file in cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        entry: CacheEntry = pickle.load(f)
                    
                    if self._is_expired(entry):
                        cache_file.unlink()
                        cleared_count += 1
                        
                except Exception as e:
                    logger.warning(f"清理缓存文件失败 {cache_file}: {e}")
                    # 删除损坏的缓存文件
                    try:
                        cache_file.unlink()
                        cleared_count += 1
                    except:
                        pass
        
        if cleared_count > 0:
            logger.info(f"清理了 {cleared_count} 个过期缓存文件")
        
        return cleared_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计数据
        """
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'by_type': {}
        }
        
        for cache_type, cache_dir in [
            ('ai', self.ai_cache_dir),
            ('tool', self.tool_cache_dir), 
            ('project', self.project_cache_dir)
        ]:
            cache_files = list(cache_dir.glob("*.cache"))
            file_count = len(cache_files)
            
            total_size = sum(f.stat().st_size for f in cache_files)
            
            stats['by_type'][cache_type] = {
                'files': file_count,
                'size_mb': round(total_size / (1024 * 1024), 2)
            }
            
            stats['total_files'] += file_count
            stats['total_size_mb'] += stats['by_type'][cache_type]['size_mb']
        
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        return stats


# 全局缓存实例
_global_cache: Optional[DeterministicCache] = None


def get_cache() -> DeterministicCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = DeterministicCache()
    return _global_cache


def cache_ai_result(prompt: str, result: Any, model: str = "unknown",
                   context: Optional[Dict] = None) -> str:
    """
    缓存AI分析结果
    
    Args:
        prompt: AI提示词
        result: AI分析结果
        model: 使用的模型名称
        context: 额外上下文
        
    Returns:
        缓存键
    """
    cache = get_cache()
    metadata = {'model': model, 'type': 'ai_analysis'}
    return cache.set('ai', prompt, result, context, metadata)


def get_cached_ai_result(prompt: str, context: Optional[Dict] = None) -> Optional[Any]:
    """
    获取缓存的AI分析结果
    
    Args:
        prompt: AI提示词
        context: 额外上下文
        
    Returns:
        缓存的AI结果，如果不存在返回None
    """
    cache = get_cache()
    return cache.get('ai', prompt, context)


def cache_tool_result(tool_name: str, project_path: str, result: Any,
                     tool_config: Optional[Dict] = None) -> str:
    """
    缓存工具执行结果
    
    Args:
        tool_name: 工具名称
        project_path: 项目路径
        result: 工具执行结果
        tool_config: 工具配置
        
    Returns:
        缓存键
    """
    cache = get_cache()
    content = {'tool': tool_name, 'project': project_path}
    metadata = {'tool_name': tool_name, 'type': 'tool_execution'}
    return cache.set('tool', content, result, tool_config, metadata)


def get_cached_tool_result(tool_name: str, project_path: str,
                          tool_config: Optional[Dict] = None) -> Optional[Any]:
    """
    获取缓存的工具执行结果
    
    Args:
        tool_name: 工具名称
        project_path: 项目路径
        tool_config: 工具配置
        
    Returns:
        缓存的工具结果，如果不存在返回None
    """
    cache = get_cache()
    content = {'tool': tool_name, 'project': project_path}
    return cache.get('tool', content, tool_config)


if __name__ == "__main__":
    # 测试缓存系统
    cache = DeterministicCache()
    
    # 测试AI缓存
    test_prompt = "分析这个项目的代码质量"
    test_result = {"score": 85, "issues": ["缺少测试"]}
    
    cache.set('ai', test_prompt, test_result, metadata={'model': 'gpt-4'})
    cached_result = cache.get('ai', test_prompt)
    
    print(f"缓存测试: {cached_result == test_result}")
    print(f"缓存统计: {cache.get_stats()}")
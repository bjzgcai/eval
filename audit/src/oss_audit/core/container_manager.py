"""
容器管理器 - 统一容器工具支持和错误处理

提供Docker、Podman等容器引擎的统一接口，增强错误处理和恢复机制。
"""

import os
import subprocess
import logging
import time
import shutil
import json
import tempfile
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ContainerEngine(Enum):
    """容器引擎类型"""
    DOCKER = "docker"
    PODMAN = "podman"
    NERDCTL = "nerdctl"
    COLIMA = "colima"


class ContainerStatus(Enum):
    """容器状态"""
    NOT_FOUND = "not_found"
    RUNNING = "running"
    STOPPED = "stopped" 
    PAUSED = "paused"
    EXITED = "exited"
    ERROR = "error"


@dataclass
class ContainerInfo:
    """容器信息"""
    name: str
    image: str
    status: ContainerStatus
    engine: ContainerEngine
    id: Optional[str] = None
    ports: Dict[str, str] = field(default_factory=dict)
    volumes: Dict[str, str] = field(default_factory=dict)
    created_at: Optional[str] = None
    

@dataclass
class ContainerError:
    """容器错误信息"""
    error_type: str
    message: str
    command: List[str]
    stderr: str = ""
    exit_code: int = -1
    suggestions: List[str] = field(default_factory=list)


class ContainerManager:
    """统一容器管理器"""
    
    def __init__(self):
        self.available_engines: List[ContainerEngine] = []
        self.primary_engine: Optional[ContainerEngine] = None
        self.fallback_engines: List[ContainerEngine] = []
        
        # 默认镜像配置
        self.default_images = {
            "tools": "oss-audit:tools-2.0",
            "python": "python:3.11-slim",
            "node": "node:18-alpine",
            "java": "openjdk:11-jre-slim",
            "golang": "golang:1.21-alpine"
        }
        
        # 容器资源限制
        self.resource_limits = {
            "memory": "1g",
            "cpu": "1.0",
            "timeout": 600
        }
        
        self._initialize()
    
    def _initialize(self):
        """初始化容器管理器"""
        logger.info("初始化容器管理器...")
        
        # 发现可用的容器引擎
        self._discover_engines()
        
        if not self.available_engines:
            logger.warning("⚠️  未发现可用的容器引擎")
            return
        
        # 设置主引擎和备用引擎
        self.primary_engine = self.available_engines[0]
        self.fallback_engines = self.available_engines[1:]
        
        logger.info(f"🐳 主容器引擎: {self.primary_engine.value}")
        if self.fallback_engines:
            engines = [e.value for e in self.fallback_engines]
            logger.info(f"🔄 备用引擎: {', '.join(engines)}")
    
    def _discover_engines(self):
        """发现可用的容器引擎"""
        engines_to_check = [
            ContainerEngine.DOCKER,
            ContainerEngine.PODMAN, 
            ContainerEngine.NERDCTL,
            ContainerEngine.COLIMA
        ]
        
        for engine in engines_to_check:
            if self._check_engine_availability(engine):
                self.available_engines.append(engine)
                logger.debug(f"✅ 发现容器引擎: {engine.value}")
            else:
                logger.debug(f"❌ 容器引擎不可用: {engine.value}")
    
    def _check_engine_availability(self, engine: ContainerEngine) -> bool:
        """检查容器引擎可用性"""
        try:
            # 检查命令是否存在
            if not shutil.which(engine.value):
                return False
            
            # 运行基本命令测试
            result = subprocess.run(
                [engine.value, 'version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def is_available(self) -> bool:
        """检查是否有可用的容器引擎"""
        return len(self.available_engines) > 0
    
    def get_engine_status(self, engine: Optional[ContainerEngine] = None) -> Dict[str, Any]:
        """获取引擎状态"""
        target_engine = engine or self.primary_engine
        if not target_engine:
            return {"available": False, "error": "No container engine available"}
        
        try:
            result = subprocess.run(
                [target_engine.value, 'info'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                return {
                    "available": True,
                    "engine": target_engine.value,
                    "running": True,
                    "info": result.stdout
                }
            else:
                return {
                    "available": True,
                    "engine": target_engine.value,
                    "running": False,
                    "error": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                "available": True,
                "engine": target_engine.value,
                "running": False,
                "error": "Engine info command timeout"
            }
        except Exception as e:
            return {
                "available": False,
                "engine": target_engine.value,
                "error": str(e)
            }
    
    def ensure_image(self, image: str, engine: Optional[ContainerEngine] = None) -> bool:
        """确保镜像存在"""
        target_engine = engine or self.primary_engine
        if not target_engine:
            logger.error("没有可用的容器引擎")
            return False
        
        try:
            # 检查镜像是否存在
            result = subprocess.run(
                [target_engine.value, 'image', 'inspect', image],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            
            if result.returncode == 0:
                logger.debug(f"✅ 镜像已存在: {image}")
                return True
            
            # 尝试拉取镜像
            logger.info(f"📥 拉取容器镜像: {image}")
            result = subprocess.run(
                [target_engine.value, 'pull', image],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"✅ 镜像拉取成功: {image}")
                return True
            else:
                logger.error(f"❌ 镜像拉取失败: {image} - {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"镜像操作超时: {image}")
            return False
        except Exception as e:
            logger.error(f"镜像操作异常: {e}")
            return False
    
    def run_container(self, 
                     image: str,
                     command: List[str],
                     volumes: Dict[str, str] = None,
                     environment: Dict[str, str] = None,
                     working_dir: str = None,
                     timeout: int = None,
                     engine: Optional[ContainerEngine] = None) -> Tuple[bool, str, str]:
        """运行容器"""
        target_engine = engine or self.primary_engine
        if not target_engine:
            return False, "", "No container engine available"
        
        # 构建运行命令
        run_cmd = [target_engine.value, 'run', '--rm']
        
        # 添加资源限制
        run_cmd.extend(['--memory', self.resource_limits['memory']])
        run_cmd.extend(['--cpus', self.resource_limits['cpu']])
        
        # 添加卷挂载
        if volumes:
            for host_path, container_path in volumes.items():
                run_cmd.extend(['-v', f'{host_path}:{container_path}'])
        
        # 添加环境变量
        if environment:
            for key, value in environment.items():
                run_cmd.extend(['-e', f'{key}={value}'])
        
        # 设置工作目录
        if working_dir:
            run_cmd.extend(['-w', working_dir])
        
        # 添加镜像和命令
        run_cmd.append(image)
        run_cmd.extend(command)
        
        # 执行容器
        try:
            logger.debug(f"执行容器命令: {' '.join(run_cmd)}")
            
            result = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout or self.resource_limits['timeout']
            )
            
            return (result.returncode == 0, result.stdout, result.stderr)
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"Container execution timeout ({timeout or self.resource_limits['timeout']}s)"
            logger.error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Container execution failed: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg
    
    def get_container_info(self, 
                          container_name: str, 
                          engine: Optional[ContainerEngine] = None) -> Optional[ContainerInfo]:
        """获取容器信息"""
        target_engine = engine or self.primary_engine
        if not target_engine:
            return None
        
        try:
            result = subprocess.run(
                [target_engine.value, 'inspect', container_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            
            if result.returncode != 0:
                return ContainerInfo(
                    name=container_name,
                    image="",
                    status=ContainerStatus.NOT_FOUND,
                    engine=target_engine
                )
            
            # 解析容器信息
            inspect_data = json.loads(result.stdout)
            if not inspect_data:
                return None
            
            container_data = inspect_data[0]
            
            # 确定容器状态
            state = container_data.get('State', {})
            if state.get('Running'):
                status = ContainerStatus.RUNNING
            elif state.get('Paused'):
                status = ContainerStatus.PAUSED
            elif state.get('Status') == 'exited':
                status = ContainerStatus.EXITED
            else:
                status = ContainerStatus.STOPPED
            
            return ContainerInfo(
                name=container_name,
                image=container_data.get('Config', {}).get('Image', ''),
                status=status,
                engine=target_engine,
                id=container_data.get('Id', '')[:12],
                created_at=container_data.get('Created')
            )
            
        except (json.JSONDecodeError, subprocess.TimeoutExpired, Exception) as e:
            logger.error(f"获取容器信息失败: {e}")
            return ContainerInfo(
                name=container_name,
                image="",
                status=ContainerStatus.ERROR,
                engine=target_engine
            )
    
    def cleanup_containers(self, pattern: str = "oss-audit*") -> int:
        """清理匹配的容器"""
        if not self.primary_engine:
            return 0
        
        cleaned = 0
        try:
            # 获取匹配的容器
            result = subprocess.run(
                [self.primary_engine.value, 'ps', '-a', '--filter', f'name={pattern}', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                container_names = result.stdout.strip().split('\n')
                
                for name in container_names:
                    if name.strip():
                        try:
                            # 停止并删除容器
                            subprocess.run([self.primary_engine.value, 'rm', '-f', name.strip()], 
                                         capture_output=True, timeout=10)
                            cleaned += 1
                            logger.debug(f"清理容器: {name.strip()}")
                        except Exception as e:
                            logger.warning(f"清理容器失败 {name.strip()}: {e}")
            
        except Exception as e:
            logger.error(f"容器清理操作失败: {e}")
        
        if cleaned > 0:
            logger.info(f"🧹 清理了 {cleaned} 个容器")
        
        return cleaned
    
    def diagnose_issues(self) -> Dict[str, Any]:
        """诊断容器相关问题"""
        diagnosis = {
            "engines_available": len(self.available_engines),
            "primary_engine": self.primary_engine.value if self.primary_engine else None,
            "issues": [],
            "recommendations": []
        }
        
        if not self.available_engines:
            diagnosis["issues"].append("没有可用的容器引擎")
            diagnosis["recommendations"].extend([
                "安装 Docker Desktop 或 Podman",
                "确保容器服务正在运行",
                "检查用户权限（可能需要加入 docker 组）"
            ])
            return diagnosis
        
        # 检查主引擎状态
        if self.primary_engine:
            status = self.get_engine_status(self.primary_engine)
            if not status.get("running", False):
                diagnosis["issues"].append(f"主容器引擎 {self.primary_engine.value} 未运行")
                diagnosis["recommendations"].append(f"启动 {self.primary_engine.value} 服务")
        
        # 检查镜像可用性
        for image_type, image_name in self.default_images.items():
            if not self.ensure_image(image_name):
                diagnosis["issues"].append(f"镜像 {image_name} 不可用")
                diagnosis["recommendations"].append(f"手动拉取镜像: {self.primary_engine.value} pull {image_name}")
        
        return diagnosis
    
    def create_error_report(self, error: Exception, command: List[str], context: Dict[str, Any]) -> ContainerError:
        """创建详细的错误报告"""
        error_type = type(error).__name__
        
        if isinstance(error, subprocess.TimeoutExpired):
            suggestions = [
                "增加超时时间",
                "检查容器镜像是否过大",
                "检查网络连接是否正常"
            ]
        elif isinstance(error, subprocess.CalledProcessError):
            suggestions = [
                "检查容器镜像是否存在",
                "验证命令语法是否正确",
                "检查容器引擎是否正常运行"
            ]
        elif isinstance(error, FileNotFoundError):
            suggestions = [
                "安装所需的容器引擎",
                "检查PATH环境变量",
                "验证引擎是否正确安装"
            ]
        else:
            suggestions = [
                "查看详细错误日志",
                "尝试重启容器服务",
                "检查系统资源使用情况"
            ]
        
        return ContainerError(
            error_type=error_type,
            message=str(error),
            command=command,
            stderr=getattr(error, 'stderr', '') if hasattr(error, 'stderr') else '',
            exit_code=getattr(error, 'returncode', -1) if hasattr(error, 'returncode') else -1,
            suggestions=suggestions
        )
    
    def attempt_recovery(self, error: ContainerError) -> bool:
        """尝试从错误中恢复"""
        logger.info(f"尝试从容器错误中恢复: {error.error_type}")
        
        # 超时错误 - 尝试增加超时并重试
        if error.error_type == "TimeoutExpired":
            self.resource_limits['timeout'] = min(self.resource_limits['timeout'] * 2, 1800)
            logger.info(f"增加超时时间到 {self.resource_limits['timeout']} 秒")
            return True
        
        # 命令错误 - 尝试使用备用引擎
        if error.error_type == "CalledProcessError" and self.fallback_engines:
            original_engine = self.primary_engine
            self.primary_engine = self.fallback_engines[0]
            self.fallback_engines = [original_engine] + self.fallback_engines[1:]
            logger.info(f"切换到备用容器引擎: {self.primary_engine.value}")
            return True
        
        # 文件未找到 - 重新发现引擎
        if error.error_type == "FileNotFoundError":
            self._discover_engines()
            if self.available_engines:
                self.primary_engine = self.available_engines[0]
                logger.info(f"重新发现主引擎: {self.primary_engine.value}")
                return True
        
        return False


# 全局容器管理器实例
_global_container_manager = None

def get_container_manager() -> ContainerManager:
    """获取全局容器管理器实例"""
    global _global_container_manager
    if _global_container_manager is None:
        _global_container_manager = ContainerManager()
    return _global_container_manager


# 使用示例和测试
if __name__ == "__main__":
    # 基本使用示例
    manager = ContainerManager()
    
    if manager.is_available():
        print(f"✅ 容器管理器可用，主引擎: {manager.primary_engine.value}")
        
        # 获取引擎状态
        status = manager.get_engine_status()
        print(f"引擎状态: {status}")
        
        # 诊断问题
        diagnosis = manager.diagnose_issues()
        print(f"诊断结果: {diagnosis}")
        
    else:
        print("❌ 没有可用的容器引擎")
        diagnosis = manager.diagnose_issues()
        print("建议:")
        for rec in diagnosis["recommendations"]:
            print(f"  - {rec}")
#!/usr/bin/env python3
"""
Project Detector - 项目检测器
负责智能检测项目语言组成、结构类型和项目类型
支持单项目、多项目和Monorepo结构
"""

import os
import pathlib
import yaml
import json
import glob
import fnmatch
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StructureType(Enum):
    """项目结构类型"""
    SINGLE_PROJECT = "single_project"    # 单一项目
    MULTI_PROJECT = "multi_project"      # 多项目仓库  
    MONOREPO = "monorepo"               # Monorepo结构
    UNKNOWN = "unknown"                 # 未知结构


class ProjectType(Enum):
    """项目类型"""
    WEB_APPLICATION = "web_application"
    LIBRARY = "library"
    CLI_TOOL = "cli_tool"
    DATA_SCIENCE = "data_science"
    MOBILE_APP = "mobile_app"
    DESKTOP_APP = "desktop_app"
    GAME = "game"
    UNKNOWN = "unknown"


@dataclass
class SizeMetrics:
    """项目规模指标"""
    total_files: int = 0
    total_lines: int = 0
    code_files: int = 0
    code_lines: int = 0
    test_files: int = 0
    test_lines: int = 0
    doc_files: int = 0
    doc_lines: int = 0
    
    def get_size_category(self) -> str:
        """获取项目规模分类"""
        if self.code_lines < 100:
            return "tiny"
        elif self.code_lines < 1000:
            return "small"
        elif self.code_lines < 10000:
            return "medium"
        elif self.code_lines < 100000:
            return "large"
        else:
            return "huge"


@dataclass
class ProjectInfo:
    """项目信息数据模型"""
    path: str
    name: str
    languages: Dict[str, float] = field(default_factory=dict)      # 语言名称 -> 占比
    structure_type: StructureType = StructureType.UNKNOWN
    project_type: ProjectType = ProjectType.UNKNOWN
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # 语言 -> 依赖列表
    size_metrics: SizeMetrics = field(default_factory=SizeMetrics)
    build_tools: List[str] = field(default_factory=list)           # 检测到的构建工具
    subprojects: List[Dict[str, Any]] = field(default_factory=list)  # 子项目信息（多项目/monorepo）
    confidence: float = 0.0                                        # 检测置信度
    
    def get_primary_language(self) -> Optional[str]:
        """获取主要编程语言"""
        if not self.languages:
            return None
        return max(self.languages.items(), key=lambda x: x[1])[0]
    
    def has_database_access(self) -> bool:
        """检查是否有数据库访问"""
        db_indicators = [
            'sqlalchemy', 'django', 'psycopg2', 'pymongo', 'redis',
            'mysql', 'postgresql', 'sqlite', 'mongodb', 'cassandra'
        ]
        for deps in self.dependencies.values():
            if any(db in dep.lower() for dep in deps for db in db_indicators):
                return True
        return False


class ProjectDetector:
    """项目检测器 - 负责智能检测项目特征"""
    
    def __init__(self, language_config_path: Optional[str] = None):
        """
        初始化项目检测器
        
        Args:
            language_config_path: 语言检测配置文件路径
        """
        self.config_path = language_config_path or self._get_default_config_path()
        self.config = self._load_language_config()
        
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        current_dir = pathlib.Path(__file__).parent
        config_dir = current_dir.parent / 'config'
        return str(config_dir / 'language_detection.yaml')
    
    def _load_language_config(self) -> Dict[str, Any]:
        """加载语言检测配置"""
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"语言检测配置文件不存在: {self.config_path}")
                return {}
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"成功加载语言检测配置: {len(config.get('languages', {}))} 种语言")
            return config
            
        except Exception as e:
            logger.error(f"加载语言检测配置失败: {e}")
            return {}
    
    def detect_project_info(self, project_path: str) -> ProjectInfo:
        """
        检测项目完整信息
        
        Args:
            project_path: 项目路径
            
        Returns:
            ProjectInfo对象
        """
        path = pathlib.Path(project_path)
        if not path.exists():
            logger.error(f"项目路径不存在: {project_path}")
            return ProjectInfo(path=project_path, name=path.name)
        
        logger.info(f"开始检测项目: {project_path}")
        
        # 基本信息
        project_name = path.name if path.name else "unknown"
        project_info = ProjectInfo(
            path=str(path),
            name=project_name
        )
        
        try:
            # 1. 检测语言组成
            project_info.languages = self._detect_languages(path)
            logger.info(f"检测到语言: {project_info.languages}")
            
            # 2. 检测项目结构类型
            project_info.structure_type = self._detect_structure_type(path)
            logger.info(f"项目结构类型: {project_info.structure_type.value if hasattr(project_info.structure_type, 'value') else str(project_info.structure_type)}")
            
            # 3. 推断项目类型
            project_info.project_type = self._infer_project_type(path, project_info.languages)
            logger.info(f"项目类型: {project_info.project_type.value if hasattr(project_info.project_type, 'value') else str(project_info.project_type)}")
            
            # 4. 分析依赖
            project_info.dependencies = self._analyze_dependencies(path, project_info.languages)
            
            # 5. 计算规模指标
            project_info.size_metrics = self._calculate_size_metrics(path, project_info.languages)
            logger.info(f"项目规模: {project_info.size_metrics.get_size_category()} ({project_info.size_metrics.code_lines} 行代码)")
            
            # 6. 检测构建工具
            project_info.build_tools = self._detect_build_tools(path, project_info.languages)
            
            # 7. 如果是多项目结构，分析子项目
            if project_info.structure_type in [StructureType.MULTI_PROJECT, StructureType.MONOREPO]:
                project_info.subprojects = self._analyze_subprojects(path)
            
            # 8. 计算检测置信度
            project_info.confidence = self._calculate_confidence(project_info)
            
        except Exception as e:
            logger.error(f"检测项目信息时发生错误: {e}")
            project_info.confidence = 0.0
        
        logger.info(f"项目检测完成，置信度: {project_info.confidence:.2f}")
        return project_info
    
    def _detect_languages(self, project_path: pathlib.Path) -> Dict[str, float]:
        """检测项目语言组成"""
        if 'languages' not in self.config:
            return {}
        
        language_files = {}  # 语言 -> 文件数量
        total_files = 0
        
        # 获取检测设置
        settings = self.config.get('detection_settings', {})
        max_files = settings.get('max_files_scan', 10000)
        max_depth = settings.get('max_depth', 10)
        ignore_dirs = set(settings.get('ignore_directories', []))
        ignore_patterns = settings.get('ignore_file_patterns', [])
        
        # 扫描文件
        scanned_files = 0
        for root, dirs, files in os.walk(project_path):
            # 限制扫描深度
            level = root.replace(str(project_path), '').count(os.sep)
            if level >= max_depth:
                dirs[:] = []
                continue
            
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if scanned_files >= max_files:
                    break
                
                # 检查是否匹配忽略模式
                if any(fnmatch.fnmatch(file, pattern) for pattern in ignore_patterns):
                    continue
                
                file_path = pathlib.Path(root) / file
                extension = file_path.suffix.lower()
                
                # 检查每种语言
                for language, lang_config in self.config['languages'].items():
                    extensions = lang_config.get('file_extensions', [])
                    if extension in extensions:
                        language_files[language] = language_files.get(language, 0) + 1
                        total_files += 1
                        break
                
                scanned_files += 1
            
            if scanned_files >= max_files:
                break
        
        # 计算权重文件数（考虑关键文件）
        weighted_files = {}
        for language, lang_config in self.config['languages'].items():
            base_files = language_files.get(language, 0)
            weight_multiplier = lang_config.get('weight_multiplier', 1.0)
            
            # 检查关键文件
            key_files = lang_config.get('key_files', [])
            key_file_bonus = 0
            for key_file in key_files:
                if (project_path / key_file).exists():
                    key_file_bonus += 10  # 关键文件权重
            
            # 检查关键目录
            key_dirs = lang_config.get('key_directories', [])
            key_dir_bonus = 0
            for key_dir in key_dirs:
                if (project_path / key_dir).exists():
                    key_dir_bonus += 5  # 关键目录权重
            
            weighted_files[language] = (base_files + key_file_bonus + key_dir_bonus) * weight_multiplier
        
        # 过滤低于阈值的语言
        min_threshold = settings.get('language_thresholds', {}).get('min_percentage', 0.01)
        total_weighted = sum(weighted_files.values())
        
        if total_weighted == 0:
            return {}
        
        # 计算百分比并过滤
        language_percentages = {}
        for language, count in weighted_files.items():
            percentage = count / total_weighted
            if percentage >= min_threshold:
                language_percentages[language] = percentage
        
        # 重新归一化
        total_percentage = sum(language_percentages.values())
        if total_percentage > 0:
            language_percentages = {
                lang: pct / total_percentage 
                for lang, pct in language_percentages.items()
            }
        
        return language_percentages
    
    def _detect_structure_type(self, project_path: pathlib.Path) -> StructureType:
        """检测项目结构类型"""
        if 'structure_detection' not in self.config:
            return StructureType.SINGLE_PROJECT
        
        structure_config = self.config['structure_detection']
        
        # 检查Monorepo标志
        monorepo_config = structure_config.get('monorepo_indicators', {})
        
        # 检查Monorepo标志文件
        monorepo_files = monorepo_config.get('files', [])
        if any((project_path / file).exists() for file in monorepo_files):
            logger.debug("检测到Monorepo标志文件")
            return StructureType.MONOREPO
        
        # 检查Monorepo目录模式
        monorepo_patterns = monorepo_config.get('directory_patterns', [])
        for pattern in monorepo_patterns:
            if list(project_path.glob(pattern)):
                logger.debug(f"检测到Monorepo目录模式: {pattern}")
                return StructureType.MONOREPO
        
        # 检查package.json数量阈值
        package_json_files = list(project_path.rglob('package.json'))
        package_threshold = monorepo_config.get('package_json_threshold', 3)
        if len(package_json_files) >= package_threshold:
            logger.debug(f"检测到 {len(package_json_files)} 个package.json文件，超过阈值")
            return StructureType.MONOREPO
        
        # 检查多项目标志
        multi_config = structure_config.get('multi_project_indicators', {})
        file_patterns = multi_config.get('file_patterns', [])
        max_depth = multi_config.get('max_search_depth', 3)
        min_project_count = multi_config.get('min_project_count', 2)
        
        project_indicators = 0
        for pattern in file_patterns:
            matches = []
            for depth in range(1, max_depth + 1):
                depth_pattern = '/'.join(['*'] * depth) + '/' + pattern.split('/')[-1]
                matches.extend(project_path.glob(depth_pattern))
            
            if len(matches) >= min_project_count:
                logger.debug(f"检测到多项目模式: {pattern} ({len(matches)} 个匹配)")
                return StructureType.MULTI_PROJECT
        
        # 检查单项目标志
        single_config = structure_config.get('single_project_indicators', {})
        root_files = single_config.get('root_files', [])
        if any((project_path / file).exists() for file in root_files):
            logger.debug("检测到单项目根文件")
            return StructureType.SINGLE_PROJECT
        
        # 默认为单项目
        return StructureType.SINGLE_PROJECT
    
    def _infer_project_type(self, project_path: pathlib.Path, 
                           languages: Dict[str, float]) -> ProjectType:
        """推断项目类型"""
        if 'project_type_inference' not in self.config:
            return ProjectType.UNKNOWN
        
        type_scores = {}
        inference_config = self.config['project_type_inference']
        
        for project_type, type_config in inference_config.items():
            score = 0.0
            weight = type_config.get('weight', 1.0)
            
            indicators = type_config.get('indicators', {})
            
            # 检查文件指示器
            files = indicators.get('files', [])
            for file in files:
                if (project_path / file).exists():
                    score += 10
            
            # 检查目录指示器
            directories = indicators.get('directories', [])
            for directory in directories:
                if (project_path / directory).exists():
                    score += 8
            
            # 检查依赖指示器
            dependencies = indicators.get('dependencies', {})
            for language, deps in dependencies.items():
                if language in languages:
                    language_weight = languages[language]
                    # 这里简化处理，实际应该解析依赖文件
                    score += language_weight * 5
            
            type_scores[project_type] = score * weight
        
        if not type_scores:
            return ProjectType.UNKNOWN
        
        # 返回得分最高的项目类型
        best_type = max(type_scores.items(), key=lambda x: x[1])
        if best_type[1] > 0:
            try:
                return ProjectType(best_type[0])
            except ValueError:
                return ProjectType.UNKNOWN
        
        return ProjectType.UNKNOWN
    
    def _analyze_dependencies(self, project_path: pathlib.Path, 
                            languages: Dict[str, float]) -> Dict[str, List[str]]:
        """分析项目依赖"""
        dependencies = {}
        
        for language in languages.keys():
            deps = self._analyze_language_dependencies(project_path, language)
            if deps:
                dependencies[language] = deps
        
        return dependencies
    
    def _analyze_language_dependencies(self, project_path: pathlib.Path, 
                                     language: str) -> List[str]:
        """分析特定语言的依赖"""
        deps = []
        
        if language == 'python':
            # 分析Python依赖
            dep_files = [
                'requirements.txt', 'requirements-dev.txt', 'requirements-prod.txt',
                'setup.py', 'pyproject.toml', 'Pipfile'
            ]
            
            for dep_file in dep_files:
                file_path = project_path / dep_file
                if file_path.exists():
                    try:
                        if dep_file.startswith('requirements'):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                for line in f:
                                    line = line.strip()
                                    if line and not line.startswith('#'):
                                        # 提取包名（去除版本信息）
                                        pkg_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('~=')[0].strip()
                                        if pkg_name:
                                            deps.append(pkg_name)
                        elif dep_file == 'setup.py':
                            # 简化处理setup.py
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if 'install_requires' in content:
                                    deps.extend(['setuptools'])  # 占位符
                        elif dep_file == 'pyproject.toml':
                            deps.extend(['poetry'])  # 占位符
                    except Exception as e:
                        logger.debug(f"解析依赖文件失败 {dep_file}: {e}")
        
        elif language == 'javascript' or language == 'typescript':
            # 分析JavaScript/TypeScript依赖
            package_json = project_path / 'package.json'
            if package_json.exists():
                try:
                    with open(package_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 获取依赖
                    for dep_type in ['dependencies', 'devDependencies']:
                        if dep_type in data:
                            deps.extend(list(data[dep_type].keys()))
                except Exception as e:
                    logger.debug(f"解析package.json失败: {e}")
        
        elif language == 'java':
            # 分析Java依赖（简化处理）
            if (project_path / 'pom.xml').exists():
                deps.append('maven')
            if (project_path / 'build.gradle').exists():
                deps.append('gradle')
        
        elif language == 'go':
            # 分析Go依赖
            go_mod = project_path / 'go.mod'
            if go_mod.exists():
                try:
                    with open(go_mod, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('require '):
                                # 提取模块名
                                parts = line.split()
                                if len(parts) >= 2:
                                    module = parts[1]
                                    deps.append(module)
                except Exception as e:
                    logger.debug(f"解析go.mod失败: {e}")
        
        elif language == 'rust':
            # 分析Rust依赖
            cargo_toml = project_path / 'Cargo.toml'
            if cargo_toml.exists():
                try:
                    with open(cargo_toml, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 简化处理，实际应该用TOML解析器
                        if '[dependencies]' in content:
                            in_deps = False
                            for line in content.split('\n'):
                                line = line.strip()
                                if line == '[dependencies]':
                                    in_deps = True
                                elif line.startswith('[') and line != '[dependencies]':
                                    in_deps = False
                                elif in_deps and '=' in line:
                                    dep_name = line.split('=')[0].strip()
                                    if dep_name:
                                        deps.append(dep_name)
                except Exception as e:
                    logger.debug(f"解析Cargo.toml失败: {e}")
        
        return deps
    
    def _calculate_size_metrics(self, project_path: pathlib.Path, 
                              languages: Dict[str, float]) -> SizeMetrics:
        """计算项目规模指标"""
        metrics = SizeMetrics()
        
        # 获取检测设置
        settings = self.config.get('detection_settings', {})
        max_files = settings.get('max_files_scan', 10000)
        max_file_size = settings.get('max_file_size', 1048576)  # 1MB
        ignore_dirs = set(settings.get('ignore_directories', []))
        ignore_patterns = settings.get('ignore_file_patterns', [])
        
        # 定义文件类型
        code_extensions = set()
        test_patterns = ['test_*.py', '*_test.py', '*.test.js', '*.spec.js', '*.test.ts', '*.spec.ts']
        doc_extensions = {'.md', '.rst', '.txt', '.doc', '.docx'}
        
        # 收集代码文件扩展名 - 从检测到的语言中收集
        if 'languages' in self.config:
            for lang_name, lang_config in self.config['languages'].items():
                # 只收集检测到的语言的扩展名
                if lang_name in languages:
                    extensions = lang_config.get('file_extensions', [])
                    code_extensions.update(extensions)
        
        # 如果没有收集到扩展名，添加默认的常见代码扩展名
        if not code_extensions:
            code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h', '.hpp'}
        
        scanned_files = 0
        for root, dirs, files in os.walk(project_path):
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if scanned_files >= max_files:
                    break
                
                # 检查忽略模式
                if any(fnmatch.fnmatch(file, pattern) for pattern in ignore_patterns):
                    continue
                
                file_path = pathlib.Path(root) / file
                
                # 检查文件大小
                try:
                    if file_path.stat().st_size > max_file_size:
                        continue
                except:
                    continue
                
                extension = file_path.suffix.lower()
                file_name = file_path.name.lower()
                
                # 统计总文件数
                metrics.total_files += 1
                
                # 计算行数
                line_count = 0
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        line_count = sum(1 for _ in f)
                    metrics.total_lines += line_count
                except:
                    continue
                
                # 分类文件
                if extension in code_extensions:
                    # 判断是否为测试文件
                    is_test = any(fnmatch.fnmatch(file_name, pattern) for pattern in test_patterns)
                    # 只检查相对于项目根目录的路径，避免项目名称影响判断
                    relative_path = os.path.relpath(root, project_path).lower()
                    is_test = is_test or ('test' in relative_path and relative_path != '.')
                    
                    
                    if is_test:
                        metrics.test_files += 1
                        metrics.test_lines += line_count
                    else:
                        metrics.code_files += 1
                        metrics.code_lines += line_count
                        
                elif extension in doc_extensions:
                    metrics.doc_files += 1
                    metrics.doc_lines += line_count
                
                scanned_files += 1
            
            if scanned_files >= max_files:
                break
        
        return metrics
    
    def _detect_build_tools(self, project_path: pathlib.Path, 
                          languages: Dict[str, float]) -> List[str]:
        """检测构建工具"""
        build_tools = []
        
        # 通用构建工具
        build_files = {
            'Dockerfile': 'Docker',
            'docker-compose.yml': 'Docker Compose',
            'docker-compose.yaml': 'Docker Compose',
            'Makefile': 'Make',
            'makefile': 'Make',
            'GNUmakefile': 'Make',
            'CMakeLists.txt': 'CMake',
            'configure.ac': 'Autotools',
            'configure.in': 'Autotools'
        }
        
        for file, tool in build_files.items():
            if (project_path / file).exists():
                build_tools.append(tool)
        
        # 语言特定构建工具
        for language in languages.keys():
            if language == 'python':
                if (project_path / 'setup.py').exists():
                    build_tools.append('setuptools')
                if (project_path / 'pyproject.toml').exists():
                    build_tools.append('Poetry/PEP518')
                if (project_path / 'tox.ini').exists():
                    build_tools.append('tox')
            
            elif language == 'javascript' or language == 'typescript':
                if (project_path / 'package.json').exists():
                    build_tools.append('npm')
                if (project_path / 'yarn.lock').exists():
                    build_tools.append('Yarn')
                if (project_path / 'webpack.config.js').exists():
                    build_tools.append('Webpack')
                if (project_path / 'rollup.config.js').exists():
                    build_tools.append('Rollup')
            
            elif language == 'java':
                if (project_path / 'pom.xml').exists():
                    build_tools.append('Maven')
                if (project_path / 'build.gradle').exists():
                    build_tools.append('Gradle')
            
            elif language == 'go':
                if (project_path / 'go.mod').exists():
                    build_tools.append('Go Modules')
            
            elif language == 'rust':
                if (project_path / 'Cargo.toml').exists():
                    build_tools.append('Cargo')
        
        return list(set(build_tools))  # 去重
    
    def _analyze_subprojects(self, project_path: pathlib.Path) -> List[Dict[str, Any]]:
        """分析子项目（用于多项目和monorepo结构）"""
        subprojects = []
        
        # 常见的子项目目录
        subproject_dirs = [
            'packages', 'apps', 'projects', 'modules', 
            'workspaces', 'libs', 'components', 'services'
        ]
        
        for subdir_name in subproject_dirs:
            subdir = project_path / subdir_name
            if subdir.exists() and subdir.is_dir():
                for item in subdir.iterdir():
                    if item.is_dir():
                        # 检查是否包含项目标志文件
                        project_files = [
                            'package.json', 'setup.py', 'pom.xml', 
                            'Cargo.toml', 'go.mod', 'pyproject.toml'
                        ]
                        
                        if any((item / pf).exists() for pf in project_files):
                            try:
                                # 简化检测子项目信息
                                sub_info = self.detect_project_info(str(item))
                                subprojects.append({
                                    'name': item.name,
                                    'path': str(item.relative_to(project_path)),
                                    'languages': sub_info.languages,
                                    'type': sub_info.project_type.value if hasattr(sub_info.project_type, 'value') else str(sub_info.project_type),
                                    'size': sub_info.size_metrics.get_size_category()
                                })
                            except Exception as e:
                                logger.debug(f"分析子项目失败 {item}: {e}")
        
        return subprojects
    
    def _calculate_confidence(self, project_info: ProjectInfo) -> float:
        """计算检测置信度"""
        confidence = 0.0
        
        # 基于语言检测结果
        if project_info.languages:
            primary_lang_pct = max(project_info.languages.values())
            confidence += primary_lang_pct * 0.4  # 最高40%权重
        
        # 基于项目规模
        if project_info.size_metrics.code_files > 0:
            confidence += 0.2  # 有代码文件加20%
        
        # 基于构建工具
        if project_info.build_tools:
            confidence += len(project_info.build_tools) * 0.1  # 每个构建工具10%
        
        # 基于依赖分析
        if project_info.dependencies:
            confidence += 0.1  # 有依赖加10%
        
        # 基于结构类型检测
        if project_info.structure_type != StructureType.SINGLE_PROJECT:
            confidence += 0.1  # 复杂结构加10%
        
        # 基于项目类型推断
        if project_info.project_type != ProjectType.UNKNOWN:
            confidence += 0.1  # 识别出项目类型加10%
        
        return min(confidence, 1.0)  # 最大1.0
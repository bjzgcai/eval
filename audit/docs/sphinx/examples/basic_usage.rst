基本使用示例
============

本章节通过具体示例演示OSS Audit 2.0的基本使用方法。

简单Python项目审计
------------------

项目结构
~~~~~~~~

.. code-block::

   my-python-project/
   ├── src/
   │   ├── __init__.py
   │   ├── main.py
   │   └── utils.py
   ├── tests/
   │   ├── test_main.py
   │   └── test_utils.py
   ├── requirements.txt
   ├── setup.py
   └── README.md

命令行审计
~~~~~~~~~~

.. code-block:: bash

   # 基本审计
   cd my-python-project
   oss-audit .
   
   # 指定输出目录
   oss-audit . --output ./audit-reports
   
   # 只运行特定工具
   oss-audit . --tools pylint,bandit,pytest

Python API使用
~~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.audit_runner import AuditRunner
   
   def audit_my_project():
       # 创建审计运行器
       runner = AuditRunner()
       
       # 运行审计
       results = runner.audit_project("./my-python-project")
       
       # 处理结果
       print(f"项目总评分: {results['overall_score']}/100")
       
       # 查看各维度评分
       for dimension, score in results['dimension_scores'].items():
           print(f"{dimension}: {score}/100")
       
       # 检查是否有严重问题
       if results['overall_score'] < 70:
           print("⚠️  项目质量需要改进")
           
           # 查看主要问题
           for tool_name, tool_result in results['tool_results'].items():
               if tool_result.get('issues_found'):
                   print(f"\n{tool_name} 发现的问题:")
                   for issue in tool_result['issues_found'][:3]:  # 显示前3个
                       print(f"  - {issue.get('message', 'Unknown issue')}")
       else:
           print("✅ 项目质量良好")
       
       return results
   
   if __name__ == "__main__":
       results = audit_my_project()

预期输出
~~~~~~~~

.. code-block::

   🚀 OSS Audit 2.0 - 开源软件成熟度评估
   ==========================================
   
   ✅ 项目检测
   📁 项目名称: my-python-project
   🐍 主要语言: Python (100%)
   📦 项目类型: CLI工具
   🔧 构建系统: setup.py
   
   🔍 执行工具分析
   ✅ pylint: 82/100 (发现 8 个问题)
   ✅ bandit: 95/100 (发现 1 个安全提示)
   ✅ black: 100/100 (代码格式完美)
   ✅ pytest: 78/100 (覆盖率 65%)
   
   📊 维度评分
   ├── 代码质量: 85/100
   ├── 安全性: 92/100  
   ├── 测试覆盖: 72/100
   ├── 文档: 60/100
   └── 可维护性: 80/100
   
   🎯 总体评分: 81/100 (良好)
   
   📝 主要建议:
   1. 提高测试覆盖率至80%以上
   2. 添加模块和函数文档字符串
   3. 修复pylint发现的代码风格问题
   
   📋 详细报告: ./reports/my-python-project/audit_report.html

JavaScript/React项目审计
------------------------

项目结构
~~~~~~~~

.. code-block::

   my-react-app/
   ├── src/
   │   ├── components/
   │   │   ├── App.js
   │   │   └── Header.js
   │   ├── utils/
   │   │   └── helpers.js
   │   └── index.js
   ├── public/
   │   └── index.html
   ├── tests/
   │   └── App.test.js
   ├── package.json
   ├── package-lock.json
   └── .eslintrc.json

配置文件示例
~~~~~~~~~~~~

**.eslintrc.json:**

.. code-block:: json

   {
     "extends": ["react-app", "react-app/jest"],
     "rules": {
       "no-console": "warn",
       "no-unused-vars": "error",
       "prefer-const": "error"
     },
     "env": {
       "browser": true,
       "node": true,
       "jest": true
     }
   }

**package.json (相关部分):**

.. code-block:: json

   {
     "name": "my-react-app",
     "version": "1.0.0",
     "scripts": {
       "test": "react-scripts test",
       "lint": "eslint src/",
       "lint:fix": "eslint src/ --fix"
     },
     "dependencies": {
       "react": "^18.2.0",
       "react-dom": "^18.2.0"
     },
     "devDependencies": {
       "eslint": "^8.45.0",
       "jest": "^29.5.0"
     }
   }

审计执行
~~~~~~~~

.. code-block:: bash

   # React项目审计
   cd my-react-app
   oss-audit . --tools eslint,jest --format html,json

Python API - React项目
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.audit_runner import AuditRunner
   from oss_audit.core.project_detector import ProjectType
   
   def audit_react_project():
       runner = AuditRunner()
       
       # 运行React项目审计
       results = runner.audit_project("./my-react-app")
       
       # 检查项目类型
       project_info = results.get('project_info', {})
       if project_info.get('project_type') == ProjectType.WEB_APPLICATION.value:
           print("✅ 检测到Web应用项目")
           
           # 检查前端特定指标
           js_issues = []
           for tool_name, tool_result in results['tool_results'].items():
               if tool_name in ['eslint', 'typescript']:
                   js_issues.extend(tool_result.get('issues_found', []))
           
           print(f"前端代码问题: {len(js_issues)}")
           
           # 检查测试覆盖率
           jest_result = results['tool_results'].get('jest', {})
           coverage = jest_result.get('coverage', 0)
           
           if coverage < 70:
               print(f"⚠️  测试覆盖率较低: {coverage}%")
               print("建议: 为React组件添加更多单元测试")
           else:
               print(f"✅ 测试覆盖率良好: {coverage}%")
       
       return results

全栈项目审计
------------

项目结构
~~~~~~~~

.. code-block::

   fullstack-app/
   ├── backend/                 # Python后端
   │   ├── app/
   │   │   ├── __init__.py
   │   │   ├── models.py
   │   │   ├── views.py
   │   │   └── utils.py
   │   ├── tests/
   │   ├── requirements.txt
   │   └── app.py
   ├── frontend/               # React前端  
   │   ├── src/
   │   ├── public/
   │   ├── package.json
   │   └── .eslintrc.json
   ├── docker-compose.yml
   └── .oss-audit.yaml

配置文件
~~~~~~~~

**.oss-audit.yaml:**

.. code-block:: yaml

   project:
     name: "Fullstack Application"
     type: "web_application"
   
   tools:
     enabled:
       # Python工具
       - pylint
       - bandit
       - pytest
       # JavaScript工具  
       - eslint
       - jest
   
   tool_configs:
     pylint:
       rcfile: "backend/.pylintrc"
     eslint:
       config_file: "frontend/.eslintrc.json"
   
   filters:
     include:
       paths:
         - "backend/"
         - "frontend/src/"
     exclude:
       paths:
         - "frontend/build/"
         - "frontend/node_modules/"
         - "backend/venv/"

执行全栈审计
~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.audit_runner import AuditRunner
   import json
   
   def audit_fullstack_project():
       runner = AuditRunner()
       
       # 配置自定义设置
       config = {
           'tools': {
               'execution': {
                   'mode': 'parallel',
                   'max_workers': 6
               }
           }
       }
       
       # 执行审计
       results = runner.audit_project(
           "./fullstack-app", 
           config=config
       )
       
       # 分析后端和前端结果
       backend_tools = ['pylint', 'bandit', 'pytest']
       frontend_tools = ['eslint', 'jest']
       
       backend_score = calculate_subsystem_score(results, backend_tools)
       frontend_score = calculate_subsystem_score(results, frontend_tools)
       
       print(f"后端评分: {backend_score}/100")
       print(f"前端评分: {frontend_score}/100")
       print(f"总体评分: {results['overall_score']}/100")
       
       # 生成分层报告
       generate_subsystem_reports(results, backend_tools, frontend_tools)
       
       return results
   
   def calculate_subsystem_score(results, tool_names):
       """计算子系统评分"""
       scores = []
       for tool_name in tool_names:
           if tool_name in results['tool_results']:
               score = results['tool_results'][tool_name].get('score', 0)
               scores.append(score)
       
       return sum(scores) / len(scores) if scores else 0
   
   def generate_subsystem_reports(results, backend_tools, frontend_tools):
       """生成子系统报告"""
       
       # 后端报告
       backend_results = {
           tool: results['tool_results'][tool] 
           for tool in backend_tools 
           if tool in results['tool_results']
       }
       
       with open('backend_audit.json', 'w') as f:
           json.dump(backend_results, f, indent=2)
       
       # 前端报告
       frontend_results = {
           tool: results['tool_results'][tool] 
           for tool in frontend_tools 
           if tool in results['tool_results']
       }
       
       with open('frontend_audit.json', 'w') as f:
           json.dump(frontend_results, f, indent=2)
       
       print("✅ 生成了子系统专用报告:")
       print("  - backend_audit.json")
       print("  - frontend_audit.json")

批量项目审计
------------

多项目管理
~~~~~~~~~~

.. code-block:: python

   import os
   from pathlib import Path
   from concurrent.futures import ThreadPoolExecutor, as_completed
   from oss_audit.core.audit_runner import AuditRunner
   
   def audit_multiple_projects(project_paths, output_base_dir="./audits"):
       """批量审计多个项目"""
       
       runner = AuditRunner()
       results = {}
       
       # 确保输出目录存在
       Path(output_base_dir).mkdir(parents=True, exist_ok=True)
       
       def audit_single_project(project_path):
           """审计单个项目"""
           try:
               project_name = Path(project_path).name
               print(f"🔍 开始审计: {project_name}")
               
               # 设置项目特定的输出目录
               output_dir = Path(output_base_dir) / project_name
               
               result = runner.audit_project(
                   project_path,
                   output_dir=str(output_dir)
               )
               
               print(f"✅ 完成审计: {project_name} (评分: {result['overall_score']}/100)")
               return project_name, result
               
           except Exception as e:
               print(f"❌ 审计失败: {project_path} - {str(e)}")
               return Path(project_path).name, {"error": str(e), "overall_score": 0}
       
       # 并行执行审计
       with ThreadPoolExecutor(max_workers=3) as executor:
           future_to_project = {
               executor.submit(audit_single_project, path): path 
               for path in project_paths
           }
           
           for future in as_completed(future_to_project):
               project_name, result = future.result()
               results[project_name] = result
       
       # 生成汇总报告
       generate_summary_report(results, output_base_dir)
       
       return results
   
   def generate_summary_report(results, output_dir):
       """生成汇总报告"""
       
       summary = {
           "total_projects": len(results),
           "successful_audits": len([r for r in results.values() if "error" not in r]),
           "failed_audits": len([r for r in results.values() if "error" in r]),
           "average_score": 0,
           "projects": {}
       }
       
       # 计算平均分
       successful_results = [r for r in results.values() if "error" not in r]
       if successful_results:
           total_score = sum(r["overall_score"] for r in successful_results)
           summary["average_score"] = total_score / len(successful_results)
       
       # 整理项目信息
       for project_name, result in results.items():
           if "error" not in result:
               summary["projects"][project_name] = {
                   "score": result["overall_score"],
                   "status": "success",
                   "key_issues": extract_key_issues(result)
               }
           else:
               summary["projects"][project_name] = {
                   "score": 0,
                   "status": "failed",
                   "error": result["error"]
               }
       
       # 保存汇总报告
       import json
       with open(Path(output_dir) / "summary_report.json", "w") as f:
           json.dump(summary, f, indent=2)
       
       # 打印汇总信息
       print(f"\n📊 批量审计汇总:")
       print(f"总项目数: {summary['total_projects']}")
       print(f"成功审计: {summary['successful_audits']}")
       print(f"失败审计: {summary['failed_audits']}")
       print(f"平均评分: {summary['average_score']:.1f}/100")
       
       return summary
   
   def extract_key_issues(result):
       """提取关键问题"""
       key_issues = []
       
       for tool_name, tool_result in result.get("tool_results", {}).items():
           issues = tool_result.get("issues_found", [])
           # 只提取严重问题
           critical_issues = [
               issue for issue in issues 
               if issue.get("severity") in ["critical", "high"]
           ]
           if critical_issues:
               key_issues.extend(critical_issues[:2])  # 每个工具最多2个问题
       
       return key_issues[:5]  # 总共最多5个问题
   
   # 使用示例
   if __name__ == "__main__":
       projects = [
           "./project-a",
           "./project-b", 
           "./project-c"
       ]
       
       results = audit_multiple_projects(projects)

定时审计任务
~~~~~~~~~~~~

.. code-block:: python

   import schedule
   import time
   from datetime import datetime
   from oss_audit.core.audit_runner import AuditRunner
   
   def scheduled_audit_job():
       """定时审计任务"""
       
       print(f"⏰ 开始定时审计: {datetime.now()}")
       
       runner = AuditRunner()
       
       # 审计配置
       projects_config = [
           {
               "path": "./critical-project",
               "name": "核心项目",
               "thresholds": {"overall_score": 85}
           },
           {
               "path": "./web-project", 
               "name": "Web项目",
               "thresholds": {"overall_score": 80}
           }
       ]
       
       alerts = []
       
       for config in projects_config:
           try:
               result = runner.audit_project(config["path"])
               score = result["overall_score"]
               threshold = config["thresholds"]["overall_score"]
               
               if score < threshold:
                   alert = {
                       "project": config["name"],
                       "score": score,
                       "threshold": threshold,
                       "timestamp": datetime.now().isoformat()
                   }
                   alerts.append(alert)
                   print(f"⚠️  {config['name']}: 评分 {score} 低于阈值 {threshold}")
               else:
                   print(f"✅ {config['name']}: 评分 {score} 符合要求")
                   
           except Exception as e:
               print(f"❌ {config['name']} 审计失败: {str(e)}")
       
       # 发送警报
       if alerts:
           send_alerts(alerts)
       
       print(f"✅ 定时审计完成: {datetime.now()}")
   
   def send_alerts(alerts):
       """发送告警通知"""
       
       # 邮件通知示例
       try:
           import smtplib
           from email.mime.text import MimeText
           
           message = "项目质量告警:\n\n"
           for alert in alerts:
               message += f"项目: {alert['project']}\n"
               message += f"当前评分: {alert['score']}/100\n" 
               message += f"要求阈值: {alert['threshold']}/100\n"
               message += f"时间: {alert['timestamp']}\n\n"
           
           print(f"📧 发送告警邮件: {len(alerts)} 个项目需要关注")
           # 实际邮件发送代码...
           
       except Exception as e:
           print(f"❌ 发送告警失败: {str(e)}")
   
   def setup_scheduled_audits():
       """设置定时任务"""
       
       # 每天上午9点执行
       schedule.every().day.at("09:00").do(scheduled_audit_job)
       
       # 每周一上午10点执行全面审计  
       schedule.every().monday.at("10:00").do(scheduled_audit_job)
       
       print("⏰ 定时审计任务已设置")
       print("- 每日 09:00 执行常规审计")
       print("- 每周一 10:00 执行全面审计")
       
       # 运行调度器
       while True:
           schedule.run_pending()
           time.sleep(60)  # 每分钟检查一次
   
   if __name__ == "__main__":
       setup_scheduled_audits()

自定义评分逻辑
--------------

自定义评分权重
~~~~~~~~~~~~~~

.. code-block:: python

   from oss_audit.core.audit_runner import AuditRunner
   from oss_audit.core.adaptive_agent import AdaptiveAgent, ScoringModel
   
   def custom_scoring_audit(project_path):
       """使用自定义评分逻辑的审计"""
       
       runner = AuditRunner()
       
       # 执行基础审计
       results = runner.audit_project(project_path)
       
       # 创建自定义评分模型
       custom_model = create_custom_scoring_model(results)
       
       # 重新计算评分
       custom_score = calculate_custom_score(results, custom_model)
       
       print(f"标准评分: {results['overall_score']}")
       print(f"自定义评分: {custom_score}")
       
       return custom_score
   
   def create_custom_scoring_model(results):
       """创建自定义评分模型"""
       
       # 获取项目信息
       project_info = results.get('project_info', {})
       project_type = project_info.get('project_type', 'unknown')
       
       # 根据项目类型调整权重
       if project_type == 'web_application':
           # Web应用重视安全性和性能
           weights = {
               'security': 0.35,      # 高权重
               'performance': 0.25,   # 高权重
               'quality': 0.20,
               'testing': 0.15,
               'documentation': 0.05
           }
       elif project_type == 'library':
           # 库项目重视API设计和文档
           weights = {
               'quality': 0.30,
               'documentation': 0.25,  # 高权重
               'testing': 0.20,
               'security': 0.15,
               'performance': 0.10
           }
       else:
           # 默认权重
           weights = {
               'quality': 0.25,
               'security': 0.20,
               'testing': 0.20,
               'performance': 0.15,
               'documentation': 0.10,
               'maintainability': 0.10
           }
       
       return ScoringModel(
           weights=weights,
           quality_adjustments={},
           historical_adjustments={},
           confidence_level=0.8
       )
   
   def calculate_custom_score(results, scoring_model):
       """计算自定义评分"""
       
       # 映射工具结果到维度
       dimension_mapping = {
           'security': ['bandit', 'safety'],
           'quality': ['pylint', 'flake8', 'black'],
           'testing': ['pytest', 'jest'],
           'performance': ['performance_profiler'],
           'documentation': ['doc_checker']
       }
       
       dimension_scores = {}
       
       for dimension, tools in dimension_mapping.items():
           scores = []
           for tool in tools:
               if tool in results['tool_results']:
                   score = results['tool_results'][tool].get('score', 0)
                   scores.append(score)
           
           if scores:
               dimension_scores[dimension] = sum(scores) / len(scores)
           else:
               dimension_scores[dimension] = 100  # 没有相关工具时给满分
       
       # 加权计算总分
       weighted_score = 0
       total_weight = 0
       
       for dimension, weight in scoring_model.weights.items():
           if dimension in dimension_scores:
               weighted_score += dimension_scores[dimension] * weight
               total_weight += weight
       
       if total_weight > 0:
           return round(weighted_score / total_weight, 1)
       else:
           return results['overall_score']  # fallback到原始评分

结果后处理
~~~~~~~~~~

.. code-block:: python

   def post_process_results(results):
       """结果后处理示例"""
       
       # 添加自定义指标
       results['custom_metrics'] = calculate_custom_metrics(results)
       
       # 生成改进建议
       results['improvement_suggestions'] = generate_improvement_suggestions(results)
       
       # 计算趋势（如果有历史数据）
       results['trends'] = calculate_trends(results)
       
       return results
   
   def calculate_custom_metrics(results):
       """计算自定义指标"""
       
       tool_results = results.get('tool_results', {})
       
       metrics = {
           'code_health_index': 0,
           'security_risk_level': 'low',
           'technical_debt_score': 0,
           'deployment_readiness': False
       }
       
       # 代码健康指数 (综合多个质量工具)
       quality_tools = ['pylint', 'flake8', 'black', 'mypy']
       quality_scores = [
           tool_results[tool]['score'] for tool in quality_tools 
           if tool in tool_results
       ]
       
       if quality_scores:
           metrics['code_health_index'] = sum(quality_scores) / len(quality_scores)
       
       # 安全风险等级
       security_tools = ['bandit', 'safety']
       security_issues = []
       
       for tool in security_tools:
           if tool in tool_results:
               issues = tool_results[tool].get('issues_found', [])
               security_issues.extend(issues)
       
       critical_issues = [i for i in security_issues if i.get('severity') == 'high']
       
       if len(critical_issues) > 5:
           metrics['security_risk_level'] = 'high'
       elif len(critical_issues) > 0:
           metrics['security_risk_level'] = 'medium'
       else:
           metrics['security_risk_level'] = 'low'
       
       # 部署就绪性
       min_requirements = {
           'overall_score': 75,
           'security': 80,
           'testing_coverage': 70
       }
       
       overall_score = results.get('overall_score', 0)
       security_score = results.get('dimension_scores', {}).get('security', 0)
       
       # 获取测试覆盖率
       pytest_result = tool_results.get('pytest', {})
       testing_coverage = pytest_result.get('coverage', 0)
       
       deployment_ready = (
           overall_score >= min_requirements['overall_score'] and
           security_score >= min_requirements['security'] and
           testing_coverage >= min_requirements['testing_coverage']
       )
       
       metrics['deployment_readiness'] = deployment_ready
       
       return metrics
   
   def generate_improvement_suggestions(results):
       """生成改进建议"""
       
       suggestions = []
       
       # 基于评分生成建议
       overall_score = results.get('overall_score', 0)
       
       if overall_score < 60:
           suggestions.append({
               'priority': 'critical',
               'category': 'overall',
               'suggestion': '项目质量严重不足，建议进行全面重构',
               'estimated_effort': 'high'
           })
       elif overall_score < 80:
           suggestions.append({
               'priority': 'high', 
               'category': 'overall',
               'suggestion': '项目质量需要系统性改进',
               'estimated_effort': 'medium'
           })
       
       # 基于具体问题生成建议
       tool_results = results.get('tool_results', {})
       
       # 测试覆盖率建议
       pytest_result = tool_results.get('pytest', {})
       coverage = pytest_result.get('coverage', 100)
       
       if coverage < 70:
           suggestions.append({
               'priority': 'high',
               'category': 'testing',
               'suggestion': f'测试覆盖率仅{coverage}%，建议增加单元测试',
               'estimated_effort': 'medium',
               'target': '达到80%覆盖率'
           })
       
       # 安全问题建议
       bandit_result = tool_results.get('bandit', {})
       security_issues = bandit_result.get('issues_found', [])
       critical_security = [i for i in security_issues if i.get('severity') == 'high']
       
       if critical_security:
           suggestions.append({
               'priority': 'critical',
               'category': 'security', 
               'suggestion': f'发现{len(critical_security)}个严重安全问题，需立即修复',
               'estimated_effort': 'high',
               'files': list(set(i.get('file', 'unknown') for i in critical_security))
           })
       
       return suggestions

这些示例展示了OSS Audit 2.0的灵活使用方式，从简单的单项目审计到复杂的企业级批量管理。您可以根据具体需求选择合适的使用模式，或者基于这些示例开发自己的定制化解决方案。
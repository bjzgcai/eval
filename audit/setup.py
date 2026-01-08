from setuptools import setup, find_packages
import os

# 获取项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))

# 读取README.md
readme_path = os.path.join(project_root, "README.md")
with open(readme_path, "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 读取requirements.txt
requirements = []
requirements_path = os.path.join(project_root, "requirements.txt")
if os.path.exists(requirements_path):
    with open(requirements_path, "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="oss-audit",
    version="2.0.0",
    author="OSS Audit Team",
    author_email="team@oss-audit.org",
    description="开源软件成熟度评估工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitee.com/zgcai/oss-audit",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "oss-audit=oss_audit.core.audit_runner:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)

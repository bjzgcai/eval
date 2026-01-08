#!/bin/bash
# OSS Audit 2.0 Docker 便捷运行脚本
# 使用方法: ./scripts/run_audit.sh [项目路径] [输出目录]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 显示使用帮助
show_help() {
    echo "OSS Audit 2.0 - Docker 运行脚本"
    echo
    echo "使用方法:"
    echo "  $0 [选项] [项目路径] [输出目录]"
    echo
    echo "参数:"
    echo "  项目路径     要分析的项目目录路径（默认: 当前目录）"
    echo "  输出目录     报告输出目录（默认: ./reports）"
    echo
    echo "选项:"
    echo "  -h, --help       显示此帮助信息"
    echo "  --build          重新构建Docker镜像"
    echo "  --no-cache       构建时不使用缓存"
    echo "  --pull           拉取最新的基础镜像"
    echo "  --advanced       启用高级服务（SonarQube, Dependency-Track）"
    echo
    echo "环境变量:"
    echo "  OPENAI_API_KEY   OpenAI API密钥"
    echo "  GEMINI_API_KEY   Gemini API密钥"
    echo "  LOG_LEVEL        日志级别（DEBUG, INFO, WARNING, ERROR）"
    echo
    echo "示例:"
    echo "  $0                           # 分析当前目录"
    echo "  $0 ./my-project             # 分析指定项目"
    echo "  $0 ./my-project ./output    # 指定输出目录"
    echo "  $0 --build ./my-project     # 重新构建并分析"
    echo
}

# 检查Docker是否可用
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装或不在PATH中"
        print_info "请访问 https://docs.docker.com/get-docker/ 安装Docker"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker服务未运行"
        print_info "请启动Docker服务"
        exit 1
    fi
    
    print_success "Docker环境检查通过"
}

# 构建Docker镜像
build_image() {
    local no_cache=""
    local pull=""
    
    if [[ "$1" == "no-cache" ]]; then
        no_cache="--no-cache"
    fi
    
    if [[ "$2" == "pull" ]]; then
        pull="--pull"
    fi
    
    print_info "构建OSS Audit 2.0 Docker镜像..."
    
    if docker build $no_cache $pull -t oss-audit:2.0 .; then
        print_success "Docker镜像构建完成"
    else
        print_error "Docker镜像构建失败"
        exit 1
    fi
}

# 检查镜像是否存在
check_image() {
    if ! docker image inspect oss-audit:2.0 &> /dev/null; then
        print_warning "OSS Audit 2.0镜像不存在，开始构建..."
        build_image
    else
        print_success "OSS Audit 2.0镜像已存在"
    fi
}

# 运行分析
run_analysis() {
    local project_path="$1"
    local output_path="$2"
    local advanced="$3"
    
    # 转换为绝对路径
    project_path=$(realpath "$project_path")
    output_path=$(realpath "$output_path")
    
    print_info "项目路径: $project_path"
    print_info "输出路径: $output_path"
    
    # 检查项目路径是否存在
    if [[ ! -d "$project_path" ]]; then
        print_error "项目路径不存在: $project_path"
        exit 1
    fi
    
    # 创建输出目录
    mkdir -p "$output_path"
    
    # 设置环境变量
    export PROJECT_PATH="$project_path"
    export OUTPUT_PATH="$output_path"
    
    # 检查配置文件
    local config_mount=""
    if [[ -f "config.yaml" ]]; then
        print_info "发现配置文件，将挂载到容器"
        export CONFIG_FILE="$(realpath config.yaml)"
    fi
    
    print_info "开始OSS审计分析..."
    
    if [[ "$advanced" == "true" ]]; then
        print_info "启用高级服务..."
        docker-compose --profile advanced up --build
    else
        docker-compose up --build
    fi
    
    print_success "分析完成！"
    print_info "报告位置: $output_path"
}

# 主函数
main() {
    local project_path="."
    local output_path="./reports"
    local build_image_flag=false
    local no_cache_flag=false
    local pull_flag=false
    local advanced_flag=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --build)
                build_image_flag=true
                shift
                ;;
            --no-cache)
                no_cache_flag=true
                shift
                ;;
            --pull)
                pull_flag=true
                shift
                ;;
            --advanced)
                advanced_flag=true
                shift
                ;;
            -*)
                print_error "未知选项: $1"
                echo "使用 $0 --help 查看使用帮助"
                exit 1
                ;;
            *)
                if [[ -z "$project_path" || "$project_path" == "." ]]; then
                    project_path="$1"
                elif [[ "$output_path" == "./reports" ]]; then
                    output_path="$1"
                else
                    print_error "过多的参数: $1"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    echo "🚀 OSS Audit 2.0 - 开源软件成熟度评估工具"
    echo "================================================"
    
    # 检查Docker环境
    check_docker
    
    # 构建或检查镜像
    if [[ "$build_image_flag" == "true" ]]; then
        local build_args=""
        [[ "$no_cache_flag" == "true" ]] && build_args="no-cache"
        [[ "$pull_flag" == "true" ]] && build_args="$build_args pull"
        build_image $build_args
    else
        check_image
    fi
    
    # 运行分析
    run_analysis "$project_path" "$output_path" "$advanced_flag"
}

# 执行主函数
main "$@"
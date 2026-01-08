# OSS Audit 2.0 Docker 便捷运行脚本 (PowerShell)
# 使用方法: .\scripts\run_audit.ps1 [项目路径] [输出目录]

param(
    [string]$ProjectPath = ".",
    [string]$OutputPath = "./reports",
    [switch]$Help,
    [switch]$Build,
    [switch]$NoCache,
    [switch]$Pull,
    [switch]$Advanced
)

# 颜色输出函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    
    $colorMap = @{
        "Red" = "Red"
        "Green" = "Green" 
        "Yellow" = "Yellow"
        "Blue" = "Cyan"
        "White" = "White"
    }
    
    Write-Host $Message -ForegroundColor $colorMap[$Color]
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput "ℹ️  $Message" "Blue"
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "✅ $Message" "Green"
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "⚠️  $Message" "Yellow"
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "❌ $Message" "Red"
}

# 显示帮助信息
function Show-Help {
    Write-Host "OSS Audit 2.0 - Docker 运行脚本"
    Write-Host ""
    Write-Host "使用方法:"
    Write-Host "  .\scripts\run_audit.ps1 [选项] [项目路径] [输出目录]"
    Write-Host ""
    Write-Host "参数:"
    Write-Host "  -ProjectPath   要分析的项目目录路径（默认: 当前目录）"
    Write-Host "  -OutputPath    报告输出目录（默认: ./reports）"
    Write-Host ""
    Write-Host "选项:"
    Write-Host "  -Help          显示此帮助信息"
    Write-Host "  -Build         重新构建Docker镜像"
    Write-Host "  -NoCache       构建时不使用缓存"
    Write-Host "  -Pull          拉取最新的基础镜像"
    Write-Host "  -Advanced      启用高级服务（SonarQube, Dependency-Track）"
    Write-Host ""
    Write-Host "环境变量:"
    Write-Host "  `$env:OPENAI_API_KEY   OpenAI API密钥"
    Write-Host "  `$env:GEMINI_API_KEY   Gemini API密钥" 
    Write-Host "  `$env:LOG_LEVEL        日志级别（DEBUG, INFO, WARNING, ERROR）"
    Write-Host ""
    Write-Host "示例:"
    Write-Host "  .\scripts\run_audit.ps1                                # 分析当前目录"
    Write-Host "  .\scripts\run_audit.ps1 -ProjectPath .\my-project     # 分析指定项目"
    Write-Host "  .\scripts\run_audit.ps1 -ProjectPath .\my-project -OutputPath .\output    # 指定输出目录"
    Write-Host "  .\scripts\run_audit.ps1 -Build -ProjectPath .\my-project    # 重新构建并分析"
    Write-Host ""
}

# 检查Docker是否可用
function Test-Docker {
    try {
        $null = Get-Command docker -ErrorAction Stop
        $null = docker info 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Docker服务未运行"
            Write-Info "请启动Docker Desktop"
            exit 1
        }
        Write-Success "Docker环境检查通过"
        return $true
    }
    catch {
        Write-Error "Docker未安装或不在PATH中"
        Write-Info "请访问 https://docs.docker.com/desktop/windows/ 安装Docker Desktop"
        exit 1
    }
}

# 构建Docker镜像
function Build-DockerImage {
    param(
        [bool]$UseNoCache = $false,
        [bool]$UsePull = $false
    )
    
    $buildArgs = @()
    
    if ($UseNoCache) {
        $buildArgs += "--no-cache"
    }
    
    if ($UsePull) {
        $buildArgs += "--pull"
    }
    
    Write-Info "构建OSS Audit 2.0 Docker镜像..."
    
    $buildArgs += "-t", "oss-audit:2.0", "."
    
    & docker build @buildArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker镜像构建完成"
    } else {
        Write-Error "Docker镜像构建失败"
        exit 1
    }
}

# 检查镜像是否存在
function Test-DockerImage {
    $null = docker image inspect oss-audit:2.0 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "OSS Audit 2.0镜像不存在，开始构建..."
        Build-DockerImage
    } else {
        Write-Success "OSS Audit 2.0镜像已存在"
    }
}

# 运行分析
function Start-Analysis {
    param(
        [string]$ProjectPath,
        [string]$OutputPath,
        [bool]$UseAdvanced = $false
    )
    
    # 转换为绝对路径
    $ProjectPath = (Resolve-Path $ProjectPath).Path
    $OutputPath = (New-Item -ItemType Directory -Path $OutputPath -Force).FullName
    
    Write-Info "项目路径: $ProjectPath"
    Write-Info "输出路径: $OutputPath"
    
    # 检查项目路径是否存在
    if (-not (Test-Path $ProjectPath -PathType Container)) {
        Write-Error "项目路径不存在: $ProjectPath"
        exit 1
    }
    
    # 设置环境变量
    $env:PROJECT_PATH = $ProjectPath
    $env:OUTPUT_PATH = $OutputPath
    
    # 检查配置文件
    if (Test-Path "config.yaml") {
        Write-Info "发现配置文件，将挂载到容器"
        $env:CONFIG_FILE = (Resolve-Path "config.yaml").Path
    }
    
    Write-Info "开始OSS审计分析..."
    
    if ($UseAdvanced) {
        Write-Info "启用高级服务..."
        & docker-compose --profile advanced up --build
    } else {
        & docker-compose up --build  
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "分析完成！"
        Write-Info "报告位置: $OutputPath"
        
        # 在Windows上尝试打开报告目录
        try {
            Start-Process $OutputPath
        } catch {
            Write-Info "可以手动打开报告目录: $OutputPath"
        }
    } else {
        Write-Error "分析过程中出现错误"
        exit 1
    }
}

# 主函数
function Main {
    if ($Help) {
        Show-Help
        return
    }
    
    Write-Host "🚀 OSS Audit 2.0 - 开源软件成熟度评估工具" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan
    
    # 检查Docker环境
    Test-Docker
    
    # 构建或检查镜像
    if ($Build) {
        Build-DockerImage -UseNoCache $NoCache -UsePull $Pull
    } else {
        Test-DockerImage
    }
    
    # 运行分析
    Start-Analysis -ProjectPath $ProjectPath -OutputPath $OutputPath -UseAdvanced $Advanced
}

# 执行主函数
Main
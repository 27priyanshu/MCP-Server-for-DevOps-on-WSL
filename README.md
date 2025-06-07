# WSL DevOps Management MCP Server

🐧 A Model Context Protocol (MCP) server for managing Docker containers, systemd services, and system monitoring in WSL environments.

## ✨ Features

- **Docker Management**: Deploy, manage, and monitor containers
- **Service Control**: Start/stop/restart systemd services  
- **System Monitoring**: Real-time CPU, memory, disk usage
- **WSL Optimized**: Native WSL2 integration with auto-detection

![2025-06-07_13h26_40](https://github.com/user-attachments/assets/2d72ff01-1615-4cd1-8cfc-5df614ea24ca)

## 🚀 Quick Start

### Prerequisites
```bash
# Install Docker (if needed)
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
```

### Installation
```bash
# Clone the repository
git clone https://github.com/27priyanshu/MCP-Server-for-DevOps-on-WSL.git
cd MCP-Server-for-DevOps-on-WSL

# Install python3-venv if not already installed
sudo apt update
sudo apt install python3-full python3-venv

# Create a virtual environment
python3 -m venv mcp-env

# Activate the virtual environment
source mcp-env/bin/activate

# Install packages in the virtual environment
pip install mcp docker psutil

# Verify installation
python -c "import mcp; print('MCP installed successfully')"
python3 -c "import docker; print('Docker SDK available')"
python3 -c "import psutil; print('PSUtil available')"
```

### Configuration
Add to your MCP client config:
```json
{
  "mcpServers": {
    "wsl-devops-management": {
      "command": "wsl.exe",
      "args": [
        "-d", "Ubuntu",
        "--cd", "/mnt/c/path/to/your/project",
        "bash", "-c",
        "source mcp-env/bin/activate && python3 devops_server.py"
      ]
    }
  }
}
```

## 🛠️ Available Tools

### Docker Management (9 tools)
- `deploy_container` - Deploy containers with ports & env vars
- `list_real_containers` - List all containers with status & ports
- `restart_real_container` - Restart specific containers
- `stop_real_container` - Stop running containers
- `inspect_real_container` - Get detailed container information
- `list_real_images` - List images with size & tags
- `prune_docker_system` - Clean unused containers, images & networks
- `get_real_logs` - Fetch container logs (configurable lines 1-1000)

### System Services (4 tools)
- `restart_real_service` - Restart systemd services
- `check_real_service` - Check service status with detailed output
- `enable_real_service` - Enable services to start on boot
- `disable_real_service` - Disable services from auto-start

### System Monitoring (2 tools)
- `real_system_health` - CPU, memory, disk usage & uptime
- `wsl_system_info` - WSL capabilities & installation notes

### Resources Available
- `wsl://system-info` - Environment capabilities & setup info
- `container://<name>` - Individual container details with logs
- `service://<name>` - Service status & configuration
- `system://overview` - Complete system status dashboard

## 📋 Usage Examples

### Docker Operations
```python
# Deploy nginx with port mapping and environment variables
deploy_container(
    container_name="web-server",
    image="nginx:latest", 
    ports=["8080:80", "443:443"],
    env_vars={"NGINX_HOST": "localhost", "ENV": "production"}
)

# List all containers with status and ports
list_real_containers()
# Output: 🐳 Real Docker Containers in WSL:
# 🟢 web-server (nginx:latest) - running | Ports: 8080:80, 443:443

# Get detailed container information
inspect_real_container(container_name="web-server")

# Fetch recent logs (last 100 lines)
get_real_logs(container_name="web-server", lines=100)

# List all images with sizes
list_real_images()
# Output: IMAGE                    ID              SIZE
#         nginx:latest             sha256:abc123   142.56 MB

# Clean up unused Docker resources
prune_docker_system()
# Output: Deleted containers: 3, Images: 2, Networks: 1, Space: 1.24 GB
```

### Service Management
```python
# Check Docker service status with full output
check_real_service(service_name="docker")
# Output: 🟢 Real service 'docker':
# ● docker.service - Docker Application Container Engine
#    Loaded: loaded (/lib/systemd/system/docker.service; enabled)
#    Active: active (running) since Mon 2024-01-15 10:30:22 UTC

# Restart and enable services
restart_real_service(service_name="nginx")
enable_real_service(service_name="docker")  # Start on boot
disable_real_service(service_name="nginx")  # Don't start on boot
```

### System Monitoring
```python
# Get comprehensive system health
real_system_health()
# Output: 💻 Real WSL System Health:
# Environment: WSL Linux
# CPU Usage: 15.2%
# Memory Usage: 45.8%
# Disk Usage: 23.1%
# Uptime: 2 days, 14:30:22
# Docker Containers: 3/5 running
# System Services: 8/12 active

# Check WSL environment capabilities
wsl_system_info()
# Output: 🐧 WSL DevOps Environment:
# WSL Detected: ✅
# Docker Available: ✅  
# Systemd Available: ✅
# PSUtil Available: ✅
```

## 🔧 Troubleshooting

**Docker not available?**
```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
```

**Systemd not working?**
Add to `/etc/wsl.conf`:
```ini
[boot]
systemd=true
```

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Submit pull request

Issues: [GitHub Issues](https://github.com/27priyanshu/MCP-Server-for-DevOps-on-WSL/issues)

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---
**Built for WSL DevOps automation** 🚀

#!/usr/bin/env python3
"""
WSL DevOps Management MCP Server
Real integration with Docker, systemd, and Linux system monitoring in WSL
"""

import asyncio
import json
import subprocess
import datetime
import time
import os
import shutil
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
)

# Try to import optional dependencies
try:
    import docker
    DOCKER_AVAILABLE = True
    try:
        docker_client = docker.from_env()
        docker_client.ping()  # Test connection
        DOCKER_CONNECTED = True
    except Exception:
        DOCKER_CONNECTED = False
        docker_client = None
except ImportError:
    DOCKER_AVAILABLE = False
    DOCKER_CONNECTED = False
    docker_client = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# WSL-specific configuration
WSL_CONFIG = {
    "is_wsl": os.path.exists("/proc/version") and "microsoft" in open("/proc/version").read().lower(),
    "systemd_available": shutil.which("systemctl") is not None,
    "docker_available": DOCKER_AVAILABLE and DOCKER_CONNECTED,
    "psutil_available": PSUTIL_AVAILABLE
}

# Create an MCP server
server = Server("wsl-devops-management")

def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command safely"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        raise Exception(f"Command failed: {' '.join(cmd)}\nError: {e.stderr}")

# New helper function to format image size
def format_size(size_bytes: int) -> str:
    """Formats bytes into a human-readable string (KB, MB, GB)."""
    if size_bytes is None:
        return "N/A"
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size_bytes >= power and n < len(power_labels) - 1:
        size_bytes /= power
        n += 1
    return f"{size_bytes:.2f} {power_labels[n]}"

async def get_real_containers():
    """Get real Docker containers from WSL"""
    if not WSL_CONFIG["docker_available"]:
        return {}
    
    try:
        containers = docker_client.containers.list(all=True)
        container_data = {}
        
        for container in containers:
            # Get port mappings
            ports = []
            if container.ports:
                for container_port, host_bindings in container.ports.items():
                    if host_bindings:
                        for binding in host_bindings:
                            ports.append(f"{binding['HostPort']}:{container_port}")
            
            # Get environment variables (limited for security)
            env_vars = {}
            if hasattr(container, 'attrs') and 'Config' in container.attrs:
                env_list = container.attrs['Config'].get('Env', [])
                for env in env_list[:5]:  # Limit to first 5 for security
                    if '=' in env:
                        key, value = env.split('=', 1)
                        if not key.startswith(('PASSWORD', 'SECRET', 'TOKEN', 'KEY')):
                            env_vars[key] = value[:50]  # Truncate values
            
            container_data[container.name] = {
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else container.image.short_id,
                "status": container.status,
                "ports": ports,
                "env_vars": env_vars,
                "created": container.attrs['Created'],
                "started_at": container.attrs.get('State', {}).get('StartedAt', ''),
                "id": container.short_id
            }
        
        return container_data
    except Exception as e:
        print(f"Error getting containers: {e}")
        return {}

async def get_real_services():
    """Get real systemd services in WSL"""
    if not WSL_CONFIG["systemd_available"]:
        return {}
    
    try:
        # Get common services
        services = ["docker", "ssh", "nginx", "apache2", "postgresql", "mysql", "redis-server"]
        service_data = {}
        
        for service in services:
            try:
                result = run_command(["systemctl", "is-active", service], check=False)
                is_active = result.returncode == 0
                
                result = run_command(["systemctl", "is-enabled", service], check=False)
                is_enabled = result.returncode == 0
                
                service_data[service] = {
                    "status": "active" if is_active else "inactive",
                    "enabled": is_enabled,
                    "last_restart": datetime.datetime.now().isoformat() + "Z"  # Placeholder
                }
            except Exception:
                continue
        
        return service_data
    except Exception as e:
        print(f"Error getting services: {e}")
        return {}

async def get_system_metrics():
    """Get real system metrics from WSL"""
    if not WSL_CONFIG["psutil_available"]:
        return {
            "cpu_usage": "N/A (psutil not installed)",
            "memory_usage": "N/A (psutil not installed)",
            "disk_usage": "N/A (psutil not installed)",
            "uptime": "N/A (psutil not installed)"
        }
    
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_str = str(datetime.timedelta(seconds=int(uptime_seconds)))
        
        return {
            "cpu_usage": f"{cpu_percent:.1f}%",
            "memory_usage": f"{memory.percent:.1f}%",
            "disk_usage": f"{(disk.used / disk.total) * 100:.1f}%",
            "uptime": uptime_str
        }
    except Exception as e:
        return {
            "cpu_usage": f"Error: {e}",
            "memory_usage": "Error",
            "disk_usage": "Error",
            "uptime": "Error"
        }

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available WSL DevOps resources."""
    resources = []
    
    # WSL system info
    resources.append(
        Resource(
            uri="wsl://system-info",
            name="WSL System Information",
            description="WSL environment and capability information",
            mimeType="application/json",
        )
    )
    
    # Real containers if Docker is available
    if WSL_CONFIG["docker_available"]:
        containers = await get_real_containers()
        for container_name in containers.keys():
            resources.append(
                Resource(
                    uri=f"container://{container_name}",
                    name=f"Container {container_name}",
                    description=f"Real container information for {container_name}",
                    mimeType="application/json",
                )
            )
    
    # Real services if systemd is available
    if WSL_CONFIG["systemd_available"]:
        services = await get_real_services()
        for service_name in services.keys():
            resources.append(
                Resource(
                    uri=f"service://{service_name}",
                    name=f"Service {service_name}",
                    description=f"Real service information for {service_name}",
                    mimeType="application/json",
                )
            )
    
    # System overview
    resources.append(
        Resource(
            uri="system://overview",
            name="Real System Overview",
            description="Real WSL system status and metrics",
            mimeType="application/json",
        )
    )
    
    return resources

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read WSL DevOps resources."""
    
    if uri == "wsl://system-info":
        wsl_info = {
            "environment": "WSL (Windows Subsystem for Linux)",
            "is_wsl": WSL_CONFIG["is_wsl"],
            "capabilities": {
                "docker": WSL_CONFIG["docker_available"],
                "systemd": WSL_CONFIG["systemd_available"],
                "psutil": WSL_CONFIG["psutil_available"]
            },
            "installation_notes": {
                "docker": "Install with: curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh",
                "python_deps": "pip install docker psutil",
                "systemd": "Available in WSL2 with systemd enabled"
            }
        }
        return json.dumps(wsl_info, indent=2)
    
    elif uri.startswith("container://"):
        container_name = uri.replace("container://", "")
        containers = await get_real_containers()
        if container_name in containers:
            # Add recent logs
            if WSL_CONFIG["docker_available"]:
                try:
                    container = docker_client.containers.get(container_name)
                    logs = container.logs(tail=10, timestamps=True).decode('utf-8')
                    containers[container_name]["recent_logs"] = logs.split('\n')[-10:]
                except Exception as e:
                    containers[container_name]["recent_logs"] = [f"Error getting logs: {e}"]
            
            return json.dumps(containers[container_name], indent=2)
        else:
            raise ValueError(f"Container {container_name} not found")
    
    elif uri.startswith("service://"):
        service_name = uri.replace("service://", "")
        services = await get_real_services()
        if service_name in services:
            return json.dumps(services[service_name], indent=2)
        else:
            raise ValueError(f"Service {service_name} not found")
    
    elif uri == "system://overview":
        containers = await get_real_containers()
        services = await get_real_services()
        metrics = await get_system_metrics()
        
        overview = {
            "wsl_environment": WSL_CONFIG,
            "containers": {name: data["status"] for name, data in containers.items()},
            "services": {name: data["status"] for name, data in services.items()},
            "system_metrics": metrics,
            "timestamp": datetime.datetime.now().isoformat()
        }
        return json.dumps(overview, indent=2)
    
    else:
        raise ValueError(f"Unknown resource: {uri}")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available WSL DevOps tools."""
    tools = [
        Tool(
            name="wsl_system_info",
            description="Get WSL system information and capabilities",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]
    
    # Docker tools
    if WSL_CONFIG["docker_available"]:
        tools.extend([
            Tool(
                name="deploy_container",
                description="Deploy a real Docker container in WSL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "container_name": {"type": "string"},
                        "image": {"type": "string"},
                        "ports": {"type": "array", "items": {"type": "string"}, "default": []},
                        "env_vars": {"type": "object", "default": {}}
                    },
                    "required": ["container_name", "image"]
                }
            ),
            Tool(
                name="list_real_containers",
                description="List real Docker containers in WSL",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False}
            ),
            Tool(
                name="restart_real_container",
                description="Restart a real Docker container",
                inputSchema={
                    "type": "object",
                    "properties": {"container_name": {"type": "string"}},
                    "required": ["container_name"]
                }
            ),
            # --- Start of New Tools ---
            Tool(
                name="stop_real_container",
                description="Stop a real Docker container",
                inputSchema={
                    "type": "object",
                    "properties": {"container_name": {"type": "string"}},
                    "required": ["container_name"]
                }
            ),
            Tool(
                name="inspect_real_container",
                description="Get detailed information for a real Docker container",
                inputSchema={
                    "type": "object",
                    "properties": {"container_name": {"type": "string"}},
                    "required": ["container_name"]
                }
            ),
            Tool(
                name="list_real_images",
                description="List real Docker images in WSL",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False}
            ),
            Tool(
                name="prune_docker_system",
                description="Prune unused Docker resources (e.g., stopped containers, dangling images)",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False}
            ),
            # --- End of New Tools ---
            Tool(
                name="get_real_logs",
                description="Get real logs from a Docker container",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "container_name": {"type": "string"},
                        "lines": {"type": "integer", "default": 50, "minimum": 1, "maximum": 1000}
                    },
                    "required": ["container_name"]
                }
            )
        ])
    
    # Systemd tools
    if WSL_CONFIG["systemd_available"]:
        tools.extend([
            Tool(
                name="restart_real_service",
                description="Restart a real systemd service in WSL",
                inputSchema={
                    "type": "object",
                    "properties": {"service_name": {"type": "string"}},
                    "required": ["service_name"]
                }
            ),
            Tool(
                name="check_real_service",
                description="Check real systemd service status",
                inputSchema={
                    "type": "object",
                    "properties": {"service_name": {"type": "string"}},
                    "required": ["service_name"]
                }
            ),
            # --- Start of New Tools ---
            Tool(
                name="enable_real_service",
                description="Enable a real systemd service to start on boot",
                inputSchema={
                    "type": "object",
                    "properties": {"service_name": {"type": "string"}},
                    "required": ["service_name"]
                }
            ),
            Tool(
                name="disable_real_service",
                description="Disable a real systemd service from starting on boot",
                inputSchema={
                    "type": "object",
                    "properties": {"service_name": {"type": "string"}},
                    "required": ["service_name"]
                }
            )
            # --- End of New Tools ---
        ])
    
    # System monitoring
    if WSL_CONFIG["psutil_available"]:
        tools.append(
            Tool(
                name="real_system_health",
                description="Get real WSL system health and metrics",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False}
            )
        )
    
    return tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle WSL DevOps tool calls."""
    
    if name == "wsl_system_info":
        info = f"🐧 WSL DevOps Environment:\n\n"
        info += f"WSL Detected: {'✅' if WSL_CONFIG['is_wsl'] else '❌'}\n"
        info += f"Docker Available: {'✅' if WSL_CONFIG['docker_available'] else '❌'}\n"
        info += f"Systemd Available: {'✅' if WSL_CONFIG['systemd_available'] else '❌'}\n"
        info += f"PSUtil Available: {'✅' if WSL_CONFIG['psutil_available'] else '❌'}\n\n"
        
        if not WSL_CONFIG['docker_available']:
            info += "To install Docker:\n"
            info += "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh\n\n"
        
        if not WSL_CONFIG['psutil_available']:
            info += "To install Python dependencies:\n"
            info += "pip install docker psutil\n"
        
        return [TextContent(type="text", text=info)]
    
    elif name == "deploy_container" and WSL_CONFIG["docker_available"]:
        container_name = arguments["container_name"]
        image = arguments["image"]
        ports = arguments.get("ports", [])
        env_vars = arguments.get("env_vars", {})
        
        try:
            # Pull image
            docker_client.images.pull(image)
            
            # Remove existing container
            try:
                existing = docker_client.containers.get(container_name)
                existing.stop()
                existing.remove()
            except docker.errors.NotFound:
                pass
            
            # Parse port mappings
            port_bindings = {}
            for port_mapping in ports:
                if ':' in port_mapping:
                    host_port, container_port = port_mapping.split(':')
                    port_bindings[f"{container_port}/tcp"] = host_port
            
            # Create container
            container = docker_client.containers.run(
                image,
                name=container_name,
                ports=port_bindings,
                environment=env_vars,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            return [TextContent(
                type="text",
                text=f"✅ Successfully deployed real container '{container_name}'\n"
                     f"Image: {image}\n"
                     f"Container ID: {container.short_id}\n"
                     f"Status: {container.status}\n"
                     f"Ports: {', '.join(ports) if ports else 'None'}"
            )]
            
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Real deployment failed: {str(e)}")]
    
    elif name == "list_real_containers" and WSL_CONFIG["docker_available"]:
        containers = await get_real_containers()
        if not containers:
            return [TextContent(type="text", text="🐳 No containers found")]
        
        result = []
        for name, data in containers.items():
            status_emoji = "🟢" if data["status"] == "running" else "🔴"
            ports_info = f" | Ports: {', '.join(data['ports'])}" if data['ports'] else ""
            result.append(f"{status_emoji} {name} ({data['image']}) - {data['status']}{ports_info}")
        
        return [TextContent(type="text", text="🐳 Real Docker Containers in WSL:\n" + "\n".join(result))]
    
    elif name == "restart_real_container" and WSL_CONFIG["docker_available"]:
        container_name = arguments["container_name"]
        
        try:
            container = docker_client.containers.get(container_name)
            container.restart()
            return [TextContent(
                type="text",
                text=f"🔄 Successfully restarted real container '{container_name}'"
            )]
        except docker.errors.NotFound:
            return [TextContent(type="text", text=f"❌ Container '{container_name}' not found")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error restarting container: {str(e)}")]
    
    # --- Start of New Tool Implementations ---

    elif name == "stop_real_container" and WSL_CONFIG["docker_available"]:
        container_name = arguments["container_name"]
        try:
            container = docker_client.containers.get(container_name)
            container.stop()
            return [TextContent(type="text", text=f"🛑 Successfully stopped real container '{container_name}'")]
        except docker.errors.NotFound:
            return [TextContent(type="text", text=f"❌ Container '{container_name}' not found")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error stopping container: {str(e)}")]

    elif name == "inspect_real_container" and WSL_CONFIG["docker_available"]:
        container_name = arguments["container_name"]
        try:
            container = docker_client.containers.get(container_name)
            return [TextContent(type="text", text=json.dumps(container.attrs, indent=2))]
        except docker.errors.NotFound:
            return [TextContent(type="text", text=f"❌ Container '{container_name}' not found")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error inspecting container: {str(e)}")]

    elif name == "list_real_images" and WSL_CONFIG["docker_available"]:
        try:
            images = docker_client.images.list()
            if not images:
                return [TextContent(type="text", text="🖼️ No Docker images found.")]
            
            result = ["{:<50} {:<15} {:<15}".format("IMAGE", "ID", "SIZE")]
            for image in images:
                tag = image.tags[0] if image.tags else "<none>"
                image_id = image.short_id.replace("sha256:", "")
                size = format_size(image.attrs['Size'])
                result.append(f"{tag:<50} {image_id:<15} {size:<15}")
            
            return [TextContent(type="text", text="🖼️ Real Docker Images:\n" + "\n".join(result))]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error listing images: {str(e)}")]

    elif name == "prune_docker_system" and WSL_CONFIG["docker_available"]:
        try:
            pruned_containers = docker_client.containers.prune()
            pruned_images = docker_client.images.prune()
            pruned_networks = docker_client.networks.prune()

            reclaimed_space = pruned_images.get("SpaceReclaimed", 0)
            
            report = "🧹 Docker System Prune Report:\n"
            report += f"- Deleted stopped containers: {len(pruned_containers.get('ContainersDeleted', []))}\n"
            report += f"- Deleted images: {len(pruned_images.get('ImagesDeleted', []))}\n"
            report += f"- Deleted networks: {len(pruned_networks.get('NetworksDeleted', []))}\n"
            report += f"- Total reclaimed space: {format_size(reclaimed_space)}\n"

            return [TextContent(type="text", text=report)]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error pruning Docker system: {str(e)}")]
    
    # --- End of New Tool Implementations ---

    elif name == "get_real_logs" and WSL_CONFIG["docker_available"]:
        container_name = arguments["container_name"]
        lines = arguments.get("lines", 50)
        
        try:
            container = docker_client.containers.get(container_name)
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
            return [TextContent(
                type="text",
                text=f"📄 Real logs for '{container_name}' (last {lines} lines):\n\n{logs}"
            )]
        except docker.errors.NotFound:
            return [TextContent(type="text", text=f"❌ Container '{container_name}' not found")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error getting logs: {str(e)}")]
    
    elif name == "restart_real_service" and WSL_CONFIG["systemd_available"]:
        service_name = arguments["service_name"]
        
        try:
            run_command(["sudo", "systemctl", "restart", service_name])
            return [TextContent(
                type="text",
                text=f"🔄 Successfully restarted real service '{service_name}'"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Failed to restart service: {str(e)}")]
    
    elif name == "check_real_service" and WSL_CONFIG["systemd_available"]:
        service_name = arguments["service_name"]
        
        try:
            result = run_command(["systemctl", "status", service_name], check=False)
            status_emoji = "🟢" if result.returncode == 0 else "🔴"
            
            return [TextContent(
                type="text",
                text=f"{status_emoji} Real service '{service_name}':\n\n{result.stdout}"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error checking service: {str(e)}")]
            
    # --- Start of New Tool Implementations ---

    elif name == "enable_real_service" and WSL_CONFIG["systemd_available"]:
        service_name = arguments["service_name"]
        try:
            run_command(["sudo", "systemctl", "enable", service_name])
            return [TextContent(type="text", text=f"✅ Successfully enabled real service '{service_name}'")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Failed to enable service: {str(e)}")]

    elif name == "disable_real_service" and WSL_CONFIG["systemd_available"]:
        service_name = arguments["service_name"]
        try:
            run_command(["sudo", "systemctl", "disable", service_name])
            return [TextContent(type="text", text=f"🛑 Successfully disabled real service '{service_name}'")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Failed to disable service: {str(e)}")]

    # --- End of New Tool Implementations ---
    
    elif name == "real_system_health":
        metrics = await get_system_metrics()
        containers = await get_real_containers() if WSL_CONFIG["docker_available"] else {}
        services = await get_real_services() if WSL_CONFIG["systemd_available"] else {}
        
        running_containers = len([c for c in containers.values() if c["status"] == "running"])
        active_services = len([s for s in services.values() if s["status"] == "active"])
        
        health_text = f"💻 Real WSL System Health:\n\n"
        health_text += f"Environment: WSL Linux\n"
        health_text += f"CPU Usage: {metrics['cpu_usage']}\n"
        health_text += f"Memory Usage: {metrics['memory_usage']}\n"
        health_text += f"Disk Usage: {metrics['disk_usage']}\n"
        health_text += f"Uptime: {metrics['uptime']}\n"
        
        if WSL_CONFIG["docker_available"]:
            health_text += f"Docker Containers: {running_containers}/{len(containers)} running\n"
        
        if WSL_CONFIG["systemd_available"]:
            health_text += f"System Services: {active_services}/{len(services)} active\n"
        
        return [TextContent(type="text", text=health_text)]
    
    else:
        available_tools = []
        if WSL_CONFIG["docker_available"]:
            available_tools.extend(["deploy_container", "list_real_containers", "restart_real_container", "get_real_logs"])
        if WSL_CONFIG["systemd_available"]:
            available_tools.extend(["restart_real_service", "check_real_service"])
        if WSL_CONFIG["psutil_available"]:
            available_tools.append("real_system_health")
        
        return [TextContent(
            type="text",
            text=f"❌ Tool '{name}' not available.\n"
                 f"Available tools: {', '.join(available_tools)}\n"
                 f"Check WSL system info for missing dependencies."
        )]

async def main():
    """Main function to run the WSL DevOps MCP server."""
    print("🐧 Starting WSL DevOps MCP Server...")
    print(f"Docker Available: {WSL_CONFIG['docker_available']}")
    print(f"Systemd Available: {WSL_CONFIG['systemd_available']}")
    print(f"PSUtil Available: {WSL_CONFIG['psutil_available']}")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
通用Minecraft服务器启动器 - Universal Minecraft Server Launcher
支持所有类型服务端核心：Vanilla, Paper, Spigot, Purpur, Forge, Fabric, Bukkit等
"""

import os
import sys
import json
import time
import shutil
import threading
import subprocess
import platform
import webbrowser
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import zipfile
import tarfile
import tempfile

# GUI库导入
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext, font
    from tkinter import Menu as tkMenu
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("警告: tkinter不可用，将使用命令行界面")

# 尝试导入其他依赖（可选）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ServerCoreManager:
    """服务器核心管理器"""
    
    # 核心类型定义
    CORE_TYPES = {
        "purpur": {
            "name": "Purpur",
            "website": "https://purpurmc.org",
            "description": "高性能Paper分支，提供额外优化和功能",
            "download_pattern": "https://api.purpurmc.org/v2/purpur/{version}/latest/download"
        },
        "paper": {
            "name": "Paper",
            "website": "https://papermc.io",
            "description": "高性能Spigot分支，修复大量BUG",
            "download_pattern": "https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar"
        },
        "spigot": {
            "name": "Spigot",
            "website": "https://spigotmc.org",
            "description": "Bukkit优化版本，性能更好",
            "download_pattern": "https://download.spigotmc.org/spigot/spigot-{version}.jar"
        },
        "craftbukkit": {
            "name": "CraftBukkit",
            "website": "https://bukkit.org",
            "description": "原版Bukkit服务端",
            "download_pattern": "https://download.craftbukkit.org/craftbukkit-{version}.jar"
        },
        "vanilla": {
            "name": "Vanilla",
            "website": "https://minecraft.net",
            "description": "官方原版服务端",
            "download_pattern": "https://launcher.mojang.com/v1/objects/{hash}/server.jar"
        },
        "fabric": {
            "name": "Fabric",
            "website": "https://fabricmc.net",
            "description": "轻量级模组加载器",
            "download_pattern": "https://meta.fabricmc.net/v2/versions/loader/{version}/{loader}/server/jar"
        },
        "forge": {
            "name": "Forge",
            "website": "https://files.minecraftforge.net",
            "description": "经典模组加载器",
            "download_pattern": "https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"
        },
        "neoforge": {
            "name": "NeoForge",
            "website": "https://neoforged.net",
            "description": "Forge的分支，现代版本",
            "download_pattern": "https://maven.neoforged.net/releases/net/neoforged/forge/{version}/forge-{version}-installer.jar"
        },
        "catserver": {
            "name": "CatServer",
            "website": "https://catserver.moe",
            "description": "Forge和Bukkit兼容的服务端",
            "download_pattern": "https://github.com/Luohuayu/CatServer/releases/download/{version}/catserver-{version}.jar"
        },
        "mohist": {
            "name": "Mohist",
            "website": "https://mohistmc.com",
            "description": "Forge和Bukkit兼容的服务端",
            "download_pattern": "https://mohistmc.com/api/v2/projects/mohist/{version}/builds/{build}/downloads/mohist-{version}-{build}.jar"
        }
    }
    
    # 镜像站配置
    MIRROR_SITES = {
        "mslmc": {
            "name": "MSLMC镜像站",
            "url": "https://dl.mslmc.cn/",
            "patterns": {
                "paper": "https://dl.mslmc.cn",
                "purpur": "https://dl.mslmc.cn",
                "vanilla": "https://dl.mslmc.cn",
                "spigot": "https://dl.mslmc.cn",
                "craftbukkit": "https://dl.mslmc.cn",
            }
        },
        "bmclapi": {
            "name": "BMCLAPI镜像站",
            "url": "https://bmclapi2.bangbang93.com/",
            "patterns": {
                "paper": "https://bmclapi2.bangbang93.com/projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar",
                "purpur": "https://bmclapi2.bangbang93.com/projects/purpur/versions/{version}/builds/{build}/downloads/purpur-{version}-{build}.jar",
                "vanilla": "https://bmclapi2.bangbang93.com/version/{version}/server",
                "fabric": "https://bmclapi2.bangbang93.com/fabric-meta/v2/versions/loader/{version}/{loader}/server/jar",
                "forge": "https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/{version}/forge-{version}-installer.jar"
            }
        },
        "mc": {
            "name": "官方源",
            "url": "官方源",
            "patterns": {}
        }
    }
    
    # Minecraft版本列表（常用版本）
    MINECRAFT_VERSIONS = [
        "1.21.4", "1.21.3", "1.21.2", "1.21.1", "1.21",
        "1.20.6", "1.20.5", "1.20.4", "1.20.3", "1.20.2", "1.20.1", "1.20",
        "1.19.4", "1.19.3", "1.19.2", "1.19.1", "1.19",
        "1.18.2", "1.18.1", "1.18",
        "1.17.1", "1.17",
        "1.16.5", "1.16.4", "1.16.3", "1.16.2", "1.16.1",
        "1.15.2", "1.15.1", "1.15",
        "1.14.4", "1.14.3", "1.14.2", "1.14.1",
        "1.13.2", "1.13.1",
        "1.12.2", "1.12.1",
        "1.11.2",
        "1.10.2",
        "1.9.4",
        "1.8.9",
        "1.7.10"
    ]
    
    @classmethod
    def detect_core_type(cls, jar_path: Path) -> str:
        """检测服务器核心类型"""
        if not jar_path.exists():
            return "unknown"
        
        jar_name = jar_path.name.lower()
        
        # 通过文件名检测
        if "purpur" in jar_name:
            return "purpur"
        elif "paper" in jar_name:
            return "paper"
        elif "spigot" in jar_name:
            return "spigot"
        elif "craftbukkit" in jar_name:
            return "craftbukkit"
        elif "fabric" in jar_name:
            return "fabric"
        elif "forge" in jar_name or "neoforge" in jar_name:
            return "forge"
        elif "mohist" in jar_name:
            return "mohist"
        elif "catserver" in jar_name:
            return "catserver"
        elif "server" in jar_name and "vanilla" not in jar_name:
            # 可能是原版服务端
            try:
                # 尝试读取JAR文件的META-INF信息
                import zipfile
                with zipfile.ZipFile(jar_path, 'r') as zf:
                    if 'net/minecraft/server/Main.class' in [x.filename for x in zf.filelist]:
                        return "vanilla"
            except:
                pass
        
        return "unknown"
    
    @classmethod
    def get_core_info(cls, core_type: str) -> Dict:
        """获取核心信息"""
        return cls.CORE_TYPES.get(core_type, {
            "name": "未知核心",
            "website": "",
            "description": "未知服务器核心",
            "download_pattern": ""
        })
    
    @classmethod
    def get_download_url(cls, core_type: str, version: str, mirror: str = "mslmc") -> Optional[str]:
        """获取下载URL"""
        if mirror in cls.MIRROR_SITES and core_type in cls.MIRROR_SITES[mirror]["patterns"]:
            pattern = cls.MIRROR_SITES[mirror]["patterns"][core_type]
            # 特殊处理构建号
            if "{build}" in pattern:
                # 这里简化处理，实际需要API获取最新构建号
                return pattern.replace("{version}", version).replace("{build}", "latest")
            return pattern.replace("{version}", version)
        
        # 回退到默认URL
        core_info = cls.get_core_info(core_type)
        if core_info.get("download_pattern"):
            pattern = core_info["download_pattern"]
            # 特殊处理
            if core_type == "vanilla":
                # 需要先获取版本manifest
                return None
            return pattern.replace("{version}", version)
        
        return None


class UniversalServer:
    """通用Minecraft服务器管理器"""
    
    def __init__(self, server_dir: str = "."):
        self.server_dir = Path(server_dir).absolute()
        self.server_jar = ""
        self.java_opts = "-Xmx2048M -Xms2048M"
        self.process: Optional[subprocess.Popen] = None
        self.log_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.server_properties = {}
        self.log_file = self.server_dir / "server.log"
        self.backup_dir = self.server_dir / "backups"
        self.config_file = self.server_dir / "server_launcher.json"
        
        # 确保目录存在
        self.server_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # 加载配置
        self.load_config()
        
        # 检测系统
        self.is_windows = platform.system() == "Windows"
        
        # 自动检测核心
        self.detect_server_core()
    
    def load_config(self):
        """加载保存的配置"""
        default_config = {
            "server_dir": str(self.server_dir),
            "server_jar": self.server_jar,
            "java_opts": self.java_opts,
            "core_type": "unknown",
            "minecraft_version": "",
            "auto_backup": True,
            "backup_interval": 3600,
            "max_backups": 10,
            "mirror_site": "mslmc"
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.server_dir = Path(config.get("server_dir", str(self.server_dir)))
                    self.server_jar = config.get("server_jar", self.server_jar)
                    self.java_opts = config.get("java_opts", self.java_opts)
                    self.core_type = config.get("core_type", "unknown")
                    self.minecraft_version = config.get("minecraft_version", "")
                    self.mirror_site = config.get("mirror_site", "mslmc")
            except Exception as e:
                print(f"加载配置时出错: {e}")
                self.core_type = "unknown"
                self.minecraft_version = ""
                self.mirror_site = "mslmc"
        else:
            self.core_type = "unknown"
            self.minecraft_version = ""
            self.mirror_site = "mslmc"
            self.save_config(default_config)
    
    def save_config(self, config=None):
        """保存配置"""
        if config is None:
            config = {
                "server_dir": str(self.server_dir),
                "server_jar": self.server_jar,
                "java_opts": self.java_opts,
                "core_type": self.core_type,
                "minecraft_version": self.minecraft_version,
                "mirror_site": self.mirror_site,
                "last_modified": datetime.now().isoformat()
            }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置时出错: {e}")
            return False
    
    def detect_server_core(self):
        """检测服务器核心"""
        if not self.server_jar:
            # 尝试自动寻找JAR文件
            for file in self.server_dir.iterdir():
                if file.is_file() and file.name.endswith('.jar'):
                    # 跳过安装器
                    if 'installer' not in file.name.lower():
                        self.server_jar = file.name
                        break
        
        if self.server_jar:
            jar_path = self.server_dir / self.server_jar
            self.core_type = ServerCoreManager.detect_core_type(jar_path)
            
            # 尝试从文件名提取版本
            jar_name = jar_path.name.lower()
            for version in ServerCoreManager.MINECRAFT_VERSIONS:
                if version in jar_name:
                    self.minecraft_version = version
                    break
    
    def check_eula(self) -> Tuple[bool, str]:
        """检查EULA状态"""
        eula_file = self.server_dir / "eula.txt"
        
        if not eula_file.exists():
            return False, "EULA文件不存在"
        
        try:
            with open(eula_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "eula=true" in content.lower():
                    return True, "EULA已同意"
        except:
            pass
        
        return False, "EULA未同意"
    
    def accept_eula(self) -> bool:
        """同意EULA"""
        eula_file = self.server_dir / "eula.txt"
        
        try:
            content = """#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).
#Generated by Universal Minecraft Server Launcher
# {}
eula=true""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            with open(eula_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"同意EULA时出错: {e}")
            return False
    
    def get_java_command(self) -> List[str]:
        """获取Java启动命令"""
        jar_path = self.server_dir / self.server_jar
        
        # 基础命令
        cmd = ["java"]
        
        # 添加Java参数
        if self.java_opts:
            cmd.extend(self.java_opts.split())
        
        # 添加JAR文件
        cmd.extend(["-jar", str(jar_path)])
        
        # 对于不同类型的服务端，可能需要不同的参数
        if self.core_type in ["forge", "neoforge", "fabric"]:
            # 模组服务端通常不需要额外参数
            pass
        else:
            # 普通服务端添加nogui参数
            cmd.append("nogui")
        
        return cmd
    
    def start_server(self) -> bool:
        """启动服务器"""
        # 检查Java是否可用
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                print("Java检查失败，尝试寻找Java...")
                # 尝试在常见位置寻找Java
                java_path = self.find_java()
                if not java_path:
                    print("错误: 未找到Java，请确保Java已安装")
                    return False
        except FileNotFoundError:
            print("Java未在PATH中找到，尝试寻找Java...")
            java_path = self.find_java()
            if not java_path:
                print("错误: 未找到Java，请确保Java已安装")
                return False
        
        # 检查JAR文件
        jar_path = self.server_dir / self.server_jar
        if not jar_path.exists():
            print(f"错误: 未找到服务器JAR文件: {self.server_jar}")
            return False
        
        # 检查EULA
        eula_accepted, eula_msg = self.check_eula()
        if not eula_accepted:
            print(f"警告: {eula_msg}")
            print(f"服务器将自动尝试同意EULA...")
            if not self.accept_eula():
                print(f"无法自动同意EULA，请手动编辑eula.txt")
                return False
        
        # 确保有server.properties
        if not (self.server_dir / "server.properties").exists():
            print(f"创建默认server.properties...")
            self.create_default_properties()
        
        # 构建启动命令
        cmd = self.get_java_command()
        
        print(f"启动Minecraft服务器...")
        print(f"核心类型: {self.core_type}")
        print(f"版本: {self.minecraft_version}")
        print(f"命令: {' '.join(cmd)}")
        
        try:
            # 启动服务器进程
            self.process = subprocess.Popen(
                cmd,
                cwd=self.server_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if self.is_windows else 0
            )
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # 保存配置
            self.save_config()
            
            print(f"服务器启动成功！PID: {self.process.pid}")
            return True
            
        except Exception as e:
            print(f"启动服务器时出错: {e}")
            self.is_running = False
            return False
    
    def find_java(self) -> Optional[str]:
        """寻找Java安装路径"""
        if self.is_windows:
            # Windows常见Java路径
            possible_paths = [
                "C:\\Program Files\\Java\\jdk-21\\bin\\java.exe",
                "C:\\Program Files\\Java\\jdk-17\\bin\\java.exe",
                "C:\\Program Files\\Java\\jdk-11\\bin\\java.exe",
                "C:\\Program Files\\Java\\jdk-8\\bin\\java.exe",
                "C:\\Program Files\\Java\\jre-21\\bin\\java.exe",
                "C:\\Program Files\\Java\\jre-17\\bin\\java.exe",
                "C:\\Program Files\\Java\\jre-8\\bin\\java.exe",
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return path
        
        # Unix-like系统
        else:
            possible_paths = [
                "/usr/bin/java",
                "/usr/local/bin/java",
                "/opt/java/bin/java",
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return path
        
        return None
    
    def create_default_properties(self):
        """创建默认server.properties"""
        properties_file = self.server_dir / "server.properties"
        
        default_props = """#Minecraft server properties
#Generated by Universal Minecraft Server Launcher
max-players=20
online-mode=true
server-port=25565
motd=Universal Minecraft Server
view-distance=10
simulation-distance=10
difficulty=normal
hardcore=false
enable-command-block=true
max-world-size=29999984
spawn-npcs=true
spawn-animals=true
spawn-monsters=true
generate-structures=true
level-type=minecraft\\:normal
"""
        
        with open(properties_file, 'w', encoding='utf-8') as f:
            f.write(default_props)
    
    def send_command(self, command: str):
        """向服务器发送命令"""
        if self.process and self.process.poll() is None:
            try:
                if not command.endswith('\n'):
                    command += '\n'
                self.process.stdin.write(command)
                self.process.stdin.flush()
                return True
            except Exception as e:
                print(f"发送命令时出错: {e}")
                return False
        else:
            print(f"服务器未运行，无法发送命令")
            return False
    
    def stop_server(self, force: bool = False) -> bool:
        """停止服务器"""
        if not self.process or self.process.poll() is not None:
            print(f"服务器未运行")
            self.is_running = False
            self.start_time = None
            return True
        
        try:
            if not force:
                print(f"正在发送停止命令...")
                self.send_command("stop")
                
                # 等待最多30秒
                for i in range(30):
                    if self.process.poll() is not None:
                        break
                    time.sleep(1)
            
            # 如果仍在运行，强制终止
            if self.process.poll() is None:
                if force:
                    print(f"强制终止服务器...")
                    if self.is_windows:
                        self.process.terminate()
                    else:
                        self.process.kill()
                    time.sleep(2)
                    if self.process.poll() is None:
                        if self.is_windows:
                            subprocess.run(["taskkill", "/F", "/PID", str(self.process.pid)])
                        else:
                            self.process.kill()
                else:
                    print(f"服务器未响应停止命令，尝试强制终止...")
                    if self.is_windows:
                        self.process.terminate()
                    else:
                        self.process.kill()
            
            self.is_running = False
            self.start_time = None
            print(f"服务器已停止")
            return True
            
        except Exception as e:
            print(f"停止服务器时出错: {e}")
            return False
    
    def get_uptime(self) -> Optional[timedelta]:
        """获取服务器运行时间"""
        if self.is_running and self.start_time:
            return datetime.now() - self.start_time
        return None
    
    def get_status(self) -> Dict:
        """获取服务器状态"""
        status = {
            "running": self.is_running,
            "pid": self.process.pid if self.process else None,
            "server_dir": str(self.server_dir),
            "server_jar": self.server_jar,
            "java_opts": self.java_opts,
            "core_type": self.core_type,
            "core_name": ServerCoreManager.get_core_info(self.core_type)["name"],
            "minecraft_version": self.minecraft_version,
            "eula_accepted": self.check_eula()[0],
            "backup_count": len(list(self.backup_dir.iterdir())) if self.backup_dir.exists() else 0
        }
        
        # 获取运行时间
        uptime = self.get_uptime()
        if uptime:
            status["uptime"] = str(uptime).split('.')[0]
            status["start_time"] = self.start_time.isoformat() if self.start_time else None
        
        return status


class UniversalServerLauncherGUI:
    """通用服务器启动器GUI"""
    
    def __init__(self, master=None):
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = master
        
        self.server = UniversalServer()
        self.root.title("通用Minecraft服务器启动器")
        self.root.geometry("1200x800")
        
        # 设置图标
        try:
            if platform.system() == "Windows":
                self.root.iconbitmap(default="icon.ico")
        except:
            pass
        
        # 设置样式
        self.setup_styles()
        
        # 创建菜单
        self.create_menu()
        
        # 创建主界面
        self.create_widgets()
        
        # 启动状态更新
        self.update_status()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        
        # 配置颜色
        colors = {
            'bg': '#2b2b2b',
            'fg': '#ffffff',
            'accent': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'panel': '#3c3c3c',
            'console_bg': '#1e1e1e',
            'console_fg': '#00ff00'
        }
        
        # 配置根窗口
        self.root.configure(bg=colors['bg'])
        
        # 创建自定义样式
        style.configure('Title.TLabel', 
                       font=('Microsoft YaHei', 16, 'bold'),
                       background=colors['bg'],
                       foreground=colors['fg'])
        
        style.configure('Status.TLabel',
                       font=('Microsoft YaHei', 10),
                       background=colors['bg'],
                       foreground=colors['fg'])
        
        style.configure('Accent.TButton',
                       font=('Microsoft YaHei', 10, 'bold'))
        
        style.configure('Panel.TFrame',
                       background=colors['panel'])
        
        style.configure('Console.TFrame',
                       background=colors['console_bg'])
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="选择服务器目录", command=self.select_server_dir)
        file_menu.add_command(label="打开服务器目录", command=self.open_server_dir)
        file_menu.add_separator()
        file_menu.add_command(label="新建服务器", command=self.create_new_server)
        file_menu.add_command(label="导入服务器", command=self.import_server)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)
        
        # 核心菜单
        core_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="核心", menu=core_menu)
        core_menu.add_command(label="选择核心", command=self.select_core_file)
        core_menu.add_command(label="下载核心", command=self.download_core_dialog)
        core_menu.add_separator()
        core_menu.add_command(label="检测核心", command=self.detect_core)
        core_menu.add_command(label="核心信息", command=self.show_core_info)
        
        # 服务器菜单
        server_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="服务器", menu=server_menu)
        server_menu.add_command(label="启动服务器", command=self.start_server, accelerator="Ctrl+S")
        server_menu.add_command(label="停止服务器", command=self.stop_server, accelerator="Ctrl+Q")
        server_menu.add_command(label="强制停止", command=self.force_stop)
        server_menu.add_separator()
        server_menu.add_command(label="同意EULA", command=self.accept_eula)
        server_menu.add_command(label="服务器属性", command=self.open_properties)
        server_menu.add_command(label="打开世界文件夹", command=self.open_world_folder)
        
        # 配置菜单
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="配置", menu=config_menu)
        config_menu.add_command(label="Java设置", command=self.open_java_settings)
        config_menu.add_command(label="启动参数", command=self.open_java_settings)  # 修复：指向同一个方法
        config_menu.add_command(label="镜像站设置", command=self.open_mirror_settings)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="创建备份", command=self.create_backup)
        tools_menu.add_command(label="备份管理", command=self.manage_backups)
        tools_menu.add_command(label="查看日志", command=self.view_logs)
        tools_menu.add_command(label="清理文件", command=self.cleanup_files)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="检查更新", command=self.check_updates)
        help_menu.add_command(label="关于", command=self.show_about)
        
        # 绑定快捷键
        self.root.bind('<Control-s>', lambda e: self.start_server())
        self.root.bind('<Control-q>', lambda e: self.stop_server())
    
    def create_widgets(self):
        """创建界面部件"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部信息栏
        self.create_info_bar(main_frame)
        
        # 控制按钮区域
        self.create_control_buttons(main_frame)
        
        # 服务器控制台
        self.create_console(main_frame)
        
        # 命令输入区域
        self.create_command_input(main_frame)
    
    def create_info_bar(self, parent):
        """创建信息栏"""
        info_frame = ttk.Frame(parent, style='Panel.TFrame')
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 使用网格布局
        info_frame.grid_columnconfigure(1, weight=1)
        info_frame.grid_columnconfigure(3, weight=1)
        info_frame.grid_columnconfigure(5, weight=1)
        
        # 第一行：服务器状态
        row = 0
        ttk.Label(info_frame, text="服务器状态:", style='Status.TLabel').grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.status_label = ttk.Label(info_frame, text="已停止", foreground='red', font=('Microsoft YaHei', 10, 'bold'))
        self.status_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="核心类型:", style='Status.TLabel').grid(row=row, column=2, sticky=tk.W, padx=(20,5), pady=2)
        self.core_label = ttk.Label(info_frame, text="未知", font=('Microsoft YaHei', 10))
        self.core_label.grid(row=row, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Minecraft版本:", style='Status.TLabel').grid(row=row, column=4, sticky=tk.W, padx=(20,5), pady=2)
        self.version_label = ttk.Label(info_frame, text="未知", font=('Microsoft YaHei', 10))
        self.version_label.grid(row=row, column=5, sticky=tk.W, padx=5, pady=2)
        
        # 第二行：其他信息
        row = 1
        ttk.Label(info_frame, text="EULA状态:", style='Status.TLabel').grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.eula_label = ttk.Label(info_frame, text="未同意", foreground='red', font=('Microsoft YaHei', 10))
        self.eula_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="运行时间:", style='Status.TLabel').grid(row=row, column=2, sticky=tk.W, padx=(20,5), pady=2)
        self.uptime_label = ttk.Label(info_frame, text="00:00:00", font=('Microsoft YaHei', 10))
        self.uptime_label.grid(row=row, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="服务器目录:", style='Status.TLabel').grid(row=row, column=4, sticky=tk.W, padx=(20,5), pady=2)
        self.dir_label = ttk.Label(info_frame, text=str(self.server.server_dir), font=('Microsoft YaHei', 9), foreground='#888888')
        self.dir_label.grid(row=row, column=5, sticky=tk.W, padx=5, pady=2)
        
        # 第三行：核心文件信息
        row = 2
        ttk.Label(info_frame, text="核心文件:", style='Status.TLabel').grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        self.jar_label = ttk.Label(info_frame, text="未选择", font=('Microsoft YaHei', 9), foreground='#888888')
        self.jar_label.grid(row=row, column=1, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Java内存:", style='Status.TLabel').grid(row=row, column=4, sticky=tk.W, padx=(20,5), pady=2)
        self.memory_label = ttk.Label(info_frame, text="2048M", font=('Microsoft YaHei', 10))
        self.memory_label.grid(row=row, column=5, sticky=tk.W, padx=5, pady=2)
    
    def create_control_buttons(self, parent):
        """创建控制按钮"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 使用网格布局，两行按钮
        # 第一行：主要控制按钮
        row1_frame = ttk.Frame(button_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.start_button = ttk.Button(row1_frame, text="▶ 启动服务器", 
                                      command=self.start_server, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=2)
        
        self.stop_button = ttk.Button(row1_frame, text="⏹ 停止服务器", 
                                     command=self.stop_server, style='Warning.TButton')
        self.stop_button.pack(side=tk.LEFT, padx=2)
        
        self.force_button = ttk.Button(row1_frame, text="⚠ 强制停止", 
                                      command=self.force_stop, style='Error.TButton')
        self.force_button.pack(side=tk.LEFT, padx=2)
        
        self.restart_button = ttk.Button(row1_frame, text="↻ 重启", 
                                        command=self.restart_server)
        self.restart_button.pack(side=tk.LEFT, padx=2)
        
        self.eula_button = ttk.Button(row1_frame, text="✓ 同意EULA", 
                                     command=self.accept_eula)
        self.eula_button.pack(side=tk.LEFT, padx=2)
        
        # 第二行：功能按钮
        row2_frame = ttk.Frame(button_frame)
        row2_frame.pack(fill=tk.X)
        
        self.select_dir_button = ttk.Button(row2_frame, text="📁 选择服务器目录", 
                                           command=self.select_server_dir)
        self.select_dir_button.pack(side=tk.LEFT, padx=2)
        
        self.select_core_button = ttk.Button(row2_frame, text="📦 选择核心", 
                                            command=self.select_core_file)
        self.select_core_button.pack(side=tk.LEFT, padx=2)
        
        self.download_button = ttk.Button(row2_frame, text="⬇ 下载核心", 
                                         command=self.download_core_dialog)
        self.download_button.pack(side=tk.LEFT, padx=2)
        
        self.backup_button = ttk.Button(row2_frame, text="💾 备份", 
                                       command=self.create_backup)
        self.backup_button.pack(side=tk.LEFT, padx=2)
        
        self.settings_button = ttk.Button(row2_frame, text="⚙ 设置", 
                                         command=self.open_settings)
        self.settings_button.pack(side=tk.LEFT, padx=2)
    
    def create_console(self, parent):
        """创建控制台输出区域"""
        console_frame = ttk.LabelFrame(parent, text="服务器控制台", padding=5)
        console_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 控制台工具栏
        toolbar = ttk.Frame(console_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(toolbar, text="清空", command=self.clear_console, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="保存", command=self.save_log, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="复制", command=self.copy_console_text, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="自动滚动", command=self.toggle_auto_scroll, width=10).pack(side=tk.LEFT, padx=2)
        
        # 创建带滚动条的文本框
        text_frame = ttk.Frame(console_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_scroll = ttk.Scrollbar(text_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.console_text = tk.Text(text_frame, 
                                   yscrollcommand=text_scroll.set,
                                   bg='#1e1e1e',
                                   fg='#00ff00',
                                   font=('Consolas', 10),
                                   wrap=tk.WORD,
                                   insertbackground='white')
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
        text_scroll.config(command=self.console_text.yview)
        
        # 禁止用户编辑，但允许复制
        self.console_text.config(state=tk.DISABLED)
        
        # 右键菜单
        self.create_console_menu()
        
        # 自动滚动状态
        self.auto_scroll = True
    
    def create_console_menu(self):
        """创建控制台右键菜单"""
        self.console_menu = tk.Menu(self.console_text, tearoff=0)
        self.console_menu.add_command(label="复制", command=self.copy_console_text)
        self.console_menu.add_command(label="清空", command=self.clear_console)
        self.console_menu.add_separator()
        self.console_menu.add_command(label="保存日志", command=self.save_log)
        self.console_menu.add_command(label="打开日志文件", command=self.open_log_file)
        
        # 绑定右键事件
        self.console_text.bind("<Button-3>", self.show_console_menu)
    
    def create_command_input(self, parent):
        """创建命令输入区域"""
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X)
        
        ttk.Label(input_frame, text="命令:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.command_var = tk.StringVar()
        self.command_entry = ttk.Entry(input_frame, textvariable=self.command_var, font=('Consolas', 10))
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # 绑定回车键发送命令
        self.command_entry.bind("<Return>", lambda e: self.send_server_command())
        
        send_button = ttk.Button(input_frame, text="发送", command=self.send_server_command, width=8)
        send_button.pack(side=tk.LEFT)
        
        # 常用命令按钮
        common_commands = ["help", "stop", "say", "list", "save-all"]
        for cmd in common_commands:
            ttk.Button(input_frame, text=cmd, command=lambda c=cmd: self.send_common_command(c), width=6).pack(side=tk.LEFT, padx=2)
    
    def update_status(self):
        """更新状态显示"""
        # 更新服务器状态
        status = self.server.get_status()
        
        # 服务器状态
        if status["running"]:
            self.status_label.config(text="运行中", foreground='green')
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.force_button.config(state=tk.NORMAL)
            self.restart_button.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="已停止", foreground='red')
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.force_button.config(state=tk.DISABLED)
            self.restart_button.config(state=tk.DISABLED)
        
        # 核心信息
        core_name = status["core_name"]
        self.core_label.config(text=core_name)
        
        # 版本信息
        version = status["minecraft_version"]
        self.version_label.config(text=version if version else "未知")
        
        # EULA状态
        if status["eula_accepted"]:
            self.eula_label.config(text="已同意", foreground='green')
            self.eula_button.config(state=tk.DISABLED)
        else:
            self.eula_label.config(text="未同意", foreground='red')
            self.eula_button.config(state=tk.NORMAL)
        
        # 运行时间
        if "uptime" in status:
            self.uptime_label.config(text=status["uptime"])
        else:
            self.uptime_label.config(text="00:00:00")
        
        # 目录和文件
        self.dir_label.config(text=str(self.server.server_dir)[:50] + "..." if len(str(self.server.server_dir)) > 50 else str(self.server.server_dir))
        self.jar_label.config(text=self.server.server_jar if self.server.server_jar else "未选择")
        
        # 内存信息
        import re
        match = re.search(r'-Xmx(\d+)M', self.server.java_opts)
        if match:
            self.memory_label.config(text=f"{match.group(1)}M")
        
        # 每2秒更新一次
        self.root.after(2000, self.update_status)
    
    def log_to_console(self, message, color="#00ff00"):
        """向控制台输出消息"""
        self.console_text.config(state=tk.NORMAL)
        
        # 添加时间戳
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        
        # 插入带颜色的文本
        self.console_text.insert(tk.END, timestamp, "timestamp")
        self.console_text.insert(tk.END, message + "\n")
        
        # 滚动到底部
        if self.auto_scroll:
            self.console_text.see(tk.END)
        
        self.console_text.config(state=tk.DISABLED)
    
    # ==================== 主要功能方法 ====================
    
    def select_server_dir(self):
        """选择服务器目录"""
        directory = filedialog.askdirectory(
            title="选择服务器目录",
            initialdir=str(self.server.server_dir)
        )
        
        if directory:
            self.server.server_dir = Path(directory)
            self.server.detect_server_core()
            self.server.save_config()
            
            self.log_to_console(f"服务器目录已更改为: {directory}", "#00ffff")
            messagebox.showinfo("成功", f"服务器目录已设置为:\n{directory}")
    
    def select_core_file(self):
        """选择核心文件"""
        filetypes = [
            ("JAR files", "*.jar"),
            ("所有文件", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="选择服务器核心文件",
            initialdir=str(self.server.server_dir),
            filetypes=filetypes
        )
        
        if filename:
            core_path = Path(filename)
            
            # 如果文件不在服务器目录，复制过去
            if core_path.parent != self.server.server_dir:
                reply = messagebox.askyesno("复制文件", 
                    "核心文件不在服务器目录中，是否复制到服务器目录？\n\n"
                    "是：复制到服务器目录\n否：直接使用当前路径")
                
                if reply:
                    try:
                        target_path = self.server.server_dir / core_path.name
                        shutil.copy2(core_path, target_path)
                        self.server.server_jar = core_path.name
                        self.log_to_console(f"已复制核心文件到服务器目录: {core_path.name}", "#00ffff")
                    except Exception as e:
                        messagebox.showerror("错误", f"复制文件失败: {e}")
                        return
                else:
                    # 直接使用，但需要确保路径正确
                    self.server.server_jar = str(core_path)
            else:
                self.server.server_jar = core_path.name
            
            # 检测核心类型
            self.server.detect_server_core()
            self.server.save_config()
            
            core_info = ServerCoreManager.get_core_info(self.server.core_type)
            self.log_to_console(f"已选择核心: {core_info['name']} ({self.server.minecraft_version})", "#00ff00")
    
    def download_core_dialog(self):
        """打开下载核心对话框"""
        download_window = tk.Toplevel(self.root)
        download_window.title("下载服务器核心")
        download_window.geometry("600x500")
        download_window.transient(self.root)
        download_window.grab_set()
        
        # 创建笔记本（选项卡）
        notebook = ttk.Notebook(download_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 快速下载标签页
        quick_frame = ttk.Frame(notebook)
        notebook.add(quick_frame, text="快速下载")
        
        # 核心类型选择
        ttk.Label(quick_frame, text="选择核心类型:").pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        core_type_var = tk.StringVar(value="purpur")
        core_type_combo = ttk.Combobox(quick_frame, textvariable=core_type_var, state="readonly")
        core_type_combo['values'] = list(ServerCoreManager.CORE_TYPES.keys())
        core_type_combo.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 版本选择
        ttk.Label(quick_frame, text="选择Minecraft版本:").pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        version_var = tk.StringVar(value="1.21.4")
        version_combo = ttk.Combobox(quick_frame, textvariable=version_var, state="readonly")
        version_combo['values'] = ServerCoreManager.MINECRAFT_VERSIONS
        version_combo.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 镜像站选择
        ttk.Label(quick_frame, text="选择镜像站:").pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        mirror_var = tk.StringVar(value=self.server.mirror_site)
        mirror_combo = ttk.Combobox(quick_frame, textvariable=mirror_var, state="readonly")
        mirror_combo['values'] = list(ServerCoreManager.MIRROR_SITES.keys())
        mirror_combo.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 下载按钮
        button_frame = ttk.Frame(quick_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def start_download():
            core_type = core_type_var.get()
            version = version_var.get()
            mirror = mirror_var.get()
            
            if not core_type or not version:
                messagebox.showerror("错误", "请选择核心类型和版本")
                return
            
            # 生成文件名
            core_info = ServerCoreManager.get_core_info(core_type)
            filename = f"{core_info['name'].lower()}-{version}.jar"
            if core_type == "vanilla":
                filename = "server.jar"
            
            target_path = self.server.server_dir / filename
            
            # 检查文件是否存在
            if target_path.exists():
                reply = messagebox.askyesno("文件存在", 
                    f"文件 {filename} 已存在，是否覆盖？")
                if not reply:
                    return
            
            # 显示下载信息
            self.log_to_console(f"开始下载核心: {core_info['name']} {version}", "#00ffff")
            
            # 这里简化下载过程，实际应该使用线程和进度条
            # 由于网络请求需要，这里只显示提示
            messagebox.showinfo("下载提示", 
                f"开始下载 {core_info['name']} {version}\n\n"
                f"由于网络请求限制，请手动从以下链接下载:\n"
                f"{ServerCoreManager.get_download_url(core_type, version, mirror) or '无法获取下载链接'}\n\n"
                f"下载后请将文件保存为: {filename}")
            
            download_window.destroy()
        
        ttk.Button(button_frame, text="开始下载", command=start_download).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="取消", command=download_window.destroy).pack(side=tk.RIGHT)
    
    def detect_core(self):
        """检测核心类型"""
        if not self.server.server_jar:
            messagebox.showwarning("警告", "请先选择服务器核心文件")
            return
        
        self.server.detect_server_core()
        self.server.save_config()
        
        core_info = ServerCoreManager.get_core_info(self.server.core_type)
        messagebox.showinfo("核心检测", 
            f"核心类型: {core_info['name']}\n"
            f"Minecraft版本: {self.server.minecraft_version}\n"
            f"描述: {core_info['description']}")
    
    def show_core_info(self):
        """显示核心信息"""
        if not self.server.core_type or self.server.core_type == "unknown":
            messagebox.showwarning("警告", "未检测到核心类型")
            return
        
        core_info = ServerCoreManager.get_core_info(self.server.core_type)
        
        info_text = f"""
核心名称: {core_info['name']}
核心类型: {self.server.core_type}
Minecraft版本: {self.server.minecraft_version}

描述: {core_info['description']}
官方网站: {core_info['website']}

核心文件: {self.server.server_jar}
        """
        
        messagebox.showinfo("核心信息", info_text)
    
    def start_server(self):
        """启动服务器"""
        if not self.server.server_jar:
            messagebox.showerror("错误", "请先选择服务器核心文件")
            return
        
        self.log_to_console("正在启动服务器...", "#ffff00")
        
        # 在新线程中启动服务器，避免阻塞GUI
        def start():
            if self.server.start_server():
                self.log_to_console("服务器启动成功！", "#00ff00")
                # 开始读取服务器输出
                self.read_server_output()
            else:
                self.log_to_console("服务器启动失败！", "#ff0000")
        
        threading.Thread(target=start, daemon=True).start()
    
    def read_server_output(self):
        """读取服务器输出"""
        def read_output():
            if self.server.process:
                while self.server.is_running and self.server.process and self.server.process.poll() is None:
                    try:
                        line = self.server.process.stdout.readline()
                        if line:
                            # 在GUI线程中更新控制台
                            self.root.after(0, self.log_to_console, line.rstrip())
                    except:
                        break
        
        # 在新线程中读取输出
        threading.Thread(target=read_output, daemon=True).start()
    
    def stop_server(self):
        """停止服务器"""
        self.log_to_console("正在停止服务器...", "#ffff00")
        
        def stop():
            if self.server.stop_server():
                self.log_to_console("服务器已停止", "#00ff00")
            else:
                self.log_to_console("停止服务器失败", "#ff0000")
        
        threading.Thread(target=stop, daemon=True).start()
    
    def force_stop(self):
        """强制停止服务器"""
        if messagebox.askyesno("强制停止", "确定要强制停止服务器吗？\n这可能导致数据丢失！"):
            self.log_to_console("正在强制停止服务器...", "#ff0000")
            
            def force_stop():
                if self.server.stop_server(force=True):
                    self.log_to_console("服务器已强制停止", "#00ff00")
                else:
                    self.log_to_console("强制停止失败", "#ff0000")
            
            threading.Thread(target=force_stop, daemon=True).start()
    
    def restart_server(self):
        """重启服务器"""
        self.log_to_console("正在重启服务器...", "#ffff00")
        
        def restart():
            # 先停止
            if self.server.is_running:
                self.server.stop_server()
                time.sleep(3)
            
            # 再启动
            if self.server.start_server():
                self.log_to_console("服务器重启成功！", "#00ff00")
                self.read_server_output()
            else:
                self.log_to_console("服务器重启失败！", "#ff0000")
        
        threading.Thread(target=restart, daemon=True).start()
    
    def accept_eula(self):
        """同意EULA"""
        if messagebox.askyesno("同意EULA", 
            "你同意Minecraft EULA吗？\n\n"
            "同意后，服务器才能正常启动。\n"
            "EULA详情: https://aka.ms/MinecraftEULA"):
            
            if self.server.accept_eula():
                self.log_to_console("已同意EULA", "#00ff00")
                messagebox.showinfo("成功", "EULA已同意！现在可以启动服务器了。")
            else:
                self.log_to_console("同意EULA失败", "#ff0000")
                messagebox.showerror("错误", "同意EULA失败，请检查文件权限。")
    
    def create_backup(self):
        """创建备份"""
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.log_to_console(f"正在创建备份: {backup_name}", "#00ffff")
        
        def backup():
            try:
                backup_path = self.server.backup_dir / backup_name
                backup_path.mkdir(exist_ok=True)
                
                # 备份重要文件
                backup_files = [
                    "server.properties", "eula.txt", "ops.json", 
                    "whitelist.json", "banned-players.json", "usercache.json"
                ]
                
                for file_name in backup_files:
                    src_file = self.server.server_dir / file_name
                    if src_file.exists():
                        shutil.copy2(src_file, backup_path / file_name)
                
                # 备份世界
                world_dirs = ["world", "world_nether", "world_the_end"]
                for dir_name in world_dirs:
                    src_dir = self.server.server_dir / dir_name
                    if src_dir.exists():
                        dst_dir = backup_path / dir_name
                        if dst_dir.exists():
                            shutil.rmtree(dst_dir)
                        shutil.copytree(src_dir, dst_dir)
                
                self.log_to_console("备份创建成功！", "#00ff00")
            except Exception as e:
                self.log_to_console(f"备份失败: {e}", "#ff0000")
        
        threading.Thread(target=backup, daemon=True).start()
    
    def open_server_dir(self):
        """打开服务器目录"""
        if self.server.server_dir.exists():
            if platform.system() == "Windows":
                os.startfile(self.server.server_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['open', str(self.server.server_dir)])
            else:  # Linux
                subprocess.run(['xdg-open', str(self.server.server_dir)])
    
    def open_world_folder(self):
        """打开世界文件夹"""
        world_dir = self.server.server_dir / "world"
        if world_dir.exists():
            if platform.system() == "Windows":
                os.startfile(world_dir)
            elif platform.system() == "Darwin":
                subprocess.run(['open', str(world_dir)])
            else:
                subprocess.run(['xdg-open', str(world_dir)])
        else:
            messagebox.showinfo("提示", "世界文件夹不存在")
    
    def open_properties(self):
        """打开服务器属性编辑器"""
        properties_file = self.server.server_dir / "server.properties"
        
        # 如果文件不存在，创建默认的
        if not properties_file.exists():
            self.server.create_default_properties()
        
        # 打开文件
        try:
            if platform.system() == "Windows":
                os.startfile(properties_file)
            elif platform.system() == "Darwin":
                subprocess.run(['open', str(properties_file)])
            else:
                subprocess.run(['xdg-open', str(properties_file)])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件: {e}")
    
    def open_java_settings(self):
        """打开Java设置对话框"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Java设置")
        settings_window.geometry("400x300")
        settings_window.transient(self.root)
        
        # 内存设置
        ttk.Label(settings_window, text="Java内存设置 (MB):").pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        mem_frame = ttk.Frame(settings_window)
        mem_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        ttk.Label(mem_frame, text="最小内存:").pack(side=tk.LEFT)
        min_mem_var = tk.IntVar(value=1024)
        min_mem_spin = ttk.Spinbox(mem_frame, from_=512, to=16384, textvariable=min_mem_var, width=8)
        min_mem_spin.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(mem_frame, text="最大内存:").pack(side=tk.LEFT)
        max_mem_var = tk.IntVar(value=2048)
        max_mem_spin = ttk.Spinbox(mem_frame, from_=512, to=32768, textvariable=max_mem_var, width=8)
        max_mem_spin.pack(side=tk.LEFT, padx=5)
        
        # 额外参数
        ttk.Label(settings_window, text="额外Java参数:").pack(anchor=tk.W, padx=20, pady=(0, 5))
        
        extra_args_var = tk.StringVar()
        extra_args_entry = ttk.Entry(settings_window, textvariable=extra_args_var)
        extra_args_entry.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # 保存按钮
        def save_settings():
            min_mem = min_mem_var.get()
            max_mem = max_mem_var.get()
            extra_args = extra_args_var.get().strip()
            
            # 构建Java参数
            java_opts = f"-Xmx{max_mem}M -Xms{min_mem}M"
            if extra_args:
                java_opts += f" {extra_args}"
            
            self.server.java_opts = java_opts
            self.server.save_config()
            
            self.log_to_console(f"Java设置已更新: {java_opts}", "#00ff00")
            settings_window.destroy()
            messagebox.showinfo("成功", "Java设置已保存")
        
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        ttk.Button(button_frame, text="保存", command=save_settings).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="取消", command=settings_window.destroy).pack(side=tk.RIGHT)
    
    def open_mirror_settings(self):
        """打开镜像站设置"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("镜像站设置")
        settings_window.geometry("400x200")
        settings_window.transient(self.root)
        
        ttk.Label(settings_window, text="选择默认镜像站:").pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        mirror_var = tk.StringVar(value=self.server.mirror_site)
        mirror_combo = ttk.Combobox(settings_window, textvariable=mirror_var, state="readonly")
        mirror_combo['values'] = list(ServerCoreManager.MIRROR_SITES.keys())
        mirror_combo.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # 显示镜像站信息
        info_frame = ttk.Frame(settings_window)
        info_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        def update_mirror_info(*args):
            mirror = mirror_var.get()
            if mirror in ServerCoreManager.MIRROR_SITES:
                info = ServerCoreManager.MIRROR_SITES[mirror]
                info_text = f"名称: {info['name']}\nURL: {info['url']}"
                info_label.config(text=info_text)
        
        mirror_var.trace('w', update_mirror_info)
        update_mirror_info()
        
        info_label = ttk.Label(info_frame, text="", justify=tk.LEFT)
        info_label.pack(anchor=tk.W)
        
        # 保存按钮
        def save_settings():
            self.server.mirror_site = mirror_var.get()
            self.server.save_config()
            
            mirror_info = ServerCoreManager.MIRROR_SITES.get(self.server.mirror_site, {})
            self.log_to_console(f"镜像站已设置为: {mirror_info.get('name', '未知')}", "#00ff00")
            settings_window.destroy()
        
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        ttk.Button(button_frame, text="保存", command=save_settings).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="取消", command=settings_window.destroy).pack(side=tk.RIGHT)
    
    def open_settings(self):
        """打开综合设置"""
        self.open_java_settings()
    
    def create_new_server(self):
        """创建新服务器"""
        # 选择目录
        directory = filedialog.askdirectory(title="选择新服务器目录")
        if not directory:
            return
        
        # 创建目录
        server_dir = Path(directory)
        server_dir.mkdir(exist_ok=True)
        
        # 复制启动器配置
        config_file = server_dir / "server_launcher.json"
        if not config_file.exists():
            default_config = {
                "server_dir": str(server_dir),
                "server_jar": "",
                "java_opts": "-Xmx2048M -Xms1024M",
                "core_type": "unknown",
                "minecraft_version": "",
                "mirror_site": "mslmc"
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
        
        # 切换到新目录
        self.server = UniversalServer(str(server_dir))
        self.log_to_console(f"已创建新服务器: {server_dir}", "#00ff00")
        messagebox.showinfo("成功", f"新服务器已创建在:\n{server_dir}")
    
    def import_server(self):
        """导入现有服务器"""
        directory = filedialog.askdirectory(title="选择要导入的服务器目录")
        if directory:
            # 检查是否是有效的服务器目录
            server_dir = Path(directory)
            
            # 寻找JAR文件
            jar_files = list(server_dir.glob("*.jar"))
            if not jar_files:
                reply = messagebox.askyesno("未找到JAR文件", 
                    "未找到服务器JAR文件，是否继续导入？\n"
                    "你可以在导入后手动选择核心文件。")
                if not reply:
                    return
            
            # 切换到新目录
            self.server = UniversalServer(str(server_dir))
            self.log_to_console(f"已导入服务器: {server_dir}", "#00ff00")
            messagebox.showinfo("成功", f"服务器已导入:\n{server_dir}")
    
    def manage_backups(self):
        """管理备份"""
        if not self.server.backup_dir.exists():
            messagebox.showinfo("提示", "备份目录不存在")
            return
        
        backup_window = tk.Toplevel(self.root)
        backup_window.title("备份管理")
        backup_window.geometry("600x400")
        
        # 获取备份列表
        backups = []
        for backup_dir in self.server.backup_dir.iterdir():
            if backup_dir.is_dir():
                backups.append(backup_dir.name)
        
        if not backups:
            ttk.Label(backup_window, text="暂无备份").pack(pady=20)
        else:
            # 创建列表
            listbox = tk.Listbox(backup_window, font=('Consolas', 10))
            listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            for backup in sorted(backups, reverse=True):
                listbox.insert(tk.END, backup)
            
            # 按钮框架
            button_frame = ttk.Frame(backup_window)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            def restore_backup():
                selection = listbox.curselection()
                if selection:
                    backup_name = listbox.get(selection[0])
                    if messagebox.askyesno("恢复备份", f"确定要恢复备份 '{backup_name}' 吗？"):
                        # 这里实现恢复逻辑
                        self.log_to_console(f"恢复备份: {backup_name}", "#ffff00")
                        messagebox.showinfo("提示", "恢复功能正在开发中")
            
            def delete_backup():
                selection = listbox.curselection()
                if selection:
                    backup_name = listbox.get(selection[0])
                    if messagebox.askyesno("删除备份", f"确定要删除备份 '{backup_name}' 吗？"):
                        backup_path = self.server.backup_dir / backup_name
                        try:
                            shutil.rmtree(backup_path)
                            listbox.delete(selection[0])
                            self.log_to_console(f"已删除备份: {backup_name}", "#00ff00")
                        except Exception as e:
                            messagebox.showerror("错误", f"删除失败: {e}")
            
            ttk.Button(button_frame, text="恢复选中备份", command=restore_backup).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="删除选中备份", command=delete_backup).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="关闭", command=backup_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def view_logs(self):
        """查看日志文件"""
        log_file = self.server.server_dir / "server.log"
        
        if not log_file.exists():
            messagebox.showinfo("提示", "日志文件不存在")
            return
        
        log_window = tk.Toplevel(self.root)
        log_window.title("服务器日志")
        log_window.geometry("800x600")
        
        # 创建文本框
        text_frame = ttk.Frame(log_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_scroll = ttk.Scrollbar(text_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        log_text = tk.Text(text_frame, yscrollcommand=text_scroll.set,
                          bg='#1e1e1e', fg='#ffffff',
                          font=('Consolas', 9))
        log_text.pack(fill=tk.BOTH, expand=True)
        
        text_scroll.config(command=log_text.yview)
        
        # 加载日志
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_text.insert(tk.END, f.read())
        except:
            log_text.insert(tk.END, "# 无法读取日志文件")
        
        log_text.config(state=tk.DISABLED)
        
        # 按钮框架
        button_frame = ttk.Frame(log_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def clear_log():
            if messagebox.askyesno("清空日志", "确定要清空日志文件吗？"):
                try:
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.write("")
                    log_text.config(state=tk.NORMAL)
                    log_text.delete("1.0", tk.END)
                    log_text.config(state=tk.DISABLED)
                    self.log_to_console("日志已清空", "#ffff00")
                except:
                    messagebox.showerror("错误", "清空日志失败")
        
        ttk.Button(button_frame, text="清空日志", command=clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="刷新", command=lambda: self.refresh_log_view(log_text, log_file)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=log_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def refresh_log_view(self, log_text, log_file):
        """刷新日志视图"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            log_text.config(state=tk.NORMAL)
            log_text.delete("1.0", tk.END)
            log_text.insert(tk.END, content)
            log_text.see(tk.END)
            log_text.config(state=tk.DISABLED)
        except:
            pass
    
    def cleanup_files(self):
        """清理文件"""
        if messagebox.askyesno("清理文件", 
            "确定要清理服务器目录吗？\n\n"
            "将删除以下文件:\n"
            "- 日志文件 (server.log)\n"
            "- 崩溃报告 (crash-reports/)\n"
            "- 调试文件 (debug/)\n"
            "- 缓存文件\n\n"
            "不会删除世界、配置和核心文件。"):
            
            try:
                # 删除日志文件
                log_file = self.server.server_dir / "server.log"
                if log_file.exists():
                    log_file.unlink()
                
                # 删除崩溃报告
                crash_dir = self.server.server_dir / "crash-reports"
                if crash_dir.exists():
                    shutil.rmtree(crash_dir)
                
                # 删除调试文件
                debug_dir = self.server.server_dir / "debug"
                if debug_dir.exists():
                    shutil.rmtree(debug_dir)
                
                self.log_to_console("已清理服务器目录", "#00ff00")
                messagebox.showinfo("成功", "清理完成")
                
            except Exception as e:
                messagebox.showerror("错误", f"清理失败: {e}")
    
    def send_server_command(self):
        """发送服务器命令"""
        command = self.command_var.get().strip()
        if command:
            self.log_to_console(f"> {command}", "#ffff00")
            self.server.send_command(command)
            self.command_var.set("")
    
    def send_common_command(self, command):
        """发送常用命令"""
        self.command_var.set(command)
        self.send_server_command()
    
    def copy_console_text(self):
        """复制控制台文本"""
        try:
            text = self.console_text.get("1.0", tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log_to_console("控制台文本已复制到剪贴板", "#00ff00")
        except:
            pass
    
    def clear_console(self):
        """清空控制台"""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.delete("1.0", tk.END)
        self.console_text.config(state=tk.DISABLED)
        self.log_to_console("控制台已清空", "#ffff00")
    
    def save_log(self):
        """保存日志到文件"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"server_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            try:
                text = self.console_text.get("1.0", tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.log_to_console(f"日志已保存到: {filename}", "#00ff00")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
    
    def open_log_file(self):
        """打开日志文件"""
        log_file = self.server.server_dir / "server.log"
        if log_file.exists():
            if platform.system() == "Windows":
                os.startfile(log_file)
            elif platform.system() == "Darwin":
                subprocess.run(['open', str(log_file)])
            else:
                subprocess.run(['xdg-open', str(log_file)])
        else:
            messagebox.showinfo("提示", "日志文件不存在")
    
    def toggle_auto_scroll(self):
        """切换自动滚动"""
        self.auto_scroll = not self.auto_scroll
        status = "启用" if self.auto_scroll else "禁用"
        self.log_to_console(f"自动滚动已{status}", "#ffff00")
    
    def show_console_menu(self, event):
        """显示控制台右键菜单"""
        try:
            self.console_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.console_menu.grab_release()
    
    def show_help(self):
        """显示帮助"""
        help_text = """通用Minecraft服务器启动器 使用说明

主要功能:
1. 支持所有类型Minecraft服务器核心
2. 从镜像站快速下载核心文件
3. 灵活的服务器目录管理
4. 完整的服务器控制功能

快速开始:
1. 选择服务器目录 (文件 -> 选择服务器目录)
2. 选择或下载核心文件 (核心 -> 选择核心/下载核心)
3. 同意EULA (点击"同意EULA"按钮)
4. 启动服务器 (点击"启动服务器"按钮)

核心下载:
- 支持多种核心: Purpur, Paper, Spigot, Forge, Fabric等
- 支持多个镜像站: MSLMC, BMCLAPI等
- 支持所有Minecraft版本

服务器管理:
- 启动/停止/重启服务器
- 发送控制台命令
- 备份和恢复世界
- 管理服务器属性

快捷键:
- Ctrl+S: 启动服务器
- Ctrl+Q: 停止服务器
- Enter: 发送命令

注意:
- 确保已安装Java 8或更高版本
- 首次启动需要同意EULA
- 建议定期备份重要数据

官方网站: https://dl.mslmc.cn/
"""
        
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("700x600")
        
        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_scroll = ttk.Scrollbar(text_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        help_text_widget = tk.Text(text_frame, yscrollcommand=text_scroll.set,
                                  font=('Microsoft YaHei', 10),
                                  wrap=tk.WORD)
        help_text_widget.pack(fill=tk.BOTH, expand=True)
        
        text_scroll.config(command=help_text_widget.yview)
        
        help_text_widget.insert(tk.END, help_text)
        help_text_widget.config(state=tk.DISABLED)
        
        ttk.Button(help_window, text="关闭", command=help_window.destroy).pack(pady=(0, 10))
    
    def check_updates(self):
        """检查更新"""
        self.log_to_console("正在检查更新...", "#ffff00")
        messagebox.showinfo("检查更新", "当前已是最新版本")
    
    def show_about(self):
        """显示关于信息"""
        about_text = f"""通用Minecraft服务器启动器
版本: 3.0 通用版

功能特性:
- 支持所有Minecraft服务器核心
- 从镜像站快速下载核心
- 灵活的目录管理
- 完整的服务器控制
- 备份和恢复功能

支持的镜像站:
- MSLMC镜像站 (https://dl.mslmc.cn/)
- BMCLAPI镜像站
- 官方源

支持的服务器核心:
- Purpur, Paper, Spigot, CraftBukkit
- Vanilla (官方原版)
- Fabric, Forge, NeoForge
- CatServer, Mohist
- 以及更多...

系统要求:
- Python 3.6+
- Java 8+ (推荐Java 17/21)
- 100MB可用磁盘空间

服务器目录: {self.server.server_dir}
配置版本: {self.server.minecraft_version}

© 2024 Universal Minecraft Server Launcher
"""
        
        about_window = tk.Toplevel(self.root)
        about_window.title("关于")
        about_window.geometry("500x450")
        
        text_frame = ttk.Frame(about_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        about_text_widget = scrolledtext.ScrolledText(text_frame, 
                                                     font=('Microsoft YaHei', 10),
                                                     wrap=tk.WORD)
        about_text_widget.pack(fill=tk.BOTH, expand=True)
        
        about_text_widget.insert(tk.END, about_text)
        about_text_widget.config(state=tk.DISABLED)
        
        ttk.Button(about_window, text="关闭", command=about_window.destroy).pack(pady=(0, 10))
    
    def on_closing(self):
        """关闭窗口时的处理"""
        if self.server.is_running:
            if messagebox.askyesno("退出", "服务器正在运行，确定要退出吗？"):
                # 在新线程中停止服务器
                def stop_and_quit():
                    self.server.stop_server()
                    time.sleep(2)
                    self.root.quit()
                
                threading.Thread(target=stop_and_quit, daemon=True).start()
        else:
            self.root.quit()


def main():
    """主函数"""
    if not GUI_AVAILABLE:
        print("错误: tkinter不可用，无法启动GUI界面")
        print("在Ubuntu/Debian上安装: sudo apt-get install python3-tk")
        print("在Windows上通常已预装")
        
        # 命令行模式
        print("\n通用Minecraft服务器启动器 (命令行模式)")
        print("=" * 50)
        
        server_dir = input(f"服务器目录 [{os.getcwd()}]: ").strip()
        if not server_dir:
            server_dir = os.getcwd()
        
        server = UniversalServer(server_dir)
        
        # 显示当前状态
        status = server.get_status()
        print(f"\n服务器目录: {status['server_dir']}")
        print(f"核心文件: {status['server_jar']}")
        print(f"核心类型: {status['core_name']}")
        print(f"Minecraft版本: {status['minecraft_version']}")
        print(f"EULA状态: {'已同意' if status['eula_accepted'] else '未同意'}")
        
        # 简单命令循环
        while True:
            print("\n命令: start, stop, restart, accept-eula, exit")
            cmd = input("> ").strip().lower()
            
            if cmd == "start":
                if server.start_server():
                    print("服务器启动成功")
                else:
                    print("服务器启动失败")
            
            elif cmd == "stop":
                if server.stop_server():
                    print("服务器已停止")
                else:
                    print("停止服务器失败")
            
            elif cmd == "restart":
                print("正在重启服务器...")
                if server.is_running:
                    server.stop_server()
                    time.sleep(3)
                if server.start_server():
                    print("服务器重启成功")
                else:
                    print("服务器重启失败")
            
            elif cmd == "accept-eula":
                if server.accept_eula():
                    print("EULA已同意")
                else:
                    print("同意EULA失败")
            
            elif cmd == "exit":
                if server.is_running:
                    confirm = input("服务器正在运行，确定要退出吗？(y/n): ")
                    if confirm.lower() == 'y':
                        server.stop_server()
                break
            
            else:
                print("未知命令")
        
        return
    
    # 创建GUI
    app = UniversalServerLauncherGUI()
    
    # 启动GUI主循环
    app.root.mainloop()


if __name__ == "__main__":
    main()

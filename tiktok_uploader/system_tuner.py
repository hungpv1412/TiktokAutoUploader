import os
import platform
import subprocess
import sys
from datetime import datetime

def log_time(message):
    """Log message with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {message}")

class SystemNetworkTuner:
    """System-level network optimization utilities"""
    
    def __init__(self):
        self.os_type = platform.system().lower()
        self.requires_root = True
    
    def check_root_privileges(self):
        """Check if running with root/admin privileges"""
        if self.os_type == 'windows':
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            except:
                return False
        else:
            return os.geteuid() == 0
    
    def detect_tcp_congestion_algorithm(self):
        """Detect current TCP congestion control algorithm"""
        try:
            if self.os_type == 'linux':
                result = subprocess.run(['sysctl', 'net.ipv4.tcp_congestion_control'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    current = result.stdout.strip().split('=')[1].strip()
                    log_time(f"Current TCP congestion control: {current}")
                    return current
        except Exception as e:
            log_time(f"Failed to detect TCP congestion control: {e}")
        
        return None
    
    def is_bbr_available(self):
        """Check if BBR congestion control is available"""
        try:
            if self.os_type == 'linux':
                result = subprocess.run(['sysctl', 'net.ipv4.tcp_available_congestion_control'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    available = result.stdout.strip().split('=')[1].strip()
                    return 'bbr' in available
        except Exception as e:
            log_time(f"Failed to check BBR availability: {e}")
        
        return False
    
    def get_network_optimization_commands(self):
        """Get system network optimization commands"""
        commands = []
        
        if self.os_type == 'linux':
            # TCP buffer optimizations
            commands.extend([
                # Increase TCP buffer sizes
                'sysctl -w net.core.rmem_max=134217728',
                'sysctl -w net.core.wmem_max=134217728', 
                'sysctl -w net.ipv4.tcp_rmem="4096 87380 134217728"',
                'sysctl -w net.ipv4.tcp_wmem="4096 65536 134217728"',
                
                # Connection tracking optimizations
                'sysctl -w net.core.netdev_max_backlog=5000',
                'sysctl -w net.core.somaxconn=1024',
                
                # TCP optimizations
                'sysctl -w net.ipv4.tcp_window_scaling=1',
                'sysctl -w net.ipv4.tcp_timestamps=1',
                'sysctl -w net.ipv4.tcp_sack=1',
                'sysctl -w net.ipv4.tcp_no_metrics_save=1',
                
                # Reduce TCP timeouts for faster recovery
                'sysctl -w net.ipv4.tcp_syn_retries=3',
                'sysctl -w net.ipv4.tcp_synack_retries=3',
                'sysctl -w net.ipv4.tcp_retries2=8',
            ])
            
            # Enable BBR if available
            if self.is_bbr_available():
                commands.append('sysctl -w net.ipv4.tcp_congestion_control=bbr')
                commands.append('sysctl -w net.core.default_qdisc=fq')
        
        elif self.os_type == 'darwin':  # macOS
            commands.extend([
                # macOS network optimizations
                'sysctl -w kern.ipc.maxsockbuf=16777216',
                'sysctl -w net.inet.tcp.sendspace=1048576',
                'sysctl -w net.inet.tcp.recvspace=1048576',
            ])
        
        elif self.os_type == 'windows':
            # Windows network optimizations (requires admin)
            commands.extend([
                # TCP window auto-tuning
                'netsh int tcp set global autotuninglevel=normal',
                'netsh int tcp set global chimney=enabled',
                'netsh int tcp set global rss=enabled',
                'netsh int tcp set global netdma=enabled',
                
                # Increase TCP buffer sizes
                'netsh int tcp set global initialrto=1000',
                'netsh int tcp set global maxsynretransmissions=4',
            ])
        
        return commands
    
    def apply_optimizations(self, dry_run=False):
        """Apply system network optimizations"""
        log_time("Starting system network optimization")
        
        if not dry_run and not self.check_root_privileges():
            log_time("ERROR: Root/Administrator privileges required for system tuning")
            log_time("Run with 'sudo' on Linux/macOS or as Administrator on Windows")
            return False
        
        commands = self.get_network_optimization_commands()
        
        if dry_run:
            log_time("DRY RUN - Commands that would be executed:")
            for cmd in commands:
                print(f"  {cmd}")
            return True
        
        success_count = 0
        total_commands = len(commands)
        
        for cmd in commands:
            try:
                log_time(f"Executing: {cmd}")
                result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    success_count += 1
                    log_time(f"  ✓ Success")
                else:
                    log_time(f"  ✗ Failed: {result.stderr.strip()}")
                    
            except subprocess.TimeoutExpired:
                log_time(f"  ✗ Timeout")
            except Exception as e:
                log_time(f"  ✗ Error: {e}")
        
        log_time(f"Applied {success_count}/{total_commands} network optimizations")
        return success_count > 0
    
    def create_persistent_config(self):
        """Create persistent network configuration"""
        if self.os_type == 'linux':
            config_file = '/etc/sysctl.d/99-network-optimization.conf'
            config_content = """# Network optimization for video upload/download
# Generated by TikTok uploader

# TCP buffer sizes
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# Connection optimizations
net.core.netdev_max_backlog = 5000
net.core.somaxconn = 1024

# TCP optimizations
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_no_metrics_save = 1

# Faster recovery
net.ipv4.tcp_syn_retries = 3
net.ipv4.tcp_synack_retries = 3
net.ipv4.tcp_retries2 = 8

# BBR congestion control (if available)
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
"""
            
            try:
                with open(config_file, 'w') as f:
                    f.write(config_content)
                log_time(f"Created persistent config: {config_file}")
                log_time("Changes will persist after reboot")
                return True
            except Exception as e:
                log_time(f"Failed to create persistent config: {e}")
                return False
        
        else:
            log_time("Persistent configuration not implemented for this OS")
            return False
    
    def benchmark_current_settings(self):
        """Benchmark current network settings"""
        log_time("Benchmarking current network settings")
        
        current_tcp = self.detect_tcp_congestion_algorithm()
        bbr_available = self.is_bbr_available()
        
        settings = {
            'tcp_congestion_control': current_tcp,
            'bbr_available': bbr_available,
            'os_type': self.os_type,
            'root_access': self.check_root_privileges()
        }
        
        if self.os_type == 'linux':
            try:
                # Get current buffer sizes
                result = subprocess.run(['sysctl', 'net.core.rmem_max'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    settings['rmem_max'] = result.stdout.strip().split('=')[1].strip()
                
                result = subprocess.run(['sysctl', 'net.core.wmem_max'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    settings['wmem_max'] = result.stdout.strip().split('=')[1].strip()
                    
            except Exception:
                pass
        
        log_time("Current network settings:")
        for key, value in settings.items():
            log_time(f"  {key}: {value}")
        
        return settings
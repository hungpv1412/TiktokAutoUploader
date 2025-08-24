import time
import socket
import subprocess
import platform
import concurrent.futures
from datetime import datetime

def log_time(message):
    """Log message with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {message}")

class NetworkOptimizer:
    """Network optimization utilities for faster downloads and uploads"""
    
    DNS_SERVERS = {
        'cloudflare': ['1.1.1.1', '1.0.0.1'],
        'google': ['8.8.8.8', '8.8.4.4'], 
        'quad9': ['9.9.9.9', '149.112.112.112'],
        'opendns': ['208.67.222.222', '208.67.220.220']
    }
    
    def __init__(self):
        self.best_dns = None
        self.system_info = self._detect_system()
    
    def _detect_system(self):
        """Detect system information"""
        return {
            'os': platform.system().lower(),
            'version': platform.version(),
            'machine': platform.machine()
        }
    
    def ping_dns_server(self, dns_ip, timeout=3):
        """Ping a DNS server and return response time in ms"""
        try:
            if self.system_info['os'] == 'windows':
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), dns_ip]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), dns_ip]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, timeout=timeout + 1)
            end_time = time.time()
            
            if result.returncode == 0:
                return (end_time - start_time) * 1000  # Convert to ms
            else:
                return float('inf')  # Failed ping
                
        except (subprocess.TimeoutExpired, Exception):
            return float('inf')
    
    def dns_lookup_test(self, dns_server, test_domain='www.youtube.com', timeout=3):
        """Test DNS lookup speed for a specific server"""
        try:
            # Configure DNS resolver to use specific server
            original_dns = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            
            start_time = time.time()
            
            # Simple DNS lookup test
            socket.gethostbyname(test_domain)
            
            end_time = time.time()
            socket.setdefaulttimeout(original_dns)
            
            return (end_time - start_time) * 1000  # Convert to ms
            
        except (socket.gaierror, socket.timeout, Exception):
            socket.setdefaulttimeout(original_dns)
            return float('inf')
    
    def benchmark_dns_servers(self, test_domains=None):
        """Benchmark all DNS servers and return the fastest"""
        if test_domains is None:
            test_domains = ['www.youtube.com', 'www.tiktok.com', 'www.google.com']
        
        log_time("Starting DNS server benchmark...")
        results = {}
        
        for name, servers in self.DNS_SERVERS.items():
            log_time(f"Testing {name} DNS ({servers[0]})")
            
            # Test ping response
            ping_time = self.ping_dns_server(servers[0])
            
            # Test DNS lookup speed
            lookup_times = []
            for domain in test_domains:
                lookup_time = self.dns_lookup_test(servers[0], domain)
                if lookup_time != float('inf'):
                    lookup_times.append(lookup_time)
            
            avg_lookup = sum(lookup_times) / len(lookup_times) if lookup_times else float('inf')
            
            results[name] = {
                'servers': servers,
                'ping_time': ping_time,
                'avg_lookup_time': avg_lookup,
                'total_score': ping_time + avg_lookup
            }
            
            log_time(f"{name}: ping={ping_time:.1f}ms, lookup={avg_lookup:.1f}ms")
        
        # Find the fastest DNS server
        best_dns = min(results.items(), key=lambda x: x[1]['total_score'])
        
        if best_dns[1]['total_score'] != float('inf'):
            log_time(f"Best DNS: {best_dns[0]} (total: {best_dns[1]['total_score']:.1f}ms)")
            self.best_dns = best_dns[0]
            return best_dns[0], best_dns[1]['servers']
        else:
            log_time("No responsive DNS servers found, using system default")
            return None, None
    
    def get_dns_servers(self, dns_choice='auto'):
        """Get DNS servers based on user choice"""
        if dns_choice == 'auto':
            # Run benchmark and return best
            best_name, best_servers = self.benchmark_dns_servers()
            return best_servers
        elif dns_choice in self.DNS_SERVERS:
            return self.DNS_SERVERS[dns_choice]
        else:
            log_time(f"Unknown DNS choice: {dns_choice}, using auto")
            return self.get_dns_servers('auto')
    
    def detect_bandwidth(self, test_url="http://www.google.com", timeout=10):
        """Detect approximate bandwidth by downloading a test file"""
        try:
            import requests
            
            log_time("Detecting bandwidth...")
            start_time = time.time()
            
            response = requests.get(test_url, timeout=timeout, stream=True)
            data_downloaded = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                data_downloaded += len(chunk)
                if time.time() - start_time > 5:  # Test for 5 seconds max
                    break
            
            elapsed_time = time.time() - start_time
            bandwidth_bps = data_downloaded / elapsed_time
            bandwidth_mbps = (bandwidth_bps * 8) / (1024 * 1024)  # Convert to Mbps
            
            log_time(f"Detected bandwidth: {bandwidth_mbps:.1f} Mbps")
            return bandwidth_mbps
            
        except Exception as e:
            log_time(f"Bandwidth detection failed: {e}")
            return 10.0  # Default to 10 Mbps assumption
    
    def get_optimal_concurrent_connections(self, bandwidth_mbps=None):
        """Calculate optimal number of concurrent connections based on bandwidth"""
        if bandwidth_mbps is None:
            bandwidth_mbps = self.detect_bandwidth()
        
        # Rough heuristic: 1 connection per 10 Mbps, minimum 2, maximum 16
        connections = max(2, min(16, int(bandwidth_mbps / 10) + 2))
        log_time(f"Optimal concurrent connections: {connections}")
        return connections
    
    def benchmark_network(self):
        """Run complete network benchmark"""
        log_time("=== Network Benchmark Starting ===")
        
        # DNS benchmark
        self.benchmark_dns_servers()
        
        # Bandwidth test
        bandwidth = self.detect_bandwidth()
        connections = self.get_optimal_concurrent_connections(bandwidth)
        
        log_time("=== Network Benchmark Complete ===")
        
        return {
            'best_dns': self.best_dns,
            'bandwidth_mbps': bandwidth,
            'optimal_connections': connections
        }
    
    def get_retry_config(self, bandwidth_mbps=None):
        """Get smart retry configuration based on bandwidth"""
        if bandwidth_mbps is None:
            bandwidth_mbps = 10.0  # Default assumption
        
        if bandwidth_mbps < 5:
            # Slow connection
            return {
                'max_retries': 5,
                'backoff_factor': 2.0,
                'timeout': 30,
                'chunk_size': 1024 * 512  # 512KB chunks
            }
        elif bandwidth_mbps < 25:
            # Medium connection
            return {
                'max_retries': 3,
                'backoff_factor': 1.5,
                'timeout': 20,
                'chunk_size': 1024 * 1024 * 2  # 2MB chunks
            }
        else:
            # Fast connection
            return {
                'max_retries': 2,
                'backoff_factor': 1.0,
                'timeout': 15,
                'chunk_size': 1024 * 1024 * 5  # 5MB chunks
            }
    
    def smart_retry(self, func, *args, max_retries=3, backoff_factor=1.5, **kwargs):
        """Execute function with smart retry logic"""
        import time
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                wait_time = backoff_factor ** attempt
                log_time(f"Attempt {attempt + 1} failed: {e}, retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
        
        return None
    
    def create_optimized_session(self):
        """Create an optimized requests session with connection pooling"""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            backoff_factor=1.5
        )
        
        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry_strategy,
            pool_block=False
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set optimized headers
        session.headers.update({
            'Connection': 'keep-alive',
            'Keep-Alive': 'timeout=30, max=100',
        })
        
        log_time("Created optimized HTTP session with connection pooling")
        return session
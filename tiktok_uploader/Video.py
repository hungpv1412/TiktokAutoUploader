from .Config import Config

from moviepy.editor import *
from moviepy.editor import VideoFileClip, AudioFileClip
import yt_dlp
import time, os
import re
from datetime import datetime

class Video:
    def __init__(self, source_ref, video_text, skip_moviepy=False, network_optimizer=None, dns_choice='auto'):
        self.config = Config.get()
        self.source_ref = source_ref
        self.video_text = video_text
        self.clip = None
        self.skip_moviepy = skip_moviepy or not video_text  # Skip if no text overlay needed
        self.network_optimizer = network_optimizer
        self.dns_choice = dns_choice

        self.source_ref = self.downloadIfYoutubeURL()
        # Wait until self.source_ref is found in the file system.
        while not os.path.isfile(self.source_ref):
            time.sleep(1)

        # Only load MoviePy if we need to process the video
        if not self.skip_moviepy:
            try:
                self.clip = VideoFileClip(self.source_ref)
            except Exception as e:
                print(f"Error loading video file: {e}")
                raise
        else:
            print("Skipping MoviePy processing for faster upload...")
    
    def __del__(self):
        """Cleanup method to properly close video clip resources"""
        if hasattr(self, 'clip') and self.clip is not None:
            try:
                self.clip.close()
            except:
                pass
    
    def close(self):
        """Explicitly close video clip resources"""
        if hasattr(self, 'clip') and self.clip is not None:
            try:
                self.clip.close()
                self.clip = None
            except:
                pass

    def log_time(self, message):
        """Log message with timestamp"""
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {message}")

    def crop(self, start_time, end_time, saveFile=False):
        if end_time > self.clip.duration:
            end_time = self.clip.duration
        save_path = os.path.join(os.getcwd(), self.config.videos_dir, "processed") + ".mp4"
        self.clip = self.clip.subclip(t_start=start_time, t_end=end_time)
        if saveFile:
            self.clip.write_videofile(save_path)
        return self.clip

    def createVideo(self):
        self.clip = self.clip.resize(width=1080)
        base_clip = ColorClip(size=(1080, 1920), color=[10, 10, 10], duration=self.clip.duration)
        bottom_meme_pos = 960 + (((1080 / self.clip.size[0]) * (self.clip.size[1])) / 2) + -20
        if self.video_text:
            try:
                meme_overlay = TextClip(txt=self.video_text, bg_color=self.config.imagemagick_text_background_color, color=self.config.imagemagick_text_foreground_color, size=(900, None), kerning=-1,
                            method="caption", font=self.config.imagemagick_font, fontsize=self.config.imagemagick_font_size, align="center")
            except OSError as e:
                print("Please make sure that you have ImageMagick is not installed on your computer, or (for Windows users) that you didn't specify the path to the ImageMagick binary in file conf.py, or that the path you specified is incorrect")
                print("https://imagemagick.org/script/download.php#windows")
                print(e)
                exit()
            meme_overlay = meme_overlay.set_duration(self.clip.duration)
            self.clip = CompositeVideoClip([base_clip, self.clip.set_position(("center", "center")),
                                            meme_overlay.set_position(("center", bottom_meme_pos))])
            # Continue normal flow.

        dir = os.path.join(self.config.post_processing_video_path, "post-processed")+".mp4"
        self.clip.write_videofile(dir, fps=24)
        return dir, self.clip

    def is_valid_file_format(self):
        if not self.source_ref.endswith('.mp4') and not self.source_ref.endswith('.webm'):
            exit(f"File: {self.source_ref} has wrong file extension. Must be .mp4 or .webm.")

    def extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
            r'(?:shorts/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_youtube_video(self, max_res=True):
        start_time = time.time()
        self.log_time("Starting YouTube video download process")
        
        url = self.source_ref
        video_dir = os.path.join(os.getcwd(), Config.get().videos_dir)
        
        # Extract video ID for filename
        self.log_time("Extracting video ID from URL")
        video_id = self.extract_video_id(url)
        if not video_id:
            video_id = 'video'  # fallback
        
        output_path = os.path.join(video_dir, f"{video_id}.mp4")
        self.log_time(f"Video ID: {video_id}")
        
        # Delete existing file to ensure fresh download
        if os.path.exists(output_path):
            self.log_time("Removing existing file")
            os.remove(output_path)
        
        # Use yt-dlp native download only
        self.log_time("Starting yt-dlp native download")
        download_start = time.time()
        
        # Base yt-dlp options
        ydl_opts = {
            'format': '18',  # 360p MP4
            'outtmpl': os.path.join(video_dir, '%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
            'no_playlist': True,
        }
        
        # Apply network optimizations
        if self.network_optimizer:
            # Get optimal settings based on bandwidth
            bandwidth = getattr(self.network_optimizer, 'bandwidth_mbps', None)
            if bandwidth is None:
                bandwidth = self.network_optimizer.detect_bandwidth()
            
            optimal_connections = self.network_optimizer.get_optimal_concurrent_connections(bandwidth)
            retry_config = self.network_optimizer.get_retry_config(bandwidth)
            
            self.log_time(f"Network optimization: {bandwidth:.1f}Mbps, {optimal_connections} connections")
            
            # Configure yt-dlp with optimal settings
            ydl_opts.update({
                'concurrent_fragment_downloads': optimal_connections,
                'fragment_retries': retry_config['max_retries'],
                'socket_timeout': retry_config['timeout'],
            })
        
        # Apply DNS optimization if network optimizer is available
        if self.network_optimizer:
            self.log_time(f"Applying DNS optimization: {self.dns_choice}")
            dns_servers = self.network_optimizer.get_dns_servers(self.dns_choice)
            if dns_servers:
                self.log_time(f"Using DNS servers: {dns_servers}")
                # Note: yt-dlp doesn't directly support DNS server configuration
                # But the system DNS resolver will be used, which we can configure
                # This is more of a system-level optimization
        elif self.dns_choice != 'auto':
            # Import NetworkOptimizer for one-time DNS setup
            from .network_utils import NetworkOptimizer
            temp_optimizer = NetworkOptimizer()
            dns_servers = temp_optimizer.get_dns_servers(self.dns_choice)
            self.log_time(f"Using DNS servers: {dns_servers}")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # Check if file was created
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    self.log_time(f"yt-dlp download complete in {time.time()-download_start:.1f}s ({file_size/1024/1024:.1f}MB)")
                    self.log_time(f"Total download time: {time.time()-start_time:.1f}s")
                    return output_path
                else:
                    # Try to find the file with any extension
                    for file in os.listdir(video_dir):
                        if video_id in file and file.endswith('.mp4'):
                            actual_path = os.path.join(video_dir, file)
                            os.rename(actual_path, output_path)
                            file_size = os.path.getsize(output_path)
                            self.log_time(f"yt-dlp download complete in {time.time()-download_start:.1f}s ({file_size/1024/1024:.1f}MB)")
                            self.log_time(f"Total download time: {time.time()-start_time:.1f}s")
                            return output_path
                        
        except Exception as e:
            self.log_time(f"yt-dlp download failed: {e}")
        
        return None

    _YT_DOMAINS = [
        "http://youtu.be/", "https://youtu.be/", "http://youtube.com/", "https://youtube.com/",
        "https://m.youtube.com/", "http://www.youtube.com/", "https://www.youtube.com/"
    ]
    
    def downloadIfYoutubeURL(self):
            if any(ext in self.source_ref for ext in Video._YT_DOMAINS):
                print("Detected Youtube Video...")
                video_dir = self.get_youtube_video()
                return video_dir
            else:
                return self.source_ref
import argparse
from tiktok_uploader import tiktok, Video
from tiktok_uploader.basics import eprint
from tiktok_uploader.Config import Config
from tiktok_uploader.network_utils import NetworkOptimizer
from tiktok_uploader.system_tuner import SystemNetworkTuner
import sys, os
import time
from datetime import datetime

if __name__ == "__main__":
    _ = Config.load("./config.txt")
    # print(Config.get().cookies_dir)
    parser = argparse.ArgumentParser(description="TikTokAutoUpload CLI, scheduled and immediate uploads")
    subparsers = parser.add_subparsers(dest="subcommand")

    # Login subcommand.
    login_parser = subparsers.add_parser("login", help="Login into TikTok to extract the session id (stored locally)")
    login_parser.add_argument("-n", "--name", help="Name to save cookie as", required=True)

    # Upload subcommand.
    upload_parser = subparsers.add_parser("upload", help="Upload video on TikTok")
    upload_parser.add_argument("-u", "--users", help="Enter cookie name from login", required=True)
    upload_parser.add_argument("-v", "--video", help="Path to video file")
    upload_parser.add_argument("-yt", "--youtube", help="Enter Youtube URL")
    upload_parser.add_argument("-t", "--title", help="Title of the video", required=True)
    upload_parser.add_argument("-sc", "--schedule", type=int, default=0, help="Schedule time in seconds")
    upload_parser.add_argument("-ct", "--comment", type=int, default=1, choices=[0, 1])
    upload_parser.add_argument("-d", "--duet", type=int, default=0, choices=[0, 1])
    upload_parser.add_argument("-st", "--stitch", type=int, default=0, choices=[0, 1])
    upload_parser.add_argument("-vi", "--visibility", type=int, default=0, help="Visibility type: 0 for public, 1 for private")
    upload_parser.add_argument("-bo", "--brandorganic", type=int, default=0)
    upload_parser.add_argument("-bc", "--brandcontent", type=int, default=0)
    upload_parser.add_argument("-ai", "--ailabel", type=int, default=0)
    upload_parser.add_argument("-p", "--proxy", default="")
    upload_parser.add_argument("--fast", action='store_true', help="Enable fast mode - skip MoviePy processing when possible")
    upload_parser.add_argument("--dns", choices=['auto', 'cloudflare', 'google', 'quad9', 'opendns'], default='auto', help="DNS server to use for faster lookups")
    upload_parser.add_argument("--benchmark", action='store_true', help="Run network benchmark and show optimization recommendations")
    upload_parser.add_argument("--fast-net", action='store_true', help="Enable all network optimizations")
    upload_parser.add_argument("--tune-system", action='store_true', help="Apply system-level network tuning (requires sudo/admin)")
    upload_parser.add_argument("--tune-dry-run", action='store_true', help="Show system tuning commands without executing them")

    # Show cookies
    show_parser = subparsers.add_parser("show", help="Show users and videos available for system.")
    show_parser.add_argument("-u", "--users", action='store_true', help="Shows all available cookie names")
    show_parser.add_argument("-v", "--videos",  action='store_true', help="Shows all available videos")

    # Parse the command-line arguments
    args = parser.parse_args()

    if args.subcommand == "login":
        if not hasattr(args, 'name') or args.name is None:
            parser.error("The 'name' argument is required for the 'login' subcommand.")
        # Name of file to save the session id.
        login_name = args.name
        # Name of file to save the session id.
        tiktok.login(login_name)

    elif args.subcommand == "upload":
        # Start timing the entire upload process
        total_start = time.time()
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] === Starting upload process ===")
        
        # Obtain session id from the cookie name.
        if not hasattr(args, 'users') or args.users is None:
            parser.error("The 'cookie' argument is required for the 'upload' subcommand.")
        
        # Check if source exists,
        if args.video is None and args.youtube is None:
            eprint("No source provided. Use -v or -yt to provide video source.")
            sys.exit(1)
        if args.video and args.youtube:
            eprint("Both -v and -yt flags cannot be used together.")
            sys.exit(1)

        # Handle network optimization flags
        network_optimizer = None
        
        # System tuning
        if getattr(args, 'tune_system', False) or getattr(args, 'tune_dry_run', False):
            system_tuner = SystemNetworkTuner()
            dry_run = getattr(args, 'tune_dry_run', False)
            system_tuner.apply_optimizations(dry_run=dry_run)
            if not dry_run:
                system_tuner.create_persistent_config()
            sys.exit(0)
        
        # Network benchmark
        if getattr(args, 'benchmark', False):
            network_optimizer = NetworkOptimizer()
            network_optimizer.benchmark_network()
            # Also show system tuning recommendations
            system_tuner = SystemNetworkTuner()
            system_tuner.benchmark_current_settings()
            sys.exit(0)
        
        # Initialize network optimizer if DNS or fast-net options are used
        if getattr(args, 'dns', 'auto') != 'auto' or getattr(args, 'fast_net', False):
            network_optimizer = NetworkOptimizer()
            
            # If fast-net is enabled, run benchmark to get optimal settings
            if getattr(args, 'fast_net', False):
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Fast network mode enabled - optimizing...")
                network_optimizer.benchmark_network()

        if args.youtube:
            # Pass fast mode flag to Video class
            skip_moviepy = getattr(args, 'fast', False)
            video_obj = Video(args.youtube, args.title, skip_moviepy=skip_moviepy, network_optimizer=network_optimizer, dns_choice=getattr(args, 'dns', 'auto'))
            # Only validate format if we're using MoviePy
            if not skip_moviepy:
                video_obj.is_valid_file_format()
            video = video_obj.source_ref
            args.video = video
            # Properly close the video object to avoid cleanup exceptions
            video_obj.close()
        else:
            if not os.path.exists(os.path.join(os.getcwd(), Config.get().videos_dir, args.video)) and args.video:
                print("[-] Video does not exist")
                print("Video Names Available: ")
                video_dir = os.path.join(os.getcwd(), Config.get().videos_dir)
                for name in os.listdir(video_dir):
                    print(f'[-] {name}')
                sys.exit(1)

        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Starting TikTok upload")
        upload_start = time.time()
        tiktok.upload_video(args.users, args.video,  args.title, args.schedule, args.comment, args.duet, args.stitch, args.visibility, args.brandorganic, args.brandcontent, args.ailabel, args.proxy, network_optimizer=network_optimizer)
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Upload completed in {time.time()-upload_start:.1f}s")
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] === Total time: {time.time()-total_start:.1f}s ===")

    elif args.subcommand == "show":
        # if flag is c then show cookie names
        if args.users:
            print("User Names logged in: ")
            cookie_dir = os.path.join(os.getcwd(), Config.get().cookies_dir)
            for name in os.listdir(cookie_dir):
                if name.startswith("tiktok_session-"):
                    print(f'[-] {name.split("tiktok_session-")[1]}')

        # if flag is v then show video names
        if args.videos:
            print("Video Names: ")
            video_dir = os.path.join(os.getcwd(), Config.get().videos_dir)
            for name in os.listdir(video_dir):
                print(f'[-] {name}')
        elif not args.users and not args.videos:
            print("No flag provided. Use -c (show all cookies) or -v (show all videos).")

    else:
        eprint("Invalid subcommand. Use 'login' or 'upload' or 'show'.")



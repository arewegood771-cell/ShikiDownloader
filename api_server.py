from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import json
from datetime import datetime

app = Flask(__name__)
# Enable CORS for all routes with specific configuration
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Temporary directory for downloads
TEMP_DIR = tempfile.gettempdir()


def get_video_info(url):
    """Get video information without downloading"""
    ydl_opts = {
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # Get available formats
        video_formats = []
        audio_formats = []
        seen_video = set()
        seen_audio = set()
        
        # Add "best" video option first
        video_formats.append({
            'format_id': 'best',
            'ext': 'mp4',
            'quality': 'Best Video',
            'filesize': None,
            'width': None,
            'height': None,
            'fps': None,
            'vcodec': None,
            'acodec': None,
            'has_video': True,
            'has_audio': True,
            'type': 'video'
        })
        
        # Add "best audio" option
        audio_formats.append({
            'format_id': 'bestaudio',
            'ext': 'm4a',
            'quality': 'Best Audio',
            'filesize': None,
            'abr': None,
            'has_video': False,
            'has_audio': True,
            'type': 'audio'
        })
        
        if 'formats' in info:
            for f in info['formats']:
                # Video formats
                if f.get('vcodec') != 'none':
                    height = f.get('height', 0)
                    width = f.get('width', 0)
                    ext = f.get('ext', 'mp4')
                    fps = f.get('fps', 0)
                    has_audio = f.get('acodec') != 'none'
                    
                    # Create quality label
                    if height:
                        quality = f"{height}p"
                        if fps and fps > 30:
                            quality += f" {int(fps)}fps"
                        if not has_audio:
                            quality += " (no audio)"
                    else:
                        quality = f.get('format_note', 'Unknown Quality')
                    
                    # Create unique key
                    format_key = f"{height}_{ext}_{has_audio}"
                    
                    # Skip duplicates
                    if format_key in seen_video:
                        continue
                        
                    seen_video.add(format_key)
                    
                    # Only add formats with both video and audio, or high quality video
                    if has_audio or height >= 720:
                        video_formats.append({
                            'format_id': f.get('format_id'),
                            'ext': ext,
                            'quality': quality,
                            'filesize': f.get('filesize'),
                            'width': width,
                            'height': height,
                            'fps': fps,
                            'vcodec': f.get('vcodec'),
                            'acodec': f.get('acodec'),
                            'has_video': True,
                            'has_audio': has_audio,
                            'type': 'video'
                        })
                
                # Audio-only formats
                elif f.get('acodec') != 'none':
                    abr = f.get('abr', 0)
                    ext = f.get('ext', 'm4a')
                    
                    # Create quality label
                    if abr:
                        quality = f"{int(abr)}kbps"
                    else:
                        quality = f.get('format_note', 'Audio')
                    
                    # Create unique key
                    format_key = f"{abr}_{ext}"
                    
                    if format_key in seen_audio:
                        continue
                    
                    seen_audio.add(format_key)
                    
                    audio_formats.append({
                        'format_id': f.get('format_id'),
                        'ext': ext,
                        'quality': quality,
                        'filesize': f.get('filesize'),
                        'abr': abr,
                        'has_video': False,
                        'has_audio': True,
                        'type': 'audio'
                    })

        # Sort video formats
        video_formats.sort(key=lambda x: (
            0 if x['format_id'] == 'best' else 1,
            -1 if x.get('has_audio') else 1,
            -(x.get('height') or 0),
        ))
        
        # Sort audio formats by bitrate
        audio_formats.sort(key=lambda x: (
            0 if x['format_id'] == 'bestaudio' else 1,
            -(x.get('abr') or 0),
        ))
        
        # Combine and limit
        video_formats = video_formats[:8]
        audio_formats = audio_formats[:5]
        all_formats = video_formats + audio_formats

        return {
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'uploader': info.get('uploader') or info.get('channel'),
            'description': info.get('description'),
            'formats': all_formats,
            'url': url
        }


def download_video(url, format_id=None):
    """Download video with specified format"""
    output_template = os.path.join(
        TEMP_DIR, f'video_{datetime.now().timestamp()}.%(ext)s')

    # Enhanced yt-dlp options with fallbacks
    ydl_opts = {
        'format': format_id if format_id else 'best',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': False,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'retries': 3,
        'fragment_retries': 3,
        'http_chunk_size': 10485760,  # 10MB chunks
        # Add headers to avoid blocking
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Verify file exists
            if not os.path.exists(filename):
                raise Exception("Download completed but file not found")
            
            return filename
    except Exception as e:
        # Try fallback with simpler format
        print(f"First attempt failed: {str(e)}, trying fallback...")
        ydl_opts['format'] = 'best'
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename
        except Exception as fallback_error:
            raise Exception(f"Download failed: {str(fallback_error)}")


@app.route('/api/video-info', methods=['POST'])
def video_info():
    """Endpoint to get video information"""
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        info = get_video_info(url)
        return jsonify(info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download', methods=['POST'])
def download():
    """Endpoint to download video"""
    try:
        data = request.get_json()
        url = data.get('url')
        format_id = data.get('format_id')

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        print(f"Download request - URL: {url}, Format: {format_id}")
        
        filepath = download_video(url, format_id)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File download failed - file not found'}), 500

        print(f"Download successful - File: {filepath}, Size: {os.path.getsize(filepath)} bytes")

        # Send file and delete after sending
        response = send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath),
            mimetype='video/mp4'
        )

        # Schedule file deletion after sending
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"Cleanup - Deleted: {filepath}")
            except Exception as e:
                print(f"Cleanup error: {str(e)}")

        return response

    except Exception as e:
        error_msg = str(e)
        print(f"Download error: {error_msg}")
        
        # Return more specific error messages
        if 'format' in error_msg.lower():
            return jsonify({'error': 'Format tidak tersedia. Coba pilih format lain.'}), 400
        elif 'private' in error_msg.lower() or 'members-only' in error_msg.lower():
            return jsonify({'error': 'Video private atau members-only. Tidak bisa didownload.'}), 403
        elif 'not available' in error_msg.lower():
            return jsonify({'error': 'Video tidak tersedia di region ini atau sudah dihapus.'}), 404
        elif 'copyright' in error_msg.lower():
            return jsonify({'error': 'Video terkena copyright. Tidak bisa didownload.'}), 403
        else:
            return jsonify({'error': f'Download gagal: {error_msg}'}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Video Downloader API is running'})


@app.route('/')
def index():
    """Root endpoint - API information"""
    return jsonify({
        'name': 'Rikkiu Video Downloader API',
        'version': '2.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'video_info': '/api/video-info (POST)',
            'download': '/api/download (POST)'
        },
        'message': 'API is working! Use the endpoints above.'
    })


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': {
            'health': '/api/health (GET)',
            'video_info': '/api/video-info (POST)',
            'download': '/api/download (POST)'
        }
    }), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500


if __name__ == '__main__':
    print("=" * 50)
    print("Video Downloader API Server")
    print("=" * 50)
    print("Server starting...")
    print("=" * 50)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

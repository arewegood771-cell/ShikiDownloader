from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Temporary directory for downloads
TEMP_DIR = tempfile.gettempdir()


def get_video_info(url):
    """Get video information without downloading"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # Get available formats
        formats = []
        if 'formats' in info:
            for f in info['formats']:
                # Only include formats with video
                if f.get('vcodec') != 'none':
                    formats.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'quality': f.get('format_note') or f.get('quality'),
                        'filesize': f.get('filesize'),
                        'width': f.get('width'),
                        'height': f.get('height'),
                        'fps': f.get('fps'),
                    })

        # Sort formats by quality (height)
        formats.sort(key=lambda x: (x.get('height') or 0), reverse=True)

        return {
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'uploader': info.get('uploader') or info.get('channel'),
            'description': info.get('description'),
            'formats': formats[:10],  # Limit to top 10 formats
            'url': url
        }


def download_video(url, format_id=None):
    """Download video with specified format"""
    output_template = os.path.join(
        TEMP_DIR, f'video_{datetime.now().timestamp()}.%(ext)s')

    ydl_opts = {
        'format': format_id if format_id else 'best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename


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

        filepath = download_video(url, format_id)

        # Send file and delete after sending
        response = send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath)
        )

        # Schedule file deletion after sending
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Video Downloader API is running'})


@app.route('/')
def serve_frontend():
    """Serve the HTML frontend"""
    return send_from_directory('.', 'video-downloader.html')


if __name__ == '__main__':
    print("=" * 50)
    print("Video Downloader API Server")
    print("=" * 50)
    print("Server starting...")
    print("=" * 50)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

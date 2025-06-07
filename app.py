from flask import Flask, request, send_file, jsonify, render_template_string
import yt_dlp
import os
import subprocess
import uuid
import re

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Video Downloader (YouTube, Facebook, Instagram)</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 50px auto;
            max-width: 600px;
            text-align: center;
        }
        input, button {
            padding: 10px;
            margin: 10px 5px;
            width: 80%;
            font-size: 1em;
        }
        button {
            width: 25%;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>Video Downloader</h1>
    <p>Supports YouTube, Facebook, and Instagram URLs</p>
    <input type="text" id="videoUrl" placeholder="Enter YouTube, Facebook, or Instagram video URL" />
    <br/>
    <button onclick="download('mp3')">Download MP3</button>
    <button onclick="download('wav')">Download WAV</button>
    <button onclick="download('mp4')">Download MP4</button>

    <script>
        function download(format) {
            const url = document.getElementById('videoUrl').value.trim();
            if (!url) {
                alert('Please enter a video URL.');
                return;
            }
            const apiUrl = `/download?url=${encodeURIComponent(url)}&format=${format}`;
            window.location.href = apiUrl;
        }
    </script>
</body>
</html>
"""

VALID_URL_PATTERN = re.compile(
    r'^(https?://)?(www\.)?'
    r'(youtube\.com/watch\?v=|youtu\.be/|facebook\.com/.+/videos/.+|instagram\.com/p/.+)'
)

def is_valid_url(url):
    return VALID_URL_PATTERN.search(url) is not None

def download_youtube(url, format):
    unique_folder = os.path.join(DOWNLOAD_DIR, str(uuid.uuid4()))
    os.makedirs(unique_folder, exist_ok=True)

    outtmpl = os.path.join(unique_folder, '%(title)s.%(ext)s')

    ydl_opts = {
        'outtmpl': outtmpl,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    if format in ['mp3', 'wav']:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif format == 'mp4':
        ydl_opts['format'] = 'bestvideo+bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        files = os.listdir(unique_folder)

        if format == 'wav':
            mp3_file = next((f for f in files if f.endswith('.mp3')), None)
            if not mp3_file:
                return None

            mp3_path = os.path.join(unique_folder, mp3_file)
            wav_path = mp3_path.rsplit('.', 1)[0] + '.wav'

            subprocess.run(['ffmpeg', '-y', '-i', mp3_path, wav_path], check=True)
            os.remove(mp3_path)

            return wav_path
        else:
            ext = 'mp3' if format == 'mp3' else 'mp4'
            file_name = next((f for f in files if f.endswith(ext)), None)
            if not file_name:
                return None
            return os.path.join(unique_folder, file_name)

    except Exception as e:
        print(f"Download error: {e}")
        return None

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/download')
def download():
    url = request.args.get('url')
    format = request.args.get('format', 'mp4').lower()

    if not url:
        return jsonify({'error': 'Missing URL parameter'}), 400

    if format not in ['mp3', 'wav', 'mp4']:
        return jsonify({'error': 'Invalid format. Choose mp3, wav, or mp4.'}), 400

    if not is_valid_url(url):
        return jsonify({'error': 'URL not supported. Use YouTube, Facebook, or Instagram video URLs.'}), 400

    file_path = download_youtube(url, format)
    if not file_path or not os.path.isfile(file_path):
        return jsonify({'error': 'Download failed or file not found.'}), 500

    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

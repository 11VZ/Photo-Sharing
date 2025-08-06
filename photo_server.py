import os
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import cgi
import mimetypes
import urllib.parse
import subprocess
import socket
import qrcode
from PIL import Image

UPLOAD_DIR = os.path.expanduser("~/UploadsFromPhone")
HOST = "0.0.0.0"
PORT = 8000
PASSWORD = None

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def convert_video_to_h264(filepath):
    base, ext = os.path.splitext(filepath)
    new_path = base + "_converted.mp4"
    print(f"Converting {filepath} to H.264 MP4...")
    subprocess.run([
        "ffmpeg", "-i", filepath,
        "-vcodec", "libx264", "-acodec", "aac",
        "-strict", "-2", "-y", new_path
    ])
    os.remove(filepath)
    return new_path

class MediaHandler(BaseHTTPRequestHandler):
    def send_html(self, html):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        if self.path.startswith(f"/{os.path.basename(UPLOAD_DIR)}"):
            return self.serve_file()

        if PASSWORD and f"?pass={PASSWORD}" not in self.path:
            self.send_html("<h1>Unauthorized</h1><p>Access denied.</p>")
            return

        files_html = ""
        for fname in sorted(os.listdir(UPLOAD_DIR), reverse=True):
            fpath = os.path.join(UPLOAD_DIR, fname)
            url_path = f"/{os.path.basename(UPLOAD_DIR)}/{urllib.parse.quote(fname)}"
            ext = os.path.splitext(fname)[1].lower()
            if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                files_html += f'<img src="{url_path}" width="200" style="margin:10px;">'
            elif ext in [".mp4", ".webm", ".mov"]:
                files_html += f'<video src="{url_path}" width="200" style="margin:10px;" controls></video>'

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Phone Media Upload</title>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: 'Segoe UI', sans-serif;
                    background-color: #121212;
                    color: #f0f0f0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }}
                h2 {{
                    margin-top: 20px;
                    font-size: 1.8em;
                    color: #ffffff;
                }}
                form {{
                    background-color: #1f1f1f;
                    padding: 20px;
                    border-radius: 12px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
                    width: 90%;
                    max-width: 400px;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                input[type="file"] {{
                    background-color: #2a2a2a;
                    color: #f0f0f0;
                    border: none;
                    padding: 10px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    width: 100%;
                }}
                input[type="submit"] {{
                    background-color: #03dac5;
                    color: #000;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 1em;
                    cursor: pointer;
                    width: 100%;
                }}
                input[type="submit"]:hover {{
                    background-color: #00c4b4;
                }}
                .gallery {{
                    width: 100%;
                    max-width: 800px;
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: center;
                    gap: 10px;
                    padding: 10px;
                }}
                img, video {{
                    border-radius: 10px;
                    max-width: 45%;
                    height: auto;
                }}
                @media (max-width: 600px) {{
                    img, video {{
                        max-width: 100%;
                    }}
                }}
            </style>
        </head>
        <body>
            <h2>📤 Upload from Phone</h2>
            <form action="/" enctype="multipart/form-data" method="post">
                <input type="file" name="file" accept="image/*,video/*" multiple required><br>
                <input type="submit" value="Upload">
            </form>
            <div class="gallery">
                {files_html or "<p style='text-align:center;width:100%;'>No uploads yet.</p>"}
            </div>
        </body>
        </html>
        """

        self.send_html(html)

    def serve_file(self):
        path = urllib.parse.unquote(self.path.lstrip("/"))
        full_path = os.path.join(os.getcwd(), path)
        if not os.path.isfile(full_path):
            self.send_error(404, "File not found")
            return

        mime_type, _ = mimetypes.guess_type(full_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-type", mime_type)
        self.send_header("Content-Length", str(os.path.getsize(full_path)))
        self.end_headers()
        with open(full_path, "rb") as f:
            self.wfile.write(f.read())

    def do_POST(self):
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_error(400, "Expected multipart/form-data")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type
            }
        )

        files_uploaded = 0
        files = form["file"]
        if not isinstance(files, list):
            files = [files]

        for file_item in files:
            if file_item.filename:
                raw_filename = os.path.basename(file_item.filename)
                filename = raw_filename
                save_path = os.path.join(UPLOAD_DIR, filename)

                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(save_path):
                    filename = f"{base}_{counter}{ext}"
                    save_path = os.path.join(UPLOAD_DIR, filename)
                    counter += 1

                with open(save_path, "wb") as f:
                    f.write(file_item.file.read())
                files_uploaded += 1

                if ext.lower() in [".mov", ".webm"]:
                    try:
                        save_path = convert_video_to_h264(save_path)
                    except Exception as e:
                        print(f"Conversion failed: {e}")

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    ip = get_local_ip()
    url = f"http://{ip}:{PORT}"

    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    img.show()

    print(f"Scan this QR code or go to: {url}")
    print(f"Uploaded files will go to: {UPLOAD_DIR}")

    server = ThreadingHTTPServer((HOST, PORT), MediaHandler)
    server.serve_forever()

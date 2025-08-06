import os
import socket
import qrcode
import threading
import subprocess
from flask import Flask, request, redirect, send_from_directory, render_template_string, url_for

UPLOAD_FOLDER = os.path.expanduser("~/UploadsFromPhone")
PORT = 8000

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

HTML_TEMPLATE = """
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
    <form action="/" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*,video/*" multiple required><br>
        <input type="submit" value="Upload">
    </form>
    <div class="gallery">
        {% for file in files %}
            {% if file.endswith(('.jpg','.jpeg','.png','.webp','.gif')) %}
                <img src="{{ url_for('uploaded_file', filename=file) }}">
            {% elif file.endswith(('.mp4','.webm','.mov')) %}
                <video src="{{ url_for('uploaded_file', filename=file) }}" controls></video>
            {% endif %}
        {% endfor %}
        {% if not files %}
            <p style="text-align:center;width:100%;">No uploads yet.</p>
        {% endif %}
    </div>
</body>
</html>
"""

def convert_video_to_h264(filepath):
    base, ext = os.path.splitext(filepath)
    new_path = base + "_converted.mp4"
    print(f"Converting {filepath} to H.264 MP4...")
    subprocess.run([
        "ffmpeg", "-i", filepath,
        "-vcodec", "libx264", "-acodec", "aac",
        "-strict", "-2", "-y", new_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(filepath)
    return os.path.basename(new_path)

@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        files = request.files.getlist("file")
        for f in files:
            filename = f.filename
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(save_path):
                filename = f"{base}_{counter}{ext}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                counter += 1

            f.save(save_path)

            if ext.lower() in [".mov", ".webm"]:
                try:
                    converted = convert_video_to_h264(save_path)
                    os.rename(os.path.join(app.config['UPLOAD_FOLDER'], converted), save_path)
                except Exception as e:
                    print("Conversion error:", e)

        return redirect("/")

    files = sorted(os.listdir(app.config['UPLOAD_FOLDER']), reverse=True)
    return render_template_string(HTML_TEMPLATE, files=files)

@app.route("/UploadsFromPhone/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return "localhost"
    finally:
        s.close()

def show_qr(ip, port):
    import tkinter as tk
    from PIL import ImageTk, Image

    url = f"http://{ip}:{port}"
    qr = qrcode.make(url)
    root = tk.Tk()
    root.title("Scan to Upload from Phone")
    img = ImageTk.PhotoImage(qr)
    label = tk.Label(root, text=f"Scan this QR code\n{url}", font=("Arial", 14), pady=10)
    label.pack()
    qr_label = tk.Label(root, image=img)
    qr_label.image = img
    qr_label.pack()
    root.mainloop()

if __name__ == "__main__":
    ip = get_ip()
    threading.Thread(target=lambda: show_qr(ip, PORT), daemon=True).start()
    print(f"Serving at http://{ip}:{PORT}")
    app.run(host="0.0.0.0", port=PORT)

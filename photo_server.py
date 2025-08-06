import os
import socket
import qrcode
from flask import Flask, request, render_template_string, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image

UPLOAD_FOLDER = 'uploads'
PORT = 8000
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'webm', 'avi'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Media Upload</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            background-color: #121212;
            color: white;
            font-family: sans-serif;
            text-align: center;
            padding: 2em;
        }
        input[type=file], input[type=submit] {
            margin: 1em;
            padding: 1em;
            font-size: 1em;
            border-radius: 10px;
            border: none;
        }
        input[type=submit] {
            background-color: #1f1f1f;
            color: white;
            cursor: pointer;
        }
        input[type=submit]:hover {
            background-color: #333;
        }
    </style>
</head>
<body>
    <h1>📷 Upload Photo or Video</h1>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept="image/*,video/*" required><br>
        <input type="submit" value="Upload">
    </form>
    {% if filename %}
        <p>Uploaded: <a href="{{ url_for('uploaded_file', filename=filename) }}">{{ filename }}</a></p>
    {% endif %}
</body>
</html>
"""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    filename = None
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
    return render_template_string(HTML_TEMPLATE, filename=filename)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

def show_qr_code(url):
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.show()

if __name__ == '__main__':
    ip = get_local_ip()
    url = f"http://{ip}:{PORT}"
    print(f"\n📱 Open this on your phone: {url}\n")
    show_qr_code(url)
    app.run(host='0.0.0.0', port=PORT)

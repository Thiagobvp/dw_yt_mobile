from flask import Flask, request, jsonify, send_file, render_template
import os
import yt_dlp

app = Flask(__name__)

# Diretório para salvar os arquivos baixados
DOWNLOAD_DIRECTORY = "downloads"
os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)

# Variável global para armazenar o progresso
download_progress = {"percent": "0%", "speed": "0 KB/s", "eta": "N/A"}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/progress")
def progress():
    return jsonify(download_progress)

@app.route("/get_qualities", methods=["POST"])
def get_qualities():
    try:
        url = request.json.get("url")
        if not url:
            return jsonify({"error": "URL do vídeo é obrigatória!"}), 400

        ydl_opts = {"quiet": True}
        qualities = []

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if "formats" in info:
                for f in info["formats"]:
                    if f.get("vcodec") != "none":  # Apenas vídeos com qualidade
                        resolution = f.get("height")
                        format_id = f.get("format_id")
                        if resolution and format_id:  # Garantir que altura e formato existam
                            qualities.append({"resolution": f"{resolution}p", "format_id": format_id})

        # Ordena as resoluções da maior para a menor
        qualities = sorted(qualities, key=lambda x: int(x["resolution"].replace("p", "")), reverse=True)

        return jsonify({"qualities": qualities})

    except Exception as e:
        return jsonify({"error": f"Erro ao obter qualidades: {str(e)}"}), 500

@app.route("/download", methods=["POST"])
def download():
    try:
        global download_progress

        # Pegando os dados do formulário
        url = request.form.get("url")
        format_option = request.form.get("format")
        format_id = request.form.get("quality")  # Recebe o format_id diretamente

        if not url:
            return jsonify({"error": "A URL do vídeo é obrigatória!"}), 400

        # Configurando as opções do yt-dlp
        def progress_hook(d):
            if d['status'] == 'downloading':
                download_progress["percent"] = d.get("_percent_str", "0%")
                download_progress["speed"] = d.get("_speed_str", "0 KB/s")
                download_progress["eta"] = d.get("_eta_str", "N/A")

        ydl_opts = {
            "outtmpl": os.path.join(DOWNLOAD_DIRECTORY, "%(title)s.%(ext)s"),
            "format": "bestaudio/best" if format_option == "audio" else format_id,
            "progress_hooks": [progress_hook],
        }

        if format_option == "audio":
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        # Fazendo o download com yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if format_option == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"

        # Resetando o progresso após o download
        download_progress = {"percent": "0%", "speed": "0 KB/s", "eta": "N/A"}

        return send_file(filename, as_attachment=True)

    except Exception as e:
        return jsonify({"error": f"Erro ao processar o vídeo: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)

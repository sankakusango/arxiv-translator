import logging
import time
import threading
from queue import Queue, Empty
import os

from flask import Flask, request, render_template, Response, send_from_directory
from fpdf import FPDF

app = Flask(__name__)

# PDF を出力するディレクトリ
PDF_DIR = "pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

# ログ出力用のキュー
log_queue = Queue()

class QueueHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        log_entry = self.format(record)
        self.queue.put(log_entry)

# ロガーのセットアップ
def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    qh = QueueHandler(log_queue)
    qh.setLevel(logging.INFO)
    qh.setFormatter(formatter)
    logger.addHandler(qh)

    return logger

logger = setup_logger()

def create_pdf(path, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)
    pdf.output(path)

def translate(arxiv_id):
    logger.info(f"Received arxiv_id: {arxiv_id}")
    time.sleep(1)
    logger.info("Starting translation process...")
    time.sleep(1)
    logger.info("Downloading source file...")
    time.sleep(1)
    logger.info("Processing document...")
    time.sleep(1)
    logger.info("Generating PDF...")
    time.sleep(1)

    safe_id = arxiv_id.replace("/", "_")
    pdf_filename = f"{safe_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)

    create_pdf(pdf_path, f"PDF generated for arxiv_id: {arxiv_id}\n\nThis is a dummy PDF content.")

    pdf_url = f"/pdf/{pdf_filename}"
    logger.info(f"PDF generated at: {pdf_url}")

    # クライアントに通知するために特別なフォーマットのログを送信
    logger.info(f"PDF_LINK: {pdf_url}")
    return pdf_url

def stream_logs():
    while True:
        try:
            message = log_queue.get(timeout=0.5)
            yield f"data: {message}\n\n"
        except Empty:
            yield "data: \n\n"

@app.route('/logs')
def logs():
    return Response(stream_logs(), mimetype="text/event-stream")

@app.route('/translate', methods=['GET', 'POST'])
def translate_route():
    if request.method == 'POST':
        arxiv_id = request.form.get('arxiv_id')
        threading.Thread(target=translate, args=(arxiv_id,)).start()
    return render_template('translate.j2')

@app.route('/pdf/<path:filename>')
def serve_pdf(filename):
    return send_from_directory("/arxiv-translator/pdfs", filename)

if __name__ == '__main__':
    app.run(debug=True, threaded=True)

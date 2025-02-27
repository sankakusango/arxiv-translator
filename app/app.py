import logging
import time
import threading
import uuid
from queue import Queue, Empty
import os
from flask import Flask, request, render_template, Response, send_from_directory
import redis
from arxiv_translator import translate, TranslatorConfig
from pathlib import Path
import time

# --- 基本設定 ---
APP = Flask(__name__)

# 並列実行の上限数
CONCURRENCY_LIMIT = 2

translator_config = TranslatorConfig.load()
OPENAI_API_KEY = translator_config.openai_api_key
WORKING_DIR    = translator_config.working_dir
TEMPLATE_DIR   = translator_config.template_dir
OUTPUT_DIR     = translator_config.output_dir
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- ロギング設定 ---
def setup_global_logger() -> logging.Logger:
    """
    グローバルロガーを作成する関数

    Returns:
        logging.Logger: ログ出力用のロガー
    """
    logger = logging.getLogger("global")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

global_logger = setup_global_logger()

class JobQueueHandler(logging.Handler):
    """
    ログレコードをジョブ専用のキューへ出力するハンドラー

    Attributes:
        queue (Queue): ログメッセージを格納するキュー
    """
    def __init__(self, queue: Queue):
        """
        コンストラクタ

        Args:
            queue (Queue): ログを送信するキュー
        """
        super().__init__()
        self.queue = queue

    def emit(self, record):
        """
        ログレコードをキューへ出力する

        Args:
            record (logging.LogRecord): ログレコード
        """
        try:
            msg = self.format(record)
            self.queue.put(msg)
        except Exception:
            self.handleError(record)

class JobQueues:
    """
    ジョブ管理クラス
    各ジョブに対し、キュー、ロガー、arxiv_id を一元管理し、さらに並列実行のスロット管理も行う。

    Attributes:
        queues (dict): {job_id: Queue} の辞書
        loggers (dict): {job_id: logger} の辞書
        arxiv_ids (dict): {job_id: arxiv_id} の辞書
        parent_logger (logging.Logger): 親ロガー
        redis_conn (redis.Redis): Redis 接続オブジェクト
        concurrency_limit (int): 同時実行可能なジョブ数の上限
        _lock (threading.Lock): スレッドセーフな操作用ロック
    """
    def __init__(self,
                 parent_logger: logging.Logger,
                 redis_conn: redis.client.Redis,
                 concurrency_limit: int
                 ):
        """
        コンストラクタ

        Args:
            parent_logger (logging.Logger): 親となるグローバルロガー
            redis_conn (redis.Redis): Redis 接続オブジェクト
            concurrency_limit (int): 同時実行可能なジョブ数の上限
        """
        self.queues = {}
        self.loggers = {}
        self.arxiv_ids = {}
        self._lock = threading.Lock()
        self.parent_logger = parent_logger
        self.redis_conn = redis_conn
        self.concurrency_limit = concurrency_limit

    def set(self, job_id: str, arxiv_id: str = None):
        """
        指定した job_id に対し、ジョブ用のキューとロガーを作成し、内部に登録する。

        Args:
            job_id (str): ジョブ固有の識別子
            arxiv_id (str, optional): 対応する arxiv_id。デフォルトは None

        Returns:
            tuple: (Queue, logger, arxiv_id)
        """
        with self._lock:
            queue = Queue()
            self.queues[job_id] = queue

            logger = self.parent_logger.getChild(job_id)
            logger.setLevel(logging.INFO)
            job_handler = JobQueueHandler(queue)
            job_handler.setLevel(logging.INFO)
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            job_handler.setFormatter(formatter)
            logger.addHandler(job_handler)
            self.loggers[job_id] = logger

            self.arxiv_ids[job_id] = arxiv_id

            return queue, logger, arxiv_id

    def get(self, job_id: str) -> tuple:
        """
        指定した job_id に関連するキュー、ロガー、arxiv_id を取得する

        Args:
            job_id (str): ジョブ固有の識別子

        Returns:
            tuple: (Queue or None, logger or None, arxiv_id or None)
        """
        with self._lock:
            return self.queues.get(job_id), self.loggers.get(job_id), self.arxiv_ids.get(job_id)

    def release(self, job_id: str):
        """
        指定した job_id に関連するリソース（キュー、ロガー、arxiv_id）を削除し、
        並列実行カウントを減少させる

        Args:
            job_id (str): ジョブ固有の識別子
        """
        with self._lock:
            logger = self.loggers.get(job_id)
            arxiv_id = self.arxiv_ids.get(job_id)
            if logger:
                logger.info(f"release: {job_id} (arxiv_id: {arxiv_id})")
            self.decrement_slot()
            self.queues.pop(job_id, None)
            self.loggers.pop(job_id, None)
            self.arxiv_ids.pop(job_id, None)

    def current_slots(self) -> int:
        """
        現在の並列実行数を取得する

        Returns:
            int: 現在の並列実行数
        """
        current = self.redis_conn.get("running_count")
        return int(current) if current else 0

    def increment_slot(self):
        """
        並列実行カウントを 1 増加させる
        """
        self.redis_conn.incr("running_count")

    def decrement_slot(self):
        """
        並列実行カウントを 1 減少させる
        """
        self.redis_conn.decr("running_count")

    def acquire_slot(self, job_id: str):
        """
        利用可能なスロットが確保できるまで待機し、スロットを確保する

        Args:
            job_id (str): ジョブ固有の識別子
        """
        _, logger, arxiv_id = self.get(job_id)
        while True:
            current = self.current_slots()
            if current < self.concurrency_limit:
                self.increment_slot()
                if self.current_slots() <= self.concurrency_limit:
                    logger.info(f"Queue acquired for {arxiv_id} (current running: {current})")
                    break
                else:
                    self.decrement_slot()
            logger.info(f"Queue waiting for {arxiv_id} (currently running: {current})")
            time.sleep(1)

# Redis 接続およびジョブキューのインスタンス生成
global_job_queues = JobQueues(parent_logger=global_logger,
                              redis_conn=redis.Redis(),
                              concurrency_limit=CONCURRENCY_LIMIT)



def dummy_translate(arxiv_id: str, logger: logging.Logger) -> str:
    """
    ダミーの翻訳処理を行い、PDF を生成する。
    各処理ステップごとにログを出力する。

    Args:
        arxiv_id (str): 処理対象の arxiv_id
        logger (logging.Logger): ジョブ専用のロガー

    Returns:
        str: 生成された PDF の URL
    """
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
    pdf_url = f"/pdf/{pdf_filename}"
    logger.info(f"PDF generated at: {pdf_url}")
    logger.info(f"PDF_LINK: {pdf_url}")
    logger.info("COMPLETED!")
    return pdf_url

def process_translate(arxiv_id: str, job_id: str) -> str:
    """
    各ジョブごとに翻訳処理を実行する関数。
    1. ジョブ用のリソース（キュー、ロガー）をセットアップ
    2. スロットの確保を行い translate 関数を実行
    3. 最後にリソースを解放する

    Args:
        arxiv_id (str): 対象の arxiv_id
        job_id (str): ジョブ固有の識別子

    Returns:
        str: 生成された PDF の URL
    """
    global_job_queues.set(job_id, arxiv_id)
    _, logger, arxiv_id = global_job_queues.get(job_id)

    result = None
    try:
        global_job_queues.acquire_slot(job_id)
    except Exception:
        logger.error("FAILED: キューの登録失敗")
    try:
        result = translate(arxiv_id, 
                           template_dir   = TEMPLATE_DIR,
                           working_dir    = WORKING_DIR,
                           output_dir     = OUTPUT_DIR,
                           openai_api_key = OPENAI_API_KEY,
                           model          = "gpt-4o",
                           logger         = logger)
        if isinstance(result, Path):
            result = Path("/pdf") / result.name
            logger.info(f"PDF_LINK: {result}")
        else:
            logger.error("FAILED.")
    except Exception as e:
            logger.error(e)
    finally:
        time.sleep(1)
        global_job_queues.release(job_id)
    return result

@APP.route('/logs')
def stream_logs():
    """
    ログのストリーミングを行うエンドポイント
    クエリパラメータ job_id に紐付くログキューからデータを取得し、サーバー送信イベントとして返す。

    Returns:
        Response: サーバー送信イベント形式のレスポンス
    """
    job_id = request.args.get("job_id")
    queue, _, _ = global_job_queues.get(job_id)
    if not job_id or not queue:
        return "job_id が不正です.", 400

    def generate():
        while True:
            try:
                message = queue.get(timeout=0.5)
                yield f"data: {message}\n\n"
            except Empty:
                yield "data: \n\n"
    return Response(generate(), mimetype="text/event-stream")

@APP.route('/translate', methods=['GET', 'POST'])
def translate_route():
    """
    翻訳処理のエンドポイント
    POST リクエスト時には、ジョブ ID を生成し、バックグラウンドスレッドで処理を開始する。
    GET リクエスト時には、ジョブ ID を表示するテンプレートを返す。

    Returns:
        str: レンダリング済みテンプレート
    """
    job_id = ""
    arxiv_id = ""
    if request.method == 'POST':
        arxiv_id = request.form.get('arxiv_id')
        job_id = str(uuid.uuid4())
        threading.Thread(target=process_translate, args=(arxiv_id, job_id)).start()
    return render_template('translate.j2', job_id=job_id, arxiv_id=arxiv_id)

@APP.route('/pdf/')
def list_pdfs():
    try:
        # OUTPUT_DIR 内の PDF ファイルのみをリストアップ
        files = [f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith('.pdf')]
        return render_template("pdf_list.j2", files=files)
    except Exception as e:
        return f"エラーが発生しました: {e}"

@APP.route('/pdf/<path:filename>')
def serve_pdf(filename: str):
    """
    指定された PDF ファイルを返すエンドポイント

    Args:
        filename (str): PDF ファイル名

    Returns:
        Response: PDF ファイルのレスポンス
    """
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == '__main__':
    APP.run(debug=True, threaded=True)

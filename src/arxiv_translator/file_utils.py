"""ファイルを取り扱う諸々"""

import tarfile
import os
import shutil
from pathlib import Path
import requests

def download_arxiv_source(arxiv_id: str, output_dir: Path) -> Path:
    """arXivのページから、コンパイル前のデータの圧縮されたデータをダウンロードする。

    Args:
        arxiv_id (str): arxivのid. バージョン指定する場合はバージョンまで含む
        output_dir (str): ダウンロード先. ファイル名は'arxiv-{arxiv_id}.tar.gz'で固定.

    Raises:
        ValueError: ダウンロードに失敗したらエラー.

    Returns:
        Path: ダウンロードしたファイルパス
    """

    url = f"https://arxiv.org/src/{arxiv_id}"
    response = requests.get(url, timeout=600)
    output_path = Path(output_dir) / f"arxiv-{arxiv_id}.tar.gz"

    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        return Path(output_path)
    else:
        raise ValueError(f"Failed to download. HTTP status code: {response.status_code}")

def unfreeze_targz(targz_path: Path, output_dir: Path) -> Path:
    """.tar.gzの解凍をする。

    Args:
        targz_path (str): 圧縮されたファイルのパス
        output_path (str, optional): 出力先のパス
    """

    output_path = Path(output_dir) / Path(targz_path).stem.split(".tar")[0]

    with tarfile.open(targz_path, mode='r:gz') as tar:
        tar.extractall(path=output_path, filter="data")

    return output_path

def copy_item(src, dst, overwrite=False):
    """
    ファイルまたはフォルダをコピーする汎用関数

    Args:
        src (str): コピー元のパス（ファイルまたはフォルダ）
        dst (str): コピー先のパス（ファイルまたはフォルダ）
        overwrite (bool): Trueの場合、コピー先のアイテムを上書きする

    Raises:
        FileNotFoundError: コピー元が存在しない場合
        FileExistsError: コピー先が存在し、上書きしない場合
        その他のエラーは標準の例外として発生
    """
    # コピー元が存在するか確認
    if not os.path.exists(src):
        raise FileNotFoundError(f"コピー元が見つかりません: {src}")

    # コピー先が存在していて上書きしない場合、例外を発生
    if os.path.exists(dst) and not overwrite:
        raise FileExistsError(f"コピー先がすでに存在しています: {dst}")

    # ファイルかフォルダかを判定してコピー
    if os.path.isfile(src):
        shutil.copy2(src, dst)
    elif os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=overwrite)
    else:
        raise ValueError(f"無効なコピー元: {src}")

def copy_pdf_file(source_dir, target_path):
    """
    指定されたディレクトリからPDFファイルを探し、
    指定されたパスにコピーします。

    Parameters:
        source_dir (str): PDFファイルを探すディレクトリのパス。
        target_path (str): PDFファイルをコピーする先の完全なパス（ファイル名を含む）。

    Returns:
        str: コピーしたファイルのパス。

    Raises:
        FileNotFoundError: 指定のディレクトリにPDFファイルが見つからない場合。
        ValueError: 複数のPDFファイルが見つかった場合。
    """
    # ディレクトリ内のファイル一覧を取得
    pdf_files = [f for f in os.listdir(source_dir) if f.endswith('.pdf')]

    if len(pdf_files) == 0:
        raise FileNotFoundError("指定されたディレクトリにPDFファイルが見つかりません。")
    elif len(pdf_files) > 1:
        raise ValueError("指定されたディレクトリに複数のPDFファイルがあります。")

    # PDFファイルの完全なパスを取得
    pdf_file = pdf_files[0]
    source_path = os.path.join(source_dir, pdf_file)

    # コピー先ディレクトリが存在しない場合は作成
    target_dir = os.path.dirname(target_path)
    os.makedirs(target_dir, exist_ok=True)

    # ファイルをコピー
    shutil.copy2(source_path, target_path)

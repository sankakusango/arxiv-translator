"""ファイルを取り扱う諸々"""

import tarfile
import os
import shutil
from pathlib import Path

def unfreeze_targz(targz_path: Path, output_dir: Path) -> None:
    """.tar.gzの解凍をする。

    Args:
        targz_path (str): 圧縮されたファイルのパス
        output_path (str, optional): 出力先のパス
    """

    # tarファイルを開く
    with tarfile.open(targz_path, mode='r:gz') as tar:
        # 全てのファイルを展開
        tar.extractall(path= Path(output_dir) / Path(targz_path).stem.split(".tar")[0] , filter="data")

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

    # コピー先が存在していて上書きする場合、削除
    if os.path.exists(dst) and overwrite:
        if os.path.isfile(dst) or os.path.islink(dst):
            os.remove(dst)  # ファイルを削除
        elif os.path.isdir(dst):
            shutil.rmtree(dst)  # フォルダを削除

    # ファイルかフォルダかを判定してコピー
    if os.path.isfile(src):
        shutil.copy2(src, dst)  # メタデータも含めてコピー
        print(f"ファイルが正常にコピーされました: {dst}")
    elif os.path.isdir(src):
        shutil.copytree(src, dst)  # フォルダ全体をコピー
        print(f"フォルダが正常にコピーされました: {dst}")
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

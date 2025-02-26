"""ファイルを取り扱う諸々"""

import tarfile
import os
import shutil
from pathlib import Path
import logging
import requests
from jinja2 import Template

logger = logging.getLogger(__name__)

def download_arxiv_source(arxiv_id: str, output_dir: Path, logger: logging.Logger = logger):
    """arXivのページから、コンパイル前のデータの圧縮されたデータをダウンロードする。

    Args:
        arxiv_id (str): arxivのid. バージョン指定する場合はバージョンまで含む
        output_dir (str): ダウンロード先. ファイル名は'arxiv-{arxiv_id}.tar.gz'で固定.

    Raises:
        ValueError: ダウンロードに失敗したらエラー.

    Returns:
        Path: ダウンロードしたファイルパス
    """

    url_template = Template("https://arxiv.org/src/{{ arxiv_id }}")
    url = url_template.render(arxiv_id=arxiv_id)
    response = requests.get(url, timeout=600)
    output_template = Template("arxiv-{{ arxiv_id }}.tar.gz")
    output_path = Path(output_dir) / output_template.render(arxiv_id=arxiv_id)

    if response.status_code == 200:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)
        logger.info("ダウンロード成功, from %s to: %s", arxiv_id, output_path)
        return output_path
    else:
        raise ValueError(f"ダウンロード失敗. URL: {url}, HTTP status code: {response.status_code}")

def unfreeze_targz(targz_path: Path, output_dir: Path, logger: logging.Logger = logger) -> Path:
    """.tar.gzの解凍をする。

    Args:
        targz_path (str): 圧縮されたファイルのパス
        output_path (str, optional): 出力先のパス
        
    Returns:
        Path: ダウンロードしたファイルパス
    """

    output_path = Path(output_dir) / Path(targz_path).stem.split(".tar")[0]

    with tarfile.open(targz_path, mode='r:gz') as tar:
        tar.extractall(path=output_path, filter="data")
        logger.info("解凍成功, from %s to: %s", targz_path, output_path)

    return output_path

def copy_item(src: Path, dst: Path, overwrite=False, logger: logging.Logger = logger):
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

    src = Path(src)
    dst = Path(dst)

    # コピー先が存在していて上書きしない場合、例外を発生
    if not src.exists() and not overwrite:
        raise FileExistsError(f"コピー先がすでに存在しています: {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    # ファイルかフォルダかを判定してコピー
    if src.is_file():
        shutil.copy2(src, dst)
        logger.info("ファイルコピー成功, from %s to: %s", src, dst)
    elif src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=overwrite)
        logger.info("ディレクトリコピー成功, from %s to: %s", src, dst)
    else:
        raise ValueError(f"無効なコピー元: {src}")

def find_files_by_ext(source_dir: Path, ext: str, single=False) -> list:
    """指定されたディレクトリ内の, extを拡張子に持つすべてのファイルを取得する。
    例:
        file_file_by_ext("/path/to/source", "tex")

    Args:
        source_dir (str): 検索対象のディレクトリ
        ext: 検索対象の拡張子
        single: singleだったら1つのパスを返すだけ。そうでなければ見つけたPathをリストで返す。

    Returns:
        list: texファイルのリスト
    """

    # 指定されたディレクトリ内のすべての .tex ファイルを取得
    file_paths = list(Path(source_dir).rglob("*"+ext))

    if single:
        return file_paths[0]
    else:
        return file_paths

def find_main_tex(source_dir: Path) -> Path:
    """入力されたディレクトリから、mainのtexファイルを探す。

    Args:
        source_dir (str): 探索するディレクトリ

    Raises:
        ValueError: 適切なtexファイルが見つからなかった。

    Returns:
        str: texのファイルパス
    """

    tex_files = find_files_by_ext(source_dir=source_dir, ext="tex")

    main_tex_file: Path = None
    # .tex ファイルを探索して \documentclass を含む最初のファイルを探す
    for tex_file in tex_files:
        with open(tex_file, 'r', encoding='utf-8') as file:
            if '\\documentclass' in file.read():
                main_tex_file = tex_file

    if main_tex_file is None:
        raise ValueError(f"適切なtexファイルが見つかりませんでした。 {source_dir}")
    else:
        return Path(main_tex_file)

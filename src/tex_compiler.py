"""texをコンパイルするための諸々"""

import glob
from pathlib import Path
import subprocess
import os

def find_main_tex(source_dir: str) -> str:
    """入力されたディレクトリから、mainのtexファイルを探す。

    Args:
        source_dir (str): 探索するディレクトリ

    Raises:
        ValueError: 適切なtexファイルが見つからなかった。

    Returns:
        str: texのファイルパス
    """

    # 指定されたディレクトリ内のすべての .tex ファイルを取得
    tex_files = glob.glob( os.path.join(source_dir, "*.tex") )

    main_tex_file: str = None
    # .tex ファイルを探索して \documentclass を含む最初のファイルを探す
    for tex_file in tex_files:
        with open(tex_file, 'r', encoding='utf-8') as file:
            if '\\documentclass' in file.read():
                main_tex_file = tex_file

    if main_tex_file is None:
        raise ValueError(f"適切なtexファイルが見つかりませんでした。 {source_dir}")
    else:
        return main_tex_file

def compile_tex(source_file_path: str, working_dir: str = None):
    """texファイルをコンパイルする。

    Args:
        source_file_path (Path): コンパイルしたいtexファイルのパス
        working_dir (Path, optional): 作業ディレクトリ. 指定がなければsource_file_pathの親ディレクトリになる。
    """

    if working_dir is None:
        working_dir = Path(source_file_path).parent
    command = ["latexmk", "-lualatex", "-interaction=nonstopmode", source_file_path]
    subprocess.run(command, cwd=working_dir, check=True, text=True, capture_output=True)

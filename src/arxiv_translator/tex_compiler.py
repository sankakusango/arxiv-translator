"""texをコンパイルするための諸々"""

import time
import logging
from pathlib import Path
import subprocess

LOGGER = logging.getLogger(__name__)

def compile_tex(source_file_path: Path,
                working_dir: Path = None,
                max_attempts: int = 5,
                delay: int = 2,
                logger: logging.Logger = LOGGER,
                ):
    """texファイルをコンパイルする。

    Args:
        source_file_path (Path): コンパイルしたいtexファイルのパス
        working_dir (Path, optional): 作業ディレクトリ。指定がなければsource_file_pathの親ディレクトリになる。
        max_attempts (int, optional): コンパイルの最大試行回数 (デフォルトは3回)
        delay (int, optional): 失敗時の再試行までの待機秒数 (デフォルトは2秒)
    """
    if working_dir is None:
        working_dir = source_file_path.parent
        logger.debug(f"working_dirが指定されなかったので、{working_dir} でコンパイル作業を行います.")

    command = ["latexmk", "-lualatex", "-interaction=nonstopmode", str(source_file_path)]

    logger.info("コンパイル中")
    for attempt in range(1, max_attempts + 1):
        try:
            result = subprocess.run(command,
                                    cwd=working_dir,
                                    check=True,
                                    text=True,
                                    capture_output=True)
            logger.info("コンパイル成功")
            return result
        except subprocess.CalledProcessError as e:
            if attempt < max_attempts:
                logger.warning("コンパイル再試行中 (%d / %d)): %s", attempt, max_attempts, e)
                time.sleep(delay)
            else:
                logger.error("コンパイル失敗 (%d / %d)): %s", attempt, max_attempts, e)
                return result

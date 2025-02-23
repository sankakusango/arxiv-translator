"""メイン"""

import logging
from pathlib import Path
import sys
from tqdm import tqdm
from jinja2 import Environment, FileSystemLoader
from .file_utils import download_arxiv_source, unfreeze_targz, copy_item, find_files_by_ext, find_main_tex
from .openai_chat import OpenAIChat
from .tex_compiler import compile_tex
from .tex_translator_utils import split_tex_to_chunks, insert_text_after_documentclass, remove_comments, reduce_newlines, is_only_commands, parse_code_blocks
from .config import TranslatorConfig

def setup_logger():
    """ロガーのセットアップ"""
    logger = logging.getLogger()  # ルートロガーを取得
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    return logger

logger = setup_logger()

def translate(arxiv_id: str,
              template_dir = None,
              working_dir: Path = None,
              output_dir: Path = None,
              openai_api_key = None):
    """翻訳実行

    Args:
        arxiv_id (str): arxivのid
    """

    config = TranslatorConfig.load()
    if template_dir is None:
        template_dir = config.template_dir
    if working_dir is None:
        working_dir = config.working_dir
    if output_dir is None:
        output_dir = config.output_dir
    if openai_api_key is None:
        openai_api_key = config.openai_api_key

    # 前処理

    ## ダウンロード
    targz_path = download_arxiv_source(arxiv_id=arxiv_id, output_dir=working_dir)

    ## tarの解凍
    raw_data_path = unfreeze_targz(targz_path, output_dir=working_dir)

    ## 作業場所へのコピー
    tex_dir = raw_data_path.parent/(raw_data_path.name+"-translated")
    copy_item(src=raw_data_path, dst=tex_dir, overwrite=True)


    # 本処理

    ## 翻訳用のLLM
    jinja_env = Environment(loader=FileSystemLoader(template_dir))
    translator = OpenAIChat(api_key=openai_api_key,
                            model="gpt-4o",
                            template=jinja_env.get_template('prompt_en_to_ja.j2'))

    ## 日本語パッケージの追加
    main_tex_path = find_main_tex(tex_dir)
    main_tex_contents = main_tex_path.read_text('utf-8')
    main_tex_contents = insert_text_after_documentclass(content=main_tex_contents,
                                                        template=jinja_env.get_template('tex_style_ja.j2')
                                                        )
    main_tex_path.write_text(main_tex_contents, encoding='utf-8')

    ## テキスト分割
    tex_file_paths = find_files_by_ext(tex_dir, "tex")
    for file_path in tex_file_paths:
        logging.info(file_path)
        file_path = Path(file_path)
        tex_content = file_path.read_text('utf-8')
        tex_content = remove_comments(tex_content)
        tex_content = reduce_newlines(tex_content)
        if is_only_commands(tex_content):
            continue
        else:
            # テキスト分割
            tex_chunks = split_tex_to_chunks(content=tex_content,
                                             token_counter=translator.count_tokens)
            # 翻訳
            translated_chunks=[]
            for tex_chunk in tqdm(tex_chunks, desc="翻訳中..."):
                if f"% skip start\n" in tex_chunk:
                    translated_chunks.append(tex_chunk)
                    logger.info("翻訳スキップ")
                else:
                    translated_chunk = translator(tex_chunk)
                    translated_chunk = parse_code_blocks(translated_chunk)[0]["code"]
                    translated_chunks.append(translated_chunk)
            translated_tex_contents = "".join(translated_chunks)
            file_path.write_text(translated_tex_contents, encoding='utf-8')

    ## コンパイル
    compile_tex(source_file_path=main_tex_path)

    ## 結果
    compiled_pdf_path = find_files_by_ext(tex_dir, ext="pdf", single=True)
    copy_item(src=compiled_pdf_path, dst= Path(output_dir) / f"{arxiv_id}_ja.pdf")

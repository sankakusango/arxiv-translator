"""メイン"""

import logging
from pathlib import Path
import sys
from tqdm import tqdm
from jinja2 import Environment, FileSystemLoader
from .file_utils import download_arxiv_source, unfreeze_targz, copy_item, find_files_by_ext, find_main_tex, extract_arxiv_id
from .openai_chat import OpenAIChat
from .tex_compiler import compile_tex
from .tex_translator_utils import split_tex_to_chunks, insert_text_after_documentclass, remove_comments, reduce_newlines, is_only_commands, parse_code_blocks
from .config import TranslatorConfig

def setup_logger():
    """ロガーのセットアップ"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    return logger

def translate(arxiv_id: str,
              template_dir = None,
              working_dir: Path = None,
              output_dir: Path = None,
              openai_api_key = None,
              model: str = "gpt-4o",
              logger: logging.RootLogger = setup_logger()
              ):
    """翻訳実行

    Args:
        arxiv_id (str): arxivのid
    """

    config = TranslatorConfig.load(logger=logger)
    if template_dir is not None:
        config.template_dir = template_dir
    if working_dir is not None:
        config.working_dir = working_dir
    if output_dir is not None:
        config.output_dir = output_dir
    if openai_api_key is not None:
        config.openai_api_key = openai_api_key
    config.show()

    # 前処理

    ## ダウンロード
    arxiv_id = extract_arxiv_id(arxiv_id)
    targz_path = download_arxiv_source(arxiv_id=arxiv_id, output_dir=config.working_dir, logger=logger)

    ## tarの解凍
    raw_data_path = unfreeze_targz(targz_path, output_dir=config.working_dir, logger=logger)

    ## 作業場所へのコピー
    tex_dir = raw_data_path.parent/(raw_data_path.name+"-translated")
    copy_item(src=raw_data_path, dst=tex_dir, overwrite=True, logger=logger)


    # 本処理

    ## 翻訳用のLLM
    jinja_env = Environment(loader=FileSystemLoader(config.template_dir))
    translator = OpenAIChat(api_key=config.openai_api_key,
                            model=model,
                            template=jinja_env.get_template('prompt_en_to_ja.j2'),
                            logger=logger
                            )
    logger.info("翻訳用のLLMとして`%s`を設定しました。", model)

    ## 日本語パッケージの追加
    main_tex_path = find_main_tex(tex_dir)
    main_tex_contents = main_tex_path.read_text('utf-8')
    template = jinja_env.get_template('tex_style_ja.j2')
    main_tex_contents = insert_text_after_documentclass(content=main_tex_contents,
                                                        template=template,
                                                        logger=logger,
                                                        )
    main_tex_path.write_text(main_tex_contents, encoding='utf-8')
    logger.info("日本語化パッケージの差し込みが完了しました。")
    
    ## テキスト分割
    tex_file_paths = find_files_by_ext(tex_dir, "tex")
    logger.info(f"合計 {len(tex_file_paths)} 個のtexファイルが見つかりました。")
    for i, file_path in enumerate(tex_file_paths, start=1):
        file_path = Path(file_path)
        logger.info(f"processing file: {file_path.name} ({i}/{len(tex_file_paths)})")
        tex_content = file_path.read_text('utf-8')
        tex_content = remove_comments(tex_content, logger)
        tex_content = reduce_newlines(tex_content)
        if is_only_commands(tex_content):
            logger.info(f"翻訳をスキップしました: {file_path.name} ({i}/{len(tex_file_paths)})")
            continue
        else:
            # テキスト分割
            tex_chunks = split_tex_to_chunks(content=tex_content,
                                             token_counter=translator.count_tokens,
                                             logger=logger)
            # 翻訳
            translated_chunks=[]
            for j, tex_chunk in tqdm(enumerate(tex_chunks, start=1), desc="翻訳中..."):
                logger.info(f"翻訳中 {j}/{len(tex_chunks)}")
                if f"% skip start\n" in tex_chunk:
                    translated_chunks.append(tex_chunk)
                else:
                    translated_chunk = translator(tex_chunk)
                    translated_chunk = parse_code_blocks(translated_chunk)[0]["code"]
                    translated_chunks.append(translated_chunk)
            translated_tex_contents = "".join(translated_chunks)
            file_path.write_text(translated_tex_contents, encoding='utf-8')
            logger.info(f"翻訳完了: {file_path.name} ({i}/{len(tex_file_paths)})")

    ## コンパイル
    compile_tex(source_file_path=main_tex_path, logger=logger)

    ## 結果
    compiled_pdf_path = find_files_by_ext(tex_dir, ext="pdf", single=True)
    
    output_path = Path(config.output_dir) / f"{arxiv_id}_ja.pdf"
    
    copy_item(src=compiled_pdf_path, dst=output_path, logger=logger)
    
    return output_path

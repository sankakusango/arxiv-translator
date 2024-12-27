"""メイン"""

from .file_utils import download_arxiv_source, unfreeze_targz, copy_item, copy_pdf_file
from .openai_chat import OpenAIChat
from .tex_compiler import find_tex_files, find_main_tex, compile_tex
from .tex_translator_utils import split_tex_to_chunks, insert_after_documentclass, extract_quoted_text

import yaml
from tqdm import tqdm


def translate(arxiv_id: str):
    """翻訳実行

    Args:
        arxiv_id (str): arxivのid
    """

    with open("/config/api_keys.yml", "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    api_key = data["OPENAI_API_KEY"]

    with open("/config/configs.yml", "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    filepath = data["filepath"]
    inserting_pre_text = data['tex']['pre_text'].replace("\\", "\\\\")
    template = data["prompt"]["translate"]["en_to_ja"]

    # 0. ダウンロード
    targz_path = download_arxiv_source(
        arxiv_id=arxiv_id, output_dir=filepath["tar_gz"])
    # 1. tarの解凍
    raw_data_path = unfreeze_targz(
        targz_path=targz_path, output_dir=filepath["raw"])
    # 2. 作業
    copy_item(src=raw_data_path,
              dst=filepath["work"]+f"/arxiv-{arxiv_id}", overwrite=True)
    translator = OpenAIChat(api_key=api_key, model="gpt-4o", template=template)

    main_tex_path = find_main_tex(
        source_dir=filepath["work"]+f"/arxiv-{arxiv_id}")
    with open(main_tex_path, 'r', encoding='utf-8') as file:
        print(main_tex_path)
        main_tex_contents = file.read()
        main_tex_contents = insert_after_documentclass(contents=main_tex_contents,
                                                       inserting_pre_text=inserting_pre_text)
    with open(main_tex_path, 'w', encoding='utf-8') as file:
        file.write(main_tex_contents)

    file_paths = find_tex_files(
        source_dir=f"/data/2_working_data/arxiv-{arxiv_id}")

    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as file:
            tex_contents = file.read()
        # テキスト分割
        tex_chunks = split_tex_to_chunks(contents=tex_contents,
                                         token_counter=translator.count_tokens)
        # 翻訳
        translated_chunks = []
        for tex_chunk in tqdm(tex_chunks):
            translated_chunk = translator(tex_chunk)
            translated_chunk = extract_quoted_text(translated_chunk)
            translated_chunks.append(translated_chunk)
        translated_tex_contents = "".join(translated_chunks)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(translated_tex_contents)

    compile_tex(source_file_path=main_tex_path)
    copy_pdf_file(f"/data/2_working_data/arxiv-{arxiv_id}",
                  f"/data/3_output_data/{arxiv_id}_ja.pdf")

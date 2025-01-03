"""texの翻訳に使うコード"""
import re

def split_tex_contents(contents: str, flag=r"\section") -> list:
    """受け取ったcontentsをflagで分割, 前にくっつける.

    Args:
        contents (str): 入力テキスト
        flag (regexp, optional): 分割フラグ. Defaults to r"\\section".

    Returns:
        list: 分割されたテキスト
    """

    parts: list = contents.split(flag)
    results: list=[parts[0]]
    for part in parts[1:]:
        results.append(flag+part)
    return results

def split_tex_to_chunks(contents: str, token_counter: callable, chunk_size: int = None) -> list:
    """texファイルを翻訳のためにチャンク分けする。

    Args:
        contents (str): 元ファイルのテキスト
        chunk_size (int): 分けるチャンクのサイズ

    Returns:
        list: チャンクのリスト
    """

    sections = split_tex_contents(contents=contents, flag=r"\section")
    subsections = []
    for section in sections:
        subsections += split_tex_contents(contents=section, flag=r"\subsection")

    subsubsections = []
    for subsection in subsections:
        subsubsections += split_tex_contents(contents=subsection, flag=r"\subsubsection")

    max_size = max([token_counter(subsubsection) for subsubsection in subsubsections])
    if chunk_size is None:
        chunk_size = max_size
    elif max_size > chunk_size:
        raise ValueError(f"too large subsubsection ({max_size})")

    chunks = []
    chunk = ""
    for subsubsection in subsubsections:
        if token_counter(chunk + subsubsection) > chunk_size:
            chunks.append(chunk)
            chunk = subsubsection
        else:
            chunk += subsubsection

    chunks.append(chunk)
    return chunks

def insert_after_documentclass(contents: str, inserting_pre_text: str) -> str:
    """documentclassの次の行にテキストを挿入

    Args:
        src_contents (str): texのテキスト
        inserting_pre_text (str): 挿入するテキスト

    Returns:
        str: 挿入後のテキスト
    """

    output_text: str = re.sub(r'(\\documentclass.*?\{.*?\}.*?\n)',
                              r'\1' + inserting_pre_text + '\n', 
                              contents,
                              count=1)
    return output_text

def extract_quoted_text(text):
    """
    テキストから `\"\"\"` で囲まれた部分を抜き出す関数。
    ただし、囲まれた箇所は1つだけを想定。
    
    Args:
        text (str): 入力テキスト。
    
    Returns:
        str: 抜き出した部分。見つからなかった場合は None を返す。
    """
    # 正規表現で """ で囲まれた部分を検索
    match = re.search(r'"""(.*?)"""', text, re.DOTALL)
    if match:
        return match.group(1)  # マッチしたグループを返す
    return text

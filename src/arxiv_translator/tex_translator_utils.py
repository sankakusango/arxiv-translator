"""texの翻訳に使うコード"""
import re
import logging
from jinja2 import Template, StrictUndefined

logger = logging.getLogger(__name__)



def parse_triple_quoted_sections(text: str) -> list:
    """
    テキストからダブルクオーテーション3つで囲まれた部分を抽出します。
    
    Args:
        text (str): 対象のテキスト
        
    Returns:
        List[str]: 各ダブルクオーテーション3つで囲まれた部分の内容を要素とするリスト
    """

    # 正規表現パターン:
    # - """ で始まり、非貪欲で中の内容 (任意の文字列) をマッチし、
    # - 次の """ で終わる部分にマッチさせる。
    pattern = r'"""(.*?)"""'

    # DOTALL フラグを指定して、改行も対象にする
    matches = re.findall(pattern, text, re.DOTALL)
    return matches

def parse_code_blocks(text: str) -> list:
    """
    マークダウンテキストからコードブロックを抽出します。
    
    Args:
        markdown_text (str): マークダウン形式の文字列
        
    Returns:
        List[dict]: 各コードブロックについて、'language'（言語指定があれば）と 'code' の辞書のリスト
    """
    # 正規表現パターン:
    # - ``` の後に任意の空白を許容し、続いて任意の言語指定（アルファベット、数字、+-等）をオプションで受け付ける。
    # - 続く任意の空白と改行の後にコード内容をマッチさせ、最後に改行と ``` で閉じる。
    pattern = r'```(?:\s*([\w+-]+))?\s*\n(.*?)\n```'

    # DOTALLフラグを使用して、コード部分の改行もマッチ対象にする
    matches = re.findall(pattern, text, re.DOTALL)

    code_blocks = []
    for lang, code in matches:
        # 言語指定が空文字列の場合はNoneにする
        language = lang.strip() if lang and lang.strip() != "" else None
        code_blocks.append({
            "language": language,
            "code": code
        })
    return code_blocks

def split_tex_contents(content: str, flag=r"\section") -> list:
    """受け取ったcontentsをflagで分割, 前にくっつける.

    Args:
        contents (str): 入力テキスト
        flag (regexp, optional): 分割フラグ. Defaults to r"\\section".

    Returns:
        list: 分割されたテキスト
    """

    parts: list = content.split(flag)
    results: list=[parts[0]]
    for part in parts[1:]:
        results.append(flag+part)
    return results

def split_tex_into_subsubsections(contents: str) -> list:
    """_summary_

    Args:
        contents (_type_): _description_

    Returns:
        _type_: _description_
    """

    sections = split_tex_contents(content=contents, flag=r"\section")

    subsections = []
    for section in sections:
        subsections += split_tex_contents(content=section, flag=r"\subsection")

    subsubsections = []
    for subsection in subsections:
        subsubsections += split_tex_contents(content=subsection, flag=r"\subsubsection")

    return subsubsections

def split_tex_to_chunks(content: str,
                        token_counter: callable = len,
                        chunk_size: int = None
                        ) -> list:
    """texファイルを翻訳のためにチャンク分けする。

    Args:
        contents (str): 元ファイルのテキスト
        chunk_size (int): 分けるチャンクのサイズ

    Returns:
        list: チャンクのリスト
    """

    chunks: list = []

    if r"\begin{document}" in content:
        logger.info(r"\begin{document}が含まれていたので、この箇所でもチャンクを区切ります。")
        contents = split_tex_contents(content, r"\begin{document}")
        chunks.append(f"% skip start\n{contents.pop(0)}\n% skip end\n")
        content = "".join(contents)

    subsubsections = split_tex_into_subsubsections(content)

    max_size = max([token_counter(subsubsection) for subsubsection in subsubsections])
    if chunk_size is None:
        chunk_size = max_size
    elif max_size > chunk_size:
        logger.warning("Some chunks are larger than chunk_size. max_size: %d", max_size)

    chunk = ""
    for subsubsection in subsubsections:
        if token_counter(chunk + subsubsection) > chunk_size:
            chunks.append(chunk)
            chunk = subsubsection
        else:
            chunk += subsubsection

    chunks.append(chunk)
    return chunks

def insert_text_after_documentclass(content: str, template: Template) -> str:
    """documentclassの次の行にテキストを挿入（jinja2を利用）

    Args:
        content (str): 元のTeXテキスト
        inserting_pre_text (str): 挿入するテキスト

    Returns:
        str: 挿入後のテキスト
    """

    # documentclass の行を抽出（改行も含む）
    pattern = re.compile(r'(\\documentclass.*?\{.*?\}.*?\n)')
    match = pattern.search(content)

    documentclass_line = match.group(1)
    rest = content[match.end():]

    if isinstance(template, str):
        logging.info("Templateに変換します.")
        template = Template(template, undefined=StrictUndefined)

    return template.render(
        documentclass_command=documentclass_line,
        content=rest
    )

def remove_comments(tex_content: str) -> str:
    """
    与えられた文字列（複数行）から LaTeX のコメントを削除して返す関数。
    
    ・LaTeX のルール:
       直前に連続するバックスラッシュ数が偶数個の場合のみ
       '%' はコメント開始とみなし、残りを削除する。
    ・行単位でコメント除去を行い、処理後の行を改行で連結して返す。
    """

    unprocessed_lines = tex_content.splitlines()
    processed_lines = []

    # テキストを改行で分割し、各行についてコメント削除
    for line in unprocessed_lines:
        new_line_chars = []
        backslash_count = 0
        for ch in line:
            if ch == '%' and backslash_count % 2 == 0:
                break
            backslash_count = backslash_count + 1 if ch == '\\' else 0
            new_line_chars.append(ch)
        # 結果
        processed_lines.append("".join(new_line_chars))

    # 処理後の行を改行でつないで返す
    return "\n".join(processed_lines)

def reduce_newlines(text: str) -> str:
    """複数の連続する空行（または半角スペースだけの行）を最大1行にまとめます。

    Args:
        text (str): 入力テキスト

    Returns:
        str: 空行がまとめられたテキスト
    """
    lines = text.splitlines()
    reduced_lines = []
    prev_empty = False

    for line in lines:
        # 半角スペースだけの行も空行とみなす
        if line.strip() == "":
            if not prev_empty:
                reduced_lines.append("")
            prev_empty = True
        else:
            reduced_lines.append(line)
            prev_empty = False

    return "\n".join(reduced_lines)


def is_only_commands(content: str) -> bool:
    """コメント除去後の文字列が、空白を除いて「コマンド（スラッシュで始まるもの）とその引数ブロック（{…} または […]）
    のみ」で構成されているかをチェックする。
    
    アプローチ：
      1. 余分な空白を除去
      2. 角括弧ブロック（入れ子はしないので単純な [^][]*）を除去
      3. 中括弧ブロックは入れ子対応のため、最も内側の {…} （中に { や } を含まない部分）を繰り返し除去
      4. 最後に、スラッシュで始まるコマンド（アルファベット連続または1文字）を除去
      5. すべて除去できれば、元はコマンド（＋ブロック・空白）のみということになる
    """

    text = remove_comments(content)
    # 余白（空白文字、改行など）を除去
    s = re.sub(r'\s+', '', text)
    # 角括弧 [...] ブロックは入れ子を考えなくてもよいので一括除去
    s = re.sub(r'\[[^\[\]]*\]', '', s)
    # 中括弧 {…} ブロックについては、入れ子対応のため「最も内側」のブロックを繰り返し除去
    old = None
    while s != old:
        old = s
        s = re.sub(r'\{[^{}]*\}', '', s)
    # コマンドは、\ の後に英字が続く場合は連続英字、そうでなければ1文字コマンドとする
    s = re.sub(r'\\(?:[A-Za-z]+|.)', '', s)
    # すべてが消えていれば有効（空文字列になっているはず）
    return s == ''

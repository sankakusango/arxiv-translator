import sys
import argparse
from pathlib import Path
from .translator import translate
from .config import TranslatorConfig
import colorama
from colorama import Fore, Style

def main():
    """CLIでarxiv-translateと打ったときの挙動"""
    parser = argparse.ArgumentParser(
        prog='arxiv-translate',
        description='Arxiv Translate Utility \n\n例1: arxiv-translate 1000.20000v1\n-> 論文の翻訳ができる.\n\n例2: arxiv-translate config\n->デフォルトのファイルパスの指定などができる.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('arxiv_id', help="実行するコマンド。 'config' を指定すると設定を実行、それ以外は翻訳対象のファイル名として扱います。")
    parser.add_argument('--working_dir', type=str, default=None, help="作業ディレクトリのパスを指定します。")
    parser.add_argument('--template_dir', type=str, default=None, help="テンプレートディレクトリのパスを指定します。")
    parser.add_argument('--output_dir', type=str, default=None, help="出力ディレクトリのパスを指定します。")
    parser.add_argument('--openai_api_key', type=str, default=None, help="OpenAI APIキーを指定します。")
    args = parser.parse_args()

    if args.arxiv_id == "config":
        update_config_interactive()
    else:
        translate(
            args.arxiv_id,
            working_dir=args.working_dir,
            template_dir=args.template_dir,
            output_dir=args.output_dir,
            openai_api_key=args.openai_api_key
        )

def update_config_interactive():
    """対話形式でConfigのアップデートをする。"""
    current_config = TranslatorConfig.load()

    # ユーザーの入力を受け付ける.
    colorama.init(autoreset=True)
    working_dir = input(f"{Style.RESET_ALL}中間ファイルを生成するディレクトリ: {Fore.CYAN}{current_config.working_dir}{Style.RESET_ALL} -> {Fore.GREEN}")
    template_dir = input(f"{Style.RESET_ALL}読み込むテンプレートのディレクトリ: {Fore.CYAN}{current_config.template_dir}{Style.RESET_ALL} -> {Fore.GREEN}")
    output_dir = input(f"{Style.RESET_ALL}PDFファイルを出力するディレクトリ: {Fore.CYAN}{current_config.output_dir}{Style.RESET_ALL} -> {Fore.GREEN}")
    current_openai_api_key = current_config.openai_api_key
    display_text =""
    if current_openai_api_key is None:
        display_text = "default"
    elif len(current_openai_api_key) <=4:
        display_text = current_openai_api_key
    else:
        display_text = current_openai_api_key[:4] + "*" * (len(current_openai_api_key) - 4)
    openai_api_key = input(f"{Style.RESET_ALL}利用する`OPENAI_API_KEY` (`default`を指定すれば環境変数の`OPENAI_API_KEY`が利用される): {Fore.CYAN}{display_text}{Style.RESET_ALL} -> {Fore.GREEN}")
    print(Style.RESET_ALL, end="") 
    # ユーザーの入力テキストの処理 (working_dir).
    if working_dir is None or working_dir == "":
        working_dir = current_config.working_dir
    elif working_dir.strip().lower() == "default":
        working_dir = None
    else:
        working_dir = Path(working_dir)

    # ユーザーの入力テキストの処理 (template_dir).
    if template_dir is None or template_dir == "":
        template_dir = current_config.template_dir
    elif template_dir.strip().lower() == "default":
        template_dir = None
    else:
        template_dir = Path(template_dir)

    # ユーザーの入力テキストの処理 (output_dir).
    if output_dir is None or output_dir == "":
        output_dir = current_config.output_dir
    elif output_dir.strip().lower() == "default":
        output_dir = None
    else:
        output_dir = Path(output_dir)

    # ユーザーの入力テキストの処理 (openai_api_key).
    if openai_api_key is None or openai_api_key =="":
        openai_api_key = current_config.openai_api_key
    else:
        openai_api_key = str(openai_api_key)

    # コンフィグのアップデート
    new_config = TranslatorConfig(openai_api_key=openai_api_key, 
                                  working_dir=working_dir, 
                                  template_dir=template_dir, 
                                  output_dir=output_dir)
    new_config.save()

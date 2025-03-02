
# About

arXivのドキュメントをOpenAIのAPIを使って日本語に翻訳します.
指定されたページの`Tex Source`をダウンロードし, texファイル全体を日本語化して再コンパイルすることで,
数式や図表等のスタイルを崩さずに翻訳できる点が特長です.

# Quickstart (WebUI)

## 事前準備
OpenAIのAPIキーとDocker環境を事前に準備してください.

## 環境構築

1. 本レポジトリを自環境にダウンロード.
```bash
git clone https://github.com/sankakusango/arxiv-translator.git
```

2. `.env`の`OPEN_AI_API_KEY`に自分のAPIキーを設定. 必要があれば`docker-compose.yml`を編集.
```bash
docker-compose build
docker-compose up -d
```

3. `https://localhost:5000/translate`にChrome等のブラウザでアクセス.
翻訳したいarXivのドキュメントのID(例: 1234.56789) またはURL(例: `https://arxiv.org/abs/1234.56789v1`)を入力し,
15分ほど待機することで翻訳したPDFをダウンロードできます.

# CLIとしての利用

1. 本レポジトリを自環境にダウンロード.
```bash
git clone https://github.com/sankakusango/arxiv-translator.git
```

2. インストール.
   `pip install .`
3. 初期設定 (Option)
   `arxiv-translate config`
   指示に従い, 作業ディレクトリ (`default: /tmp`), PDFファイルを出力するディレクトリ (`default: /output`), 翻訳用テンプレートのパス (`default: /templates`), OpenAIのAPIを設定してください.
   設定しない場合, 環境変数`OPENAI_API_KEY`を利用します.
   後で設定変更する場合も`arxiv-translate config`です.
4. 実行
   `arxiv-translate {ARXIV_ID}`で翻訳できます.
   `ARXIV_ID`は翻訳したいarXivのドキュメントのID(例: 1234.56789) またはURL(例: `https://arxiv.org/abs/1234.56789v1`)で置き換えてください.

# Pythonライブラリとしての利用

```python
import arxiv_translator.translate
arxiv_translator.translate(
    arxiv_id="1234.56789",
    template_dir="/templates",
    working_dir="/tmp",
    output_dir="/output",
    openai_api_key="sk-###",
    model="gpt-4o",
)
```

**パラメータ**

- `arxiv_id (str)`
  - 翻訳対象の arXiv 論文の ID を指定します。

- `template_dir (Path)`
  - 翻訳処理で使用するテンプレートファイルが格納されているディレクトリを指定します。
  - デフォルト: None
  - 指定しない場合は, `arxiv-translate config`の値が設定される.

- `working_dir (Path)`
  - 作業ディレクトリを指定します。
  - デフォルト: None
  - 指定しない場合は, `arxiv-translate config`の値が設定される.

- `output_dir (Path)`
  - 最終的な翻訳結果を保存する出力ディレクトリを指定します。
  - デフォルト: None
  - 指定しない場合は, `arxiv-translate config`の値が設定される.
  - 
- `openai_api_key (str)`
  - 翻訳モデルへアクセスするための OpenAI API キーを指定します。
  - デフォルト: None
  - 指定しない場合は, `arxiv-translate config`の値が設定される.
    
- `model (str)`
  - 利用する翻訳モデルを指定します。
  - デフォルト: 'gpt-4o'

# Advanced

## 翻訳に失敗するとき

作業ディレクトリの`{ARXIV_ID}-translated`のtexファイルを適切に書き換え,
```python
import arxiv_translator.compile_tex
arxiv_translator.compile_tex(source_file_path)
```
を使って再コンパイルしてください.

## よくあるカスタマイズ

> [!WARNING]
> WebUIを利用している場合, 変更後はコンテナをビルドし直してください.

- 翻訳テンプレートの差し替え
`templates/prompt_en_to_ja.j2`

- 翻訳モデルの差し替え
   - WebUIの場合: `app/app.py`にハードコードされている"gpt-4o"を他モデルに変えてください.
   - `src/arxiv_translator/cli.py`の`translate`に`model="gpt-4o"`を追加してください.
   
- 翻訳のスキップルール等
   - `src/arxiv_translator/translator.py`を書き換えてください.

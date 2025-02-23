"""openaiのAPIを叩く"""
import os
import logging
from jinja2 import Template, StrictUndefined
from openai import OpenAI
import tiktoken

logger = logging.getLogger(__name__)

class OpenAIChat:
    """OpenAIのAPIを叩いて出力させるクラス"""

    _api_key: str
    model: str
    _client: OpenAI
    _template: Template = Template("{{ prompt }}", undefined=StrictUndefined)
    _output_formatter: callable = lambda self, x: x

    def __init__(self, model: str, api_key: str = None, template: Template = None, output_formatter: callable = None):

        self.api_key = api_key
        self.model = model
        if template is not None:
            self.template = template
        if output_formatter is not None:
            self.output_formatter = output_formatter

    @property
    def api_key(self):
        """apiキーのゲッター"""
        return self._api_key

    @api_key.setter
    def api_key(self, value):
        """apiキーを設定すると、clientにも反映する。"""
        if value is not None:
            self._api_key = value
        else:
            logger.info("apiキーを環境変数`OPENAI_API_KEY`から取得します.")
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key is None:
                raise ValueError("環境変数`OPENAI_API_KEY`が設定されていません。")
            self._api_key = openai_api_key

        self._client = OpenAI(api_key=self.api_key)

    @property
    def template(self):
        """テンプレートのゲッター"""
        return self._template

    @template.setter
    def template(self, value):
        """テンプレートのセッター"""
        if isinstance(value, str):
            self._template = Template(value)
        else:
            self._template = value

    @property
    def output_formatter(self):
        """output_formatterのゲッター"""
        return self._output_formatter

    @output_formatter.setter
    def output_formatter(self, value):
        """output_formatterのセッター"""
        self._output_formatter = value

    def get_response(self, text_in: str) -> str:
        """textを受け取って、応答する。

        Args:
            text_in (str): 入力文

        Returns:
            str: 出力文
        """

        prompt = self.template.render(prompt=text_in)

        chat_completion = self._client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=self.model,
            temperature=0,
        )

        text_out = chat_completion.choices[0].message.content

        return self.output_formatter(text_out)

    def count_tokens(self, text_in: str):
        """指定されたモデルのトークナイザーを使用してテキストのトークン数を計算する。

        Args:
            text_in (str): トークン数を計算するテキスト。

        Returns:
            int: テキストのトークン数。
        """

        prompt = self.template.render(prompt=text_in)
        encoding = tiktoken.encoding_for_model(self.model)
        tokenized = encoding.encode(prompt)
        return len(tokenized)

    def __call__(self, *args, **kwds):
        return self.get_response(*args, **kwds)

if __name__ == "__main__":

    openai_chat = OpenAIChat(
        api_key="sk-###",
        model="gpt-4"
    )
    print(openai_chat("こんにちは"))

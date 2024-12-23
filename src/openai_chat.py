import os
from openai import OpenAI
import tiktoken

class OpenAIChat:
    """OpenAIのAPIを叩いて出力させるクラス

    Returns:
        _type_: _description_
    """

    _api_key: str
    _model: str
    _client: OpenAI
    _template: str

    def __init__(self, api_key: str, model: str, template: str = None):

        self.api_key = api_key
        self.model = model
        if template is not None:
            self.template = template

    @property
    def api_key(self):
        """のゲッター"""
        return self._api_key

    @api_key.setter
    def api_key(self, value):
        self._api_key = value
        self._client = OpenAI(api_key=self.api_key)

    @property
    def model(self):
        """のゲッター"""
        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    @property
    def client(self):
        """のゲッター"""
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    @property
    def template(self):
        """のゲッター"""
        return self._template

    @template.setter
    def template(self, value):
        if not "{prompt}" in value:
            raise ValueError("template should include {prompt}.")
        self._template = value

    def get_response(self, text_in: str, use_template=True) -> str:
        """textを受け取って、応答する。

        Args:
            text_in (str): 入力文

        Returns:
            str: 出力文
        """

        if use_template:
            prompt = self.template.format(prompt=text_in)
        else:
            prompt = text_in

        chat_completion = self.client.chat.completions.create(
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

        return text_out

    def count_tokens(self, text_in: str, use_template=True):
        """指定されたモデルのトークナイザーを使用してテキストのトークン数を計算する。

        Args:
            text (str): トークン数を計算するテキスト。
            model (str): 使用するモデル（デフォルトは "gpt-3.5-turbo"）。

        Returns:
            int: テキストのトークン数。
        """

        if use_template:
            prompt = self.template.format(prompt=text_in)
        else:
            prompt = text_in

        encoding = tiktoken.encoding_for_model(self.model)
        tokenized = encoding.encode(prompt)
        return len(tokenized)

    def __call__(self, *args, **kwds):
        return self.get_response(*args, **kwds)

if __name__ == "__main__":

    MY_API = "sk-###"
    openai_chat = OpenAIChat(
        api_key=MY_API,
        model="gpt-4"
    )
    print(openai_chat.get_response("こんにちは"))

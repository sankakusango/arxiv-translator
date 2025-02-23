"""pip install"""
from setuptools import setup, find_packages

setup(
    name='arxiv_translator',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'arxiv-translate = arxiv_translator.cli:main',  # pyrnコマンド実行時にpyrn/cli.py内のmain()が呼ばれる
        ]
    },
)

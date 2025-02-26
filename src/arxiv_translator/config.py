from dataclasses import dataclass
from pathlib import Path
import logging
import os
import yaml
from colorama import Fore, Style

LOGGER = logging.getLogger(__name__)
HERE = Path(__file__).resolve().parent

def mask_openai_key(text: str, reveal: int=4, max_size=10):
    reveal = int(reveal)
    max_size = int(max_size)
    if text is None:
        text = "default"
    elif len(text) <=reveal:
        text = text
    else:
        text = text[:reveal] + "*" * min((len(text) - reveal), max_size)
    return text

def show(data: dict, 
         logger: logging.Logger, 
         border_color = Fore.BLUE, 
         text_color = Fore.CYAN):

    # "key: value"の形式でリスト化
    lines = [f"{key}: {value}" for key, value in data.items()]
    max_length = max(len(line) for line in lines)
    
    # Unicodeのボックス描画文字で枠を作成
    top_border = f"{border_color}┌{'─' * max_length}┐{Style.RESET_ALL}"
    bottom_border = f"{border_color}└{'─' * max_length}┘{Style.RESET_ALL}"
    
    logger.info(top_border)
    for line in lines:
        logger.info(f"{border_color}│{text_color}{line.ljust(max_length)}{border_color}│{Style.RESET_ALL}")
    logger.info(bottom_border)

@dataclass
class TranslatorConfig:
    """configデータを格納するクラス
    """
    openai_api_key: str
    working_dir: Path
    template_dir: Path
    output_dir: Path
    logger: logging.Logger = LOGGER

    def __post_init__(self):

        if str(self.openai_api_key).strip().lower() in ["", "none", "default"]:
            self.openai_api_key = None

        if isinstance(self.working_dir, Path):
            pass
        elif str(self.working_dir).strip().lower() in ["", "none"]:
            self.working_dir = HERE.parent.parent / "tmp"
        else:
            self.working_dir = Path(self.working_dir)

        if isinstance(self.template_dir, Path):
            pass
        elif str(self.template_dir).strip().lower() in ["", "none"]:
            self.template_dir = HERE.parent.parent / "templates"
        else:
            self.template_dir = Path(self.template_dir)

        if isinstance(self.output_dir, Path):
            pass
        elif str(self.output_dir).strip().lower() in ["", "none"]:
            self.output_dir = HERE.parent.parent / "outputs"
        else:
            self.output_dir = Path(self.output_dir)

    @classmethod
    def load(cls, logger: logging.Logger = LOGGER) -> "TranslatorConfig":
        """`~/.arxiv_translator/config.yaml`からconfigを読み込む.

        Returns:
            TranslatorConfig: 読み込まれたConfig
        """
        config_path = Path.home() / ".arxiv_translator" / "config.yaml"
        try:
            with config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            logger.info("loaded: %s", config_path)
            # 文字列で保存されているパスを Path オブジェクトに変換
            data["working_dir"] = Path(data["WORKING_DIR"])
            data["template_dir"] = Path(data["TEMPLATE_DIR"])
            data["output_dir"] = Path(data["OUTPUT_DIR"])
            loaded_data = {
                "openai_api_key": data["OPENAI_API_KEY"],
                "working_dir": Path(data["WORKING_DIR"]),
                "template_dir": Path(data["TEMPLATE_DIR"]),
                "output_dir": Path(data["OUTPUT_DIR"])
            }
            return cls(**loaded_data, logger=logger)
        except Exception as e:
            logger.warning("Load default config because could not find correct config. %s", e)
            default_config = TranslatorConfig(
                None,
                None,
                None,
                None,
                )
            return default_config

    def save(self):
        """`~/.arxiv_translator/config.yaml`にconfigを保存する."""
        config_dir = Path.home() / ".arxiv_translator"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.yaml"
        data = {
            "OPENAI_API_KEY": self.openai_api_key,
            "WORKING_DIR": str(self.working_dir),
            "TEMPLATE_DIR": str(self.template_dir),
            "OUTPUT_DIR": str(self.output_dir)
        }
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f)
        self.logger.info("saved: %s", config_path)
        # ファイルのパーミッションを所有者のみ (rw-------) に設定
        os.chmod(config_path, 0o600)
        self.logger.info("permittion only to rw-------: %s", config_path)

    def show(self):
        data = {
            "OPENAI_API_KEY": mask_openai_key(self.openai_api_key),
            "WORKING_DIR": str(self.working_dir),
            "TEMPLATE_DIR": str(self.template_dir),
            "OUTPUT_DIR": str(self.output_dir)
        }
        show(data = data, logger = self.logger)
            
if __name__ == "__main__":
    config = TranslatorConfig.load()
    config.show()
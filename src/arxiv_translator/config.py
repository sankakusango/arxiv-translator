from dataclasses import dataclass
from pathlib import Path
import logging
import os
import yaml

logger = logging.getLogger(__name__)
here = Path(__file__).resolve().parent

@dataclass
class TranslatorConfig:
    """configデータを格納するクラス
    """
    openai_api_key: str
    working_dir: Path
    template_dir: Path
    output_dir: Path

    def __post_init__(self):

        if str(self.openai_api_key).strip().lower() in ["", "none", "default"]:
            self.openai_api_key = None

        if isinstance(self.working_dir, Path):
            pass
        elif str(self.working_dir).strip().lower() in ["", "none"]:
            self.working_dir = here.parent.parent / "data/tmp"
        else:
            self.working_dir = Path(self.working_dir)

        if isinstance(self.template_dir, Path):
            pass
        elif str(self.template_dir).strip().lower() in ["", "none"]:
            self.template_dir = here.parent.parent / "templates"
        else:
            self.template_dir = Path(self.template_dir)

        if isinstance(self.output_dir, Path):
            pass
        elif str(self.output_dir).strip().lower() in ["", "none"]:
            self.output_dir = here.parent.parent / "data"
        else:
            self.output_dir = Path(self.output_dir)

    @classmethod
    def load(cls) -> "TranslatorConfig":
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
            return cls(**loaded_data)
        except Exception as e:
            logger.warning("Load default config because could not find correct config. %s", e, exc_info=True)
            default_config = TranslatorConfig(
                None,
                None,
                None,
                None,
                )
            return default_config

    def save(self):
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
        logger.info("saved: %s", config_path)
        # ファイルのパーミッションを所有者のみ (rw-------) に設定
        os.chmod(config_path, 0o600)
        logger.info("permittion only to rw-------: %s", config_path)

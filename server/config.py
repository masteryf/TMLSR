import os
import yaml

class Settings:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            # Fallback if config is not found, though expected to be in root
            print(f"Warning: {self.config_path} not found. Using defaults.")
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def oss_config(self):
        return self._config.get("oss", {})

    @property
    def max_workers(self):
        return self._config.get("server", {}).get("max_workers", 2) # Limit concurrent heavy tasks

    @property
    def max_retries(self):
        return self._config.get("server", {}).get("max_retries", 3)

    @property
    def retry_delay(self):
        return self._config.get("server", {}).get("retry_delay", 5)

settings = Settings()

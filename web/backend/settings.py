from lib.settings import CoreSettings


class Settings(CoreSettings):
    web_host: str = "0.0.0.0"
    web_port: int = 8001


settings = Settings()

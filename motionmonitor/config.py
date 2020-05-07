class Config:
    ZABBIX_SERVER_ADDR = "192.168.0.83"
    JSON_SOCKET_ADDR = "192.168.0.89"
    JSON_SOCKET_PORT = 8889
    MOTION_SOCKET_ADDR = "127.0.0.1"
    MOTION_SOCKET_PORT = 8888
    DB_SERVER_ADDR = "192.168.0.83"
    DB_NAME = "motion"
    DB_USER = "motion"
    DB_PASSWORD = "motion"
    LOGGING_FILENAME = "motion-motionmonitor.log"
    LOGGING_LEVEL = "INFO"
    TARGET_DIR = "/data/motion"


class Production(Config):
    ENV = 'prod'
    DEBUG = False
    API_URL = '/api'


class Development(Config):
    ENV = 'dev'
    DEBUG = True

    JSON_SOCKET_ADDR = "127.0.0.1"
    API_URL = 'http://127.0.0.1:5000/api'


class Testing(Config):
    TESTING = True
    DEBUG = True
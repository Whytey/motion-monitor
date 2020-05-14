class Config:
    ZABBIX_SERVER_ADDR = "192.168.0.83"
    MOTION_SOCKET_ADDR = "127.0.0.1"
    MOTION_SOCKET_PORT = 8888
    WEB_SERVER_ADDR = "127.0.0.1"
    WEB_SERVER_PORT = 8080
    DB_SERVER_ADDR = "192.168.0.83"
    DB_NAME = "motion"
    DB_USER = "motion"
    DB_PASSWORD = "motion"
    LOGGING_FILENAME = "motion-monitor.log"
    LOGGING_LEVEL = "INFO"
    TARGET_DIR = "/data/motion/"
    MOTION_FILENAME = 'motion/camera%t/%Y%m%d/%C/%Y%m%d-%H%M%S-%q'
    SNAPSHOT_FILENAME = 'snapshots/camera%t/%Y/%m/%d/%H/%M/%S-snapshot'


class Production(Config):
    ENV = 'prod'
    DEBUG = False
    API_URL = '/api'


class Development(Config):
    ENV = 'dev'
    DEBUG = True
    TARGET_DIR = "/tmp/"
    API_URL = 'http://127.0.0.1:5000/api'
    DB_NAME = "motion-dev"


class Testing(Config):
    TESTING = True
    DEBUG = True
    MOTION_SOCKET_PORT = 9999

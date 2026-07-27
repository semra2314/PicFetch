OVERFETCH = 2
DETECT_THRESHOLD = 0.25
DOWNLOAD_TIMEOUT = 8
DOWNLOAD_RETRIES = 2
SEARCH_RETRIES = 3
SEARCH_RETRY_DELAY = 3
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_COUNT = 50  # kullanıcının girebileceği count üst sınırı - anormal girdinin sunucuyu düşürmesini engeller
# (count × OVERFETCH ≤ 325 mantığı)

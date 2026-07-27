# --- Arama / getirme ---

OVERFETCH = 2
# Ne işe yarar: Arama sonucundan istenenden kaç kat fazla görsel çekileceği
#   (ör. 5 görsel isteniyorsa 5*OVERFETCH=10 tanesi getirilir).
# Neden bu değer: Bazı sonuçlar indirme/doğrulama aşamasında elenebiliyor;
#   2x pay, tipik elenme oranında istenen sayıya ulaşmayı garantiliyor.
# Değişirse: Artarsa -> gereksiz indirme/ağ trafiği ve maliyet artar.
#   Azalırsa (1'e yakın) -> eleme sonrası istenen sayıya ulaşamama riski artar.

DETECT_THRESHOLD = 0.25
# Ne işe yarar: Nesne tespit modelinin bir tespiti "geçerli" sayması için
#   gereken minimum güven skoru.
# Neden bu değer: Model çıktıları üzerinde yapılan deneylerde false-positive/
#   false-negative dengesini bu seviyede kabul edilebilir bulduk.
# Değişirse: Yükselirse -> daha az ama daha güvenilir tespit (bazı gerçek
#   nesneler kaçabilir). Düşerse -> daha fazla tespit ama gürültü/yanlış
#   pozitif oranı artar.

# --- İndirme ---

DOWNLOAD_TIMEOUT = 8
# Ne işe yarar: Bir görselin indirilmesi için beklenecek maksimum süre (sn).
# Neden bu değer: Çoğu görsel host'u bu sürede yanıt veriyor; daha uzun
#   beklemek toplu indirmede tıkanmaya yol açıyor.
# Değişirse: Artarsa -> yavaş sunuculardan da indirme şansı artar ama toplam
#   iş süresi uzar. Azalırsa -> yavaş bağlantılarda gereksiz timeout hataları.

DOWNLOAD_RETRIES = 2
# Ne işe yarar: Bir indirme timeout/hata verirse kaç kez daha denenecek.
# Neden bu değer: Geçici ağ hatalarının çoğu 1-2 denemede çözülüyor;
#   fazlası toplam süreyi anlamsız şekilde uzatıyor.
# Değişirse: Artarsa -> geçici hatalara karşı dayanıklılık artar ama toplam
#   süre uzar. Azalırsa (0) -> geçici hatalarda bile görsel tamamen kaybolur.

# --- Kaynak arama servisi ---

SEARCH_RETRIES = 3
# Ne işe yarar: Arama servisi (ör. rate limit/5xx) hata verirse kaç kez
#   tekrar denenecek.
# Neden bu değer: Servisin geçici hatalarının çoğu birkaç denemede geçiyor;
#   deneyimsel olarak 3 yeterli bulundu.
# Değişirse: Artarsa -> geçici servis kesintilerine dayanıklılık artar ama
#   hata durumunda toplam bekleme uzar. Azalırsa -> geçici hatalarda erken
#   pes edilir, arama başarısız sayılır.

SEARCH_RETRY_DELAY = 3
# Ne işe yarar: Tekrar denemeler arasında beklenecek süre (sn).
# Neden bu değer: Rate-limit'in genelde bu sürede sıfırlandığı gözlemlendi;
#   ayrıca servisi art arda yeniden bombalamamak için bir tampon sağlıyor.
# Değişirse: Artarsa -> servise nazik davranılır ama toplam süre uzar.
#   Azalırsa -> rate limit'e tekrar takılma riski artar.

# --- Dosya doğrulama ---

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
# Ne işe yarar: İndirilen bir görselin kabul edilecek maksimum boyutu.
# Neden bu değer: Kullanım senaryosundaki görseller için 10MB fazlasıyla
#   yeterli; daha büyükleri genelde hatalı/şişirilmiş dosya ya da
#   istenmeyen içerik olabiliyor.
# Değişirse: Artarsa -> disk/bellek kullanımı ve indirme süresi artabilir.
#   Azalırsa -> yüksek çözünürlüklü meşru görseller reddedilebilir.

# --- Depolama ---

DOWNLOADS_DIR = "data/downloads"
# Ne işe yarar: İndirilen görsellerin yazılacağı kök klasör.
# Neden bu değer: Karar 7'de belirlenen standart yol; proje kökünden
#   göreli olduğu için farklı ortamlarda (dev/CI) tutarlı çalışır.
# Değişirse: Testlerin geçici klasör (tmp_path) verebilmesi için config
#   üzerinden okunmalı — koda gömülü olursa testler prod klasörüne yazar.

MODEL_NAME = "yoloe-26m-seg.pt"
# Ne işe yarar: Nesne tespiti için kullanılan model dosyasının adı.
# Neden bu değer: Şu an detector.py içinde sabit kodlanmış; buraya taşınıyor
#   ki model boyutu/versiyonu değiştirilmek istendiğinde (ör. canlıda
#   performans/doğruluk denemesi) tek satır değişip yeniden başlatmak yetsin.
# Değişirse: Model dosyasının proje içinde/erişilebilir yolda bulunması
#   gerekir; aksi halde detector başlatılamaz.

MAX_COUNT = 50
# Ne işe yarar: Tek istekte istenebilecek maksimum görsel sayısı.
# Neden bu değer: Geçici/tahmini
# Değişirse: Gerçek yük MAX_COUNT × OVERFETCH'tir (bugün 100 indirme +
#   100 çıkarım). Bu yüzden MAX_COUNT, OVERFETCH ve MAX_FILE_SIZE birbiriyle
#   bağlantılı — biri değiştiğinde diğer ikisi de gözden geçirilmeli
#   (toplam indirme hacmi ve disk/bellek etkisini birlikte değerlendirin).

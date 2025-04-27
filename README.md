# TraderHub: Prompt Tabanlı İşlem Açma ve Sentiment Analizi Sistemi

TraderHub, finansal işlemleri prompt tabanlı yönetmek için geliştirilmiş bir platformdur. Kullanıcılar, sistem üzerinden **prompt tabanlı** alım-satım işlemleri gerçekleştirebilirler. Ayrıca, **Reddit verileri** üzerinden yapılan sentiment analizi ile piyasa duyarlılığını ölçer ve bu veriye dayalı işlem stratejileri geliştirilebilir. İşlemler BINANCE Testnet kısmında gerçekleştirilir. Canlı olarak takip edilebilir işlemler, kapatılabilir veya açılan işlemler iptal edilebilir.

---

## Özellikler

### 1. **Prompt Tabanlı İşlem Açma**
TraderHub, kullanıcıların **belirli işlem çiftleri ve stratejilerle** alım-satım işlemleri yapmalarına olanak tanır. Kullanıcılar işlem yapmak için belirli bir prompt girerler, sistem buna karşılık işlem açar. 

#### **Örnek Prompt:**
```
Bana 65000$ 10x lev 250 dolar long aç
```
Bu prompt, sistem tarafından işlenir ve alım-satım işlemi başlatılır. Kullanıcı işlem açıldığında sonucu **Open Orders** kısmında görebilir.

#### **İşlem Sonucu:**
```
Processing request..

Your request was successful.
You can check at 'Positions & Orders'.
"{'symbol': 'BTCUSDT', 'side': 'BUY', 'price': 65000.0, 'leverage': 10, 'position_size': 250.0}"

```
### 2. **Sentiment Analizi**
TraderHub, **Reddit verilerini** analiz ederek piyasa duyarlılığını ölçer. Kullanıcılar, işlem yapmak istedikleri kripto para birimleri hakkında Reddit üzerindeki yorumları analiz edebilir ve **sentiment score** alabilirler. Bu duygu analizi, yatırım kararlarını desteklemek için kullanılır.

#### **Sentiment Analiz Sonucu:**
```
Sentiment analysis from Reddit data:

Positive: ███████████ 85%
Negative: ██ 10%
Neutral:  ███ 15%

Reddit data shows a strongly positive sentiment towards Bitcoin (BTC), with a smaller portion expressing negative or neutral views. The data likely reflects a community already invested in or bullish on the cryptocurrency.
```
---

## Kullanıcı Akışı

TraderHub üzerinden işlem yapma süreci şu şekilde işler:

1. **Prompt ile İşlem Açma**:  
   Kullanıcılar, işlem yapmak istedikleri piyasa çiftini ve stratejiyi belirten bir **prompt** girerler. Bu işlem anında işleme alınır.

2. **Sentiment Analizi**:  
   Kullanıcılar, işlem yapacakları kripto para biriminin **Reddit üzerindeki duyarlılık analizini** talep edebilir. Bu analiz, pozitif, negatif veya nötr yorum oranlarını gösterir.

3. **İşlem Sonucu**:  
   İşlem açıldıktan sonra, kullanıcıya işlem detayları döndürülür. Bu işlem sonuçları **pozisyonlar ve siparişler** sekmesinde takip edilebilir.

---

## Proje Yapısı
```
TraderHub projesinin yapısı aşağıdaki gibi düzenlenmiştir:
TraderHub/
│
├── app.py                                  # Ana Flask uygulama dosyası
├── requirements.txt                        # Library listesi
├── binance_future_process.py               # Binance API tarafı işlem modülü
├── data/BTC/                               
│   ├── tweets_2025-04-27.csv               # Fetch edilmiş Reddit Data
├── instance/                               # Db
│   ├── users.db
├── flask_app.py                            # Flask API
├── token_manager_async.py                  # Token yönetim scripti
├── web_css.css                             # Streamlit için .css düzenlemeleri
├── main.py                                 # Base script file
├── streamlit_app.py                        # Streamlit 
└── README.md                               # Proje açıklaması
```

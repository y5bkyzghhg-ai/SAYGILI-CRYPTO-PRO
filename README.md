# SAYGILI CRYPTO PRO — Safari mobil prototip

Binance USDⓈ-M Futures halka açık verileriyle çalışan **yalnızca sanal işlem** paneli. API anahtarı gerekmez; gerçek emir göndermez. Teknik analiz ve emir defteri görüntüsü içerir. 2x–125x seçimi temsili olup gerçek borsa limitlerini doğrulamaz.

## iPhone'da açmak için yayınlama
1. ZIP içeriğini bir GitHub deposuna yükleyin (`app.py`, `requirements.txt`, `.streamlit/config.toml`).
2. https://share.streamlit.io/ adresinde GitHub hesabıyla oturum açıp **Create app** seçin.
3. Depo, dal `main` ve ana dosya `app.py` seçerek uygulamayı yayınlayın.
4. Verilen HTTPS adresini iPhone Safari'de açın; Paylaş > Ana Ekrana Ekle.

**Önemli:** Bu dosyalar henüz internete yüklenmedi. Streamlit Community Cloud kaynak ve uyku sınırları nedeniyle 7/24 bot sunucusu değildir. Oturum verileri kalıcı değildir; sayfa/oturum yenilenince sanal işlemler kaybolabilir. Bazı ülkelerde Binance Futures API erişimi kısıtlıdır. İnternette herkese açık yayımlarsanız panel başkalarınca da görülebilir. Gerçek para yatırmayın ve API anahtarı eklemeyin.

## Yerel geliştirme
`pip install -r requirements.txt` ardından `streamlit run app.py`.

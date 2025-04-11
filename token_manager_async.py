import asyncio
import aiohttp
import time,jwt
from cryptography.fernet import Fernet
import dotenv,os,json


dotenv.load_dotenv()
cipher = Fernet(os.environ['data_secret_key'])

class AsyncTokenManager:
    def __init__(self, login_url, username, password, token_expiry=3600):
        self.login_url = login_url
        self.username = username
        self.password = password
        self.token = None
        self.token_expiry = token_expiry  # Token geçerlilik süresi (saniye)
        self.token_timestamp = 0  # Token alındığı zaman
        self.session = None
        self.lock = asyncio.Lock()  # Token yenilemek için kilit mekanizması
    
    async def ensure_session(self):
        """Session yoksa yeni bir tane oluştur"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def login(self):
        """API'ye login olup token alır"""
        await self.ensure_session()
        
        async with self.lock:  # Birden fazla isteğin aynı anda login olmasını engelle
            # Token süresi dolmadıysa yeni token alma
            current_time = time.time()
            if self.token and (current_time - self.token_timestamp) < self.token_expiry:
                return self.token
            
            print("Login işlemi yapılıyor...")
            try:
                async with self.session.post(
                    self.login_url,
                    json={"username": self.username, "password": self.password}
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Login hatası: {response.status}")
                    
                    data = await response.json()
                    decrypted_data = cipher.decrypt(data.get("token").encode())
                    self.token=json.loads(decrypted_data.decode())
                    self.token_timestamp = time.time()
                    
                    if not self.token:
                        raise Exception("Token alınamadı")
                    
                    print("Token başarıyla alındı")
                    return self.token
            except Exception as e:
                print(f"Login hatası: {e}")
                raise
    
    async def get_data(self, endpoint):
        """Verilen endpoint'ten veri çeker, gerekirse token yeniler"""
        await self.ensure_session()
        
        # Token yoksa veya süresi geçtiyse yeni token al
        current_time = time.time()
        if not self.token or (current_time - self.token_timestamp) >= self.token_expiry:
            await self.login()
        
        # Veriyi çek
        headers = {"Authorization": f"Bearer {self.token}"}
        async with self.session.get(endpoint, headers=headers) as response:
            if response.status == 401:  # Yetkisiz erişim (token geçersiz)
                print("Token geçersiz, yenileniyor...")
                self.token_timestamp = 0
                await self.login()
                headers = {"Authorization": f"Bearer {self.token}"}
                async with self.session.get(endpoint, headers=headers) as retry_response:
                    return await retry_response.json()
            elif response.status != 200:
                raise Exception(f"Veri çekme hatası: {response.status}")
            
            return await response.json()
    async def post_data(self, endpoint,data):
        """Verilen endpoint'ten veri çeker, gerekirse token yeniler"""
        await self.ensure_session()
        
        # Token yoksa veya süresi geçtiyse yeni token al
        current_time = time.time()
        if not self.token or (current_time - self.token_timestamp) >= self.token_expiry:
            await self.login()
        
        # Veriyi çek
        headers = {"Authorization": f"Bearer {self.token}"}
        async with self.session.post(endpoint,json=data, headers=headers) as response:
            if response.status == 401:  # Yetkisiz erişim (token geçersiz)
                print("Token geçersiz, yenileniyor...")
                self.token_timestamp = 0
                await self.login()
                headers = {"Authorization": f"Bearer {self.token}"}
                async with self.session.post(endpoint,json=data, headers=headers) as retry_response:
                    return await retry_response.json()
            elif response.status != 201:
                raise Exception(f"Veri çekme hatası: {response.status}")
            
            return await response.json()
    async def close(self):
        """Session'ı kapatır ama token'ı korur"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            print("Session kapatıldı, token korundu")
import os
import time
import threading
import warnings
import asyncio,jwt
import aiohttp
import signal
import google.generativeai as genai

import binance_future_process
from binance_future_process import get_klines_data as kline
from binance_future_process import connect_future_binance
from binance_future_process import connect_binance
from binance_future_process import precision_asset
from binance_future_process import new_order
from binance_future_process import change_leverage
from binance_future_process import all_margin_orders
from binance_future_process import stream_events_symbol
from binance_future_process import get_open_orders
from binance_future_process import get_order_book
from binance_future_process import get_future_balance_assets
from binance_future_process import check_position

from token_manager_async import AsyncTokenManager



import streamlit as st
import requests,json
import dotenv


dotenv.load_dotenv()
thread_list=[]
#thread_list.pop(1)
symbol='BTCUSDT'
interval='1d'
client=connect_binance(binance_future_process.api_key, binance_future_process.api_secret)
cm_futures_client=connect_future_binance(binance_future_process.api_key,binance_future_process.api_secret)
google_api=os.environ['gemini_key']
token_manager = AsyncTokenManager("http://127.0.0.1:5000/login",os.environ['user_id'],os.environ['pw'])


def run_stream(*args):
    stream.run()
   
stream=stream_events_symbol(symbol='BtcUsdt',interval=interval)
#stream.ws.close()
#thread = threading.Thread(target=run_stream,name="websocket")
#thread_list.append(thread)

class ThreadManager:
    def __init__(self):
        # Thread'ler için stop event'ları
        self.stop_events = {
            "websocket": threading.Event(),
            #"flask_app": threading.Event()
            # Gerekirse diğer thread'ler için de ekleyebilirsiniz
        }
        
        # Thread tanımlamaları
        self.thread_dict = {
            "websocket": None,
            #"flask_app": None
        }

    def create_websocket_thread(self):
        # Her thread için ayrı bir stop event kullanın
        websocket_stop_event = self.stop_events["websocket"]
        def run_websocket(websocket_stop_event):
            while not websocket_stop_event.is_set():
                try:
                    # flask app çalışma mantığı
                    run_stream(websocket_stop_event)
                except Exception as e:
                    print(f"websocket thread hatası: {e}")
                    break
            
        thread = threading.Thread(target=run_websocket,args=(websocket_stop_event,), name="websocket")
        self.thread_dict['websocket']=thread
        return thread

    def check_threads(self, thread_list):
        for index, thr in enumerate(thread_list):
            if not thr.is_alive():
                print(f"{thr.name} thread beklenmedik şekilde durdu.")
                
                # Eski thread'in stop event'ını set et
                if thr.name in self.stop_events:
                    self.stop_events[thr.name].set()
                
                # Yeni thread oluştur
                if thr.name == "websocket":
                    new_thread = self.create_websocket_thread()
                elif thr.name == "flask_app":
                    new_thread = self.create_flask_thread()
                else:
                    continue
                
                # Yeni stop event'ı resetle
                self.stop_events[thr.name].clear()
                
                # Yeni thread'i başlat
                new_thread.start()
                
                # Thread listesini güncelle
                thread_list[index] = new_thread
                
                print(f"{thr.name} thread'i yeniden başlatıldı.")
                time.sleep(4)
            else:
                print("ALl threads running.")

    def stop_all_threads(self):
        # Tüm thread'leri güvenli bir şekilde durdur
        for name, stop_event in self.stop_events.items():
            if name=='websocket':
                self.thread_dict[name]._args[0].set()
                stream.ws.close()
            else:
                self.thread_dict[name]._args[0].set()
            


def post_assets():
    data=get_future_balance_assets(client)
    asset_name=['Balance_USDT','Margin_USDT']
    balance_r=[float(data.loc[4,'balance']),(float(data.loc[4,'balance'])-float(data.loc[4,'crossWalletBalance']))]
    data=data.append([data.copy()],ignore_index=True)
    data['asset_name']=asset_name
    data['balance_r']=balance_r
    json_list = json.loads(json.dumps(list(data.T.to_dict().values())))
    

    return json_list

def post_realtime(stream):
    if hasattr(stream, 'klines_df') and stream.klines_df is not None:
        data = stream.klines_df
        pair_data = {key: value.values[0] if data[key].dtypes != '<M8[ns]' else str(value.values[0]) for key, value in data.items()}
        return pair_data
    else:
        return {"error": "Stream data not available"}

def post_openPosition():
    return check_position(client)


    
# Kullanım
"""
token_manager = TokenManager(
    login_url='http://127.0.0.1:5000/login',
    username=os.environ['user_id'],
    password=os.environ['pw']
)"""
  

#{symbol} {price} dolardan/$/dolar {leverage}x {amount} $/dolar {side} open/close/long/short
async def gemini_request(token_manager):
    
    genai.configure(api_key=google_api)
    model = genai.GenerativeModel("gemini-1.5-flash")
    system_instruction = """
        You are a parser bot. You can't respond to anything else, you don't have knowledge. If you get any text, you need to parse it in both Turkish and English.
        
        Parse inputs containing information about trading positions with these required fields:
        - symbol (e.g., BTC, ETH) text - Automatically append USDT to form a trading pair (e.g., BTCUSDT) unless another pair is specified
        - side (open, close, long, short) text 
        - price (number, without currency symbols) float 
        - leverage (number followed by x) int
        - position_size (amount, without currency) float 
        
        Output format:
        If all required fields are found and clear, return:
        {"symbol": symbol, "side": side, "price": price, "leverage": leverage, "position_size": amount}
        
        If any required field is missing, irrelevant, or ambiguous, return:
        I can't do that your request. My responsibility just Open/close Margin operations. You have to send like this theme or similar: ETH 3200$ short position 5x leverage 1000$
        "missing": list the missing fields
        
        The input can have these elements in any order. Look for specific keywords to identify each field.
        """

    test_inputs = [
    "BTC 62000 dolardan 10x 500 dolar long open",
    "ETH 3200$ short position 5x leverage 1000$",
    "Bugün hava nasıl olacak?",
    "SOL position close at 145$ from 20x 300$",
    "En iyi pizza tarifi nedir?",
    "AVAX 35$ long 15x for 250 dolar open position",
    "Bana bir film önerir misin?",
    "DOT 8.5 dolardan 4x 150 dolar short",
    "2+2 kaç eder?",
    "LINK 18$ open long with 8x leverage 400$",
    "DOGE 0.12$ 3x 200$ short close",
    "Yarın için randevu alabilir miyim?",
    "XRP 0.55 dolardan 15x 300 dolar long open",
    "Yeni telefon önerilerin var mı?",
    "ADA 0.4$ short 12x position 150 dolar",
    "Python öğrenmek istiyorum nereden başlamalıyım?",
    "SHIB 0.00002$ 10x 75$ long position open",
    "Nasıl kilo verebilirim?",
    "UNI 8$ dolardan 7x 200 dolar short close",
    "Akşam yemeği için ne pişirsem?",
    "MATIC 0.75$ 8x 400$ long position",
    "Hangi kitabı okumalıyım?",
    "NEAR 3.2 dolardan 5x 120 dolar short open",
    "Bana bir joke anlatır mısın?",
    "ATOM 8.9$ close long with 10x leverage 250$",
    "İstanbul'da görülecek yerler nerelerdir?",
    "LTC 80 dolardan 6x 180 dolar short position",
    "Kedi mi köpek mi daha iyi evcil hayvan?",
    "DOT position long at 9$ from 7x 220$",
    "Borsa nasıl çalışır?",
    "AAVE 95$ 12x 300$ short open",
    "Sağlıklı kahvaltı önerileri verebilir misin?",
    "ALGO 0.25 dolardan 15x 130 dolar long close",
    "En iyi online kurslar hangileri?",
    "COMP 42$ short position 9x for 175 dolar",
    "Nasıl meditasyon yapılır?",
    "FTM 0.5$ 20x 80$ long open position",
    "2025'te teknoloji nasıl olacak?",
    "ZEC 65 dolardan 4x 210 dolar short close",
    "En iyi kahve nasıl yapılır?",
    "SNX 3.4$ long 6x for 95 dolar open",
    "Kripto para nedir?",
    "CRV 0.85$ position 12x 140$ short",
    "Seyahat için en iyi ülkeler hangileri?",
    "1INCH 0.45 dolardan 18x 75 dolar long",
    "Nasıl daha iyi uyuyabilirim?",
    "ENJ 0.38$ short position 10x for 120$",
    "En popüler spor hangisi?",
    "GRT 0.15 dolardan 25x 60 dolar long open",
    "Yapay zeka hakkında ne düşünüyorsun?"
    ]
    lps=True
    processed_prompt_ids = set()
    while lps:
        Output=[]
        try:
            inputs=await token_manager.get_data('http://127.0.0.1:5000/api/data/get_prompt')
            prompt_id = inputs['data']['id']
            print("id:",prompt_id)
            if prompt_id in processed_prompt_ids:
                print("still_id:",prompt_id)
                await asyncio.sleep(2)
                continue
            else:
                processed_prompt_ids.add(prompt_id)
                print(processed_prompt_ids)
                #print(inputs)
                if (inputs['data']['answer'] is None): 
                    user_input=inputs['data']['prompt_text']
                    gemini_messages = []
                    gemini_messages.append({"role": "user", "parts": [system_instruction]})
                    gemini_messages.append({"role": "user", "parts":user_input})
                    response = model.generate_content(gemini_messages)
                    print("response:",response.text.replace("```json", "").replace("```", ""))
                    cleaned_json_str = response.text.replace("```json", "").replace("```", "").strip()
                    print("uzunluk:",len(cleaned_json_str))
                    if len(cleaned_json_str)<150:
                        print("içerdeyiz")
                        response_json=json.loads(cleaned_json_str)
                        Output.append(response_json)
                        print("response:",response_json)
                        levereage=change_leverage(client,response_json['symbol'],response_json['leverage'])
                        print("levereage:",levereage)
                        time.sleep(0.2)
                        precsion_order_amount, price = precision_asset(client, response_json['symbol'], leverage=response_json['leverage'], price=response_json['price'], trade_size=response_json['position_size'])
                        time.sleep(0.2)
                        print("precsion_order_amount:",precsion_order_amount)
                        if (response_json['side']=='short') | (response_json['side']=='close'):
                            response_json['side']='SELL'
                        else:
                            response_json['side']='BUY'
                        response_order=new_order(client,symbol=response_json['symbol'],side=response_json['side'],type='LIMIT',price=response_json['price'],quantity=precsion_order_amount)
                        time.sleep(0.2)
                        print("response_order:",response_order)
                        data={'prompt_text':inputs,'answer':response_json}
                        #print("Doğru Tanımlama blogu: ",data)
                        await token_manager.post_data('http://127.0.0.1:5000/api/data/post_prompt',data)
                    else:
                        data={'prompt_text':inputs,'answer':cleaned_json_str}
                        #print("Yanlış Tanımlama blogu: ",data)
                        await token_manager.post_data('http://127.0.0.1:5000/api/data/post_prompt',data)
                else:
                    await asyncio.sleep(2)
        except:
            await asyncio.sleep(2)
            pass
# activate traderhub && cd OneDrive\Masaüstü\TraderHub && python main.py
async def periodic_task(token_manager, endpoint,interval,func):
    """Belirli aralıklarla veri gönderen periyodik görev"""
    while True:
        try:
            
            # Eğer data_func bir fonksiyon ise çağırıyoruz
            if endpoint == "http://127.0.0.1:5000/api/data/post_realtime":
                data =func(stream)
            else:
                data = func() if callable(func) else func
                
            result = await token_manager.post_data(endpoint, data)
            
            
        except aiohttp.ClientResponseError as e:
            if e.status == 401:
                print(f"{endpoint} - Token expired, refreshing token...")
                try:
                    # Force token refresh
                    await token_manager.login()
                    print(f"{endpoint} - Token refreshed, retrying request...")
                    
                    # Retry the request with new token
                    if endpoint == "http://127.0.0.1:5000/api/data/post_realtime":
                        data = func(stream)
                    else:
                        data = func() if callable(func) else func
                    
                    result = await token_manager.post_data(endpoint, data)
                except Exception as refresh_error:
                    print(f"{endpoint} - Token refresh failed: {refresh_error}")
            else:
                print(f"{endpoint} - HTTP error: {e}")
        except Exception as e:
            print(f"{endpoint} - General error: {e}")
        
        await asyncio.sleep(interval)  # Belirtilen süre kadar bekle
async def all_requests():

    realtime_task = asyncio.create_task(
        periodic_task(token_manager, 'http://127.0.0.1:5000/api/data/post_realtime', 
                              2,post_realtime))
    
    positions_task = asyncio.create_task(
        periodic_task(token_manager, 'http://127.0.0.1:5000/api/data/post_open_positions', 
                              5, post_openPosition))
    
    assets_task = asyncio.create_task(
        periodic_task(token_manager, 'http://127.0.0.1:5000/api/data/post_assets', 
                              10,post_assets))
    prompt_task = asyncio.create_task(gemini_request(token_manager))
    # Tüm görevlerin sonsuza kadar çalışmasını sağla
    await asyncio.gather(realtime_task, positions_task, assets_task,prompt_task)
            
             
    
        
                    
                    
thread_manager = ThreadManager()
def main(): 
    # İlk thread'leri oluştur
    websocket_thread = thread_manager.create_websocket_thread()
    #flask_thread = thread_manager.create_flask_thread()

    # Thread listesini oluştur
    thread_list = [websocket_thread]
    
    # Thread'leri başlat
    for thread in thread_list:
        thread.start()

    thread_manager.check_threads(thread_list)
    time.sleep(5)
    #thread_manager.stop_all_threads()
async def shutdown():
    """Program kapatıldığında tüm task'leri sonlandır ve session'ı kapat"""
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    for task in tasks:
        task.cancel()
    
    print("Tüm görevler iptal edildi. Token yöneticisi kapatılıyor...")
    await token_manager.close()
    
def setup_shutdown_handler():
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda sig, frame: shutdown())
    signal.signal(signal.SIGINT, lambda sig, frame: shutdown())
    
async def run_all():
    loop = asyncio.get_event_loop()
    #loop.create_task(shutdown())
        
    main()
    await asyncio.sleep(5)
    
    try:
        await all_requests()
        thread_manager.check_threads(thread_list)
    except KeyboardInterrupt:
        await shutdown()


if __name__ == "__main__":
    asyncio.run(run_all())



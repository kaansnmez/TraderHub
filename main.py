from haystack import Pipeline
from haystack.components.preprocessors import DocumentCleaner,DocumentSplitter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder,SentenceTransformersTextEmbedder
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack.document_stores.types import FilterPolicy

from haystack.dataclasses import ChatMessage,Document
from haystack.components.routers import ConditionalRouter
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.websearch import SerperDevWebSearch
from haystack.components.builders import ChatPromptBuilder
from haystack_integrations.components.generators.google_ai.chat.gemini import GoogleAIGeminiChatGenerator
from pathlib import Path
from transformers import pipeline
import asyncpraw

import os
import time
import threading
import warnings
import asyncio
import aiohttp
import signal
import pandas as pd
from datetime import datetime,timedelta
import json
import dotenv,subprocess
import traceback

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
from binance.exceptions import BinanceAPIException

from token_manager_async import AsyncTokenManager




dotenv.load_dotenv()
thread_list=[]
#thread_list.pop(1)
symbol='BTCUSDT'
interval='1d'
client=connect_binance(binance_future_process.api_key, binance_future_process.api_secret)
cm_futures_client=connect_future_binance(binance_future_process.api_key,binance_future_process.api_secret)
tw_bearer_token=os.environ['tw_bearer']
host='https://traderhub-flask.onrender.com'
token_manager = AsyncTokenManager(f"{host}/login",os.environ['user_id'],os.environ['pw'])

document_store=InMemoryDocumentStore()
existing_documents =document_store.filter_documents(filters={})# Index Pipeline
existing_ids = [doc.id for doc in existing_documents]
document_store.delete_documents(existing_ids)

def flasks(*args):
    subprocess.run(["python", r"flask_app.py"])
def streamlit(*args):
    subprocess.run(["streamlit","run", r"streamlit_app.py"])
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
            "flask_app": threading.Event(),
            "streamlit_app":threading.Event()
            # Gerekirse diğer thread'ler için de ekleyebilirsiniz
        }
        
        # Thread tanımlamaları
        self.thread_dict = {
            "websocket": None,
            "flask_app": None,
            "streamlit_app": None
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
    
    def create_streamlit_thread(self):
        # Her thread için ayrı bir stop event kullanın
        streamlit_stop_event = self.stop_events["flask_app"]
        def run_streamlit(streamlit_stop_event):
            while not streamlit_stop_event.is_set():
                try:
                    # flask app çalışma mantığı
                    streamlit(streamlit_stop_event)
                except Exception as e:
                    print(f"websocket thread hatası: {e}")
                    break
            
        thread = threading.Thread(target=run_streamlit,args=(streamlit_stop_event,), name="streamlit_app")
        self.thread_dict['streamlit_app']=thread
        return thread
    def create_flask_thread(self):
        # Her thread için ayrı bir stop event kullanın
        flask_stop_event = self.stop_events["flask_app"]
        def run_flask(flask_stop_event):
            while not flask_stop_event.is_set():
                try:
                    # flask app çalışma mantığı
                    flasks(flask_stop_event)
                except Exception as e:
                    print(f"websocket thread hatası: {e}")
                    break
            
        thread = threading.Thread(target=run_flask,args=(flask_stop_event,), name="flask_app")
        self.thread_dict['flask_app']=thread
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
                elif thr.name == "streamlit_app":
                    new_thread = self.create_streamlit_thread()
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
  
def retry_order(client, symbol, side, order_type, price, quantity, max_retries=3, delay_seconds=2):
    """
    Attempt to place an order with retries on timeout errors.
    
    Args:
        client: Binance client instance
        symbol: Trading pair
        side: 'BUY' or 'SELL'
        order_type: Order type (e.g., 'LIMIT')
        price: Order price
        quantity: Order quantity
        max_retries: Maximum number of retry attempts
        delay_seconds: Delay between retries in seconds
        
    Returns:
        Response from the successful order or raises the last exception
    """
    attempts = 0
    last_exception = None
    
    while attempts < max_retries:
        try:
            response = new_order(
                client, 
                symbol=symbol,
                side=side,
                type=order_type,
                price=price, 
                quantity=quantity
            )
            return response  # Success, return the response
            
        except BinanceAPIException as e:
            last_exception = e
            # Check if it's a timeout error (code -1007)
            if e.code == -1007:
                attempts += 1
                print(f"Timeout error occurred. Retry attempt {attempts}/{max_retries}")
                if attempts < max_retries:
                    time.sleep(delay_seconds)
                    continue
            else:
                # If it's not a timeout error, raise immediately
                raise
            return 'timeout'
    # If we've exhausted all retries, raise the last exception
    raise last_exception
#{symbol} {price} dolardan/$/dolar {leverage}x {amount} $/dolar {side} open/close/long/short

class AsyncTradingAgent:
    def __init__(self,token_manager,tw_bearer_token,document_store,subreddits,keywords):
        self.token_manager=token_manager
        self.tw_bearer_token=tw_bearer_token
        self.processed_prompt_ids = set()
        self.check_interval=2
        self.subreddits=subreddits
        self.keywords=keywords
        self.advanced_rag=None
        self.document_store=document_store
        self.model = None
        
    """       
    #def init_model(self):
    #   genai.configure(api_key=self.gemini_api_key)
    #   self.model = genai.GenerativeModel("gemini-1.5-flash")

    #async def parse_prompt(self, prompt):
    #    try:
    #       gemini_messages = [
    #           {"role": "user", "parts": [self.system_instruction]},
    #           {"role": "user", "parts": prompt}
           ]
           response = self.model.generate_content(gemini_messages)
           text = response.text.replace("```json", "").replace("```", "").strip()
           if len(text) < 150:
               return json.loads(text)
           else:
               return text
        except Exception as e:
            return {"error": str(e)}
    """
    async def fetch_tw_data(self,query,start_date,end_date):
        def create_headers(bearer_token):
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "User-Agent": "v2RecentSearchPython"
            }
            return headers
        async def search_tweets_by_date(session,query, start_date, end_date, max_results=100):
            # URL'yi belirle
            url = "https://api.twitter.com/2/tweets/search/recent"
            
            # Tarihleri epoch formatına çevir
            start_epoch = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_epoch = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
            
            # Query parametrelerini ayarla
            params = {
                "query": query,  # Örneğin: "#Bitcoin"
                "max_results": max_results,  # Geri döndürülecek tweet sayısı (max 100)
                "start_time": datetime.utcfromtimestamp(start_epoch).isoformat() + "Z",  # UTC formatında start date
                "end_time": datetime.utcfromtimestamp(end_epoch).isoformat() + "Z"  # UTC formatında end date
            }
            
            headers = create_headers(self.tw_bearer_token)
            
            # API'ye istek gönder
            while True:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                         data = await response.json()
                         return data
                    else:
                         if response.status == 429:
                             # Rate limit aşılmış, bekleme süresi
                             reset_time = int(response.headers['x-rate-limit-reset'])
                             current_time = int(time.time())
                             sleep_time = reset_time - current_time + 5  # 5 saniye buffer ekleyelim
                             print(f"Rate limit exceeded. Sleeping for {sleep_time} seconds.")
                             await asyncio.sleep(sleep_time) # Bekleme süresi
                         
                         else:
                             print(f"Error: {response.status}")
                             print(await response.text())
        async def get_tweet_texts(self,query, start_date, end_date, max_results=100):
            # Tweetlerin metinlerini çek
            async with aiohttp.ClientSession() as session:
                tweets_data = await search_tweets_by_date(session,query, start_date, end_date, max_results)
            
            if tweets_data and "data" in tweets_data:
                # Tweetlerin text kısımlarını çıkar ve listeye ekle
                tweets = []
                for tweet in tweets_data["data"]:
                    tweets.append(tweet["text"])
                
                # Sayfalama kontrolü
                next_token = tweets_data.get("meta", {}).get("next_token")
                
                while next_token:
                    # Sayfa token'ı ile bir sonraki sayfayı al
                    async with aiohttp.ClientSession() as session:
                        tweets_data = await search_tweets_by_date(session,query, start_date, end_date, max_results)
                    tweets.extend([tweet["text"] for tweet in tweets_data["data"]])
                    next_token = tweets_data.get("meta", {}).get("next_token")
                
                # Listeyi DataFrame'e dönüştür
                df = pd.DataFrame(tweets, columns=["Text"])
                return df
            else:
                print("No tweets found or error occurred.")
                return None
    
    async def search_reddit(self,subreddit_name, keyword, start_epoch, end_epoch, limit_per_combo=300):
        reddit = asyncpraw.Reddit(
            client_id=os.environ['REDDIT_CLIENT_ID'],
            client_secret=os.environ['REDDIT_CLIENT_SECRET'],
            user_agent='script:sentiment-analyzer:v1.0 (by u/TheCrucial09)'
        )
        all_posts = []

        # Her subreddit ve keyword kombinasyonu için
        #keyword="BTC"
        subreddit=await reddit.subreddit(subreddit_name)
        try:
            async for submission in subreddit.search(keyword, limit=limit_per_combo,time_filter='week'):
                print(submission.title,submission.created_utc)
                created = int(submission.created_utc)
                if start_epoch <= created <= end_epoch:
                    title = submission.title or ""
                    text = submission.selftext or ""
                    full_text = (title + " " + text).strip()

                    all_posts.append({
                        "subreddit": subreddit_name,
                        "keyword": keyword,
                        "date": datetime.utcfromtimestamp(created).strftime('%Y-%m-%d'),
                        "title": title,
                        "text": text,
                        "full_text": full_text,
                        "url": submission.url
                    })
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"Error in r/{subreddit_name} for '{keyword}': {e}")

        return all_posts

    async def search_multiple_keywords(self,subreddits, keywords, start_date, end_date, limit_per_combo=100):
        # Tarihleri epoch formatına çevir
        start_epoch = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_epoch = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

        tasks = []
        all_posts = []

        # Asenkron görevleri başlat
        for subreddit_name in subreddits:
            for keyword in keywords:
                task = self.search_reddit(subreddit_name, keyword, start_epoch, end_epoch, limit_per_combo)
                tasks.append(task)

        # Görevleri bekle ve sonuçları topla
        results = await asyncio.gather(*tasks)

        # Sonuçları birleştir
        for result in results:
            all_posts.extend(result)

        # DataFrame'e dönüştür
        df = pd.DataFrame(all_posts)
        
        return df
    
    async def check_fetch_data(self):
        today = datetime.now().date()
        filename = f"data/BTC/tweets_{today}.csv"
        if os.path.exists(filename):
            print(f"{filename} zaten mevcut. Yeni veri çekilmeyecek.Embeding başlıyor...")
            return self.embeding_doc()
        else:
            print(f"{filename} bulunamadı veya tarih eski. Yeni veriler ekleniyor...")
            latest_df=await self.search_multiple_keywords(self.subreddits, self.keywords, str(datetime.now().date() - timedelta(days=7)), str(datetime.now().date()))
            #old_df=pd.read_csv(filename)
            #df_combined = pd.concat([old_df, latest_df], ignore_index=True)
            self.label_sentiment(latest_df)
            print("Yeni Veri eklendi.Embeding Başlıyor.")
            return self.embeding_doc()
        
    def label_sentiment(self,df):
        df_sentiment=df.copy()
        label_map = {
        "LABEL_0": "Negative",
        "LABEL_1": "Neutral",
        "LABEL_2": "Positive"}
        sentiment_model = pipeline("sentiment-analysis",
                                   model="cardiffnlp/twitter-roberta-base-sentiment",
                                   truncation=True,
                                   tokenizer="cardiffnlp/twitter-roberta-base-sentiment",
                                   max_length=512)
        df_sentiment["sentiment"] = df_sentiment["full_text"].apply(lambda x: sentiment_model(x)[0]["label"])
        df_sentiment["sentiment"]=df_sentiment["sentiment"].replace(label_map)
        os.makedirs(f"data/{'#BTC'.replace('#','')}", exist_ok=True)
        filename = f"data//BTC//tweets_{datetime.now().date()}.csv"
        df_sentiment[['date','full_text','sentiment']].to_csv(filename, index=False, encoding="utf-8")
        return df_sentiment
    def embeding_doc(self):
        print("Starting writing documents to document store..")
        file_path = Path("data") / "BTC" / f"tweets_{datetime.now().date()}.csv"

        df = pd.read_csv(file_path)
        timestamp = int(time.time())
        documents = [
            Document(
                content=row["full_text"],
                id=f"doc_{timestamp}_{index}",
                meta={
                    "date": row["date"],         # Tweet tarihi
                    "tag": "BTC" if "BTC" in row["full_text"] else "Other"  # Otomatik taglama opsiyonu
                }
            )
            for index, (_, row) in enumerate(df.iterrows())
        ]
        indexing_pipeline = Pipeline()
        #indexing_pipeline.add_component(instance=CSVToDocument(content_column='text'),name="converter")
        indexing_pipeline.add_component(instance=DocumentCleaner(),name="cleaner")
        #indexing_pipeline.add_component(instance=DocumentSplitter(split_by="sentence",split_length=3),name="splitter")
        indexing_pipeline.add_component(instance=SentenceTransformersDocumentEmbedder(model='sentence-transformers/all-mpnet-base-v2'),name="embeder")
        indexing_pipeline.add_component(instance=DocumentWriter(policy=DuplicatePolicy.OVERWRITE,document_store=self.document_store),name='writer')
        #indexing_pipeline.connect("converter.documents","cleaner")
        #indexing_pipeline.connect("cleaner","splitter")
        indexing_pipeline.connect("cleaner","embeder")
       #indexing_pipeline.connect("splitter","embeder")
        indexing_pipeline.connect("embeder","writer")
        
        try :
            indexing_pipeline.run({"cleaner": {"documents": documents}})
            return "embeding OK"
        except Exception as e:
            print("Writing documents error:",e)
        
    def rag(self):
        prompt_template="""
        {% if mode == "parse" %}
            You are a parser bot. You can't respond to anything else, you don't have knowledge. If you get any text, you need to parse it in both Turkish and English.
            
            Parse inputs containing information about trading positions with these required fields:
            - symbol (e.g., BTC, ETH) text - Automatically append USDT to form a trading pair (e.g., BTCUSDT) unless another pair is specified
            - side (open, close, long, short) text 
            - price (number, without currency symbols or with currency symbol) float 
            - leverage (number followed by x) int
            - position_size (amount, without currency or with currency symbol) float 
            
            Here is the user question: {{query}}
            Output format:
            If all required fields are found and clear, return:
            {"symbol": symbol, "side": side, "price": price, "leverage": leverage, "position_size": amount}
            
            If any required field is missing, irrelevant, or ambiguous, return:
            I can't do that your request. My responsibility just Open/close Margin operations. You have to send like this theme or similar: ETH 3200$ short position 5x leverage 1000$
            "missing": list the missing fields
            
            The input can have these elements in any order. Look for specific keywords to identify each field.

        {% elif mode == "sentiment" %}
            Here is the user question: {{query}}
            If query is 'yes' or similar positive , continue to sentiment step elif query is 'no' or similar negative break this all step and return Return "Acknowledge"
            {% if web_documents %}
                You were answer the following query given the documents retrieved from sentiment documentation but the context was not enough.
                        
                Context:
                    {% for document in web_documents %}
                    URL:{{document.meta.link}}
                    TEXT:{{document.content}}
                    ---
                    {% endfor %}
                Briefly talk about the market situation and give information about the fear greed index. Latest You have to return today fear & greed rate in document.This rate not interval have to just number.
                Also return URL and trusted source ["https://www.binance.com/en-TR/square/fear-and-greed-index","https://alternative.me/crypto/fear-and-greed-index/","https://coinmarketcap.com/charts/fear-and-greed-index/"]
                answer type is text not return json.
                return answer
            {% else %}
                You are a sentiment analysis expert.Your answer is clearly and the following retrieved docutments based from sentiment documentation:    
                Documents:
                    {% for document in documents %}
                        {{document.content}}
                    {% endfor %}
                If you don't have enough context to answer in documents , say 'NO_ANSWER'
                Your tasks:
                    - Count the number of each sentiment type in the documents for {{coins}}
                    - Calculate the percentage of each sentiment type (ensure they sum exactly to 100%)
                    - Provide a brief, concise summary (1-2 sentences) mentioning this is Reddit data
                    - Draw an ASCII bar chart with these exact specifications:
                        - Each bar uses █ symbols
                        - 1 symbol = 5% (exactly 20 symbols total across all bars)
                        - Format: Sentiment: [bar] XX%
                    
                Output Format:
                Sentiment analysis from Reddit data:

                Positive: [bar] XX% 
                Negative: [bar] XX% 
                Neutral: [bar] XX% 

                [Brief 1-2 sentence summary.You doens't have to write Note.]
            {% endif %}
        {% endif %}
        """

        main_routes= [
            {
             "condition":"{{'NO_ANSWER' in replies[0].text.replace('\n','')}}",
             "output": "{{query}}",
             "output_name": "go_web",
             "output_type":str
             
             
             },
             {
              "condition":"{{'NO_ANSWER' not in replies[0].text.replace('\n','')}}",
              "output": "{{{'parsed_result': replies[0].text, 'return_q': 'Would you like to run a sentiment analysis on this input as well?'} | tojson }}",
              "output_name": "answer",
              "output_type":str

              }   

            ]
        domain_list_allowed=["https://www.binance.com/en-TR/square/fear-and-greed-index","https://alternative.me/crypto/fear-and-greed-index/","https://coinmarketcap.com/charts/fear-and-greed-index/"]

        prompt=[ChatMessage.from_user(prompt_template)]

        advanced_rag= Pipeline(max_runs_per_component=5)
        advanced_rag.add_component("embeder", SentenceTransformersTextEmbedder(model="sentence-transformers/all-mpnet-base-v2"))
        advanced_rag.add_component("retriever", InMemoryEmbeddingRetriever(document_store=document_store,top_k=len(document_store.filter_documents(filters={}))))
        advanced_rag.add_component("prompt_builder", ChatPromptBuilder(template=prompt,required_variables=["query", "mode"]))
        advanced_rag.add_component("llm", GoogleAIGeminiChatGenerator(model="gemini-1.5-flash"))
        advanced_rag.add_component("web_search", SerperDevWebSearch(top_k=5))
        advanced_rag.add_component("router", ConditionalRouter(main_routes))

        advanced_rag.connect("embeder","retriever")
        advanced_rag.connect("retriever","prompt_builder.documents")
        advanced_rag.connect("prompt_builder","llm")
        advanced_rag.connect("llm.replies","router.replies")
        advanced_rag.connect("router.go_web","web_search.query")
        advanced_rag.connect("web_search.documents","prompt_builder.web_documents")
        
        return advanced_rag
    def request_query(self,query,mode='parse'):
        result=self.advanced_rag.run({
            "embeder":{"text":'Analyze sentiment about Bitcoin'},
            "prompt_builder":{"query":query,"mode":mode,"coins":'BTC'},
            "router":{"query":"Today What is the rate  of Crypto Fear & Greed Index"},
            
            })
        return result
    async def run(self):
        await self.check_fetch_data()
        self.advanced_rag=self.rag()
        while True:
            try:
                inputs = await self.token_manager.get_data(f'{host}/api/data/get_prompt')
                prompt_id = inputs['data']['id']
                if prompt_id in self.processed_prompt_ids:
                    await asyncio.sleep(2)
                    continue
                self.processed_prompt_ids.add(prompt_id)
                if inputs['data']['answer'] is None:
                    prompt_text = inputs['data']['prompt_text']
                    response_json = self.request_query(prompt_text,mode='parse')['router']['answer']['parsed_result']
                    print("gemini result:",response_json)
                    
                    
                    #Burda kaldın
                    if "missing" not in response_json and all(k in response_json for k in ['symbol', 'side', 'price', 'leverage', 'position_size']):
                        response_json_sentiment = self.request_query("Yes",mode='sentiment')
                        response_json_sentiment=response_json_sentiment['router']['answer']['parsed_result']
                        time.sleep(1)
                        response_json=response_json.strip("`'\n ")   
                        json_text_start = response_json.find('{')  # JSON başlangıcını bul
                        response_json = json.loads(response_json[json_text_start:])
                        print("response_json_before_lev:",response_json)
                        levereage=change_leverage(client,response_json['symbol'],response_json['leverage'])
                        time.sleep(0.2)
                        precsion_order_amount, price = precision_asset(client, response_json['symbol'], leverage=response_json['leverage'], price=response_json['price'], trade_size=response_json['position_size'])
                        time.sleep(0.2)
                        if (response_json['side'].lower()=='short') | (response_json['side'].lower()=='close'):
                            response_json['side']='SELL'
                        else:
                            response_json['side']='BUY'
                        response_order = retry_order(
                            client,
                            symbol=response_json['symbol'],
                            side=response_json['side'],
                            order_type='LIMIT',
                            price=response_json['price'],
                            quantity=precsion_order_amount
                        )
                        if response_order=='timeout':
                            response_json='BinanceAPI Timeout error occurred. Retry attempt 3/3.Timeout waiting for response from backend server. Send status unknown; execution status unknown.'
                            data={'prompt_text':inputs,'answer':response_json}
                            print(data)
                            await token_manager.post_data(f'{host}/api/data/post_prompt',data)
                        time.sleep(0.2)
                        print("response_order:",response_order)
                        response_json=str(response_json)+'\n'+str(response_json_sentiment)
                        data={'prompt_text':inputs,'answer':response_json}
                        await token_manager.post_data(f'{host}/api/data/post_prompt',data)
                        
                    else:
                        data={'prompt_text':inputs,'answer':response_json}
                        #print("Yanlış Tanımlama blogu: ",data)
                        await token_manager.post_data(f'{host}/api/data/post_prompt',data)
                else:
                    await asyncio.sleep(2)
            except Exception as e:
                tb = traceback.extract_tb(e.__traceback__)
                # Şu anki çalışan dosya
                current_dir = os.path.dirname(__file__)
            
                # Stack trace üzerinde sondan başa doğru dolaşıyoruz
                for frame in reversed(tb):
                    filename, lineno, funcname, text = frame
                    # Eğer hata kendi dosyamızdaysa
                    if current_dir in os.path.abspath(filename):
                        print(f"Hata {filename} dosyasında, {funcname} fonksiyonunda, {lineno}. satırda oluştu.")
                        print(f"Hatalı kod: {text}")
                        print(f"Hata mesajı: {e}")
                        break
                else:
                    # Kendi kodunda bulamazsa genel hata verir
                    print(f"Harici bir kütüphane hatası: {e}")
                await asyncio.sleep(2)
    

# activate traderhub && cd OneDrive\Masaüstü\TraderHub && python main.py
async def periodic_task(token_manager, endpoint,interval,func):
    """Belirli aralıklarla veri gönderen periyodik görev"""
    while True:
        try:
            
            # Eğer data_func bir fonksiyon ise çağırıyoruz
            if endpoint == f"{host}/api/data/post_realtime":
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
                    if endpoint == f"{host}/api/data/post_realtime":
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
        
        await asyncio.sleep(10)  # Belirtilen süre kadar bekle
async def all_requests():

    realtime_task = asyncio.create_task(
        periodic_task(token_manager, f'{host}/api/data/post_realtime', 
                              2,post_realtime))
    
    positions_task = asyncio.create_task(
        periodic_task(token_manager, f'{host}/api/data/post_open_positions', 
                              5, post_openPosition))
    
    assets_task = asyncio.create_task(
        periodic_task(token_manager, f'{host}/api/data/post_assets', 
                              10,post_assets))
    
    subreddits = ["CryptoCurrency", "Bitcoin", "CryptoMarkets","btc","BitcoinBeginners","CryptoMoonShots","cryptotechnology"]
    keywords = [
        "BTC", "Bitcoin", "crypto", 
        "FED", "FOMC", "interest rate", 
        "inflation", "CPI", "recession"
    ]

    agent = AsyncTradingAgent(token_manager,tw_bearer_token,document_store,subreddits,keywords)

    prompt_task = asyncio.create_task(agent.run())
    # Tüm görevlerin sonsuza kadar çalışmasını sağla
    await asyncio.gather(realtime_task, positions_task, assets_task,prompt_task)
            
             
    
        
                    
                    
thread_manager = ThreadManager()
def main(): 
    # İlk thread'leri oluştur
    websocket_thread = thread_manager.create_websocket_thread()
    #flask_thread = thread_manager.create_flask_thread()
    #streamlit_thread = thread_manager.create_streamlit_thread()

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
    #loop = asyncio.get_event_loop()
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



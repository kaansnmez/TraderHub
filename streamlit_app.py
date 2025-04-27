import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import warnings
import requests
import time
import dotenv
from token_manager_async import AsyncTokenManager
import asyncio
import jwt
import binance_future_process
from binance.exceptions import BinanceAPIException
import traceback

st.set_page_config(
    page_title="TradeHub",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
    
)

dotenv.load_dotenv()
API_BASE_URL = 'https://traderhub-flask.onrender.com'
host='https://traderhub-flask.onrender.com'
client=binance_future_process.connect_binance(binance_future_process.api_key, binance_future_process.api_secret)


token_manager = AsyncTokenManager(f"http://{host}/login",os.environ['user_id'],os.environ['pw'])


loop = asyncio.new_event_loop()   

def safe_cancel_order(symbol, order_id, max_retries=3, wait_sec=2):
    for attempt in range(max_retries):
        try:
            response = client.futures_cancel_order(symbol=symbol, orderId=order_id)
            print(" Emir başarıyla iptal edildi.")
            return response
        except BinanceAPIException as e:
            if "code=-1007" in str(e):
                print(f" Timeout oldu. Deneme: {attempt + 1}/{max_retries}")
                time.sleep(wait_sec)
                
                # Emir gerçekten iptal olmuş mu kontrol et
                orders = client.futures_get_all_orders(symbol=symbol)
                for o in orders:
                    if o["orderId"] == order_id:
                        if o["status"] == "CANCELED":
                            print("Emir aslında iptal edilmiş (timeout sonrası kontrol edildi).")
                            return {"status": "CANCELED"}
                continue
            else:
                raise e
    print(" Emir iptal edilemedi. Tüm denemeler başarısız.")
    return None
def register_user(username, password):
    """
    Register a new user via the Flask API
    """
    try:
        response = requests.post(
            f'{API_BASE_URL}/register', 
            json={
                'username': username, 
                'password': password
            },
            headers={'Content-Type': 'application/json'}
        )
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {e}")
        return None, 500

def login_user(username, password):
    """
    Login user via the Flask API
    """
    try:
        response = requests.post(
            f'{API_BASE_URL}/login', 
            json={
                'username': username, 
                'password': password
            },
            headers={'Content-Type': 'application/json'}
        )
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        #st.error(f"Connection error: {e}")
        error=e
        return None, 500

def registration_page():
    st.title("Trading Platform Registration")
    
    with st.form("registration_form"):
        new_username = st.text_input("Choose a Username")
        new_password = st.text_input("Create a Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        register_button = st.form_submit_button("Register")
        
        if register_button:
            # Validate inputs
            if not new_username or not new_password:
                st.error("Username and password cannot be empty")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            else:
                # Attempt registration
                result, status_code = register_user(new_username, new_password)
                
                if status_code == 201:
                    st.success("Registration successful! You can now log in.")
                    # Optional: Automatically switch to login page
                    st.session_state['page'] = 'login'
                    
                else:
                    st.error(result.get('message', 'Registration failed'))

def login_page():
    st.title("Trading Platform Login")
    
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")
        
        st.markdown("Don't have an account? [Register here](#registration)")
        
        if login_button:
            result, status_code = login_user(username, password)
            
            if status_code == 200:
                # Explicitly set login state and username
                st.session_state['logged_in'] = True
                st.session_state['token'] = result['token']
                st.session_state['username'] = result['username']
                """
                headers = {"Content-Type": "application/json",
                           "Authorization": f"Bearer {result['token']}"}
                data={"token_hash":st.session_state['token']}
                requests.post("http://127.0.0.1:5000/api/data/post_token",json=data,headers=headers)
                # Directly update the page state to trigger navigation
                """
                st.session_state['page'] = 'dashboard'

                # Force a rerun to refresh the entire app state
                st.rerun()
            else:
                if status_code == 500:
                    st.error("Username/password is incorrect or no such account exists")
                else:
                    st.error("Login failed. Please check your credentials.")

async def get_data(order=False,req_type='post',data=""):
    
    data_dict={'RealTime':{'get_realtime':{}
                          },
             'Historical':{'get_assets':{},
                           'get_openPositions':{}
                         }}
    if order!=False:
        if req_type=='post':
            await token_manager.post_data(f"http://{host}/api/data/{order}",data)
        else:
            data=await token_manager.get_data(f"http://{host}/api/data/{order}")
        
        return data
    else:    
        for url in data_dict.keys():
            for key in data_dict[url].keys():
                data=await token_manager.get_data(f"http://{host}/api/data/{key}")
                data_dict[url][key]=data
    return data_dict
def json_to_df(json_dict):
    json_dict=pd.DataFrame.from_dict(json_dict['data'])
    return json_dict
def convert_json_decode_format(df):
    columns=['entry','close','close_real_data','qty','margin_size','profit','leverage']
    for x in columns: 
        try:
            df[x]=df[x].apply(lambda x : float(str(x).replace(',','.')))
        except:
            pass
    return df
def order_func():
    
    data_wrap= loop.run_until_complete(get_data())
    return data_wrap
@st.fragment(run_every="10 sec")
def stream():
    contanier=st.columns((1,1,1.5,1))
    #contanier=st.columns((1,1,1.5))
    
    
    try:        
        data_wrap= loop.run_until_complete(get_data())
        data=data_wrap['RealTime']['get_realtime']['data']
        assets=json_to_df(data_wrap['Historical']['get_assets'])
        getopen_positions=data_wrap['Historical']['get_openPositions']['data']
        
        
    except:
        
            
        print("API is not ready")
         
        st.warning("API is not ready.Logging out.")
        time.sleep(10) 
        st.session_state.clear()
        st.rerun()
          
    data={k: 0 if v==None else v for k, v in data.items()}
    with contanier[0]:
        contanier[0].metric(
            label="Open Price",
            value=f"$ {data['open']} "
            
        )
        contanier[0].markdown("****")
        contanier[0].metric(
            label="Close Price",
            value=f"$ {data['close']} "
            
        )
        
    with contanier[1]:

        contanier[1].metric(
            label="High Price",
            value=f"$ {data['high']} "
            
        )
        contanier[1].markdown("***")
        contanier[1].metric(
            label="Low Price",
            value=f"$ {data['low']} "
            
        )
        
    with contanier[2]:
        fig2=go.Figure(data=[go.Pie(labels=assets['asset_name'], 
                              values=assets['balance_r'],
                              marker_colors=['rgb(1, 184, 170)','rgb(237, 111, 19)'],
                              hoverlabel = dict(namelength = -1))])
      
        fig2.update_traces(hoverinfo="label+value")
        fig2.update_layout(
            hoverlabel = dict(
                bgcolor = 'rgba(39,46,72,1)' #whatever format you want
                            ),
            title=dict(text="Account Balance Chart"),
            legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="left",
                        bgcolor='rgba(39,46,72,0)'
                
                    ))
        st.plotly_chart(fig2)
     
    with contanier[3]:

        contanier[3].metric(
            label="Profit",
            value=f"$ {getopen_positions[0]['total_profit']}"
            
        )
        contanier[3].markdown("***")
        contanier[3].metric(
            label="Volume BTC",
            value=f"{data['volume']} "
            
        )
        
def tradingview_chart():
    st.title("Chart")
    contanier = st.container(height=550)
    with contanier:
        tradingview_widget = """
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <div class="tradingview-widget-copyright"><a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank"><span class="blue-text">Track all markets on TradingView</span></a></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {
          "width": "100%",
          "height": "500",
          "symbol": "BINANCE:BTCUSDT",
          "interval": "D",
          "timezone": "Etc/UTC",
          "theme": "dark",
          "style": "1",
          "locale": "en",
          "hide_side_toolbar": false,
          "allow_symbol_change": true,
          "studies": [
            "STD;Connors_RSI"
          ],
          "support_host": "https://www.tradingview.com"
        }
          </script>
        </div>
        """
        st.components.v1.html(tradingview_widget,height=500)

def verify_token(token):
    try:
        payload = jwt.decode(token, os.environ['flask_secret_key'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None   
def create_interactive_portfolio_table(df,title,color_column):   
    row_colors = []
    for value in df[color_column]:
        # Create a row of colors matching the number of columns
        if float(value) < 0:
            row_colors.append(['rgba(255, 0, 0, 0.5)'] * len(df.columns))
        else:
            if float(value)==0:
                
                row_colors.append(['rgba(255, 255, 0, 0.5)'] * len(df.columns))
            else:    
                row_colors.append(['rgba(0, 255, 0, 0.5)'] * len(df.columns))
    

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=list(df.columns),
            
            align='left'
        ),
        cells=dict(
            values=[df[col] for col in df.columns],
            fill_color=row_colors,  # Now a 2D list of colors
            align='left'
        )
    )])
    
    # Adjust layout
    fig.update_layout(
        title=f'{title}',
        height=400
    )

    return fig  

 

@st.fragment(run_every="2 sec")
def trade_execution_page():
    st.subheader("Active Trades")  
    
    try:
        getopen_positions = loop.run_until_complete(get_data('get_openPositions','get'))['data'][0]
    except:
        print("API is not ready")
        st.warning("API is not ready. Logging out.")
        time.sleep(10) 
        st.session_state.clear()
        st.rerun()
    
    if getopen_positions['pos_opens?'] == False:
        st.warning("Not have any active positions.")
    else:
        # Get positions
        get_openPositions_all = getopen_positions['long_positions'] + getopen_positions['short_positions']
        df_openPos = pd.DataFrame(get_openPositions_all)
        print(df_openPos)
        # Select required columns
        df_openPos_selected = df_openPos[['symbol', 'isolatedWallet', 'entryPrice', 'leverage', 'positionSide', 'unrealizedProfit']]
        
        # CSS for custom styling
        st.markdown("""
        <style>
        .stExpander {
            background-color: rgba(22, 27, 34, 0.8) !important;
            border-radius: 8px !important;
            margin-bottom: 10px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create individual rows as separate elements
        for i, row in df_openPos_selected.iterrows():
            # Use an expanded expander as a container
            position_title  = f"{row['symbol']}_{row['positionSide']}"
            
            with st.expander(position_title, expanded=True):
                cols = st.columns([1, 1, 1, 1, 1,0.5])
                
                cols[0].write(f"**{row['symbol']}** ({row['positionSide']})")
                cols[1].write(f"isolatedWallet: {row['isolatedWallet']}")
                cols[2].write(f"entryPrice: {row['entryPrice']}")
                cols[3].write(f"leverage: {row['leverage']}x")
                # Format profit/loss
                profit = float(row['unrealizedProfit'])
                if profit > 0:
                    cols[4].markdown(f"<span style='color:green'>+${profit:.2f}</span>", unsafe_allow_html=True)
                elif profit < 0:
                    cols[4].markdown(f"<span style='color:red'>${profit:.2f}</span>", unsafe_allow_html=True)
                else:
                    cols[4].write(f"${profit:.2f}")
                
                # Delete button
                if cols[5].button("🗑️", key=f"delete_{i}_{row['symbol']}_{row['positionSide']}"):
                    st.warning(f"Closing position for {row['symbol']}...")
                    all_orders=client.futures_position_information(symbol=row['symbol'])
                    for data in all_orders:
                        if float(data['positionAmt'])>0:
                            sides='SELL'
                        else:
                            sides='BUY'
                        order_price=binance_future_process.get_order_book(client, symbol=row['symbol'], pos=sides)
                        response = client.futures_create_order(
                          symbol=row['symbol'],
                          side=sides,
                          type='LIMIT',
                          quantity=abs(float(data['positionAmt'])),
                          price=order_price,
                          timeInForce='GTC',
                          reduceOnly=True
                      )  
                    time.sleep(1)
                    # Your position closing code
                    st.rerun()
@st.fragment(run_every="3 sec")
def open_orders_page():
    st.subheader("Open Orders")  
    try:
        getopen_positions=binance_future_process.open_orders_all(client)
    except:
        print("API is not ready")
        st.warning("API is not ready.Logging out.")
        time.sleep(10) 
        st.session_state.clear()
        st.rerun()
    if getopen_positions is None:
        st.warning("Not have a open order.")
        df_openPos_selected=pd.DataFrame()
    else:
        df_openPos_selected=getopen_positions.copy()
        #st.plotly_chart(create_interactive_portfolio_table(df_openPos_selected,' ','filled'), use_container_width=True)   
        # CSS for custom styling
        st.markdown("""
        <style>
        .stExpander {
            background-color: rgba(22, 27, 34, 0.8) !important;
            border-radius: 8px !important;
            margin-bottom: 10px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create individual rows as separate elements
        for i, row in df_openPos_selected.iterrows():
            # Use an expanded expander as a container
            position_title  = f"{row['symbol']}_{row['side']}"
            
            with st.expander(position_title, expanded=True):
                cols = st.columns([1, 1, 1, 1, 1,1,0.5])
                
                cols[0].write(f"time: {row['time']}")
                cols[1].write(f"orderId: {row['orderId']}")
                cols[2].write(f"**{row['symbol']}** ({row['side']})")
                cols[3].write(f"price: {row['price']}")
                cols[4].write(f"amount: {row['amount']}")
                # Format profit/loss
                profit = float(row['filled'])
                if profit > 0:
                    cols[5].markdown(f"<span style='color:green'>Filled: +${profit:.2f}</span>", unsafe_allow_html=True)
                elif profit < 0:
                    cols[5].markdown(f"<span style='color:red'>Filled: ${profit:.2f}</span>", unsafe_allow_html=True)
                else:
                    cols[5].markdown(f"<span style='color:yellow'>Filled: ${profit:.2f}</span>", unsafe_allow_html=True)
                
                # Delete button
                if cols[6].button("🗑️", key=f"delete_{i}_{row['symbol']}_{row['side']}"):
                    st.warning(f"Closing position for {row['symbol']}...")
                    
                    order_price=client.futures_cancel_order(symbol=row['symbol'],orderid=row['orderId'])
                    time.sleep(1)
                    # Your position closing code
                    st.rerun()
    #st.dataframe()
    
async def request_async(adress,req_side,data=""):
    if req_side=='post':
        return await token_manager.post_data(adress,data)
    else:
        return await token_manager.get_data(adress)
    
def prompt():
    wait_time = 1
    st.title("Trade Execution")
    data={'prompt_text':"",'answer':""}
    trade_prompt = st.chat_input("Enter your trade prompt: Tips 'ETH 3200$ short position 5x leverage 1000$' ")
    data['prompt_text']=trade_prompt
    
    if trade_prompt:
        print(trade_prompt)
        if trade_prompt:
            loop.run_until_complete(get_data("post_prompt",'post',data))
            with st.chat_message("user"):
                st.text(f"{trade_prompt}")
            with st.chat_message("assistant"):
                st.write("Processing request..")
            
        else:
            st.info("You can't send empty prompt.")
        with st.spinner("Executing.."):    
            while True:
                    try:
                        data=loop.run_until_complete(get_data("get_prompt",'get'))
                        print(data)
                        time.sleep(1)
                        wait_time = min(wait_time * 2, 10)
                        
                        #loop.close()
                        if not data['data']['answer'] is None:
                            if "missing" not in data['data']['answer'] and all(k in data['data']['answer'] for k in ['symbol', 'side', 'price', 'leverage', 'position_size']):
                                with st.chat_message("assistant"):
                                    st.text("Your request was successful. You can check at 'Positions & Orders'.")
                                    pretty_text = data['data']['answer'].encode().decode('unicode_escape')

                                    st.text(pretty_text)
                                    break
                            else:
                                with st.chat_message("assistant"):
                                    
                                    st.text(data['data']['answer'].split('\\n')[0])
                                    try:
                                        st.text(data['data']['answer'].split('\\n')[1].replace('\\"',""))
                                    except:
                                        st.text("Your request was unsuccessful.")
                                        break
                                    break
                                break
                        
                    except Exception as e:
                        st.error(f"Hata oluştu: {traceback.format_exc()}")
                        
                        break
def dashboard_page():
    st.session_state['page'] = 'dashboard'
    st.title(":bar_chart: TraderHub - Prompt Based Trading :currency_exchange:")
    warnings.filterwarnings('ignore')
    
    stream()
    st.title("Positions & Orders")
    trade_execution_page()
    open_orders_page()
    prompt()
    tradingview_chart()
    with open("web_css.css")as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

def web_app():
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'
        
    
    # Page routing
    if not st.session_state['logged_in']:
        # Toggle between login and registration
        if st.session_state['page'] == 'login':
            login_page()
            if st.button("Need an account? Register"):
                st.session_state['page'] = 'registration'
                
        else:
            registration_page()
            if st.button("Already have an account? Login"):
                st.session_state['page'] = 'login'
                
    else:
        st.sidebar.title(":currency_exchange: TraderHub :currency_exchange:")
        menu_options = {
            "Dashboard": dashboard_page,
            
        }
        selection = st.sidebar.radio(
            f"Welcome, {st.session_state['username']}!", 
            list(menu_options.keys())
        )
        menu_options[selection]()

        
        # Logout button at the bottom of the sidebar
        st.sidebar.markdown("---")
        if st.sidebar.button("Logout"):
            # Clear session state
            st.session_state['logged_in'] = False
            st.session_state['token'] = None
            st.session_state['username'] = None
            st.session_state['page'] = 'login'
            st.rerun()
            

       
if __name__=='__main__':
    
    web_app()
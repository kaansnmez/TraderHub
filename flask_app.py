from flask import Flask, request, jsonify,json,make_response,session

from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import JSON
from datetime import timedelta
from sqlalchemy import desc,inspect,func
import jwt
import datetime,os
from functools import wraps
import dotenv
from cryptography.fernet import Fernet


app = Flask(__name__)

dotenv.load_dotenv()
app.config['SECRET_KEY'] = os.environ['flask_secret_key']
app.config['DATA_SECRET_KEY'] = os.environ['data_secret_key']  # Gerçek bir uygulamada güçlü bir anahtar kullanın
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# Flask-Session yapılandırması
db = SQLAlchemy(app)
cipher = Fernet(app.config['DATA_SECRET_KEY'])

#with app.app_context():
#    Open_Position.__table__.drop(db.engine)

"""
with app.app_context():
    # User tablosundaki tüm kayıtları al
    #User.query.filter_by(username=data['username']).first()
    recent_data = tokens.query.filter_by(uid=1).order_by(
        desc(tokens.created_at)
    ).first().as_dict()
    users = tokens.query.all()
    #db.drop_all()
    # Kullanıcıları listele
    for user in users:
        print(user.as_dict())
        """
# Basit bir veritabanı yerine kullanacağımız veri yapısı
database = {}
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    asset = db.relationship("Assets", backref="user_asset", uselist=True, cascade="all, delete-orphan")
    realtime = db.relationship("Realtime", backref="user_realtime", uselist=True, cascade="all, delete-orphan")
    open_position = db.relationship("Open_Position", backref="user_open_position", uselist=True, cascade="all, delete-orphan")
    prompt = db.relationship("Prompt", backref="user_prompt", uselist=True, cascade="all, delete-orphan")
    token = db.relationship("tokens", backref="user_tokens", uselist=True, cascade="all, delete-orphan")

    def as_dict(self):
        return {'id':self.id,
                'username':self.username,
                'password':self.password}
class Assets(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer,db.ForeignKey('users.id'), nullable=False)
    accountAlias = db.Column(db.String(50), nullable=False)
    asset = db.Column(db.String(50), nullable=False)
    balance = db.Column(db.Float, nullable=False)
    crossWalletBalance = db.Column(db.String(50), nullable=False)
    crossUnPnl = db.Column(db.String(50), nullable=False)
    availableBalance = db.Column(db.String(50), nullable=False)
    maxWithdrawAmount = db.Column(db.String(50),  nullable=False)
    marginAvailable = db.Column(db.Boolean, nullable=False)
    updateTime = db.Column(db.Integer, nullable=False)
    asset_name = db.Column(db.String(50), nullable=False)
    balance_r = db.Column(db.Integer, nullable=False)
    
    def as_dict(self):
        return {
            "id": self.id,
            'uid':self.uid,
            "accountAlias": self.accountAlias,
            "asset": self.asset,
            "balance": self.balance,
            "crossWalletBalance": self.crossWalletBalance,
            "crossUnPnl": self.crossUnPnl,
            "availableBalance": self.availableBalance,
            "maxWithdrawAmount": self.maxWithdrawAmount,
            "marginAvailable": self.marginAvailable,
            "updateTime": self.updateTime,
            "asset_name": self.asset_name,
            "balance_r": self.balance_r
        }

class Realtime(db.Model):
    __tablename__ = 'realtime'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer,db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    open_time = db.Column(db.String(50), nullable=False)
    open = db.Column(db.Float, nullable=False)
    close = db.Column(db.Float, nullable=False)
    high = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=False)
    close_time = db.Column(db.String(50),  nullable=False)
    number_of_trades = db.Column(db.Float, nullable=False)
    kline_closed = db.Column(db.String(50), nullable=False)
    quote_asset_volume = db.Column(db.Float, nullable=False)
    taker_buy_base_volume = db.Column(db.Float, nullable=False)
    taker_buy_quote_volume = db.Column(db.Float, nullable=False)
    ignore = db.Column(db.Float, nullable=False)
    

    def as_dict(self):
        return {
         'uid': self.uid,
         'open_time': self.open_time,
         'created_at':self.created_at,
         'open': self.open,
         'close': self.close,
         'high':self.high,
         'low':self.low,
         'volume': self.volume,
         'close_time': self.close_time,
         'number_of_trades': self.number_of_trades,
         'kline_closed': self.kline_closed,
         'quote_asset_volume': self.quote_asset_volume,
         'taker_buy_base_volume': self.taker_buy_base_volume,
         'taker_buy_quote_volume':self.taker_buy_quote_volume,
         'ignore':self.ignore}
    
class Open_Position(db.Model):
    __tablename__ = 'open_position'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer,db.ForeignKey('users.id'), nullable=False)
    sensitive_data = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    

    def as_dict(self):
        return {'id':self.id,
                'uid':self.uid,
                'sensitive_data':self.sensitive_data,
                'created_at':self.created_at}
class Prompt(db.Model):
    __tablename__ = 'prompt'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer,db.ForeignKey('users.id'), nullable=False)
    prompt_text = db.Column(db.String(1000), nullable=False)
    answer= db.Column(db.String(1000), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def as_dict(self):
        return {'id':self.id,
                'uid':self.uid,
                'prompt_text':self.prompt_text,
                'answer':self.answer,
                'created_at':self.created_at}
class tokens(db.Model):
    __tablename__='tokens'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer,db.ForeignKey('users.id'), nullable=False)
    token_hash=db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def as_dict(self):
        return {'id':self.id,
                'uid':self.uid,
                'token_hash':self.token_hash,
                'created_at':self.created_at}
def decrypt_sensitive_data(encrypted_data):
    """
    Şifreli veriyi çözme fonksiyonu
    """
    decrypted_data = cipher.decrypt(encrypted_data.encode())
    
    return json.loads(decrypted_data.decode())
def encrypt_sensitive_data(data):
    """
    Hassas veriyi şifreleme fonksiyonu
    Gerçek uygulamada güçlü şifreleme kullanılmalı
    """
    json_data = json.dumps(data)
    encrypted_data = cipher.encrypt(json_data.encode())
    # Örnek basit şifreleme (production'da daha güçlü yöntemler kullanın)
    return encrypted_data.decode()

def cleanup_old_data(table):
    """Belirli süreden eski verileri temizle"""
    try:
        # 24 saat öncesinden eski kayıtları sil
        cutoff_time = datetime.datetime.utcnow() - timedelta(hours=24)
        deleted_count = db.session.query(table).filter(
            table.created_at < cutoff_time
        ).delete(synchronize_session=False)
        
        # Mevcut kayıt sayısını 10000 ile sınırla
        total_count = db.session.query(func.count(table.id)).scalar()
        if total_count > 10000:
            excess = total_count - 10000
            db.session.query(table).order_by(
                table.created_at.asc()
            ).limit(excess).delete(synchronize_session=False)
        
        db.session.commit()
        print(f"Temizlenen kayıt sayısı: {deleted_count}")
    except Exception as e:
        db.session.rollback()
        print(f"Veri temizleme hatası: {e}")
        
# Token doğrulama decorator'ı
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Token'ı headers'dan al
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'message': 'Authentication token is missing!'}), 401
        
        try:
            # Token'ı çöz
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(username=data['username']).first()
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated
"""
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'API çalışıyor',
        'endpoints': {
            'login': '/login',
            'register': '/register',
            'data': '/api/data'
        }
    }), 200
"""
# Kayıt endpoint'i
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Kullanıcı zaten var mı kontrol et
    existing_user = User.query.filter_by(username=data['username']).first()
    if existing_user:
        return jsonify({'message': 'Kullanıcı zaten mevcut!'}), 400
    
    # Şifreyi hashle
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    
    new_user = User(
        username=data['username'], 
        password=hashed_password
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'Kullanıcı başarıyla kaydedildi!'}), 201

# Giriş endpoint'i
@app.route('/login', methods=['POST'])
def login():
    auth = request.get_json()
    
    if not auth or not auth['username'] or not auth['password']:
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'})
    
    user = User.query.filter_by(username=auth['username']).first()
    
    if not user:
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="User not found!"'})
    
    # Şifreyi kontrol et
    if check_password_hash(user.password, auth['password']):
        # JWT token oluştur
        token = encrypt_sensitive_data(jwt.encode({
            'username': user.username,
            'uid':user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }, app.config['SECRET_KEY'], algorithm="HS256"))
        
        

        new_token_entry = tokens(
            uid=user.id,
            token_hash=encrypt_sensitive_data(token)  # Token'ı şifrele ve kaydet
        )
        db.session.add(new_token_entry)
        db.session.commit()
        
        return jsonify({
            'token': token,
            'uid':user.id,
            'username': user.username
        })
    
    return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Wrong Password!"'})



# Veritabanını başlat
with app.app_context():
    db.create_all()


# GET isteği için endpoint - tüm verileri al
@app.route('/api/data/get_prompt', methods=['GET'])
@token_required
def get_prompt(current_user):
     
    recent_data = Prompt.query.filter_by(uid=current_user.id).order_by(
        desc(Prompt.created_at)
    ).first().as_dict()
    
    return jsonify({
        "message": "Realtime veriler başarıyla alındı",
        "data": recent_data,
        "user_id":current_user.id
    }), 200

@app.route('/api/data/get_realtime', methods=['GET'])
@token_required
def get_data_realtime(current_user):
    recent_data = Realtime.query.filter_by(uid=current_user.id).order_by(
        desc(Realtime.created_at)
    ).first().as_dict()
    
    return jsonify({
        "message": "Realtime veriler başarıyla alındı",
        "data": recent_data,
        "user_id":current_user.id
    }), 200

@app.route('/api/data/get_assets', methods=['GET'])
@token_required
def get_data_assets(current_user):
    if not inspect(db.engine).has_table('Assets'):
        raise ValueError("database is empty")
      
    balance_usdt=Assets.query.filter_by(uid=current_user.id,asset_name="Balance_USDT") \
                               .order_by(desc(Assets.id)) \
                               .first().as_dict()
    margin_usdt=Assets.query.filter_by(uid=current_user.id,asset_name="Margin_USDT") \
                               .order_by(desc(Assets.id)) \
                               .first().as_dict()
    return jsonify({"message": "Assets veriler başarıyla alındı", 
                    "data": [balance_usdt,margin_usdt],
                    "user_id":current_user.id})

@app.route('/api/data/get_openPositions', methods=['GET'])
@token_required
def get_data_openPosition(current_user):
    
    recent_data = Open_Position.query.filter_by(uid=current_user.id).order_by(
        desc(Open_Position.created_at)
    ).first().as_dict()
    
    return jsonify({
        "message": "Realtime veriler başarıyla alındı",
        "data": decrypt_sensitive_data(recent_data['sensitive_data']),
        "user_id":current_user.id
    }), 200
@app.route('/api/data/post_token', methods=['POST'])
@token_required
def post_token(current_user):
    # Gelen JSON verisini al
    
    # Gelen veriyi al
    data = request.json
    print(data)
    # Veri doğrulama
    if not data['token_hash']:
        return jsonify({"error": "Eksik veri"}), 400
    # Yeni kayıt oluştur
    
    new_entry = tokens(
        uid=current_user.id,
        token_hash=encrypt_sensitive_data(data['token_hash'])
    )
    
    db.session.add(new_entry)
    db.session.commit()
    
    # Periyodik temizlik
    cleanup_old_data(tokens)
    
    
    # Periyodik temizlik
    #cleanup_old_data(Open_Position)
    
    return jsonify({"message": "Veri kaydedildi", "id": new_entry.id}), 201    
@app.route('/api/data/post_prompt', methods=['POST'])
@token_required
def post_prompt(current_user):
    # Gelen JSON verisini al
    
    # Gelen veriyi al
    data = request.json
    # Veri doğrulama
    
    if not data["prompt_text"]:
        return jsonify({"error": "Eksik veri"}), 400
    # Yeni kayıt oluştur
    if not data['answer']:
        new_entry = Prompt(
            uid=current_user.id,
            prompt_text=data['prompt_text']
        )
        
        db.session.add(new_entry)
        db.session.commit()
    else:
        record = Prompt.query.filter_by(uid=current_user.id).order_by(desc(Prompt.created_at)).first()
        record.answer=json.dumps(data['answer'])
        db.session.commit()
    
    # Periyodik temizlik
    #cleanup_old_data(Open_Position)
    
    return jsonify({"message": "Veri kaydedildi", "id": new_entry.id}), 201

    
@app.route('/api/data/post_open_positions', methods=['POST'])
@token_required
def open_position(current_user):
    # Gelen JSON verisini al
    
    # Gelen veriyi al
    data = request.json
    # Veri doğrulama
    if not data:
        return jsonify({"error": "Eksik veri"}), 400
    # Yeni kayıt oluştur
    
    new_entry = Open_Position(
        uid=current_user.id,
        sensitive_data=encrypt_sensitive_data(data['sensitive_data'])
    )
    
    db.session.add(new_entry)
    db.session.commit()
    
    # Periyodik temizlik
    cleanup_old_data(Open_Position)
    
    return jsonify({"message": "Veri kaydedildi", "id": new_entry.id}), 201

    
    
@app.route('/api/data/post_realtime', methods=['POST'])
@token_required
def add_data_realtime(current_user):
    # Gelen JSON verisini al
    data = request.json
    #pair_data={key:value.values[0] if data[key].dtypes!='<M8[ns]' else str(value.values[0]) for key,value in data.items()}
    
    if not data:
        return jsonify({"error": "Veri boş olamaz"}), 400
    
    # Veriyi "veritabanına" ekle
    
    new_assets=Realtime(**data,uid=current_user.id)
    db.session.add(new_assets)
    db.session.commit()

    cleanup_old_data(Realtime)

    # Yanıt döndür
    return jsonify({
        "message": "Realtime veri başarıyla kaydedildi", 
        "data": data
    }), 201

@app.route('/api/data/post_assets', methods=['POST'])
@token_required
def add_data_assets(current_user):
    # Gelen JSON verisini al
    data = request.json
    if not data:
        return jsonify({"error": "Veri boş olamaz"}), 400
    
    # Veriyi "veritabanına" ekle
    for d_ind in data:
        new_assets=Assets(**d_ind,uid=current_user.id)
        db.session.add(new_assets)
        db.session.commit()
    
    # Yanıt döndür
    return jsonify({
        "message": "Veri başarıyla kaydedildi", 
        "data": data
    }), 201

    
if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000,debug=True)

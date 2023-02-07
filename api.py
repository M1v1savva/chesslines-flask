import time
import logging
import pymongo
from flask import Flask, request, jsonify, session
from flask_cors import CORS, cross_origin
import requests
from os import environ 
import hashlib
from dotenv import dotenv_values
from datetime import datetime, timedelta, timezone
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, \
                               unset_jwt_cookies, jwt_required, JWTManager
from werkzeug.security import generate_password_hash, check_password_hash

config = dotenv_values(".env")

api = Flask(__name__)
api.config["JWT_SECRET_KEY"] = config['JWT_SECRET_KEY']
jwt = JWTManager(api)

cors = CORS(api)
api.config['CORS_HEADERS'] = 'Content-Type'

client = pymongo.MongoClient(config['MONGODB_TOKEN'])
db = client.get_database('chesslines')
users_db = db['chesslines']
profiles_db = db['auth']

api.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

@api.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            data = response.get_json()
            if type(data) is dict:
                data["access_token"] = access_token 
                response.data = json.dumps(data)
        return response
    except (RuntimeError, KeyError):
        # Case where there is not a valid JWT. Just return the original respone
        return response

@api.route('/confirmation', methods=['POST'])
def confirmation():
    return {"status": 200}

@api.route('/login', methods=["POST"])
def login_user():
    email = request.json.get("email", None)
    password = request.json.get("password", None)

    user_dt = profiles_db.find_one({'handle': email})

    cur_hash = ''
    if user_dt != None:
        cur_hash = user_dt['password']

    if not check_password_hash(cur_hash, password):
        return {"msg": "Wrong email or password"}, 401

    access_token = create_access_token(identity=email)
    response = {"access_token":access_token}
    return response

@api.route('/signup', methods=["POST"])
def signup_user():
    email = request.json.get("email", None)
    password = request.json.get("password", None)

    user_dt = profiles_db.find_one({'handle': email})
    if user_dt != None:
        return {"msg": "User already exists"}, 409

    access_token = create_access_token(identity=email)
    user_dt = {'handle': email, 'password': generate_password_hash(password)}
    profiles_db.insert_one(user_dt)
    response = {"access_token":access_token}
    return response

@api.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response

@api.route('/update-comment', methods=["POST"])
@jwt_required() 
def update_comment():
    position = request.json.get("position", None)
    comment = request.json.get("comment", None)
    
    username = get_jwt_identity()
    user_dt = users_db.find_one({'handle': username})
    insert_flag = False
    if user_dt == None:
        insert_flag = True

    cur_dict = dict()
    if (user_dt != None) and ('comment_data' in user_dt.keys()):
        cur_dict = user_dt['comment_data']

    cur_dict[position] = comment

    if insert_flag:
        users_db.insert_one({'handle': username, 'comment_data': cur_dict, 'move_data': dict()})
    else:
        users_db.update_one({'handle': username}, {'$set': {'comment_data': cur_dict}})
    return {}

@api.route('/update-move', methods=["POST"])
@jwt_required() 
def update_move():
    move_sequence = request.json.get("move_sequence", None)
    username = get_jwt_identity()
    user_dt = users_db.find_one({'handle': username})
    insert_flag = False
    if user_dt == None:
        insert_flag = True

    cur_dict = dict()
    if (user_dt != None) and ('move_data' in user_dt.keys()):
        cur_dict = user_dt['move_data']

    spl = move_sequence.split(' ')
    current_moves = ''

    for i in range(len(spl)):
        if current_moves not in cur_dict.keys():
            cur_dict[current_moves] = [spl[i]]
        else:
            if spl[i] not in cur_dict[current_moves]:
                cur_dict[current_moves].append(spl[i]) 
        
        if current_moves != '':
            current_moves += ' '
        current_moves += spl[i]

    if insert_flag:
        users_db.insert_one({'handle': username, 'comment_data': dict(), 'move_data': cur_dict})
    else:
        users_db.update_one({'handle': username}, {'$set': {'move_data': cur_dict}})
    return {}

@api.route('/get-comment', methods=["POST"])
@jwt_required() 
def get_comment():
    username = get_jwt_identity()
    dt = users_db.find_one({'handle': username})
    if dt == None:
        return {'comment_data': {}}    
    return {'comment_data': dt['comment_data']}
    
@api.route('/get-move', methods=["POST"])
@jwt_required() 
def get_move():
    username = get_jwt_identity()
    dt = users_db.find_one({'handle': username})
    if dt == None:
        return {'move_data': {}}
    return {'move_data': dt['move_data']}
    
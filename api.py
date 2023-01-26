import time
import logging
import pymongo
from flask import Flask, request, jsonify, session
from flask_cors import CORS, cross_origin
import requests
from os import environ 
import hashlib
from dotenv import dotenv_values

config = dotenv_values(".env")

api = Flask(__name__)
cors = CORS(api)
api.config['CORS_HEADERS'] = 'Content-Type'

client = pymongo.MongoClient(config['MONGODB_TOKEN'])
db = client.get_database('chesslines')
users_db = db['chesslines']

username = 'keker1'

@api.route('/update-comment', methods=["POST"])
def update_comment():
    position = request.json.get("position", None)
    comment = request.json.get("comment", None)
    
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
def update_move():
    move_sequence = request.json.get("move_sequence", None)
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
def get_comment():
    dt = users_db.find_one({'handle': username})
    if dt == None:
        return {'comment_data': {}}    
    return {'comment_data': dt['comment_data']}
    
@api.route('/get-move', methods=["POST"])
def get_move():
    dt = users_db.find_one({'handle': username})
    if dt == None:
        return {'move_data': {}}
    return {'move_data': dt['move_data']}
    
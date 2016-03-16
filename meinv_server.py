#!/bin/python

from flask import Flask, request, session, g, redirect, url_for, flash
import sqlite3
from json import *
import uuid, time


#configuration
DATABASE = 'static/doubanmeizi.db'
DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)

@app.route('/types', methods=['POST', 'GET'])
def lookup_types():
    sql = 'select image_category_name from ImageTable group by image_category_name;'
    cur = g.db.execute(sql)
    types = [row[0] for row in cur.fetchall()]
    return_dic = dict(code=0, desc="Success",types=types)
    return JSONEncoder().encode(return_dic)
    

@app.route('/beauties', methods=['POST'])
def lookup_beauties():
    beauty_type = request.json.get("type", "all")
    user_uuid = request.json.get("user_uuid", "default")
    all_valid_types = ["gif", 'meitui', 'meitun', 'meixiong', 'qingxin']
    if (beauty_type not in all_valid_types):
        return_dic = dict(code=421, desc="{} is not a valid type. Valide type must be contained in {}".format(beauty_type, all_valid_types))
        return JSONEncoder().encode(return_dic)
    
    sql = ""
    if (user_uuid == 'default'):
        sql = """
    select image_name, image_url, image_width, image_height, image_category_name, image_id
         from ImageTable
    where image_category_name = "{}";
    """.format(beauty_type)
    else: 
        sql = """
        select image_name, image_url, image_width, image_height, image_category_name, ImageTable.image_id, FavoriteRelation.user_uuid
             from ImageTable
        left outer join FavoriteRelation on ImageTable.image_id = FavoriteRelation.image_id 
        where image_category_name = "{}" and (FavoriteRelation.user_uuid = "{}" or FavoriteRelation.user_uuid is NULL);
        """.format(beauty_type, user_uuid)
        
    cur = g.db.execute(sql)
    beauties = [dict(name=row[0], url=row[1], width=row[2], height=row[3],type=row[4], image_id=row[5], favorited=(0 if user_uuid == 'default' or row[6] != user_uuid else 1)) for row in cur.fetchall()]
    print(len(beauties))
    return_dic = dict(code=0, desc="Success",beauties=beauties)
    return JSONEncoder().encode(return_dic)


@app.route('/register', methods=['POST'])
def register_user():
    valid_user = True
    error_code = 0
    error_desc = "Success"
    uuid_str = ""
    user_name = request.json.get('username', "")
    user_password = request.json.get("password", "")
    user_nickname = request.json.get("nickname", "")
    
    if (len(user_name) == 0):
        error_code = 431
        valid_user = False
        error_desc = "invalid username"
    # select user 
    if user_in_database(user_name):
        error_code = 432
        valid_user = False
        error_desc = "username has been used"
        
    if (valid_user and len(user_password) == 0):
        error_code = 433
        valid_user = False
        error_desc = "invalid password"
    
    if (valid_user):
        #regiger
        uuid_str = register(user_name, user_password, user_nickname)
    
    return_dic = dict(code=error_code, desc=error_desc)
    user_dic = dict(user_name=user_name, user_uuid=uuid_str, user_nickname= user_nickname)
    if (valid_user): 
        return_dic = dict(code=0, desc=error_desc, user_info=user_dic)
        
    return JSONEncoder().encode(return_dic)
    
@app.route('/login', methods=['POST'])
def login():
    error_code = 0
    error_desc = "Success"
    
    user_name = request.json.get('username', "")
    user_password = request.json.get("password", "")
    users = find_user(user_name, user_password)
    if (len(users) == 0):
        error_code = 441
        error_desc = "Invald username or password"
        return_dic = dict(code=error_code, desc=error_desc)
        return JSONEncoder().encode(return_dic)
    
    user = users[0]
    return_dic = dict(code=error_code, desc=error_desc, user_info=user)
    return JSONEncoder().encode(return_dic)


@app.route('/favorite', methods=['POST'])
def favorite_beauty():
    beauty_uuid = request.json.get('beauty_uuid')
    user_uuid = request.json.get('user_uuid')
    return_code = insert_one_recode(user_uuid, beauty_uuid)
    if (return_code == 0):
        return_dic = dict(code=0, desc="Success")
        return JSONEncoder().encode(return_dic)
    else:
        return_dic = dict(code=451, desc="Failed to Favorite")
        return JSONEncoder().encode(return_dic)




def insert_one_recode(user_uuid, beauty_uuid):
    create_date = time.ctime()
    sql = """insert into FavoriteRelation(favorite_id, user_uuid, image_id, create_date) 
    values(NULL, '{}', '{}', '{}')""".format(user_uuid, beauty_uuid, create_date)
    try:
        cur = g.db.execute(sql)
    except sqlite3.Error,e:
        return -1
    g.db.commit()
    return 0

def find_user(username, user_password):
    sql = "select * from User where user_name = '{}' and user_password = '{}';".format(username, user_password)
    cur = g.db.execute(sql)
    result = [dict(user_uuid=row[0], user_name=row[1], user_nickname=row[2]) for row in cur.fetchall()]
    return result
    
def register(username, user_password, user_nickname):
    uuid_str = str(uuid.uuid1())
    create_date = time.ctime()
    sql = """insert into User(user_uuid, user_name, user_nickname, user_password, user_create_date)
    values('{}', '{}', '{}', '{}', '{}')""".format(uuid_str, username, user_nickname, user_password, create_date)
    cur = g.db.execute(sql)        
    g.db.commit()
    return uuid_str
    
    
def user_in_database(user_name):
    if (not user_name or len(user_name) == 0):
        return False
    sql = "select count() from User where user_name = '{}'".format(user_name)
    cur = g.db.execute(sql)
    result = [row[0] for row in cur.fetchall()]
    if (len(result) == 0): 
        return False
    count = int(result[0])
    return count == 1

@app.before_request
def before_request():
    g.db = connect_db()    

@app.teardown_request
def teardown_request(exception):
    g.db.close()


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0')


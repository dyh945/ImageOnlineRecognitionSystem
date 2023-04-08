from flask import Flask, request, render_template
import requests
import json
import redis
import mysql.connector
import os
from PIL import Image
from datetime import datetime

# 初始化 Flask 应用
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'WebServer/uploads' # 上传文件保存的路径

# 初始化 Redis 数据库
redis_client = redis.Redis(host='localhost', port=6379, db=0)
# 设置 Redis 数据库数据过期时间为 1 小时
redis_client.config_set('maxmemory', '1gb')
redis_client.config_set('maxmemory-policy', 'allkeys-lru')
redis_client.config_set('maxmemory-samples', '10')
redis_client.config_set('timeout', '3600')

# 初始化 MySQL 数据库
mysql_connection = mysql.connector.connect(
    host="localhost",
    # port=3306,
    user="root",
    password="root",
    database="ImageOnlineRecognitionSystem"
)

# def image2byte(image):
#     '''
#     图片转byte
#     image: 必须是PIL格式
#     image_bytes: 二进制
#     '''
#     # 创建一个字节流管道
#     import io
#     img_bytes = io.BytesIO()
#     #把PNG格式转换成的四通道转成RGB的三通道，然后再保存成jpg格式
#     image = image.convert("RGB")
#     # 将图片数据存入字节流管道， format可以按照具体文件的格式填写
#     image.save(img_bytes, format="JPEG")
#     # 从字节流管道中获取二进制
#     image_bytes = img_bytes.getvalue()
#     return image_bytes

def str2datetime(a):
    if type(a) == str:
        return datetime.strptime(a, '%Y-%m-%d %H:%M:%S')
    else:
        return a

# 定义路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image(model_url='http://localhost:5002/analyze_file'):
    # 获取上传的文件
    file = request.files['image']
    filename = file.filename
    # 保存上传的文件
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        file.save(file_path)

    # 加载图片
    files = {'image':open(file_path, "rb")}
    # 把图片传给识别模型
    response = requests.post(model_url, files=files)
    
    # 解析识别模型反馈的结果
    result = json.loads(response.content) 
    insert_log_to_mysql(filename, result['objects'][0][0])        # 将结果日志插入mysql数据库
    return {'result': result['objects'][0][0]}

def insert_log_to_mysql(filename, results):
    # 插入数据
    cursor = mysql_connection.cursor()
    sql = "INSERT INTO logs (filename, results) VALUES (%s, %s)"
    values = (filename, results)
    cursor.execute(sql, values)
    mysql_connection.commit()

    # 查询数据
    cursor.execute("SELECT * FROM logs")
    logs = cursor.fetchall()
    print(logs)

    # 关闭连接
    cursor.close()
    # mysql_connection.close()

@app.route('/api/logs')
def logs():
    # 从 Redis 中查询日志
    logs = []
    for key in redis_client.scan_iter("log:*"):
        log = redis_client.hgetall(key)
        # log['timestamp'] = datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S')   # 将字符串转换为 datetime 类型
        # logs.append(log)

    # 从 MySQL 中查询日志
    mysql_cursor = mysql_connection.cursor(dictionary=True)
    mysql_cursor.execute("SELECT * FROM logs")
    mysql_logs = mysql_cursor.fetchall()
    mysql_cursor.close()

    # 更新 Redis 数据库，将 MySQL 中存在但 Redis 中不存在的日志加入 Redis
    for log in mysql_logs:
        key = f"log:{log['filename']}"
        if not redis_client.exists(key):
            # log['timestamp'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')    # 将 datetime 类型转换为字符串
            redis_client.hmset(key, log)

    # 将 Redis 和 MySQL 中的日志合并
    logs += mysql_logs
    print(logs)

    # # 根据时间戳降序排列
    # logs = sorted(logs, key=lambda log: str2datetime(log.get('timestamp', '')), reverse=True)

    # 返回渲染后的 HTML 页面
    return render_template('logs.html', logs=logs)

@app.route('/api/logs/<filename>', methods=['DELETE'])
def delete_log(filename):
    # 删除 MySQL 中的日志
    cursor = mysql_connection.cursor()
    cursor.execute('DELETE FROM logs WHERE filename = %s', (filename))
    mysql_connection.commit()
    cursor.close()

    # 如果 Redis 中存在该日志，则删除
    key = f'log:{filename}'
    if redis_client.exists(key):
        redis_client.delete(key)

    return {'message': f'日志 {filename} 删除成功'}


if __name__ == '__main__':
    app.run(debug=True)
    redis_client.close()
    mysql_connection.close()
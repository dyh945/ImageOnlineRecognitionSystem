from flask import Flask, request, render_template
import requests
import json
import redis
import mysql.connector
import os
from PIL import Image

# test


# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads' # 上传文件保存的路径

# # Initialize Redis client
# redis_client = redis.Redis(host='localhost', port=6379, db=0)

# # Initialize MySQL connection
# mysql_connection = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="your_password",
#     database="your_database"
# )

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

# Define routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image(model_url='http://localhost:5002/analyze_file'):
    # TODO: Implement image recognition logic here
    # 获取上传的文件
    file = request.files['image']
    filename = file.filename
    # 保存上传的文件
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # 加载图片
    files = {'image':open(file_path,"rb")}
    # 把图片传给识别模型
    response = requests.post(model_url, files=files)
    
    # 解析识别模型反馈的结果
    result = json.loads(response.content) 
    return {'result': result['objects'][0][0]}

@app.route('/logs')
def logs():
    # Query logs from Redis
    logs = []
    for key in redis_client.scan_iter("log:*"):
        log = redis_client.hgetall(key)
        logs.append(log)

    # Query logs from MySQL
    mysql_cursor = mysql_connection.cursor(dictionary=True)
    mysql_cursor.execute("SELECT * FROM logs")
    logs += mysql_cursor.fetchall()

    # Sort logs by timestamp in descending order
    logs = sorted(logs, key=lambda log: log.get('timestamp', ''), reverse=True)

    return render_template('logs.html', logs=logs)

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True)

# -*- coding:utf-8 -*-
import requests
from urllib.parse import urlencode
from requests.exceptions import RequestException
import json
from  bs4 import BeautifulSoup
import re
from config import *
import pymongo
import os
from hashlib import md5
from multiprocessing import Pool

client = pymongo.MongoClient(MONGO_URL,connect=False )
db = client[MONGO_DB]

def get_page_index(offset,keyword):#获取索引页网站源代码
    data={
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 3
    }

    url = 'https://www.toutiao.com/search_content/?'+ urlencode(data)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求索引页出错')
        return None
def parse_page_index(html):#解析索引页信息
    data = json.loads(html)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            yield item.get('article_url')

def get_page_detail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求详情页出错',url)
        return None

def parse_page_detial(html,url):
    soup =BeautifulSoup(html,'lxml')
    title = soup.select('title')[0].get_text()
    print(title)
    image_pattern = re.compile('gallery: JSON.parse\((.*?)\),\n',re.S)
    result = re.search(image_pattern,html)
    if result:
        data= json.loads(json.loads(result.group(1)))
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:
                download_image(image)
            return{
                'title':title,
                'url':url,
                'images':images
            }

def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print('存储到MONGODB成功',result)
            return True
        return False
    except Exception:
        pass

def download_image(url):
    print('正在下载',url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            save_image(response.content)
        return None
    except RequestException:
        print('请求图片出错',url)
        return None

def save_image(content):#创建对应分类的文件夹，并且保存图片。个人
    dir_name=str(KEYWORD)+'_'+str(GROUP_START)+'-'+str(GROUP_END)#个人补充功能！
    dir_path='F:\python\DATA\jiepai\jiepai\{}'.format(dir_name)
    try:
        os.mkdir(dir_path)
    except:
        pass

    file_path='{0}/{1}.{2}'.format(dir_path,md5(content).hexdigest(),'jpg')
    if not os.path.exists(file_path):
        with open(file_path,'wb') as f:
            f.write(content)
            f.close()

def main(offset):#主程序流程
    html = get_page_index(offset ,KEYWORD)#自己输入搜索内容，还有搜索量，获取索引页源代码
    for url in parse_page_index(html):#解析索引页代码，并且用遍历，提取出url(各个详情页链接入口)
        html = get_page_detail(url)#得到详情页网页源代码
        if html:#如果得到正常得到详情页网站源代码，继续以下步骤
            result = parse_page_detial(html,url)#解析详情页源代码，得到result，包含各个图片的链接，所在图集标题，详情页地址。
            if result:
                save_to_mongo(result)

if __name__ == '__main__':
    groups = [x*20 for x in range(GROUP_START,GROUP_END + 1)]
    pool = Pool()
    pool.map(main,groups)

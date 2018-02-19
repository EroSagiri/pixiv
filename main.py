from urllib import request, parse
from urllib.error import HTTPError,URLError
import re, json, http.cookiejar, requests
import socket, time, sys, threading

class Main(object):
    def __init__(self, url=None):
        """
        url 爬取页面的url
        """
        self.request = Request()
        self.downloader = Downloader()
        self.parse = Parse()
        self.url = url
        self.cookies = None
        self.dir = "images"
        self.threadIndex = 1
        self.threadOver = 0
    

    def run(self, index=None):
        if index == None:
            try:
                f = open("schedule.txt", "r")
                t = f.read()
                f.close()

                if t == '' or t == None:
                    index = 1
                else:
                    index = int(t)
            except:
                print("读取进度错误")
                index = 1

            

        print("获取到进度" + str(index) )
        print("正在获取登陆信息...")
        if not(self.cookies == None):
            try:
                html = requests.get("https://www.pixiv.net/", headers=self.request.headers, cookies=self.cookies).text
                status = self.parse.getStatus(html)
                if status == False:
                    print("未登陆")
                else:
                    print(status + "， 已登陆")
                    self.status = True
            except:
                print("获取登陆信息失败")
        else:
            print("cookie未设置")
        self.index = index

        for i in range(self.threadIndex):
            try:
                threading.Thread(target=self.newThread, args=()).start()
            except:
                print("启动线程失败")
        
            
    def newThread(self):
        """
        一个单线程
        """
        index = self.index
        self.index += 1

        while True:
            print(time.strftime("%H:%M:%S", time.localtime()) + "开始爬取页面 " + str(index))
            startTime = time.time()

            t = self.getItems(index)

            if t == 'over':
                self.over()
                break
            if t == True:
                overTime = time.time()
                print(time.strftime("%H:%M:%S", time.localtime()) + " 成功爬取页面 " + str(index) + "用时: " + str(overTime - startTime) + "s" )
                try:
                    f = open("schedule.txt", "w")
                    f.write(str(index))
                    f.close()
                except:
                    print("保存进度失败")
            else:
                print("页面" + str(index) + "爬取失败")

            index = self.index
            self.index += 1


            

    def over(self):
        self.threadOver += 1
        print(str(self.threadOver) + "个线程爬取完成")
        if self.threadOver == self.threadIndex:
            print("所有线程爬取完成， 5秒后关闭")
            time.sleep(5)
            sys.exit()


            
        


    
    def getItems(self, p):
        """
        用途 获取一个页面的所有图片
        p 页面序号
        """
        # 拼接url
        pUrl = self.url + '&p=' + str(p)


        try:
            html = requests.get(pUrl, headers=self.request.headers, cookies=self.cookies).text
        except:
            print("请求失败")
            return False
        
        if self.parse.getOver(html):
            return 'over'

        items = self.parse.getItems(html)
        if items == False:
            print("从页面获取items 失败")
            return False
        if len(items) == 0:
            return False

        # self.getI(items[0])

        # 开始遍历 items
        _errorItems = []
        while len(items) > 0 or len(_errorItems) > 0:
            if len(items) > 0:
                item = items.pop()
                if self.getI(item) == False:
                    _errorItems.append({
                        "index" : 1,
                        "data" : item
                    })
            elif len(_errorItems) > 0:
                item = _errorItems.pop()
                if self.getI(item["data"]) == False:
                    item["index"] += 1
                    if item["index"] > 3:
                        # 写进日志
                        try:
                            pid = str(item['data']['illustId'])
                            print("pid:" + pid + " 获取失败")
                            f = open("error_item.txt", "a")
                            f.write(pid + '\n')
                        except:
                            print("写进日志失败")
                    else:
                        _errorItems.append(item)
        
        return True

    
    def getI(self, item):
        """
        用途 获取指定Pid的图片
        Pid P站id
        """
        pUrl = "https://www.pixiv.net/member_illust.php?mode=medium&illust_id=" + str(item["illustId"])
        pId = item["illustId"]
        http = self.request.get(pUrl)
        if not(http["status"] == "OK"):
            print("在获取pid页面是失败")
            return False
        html = http["data"].decode('utf-8')
        
        if int(item["pageCount"]) > 1:
            data = self.parse.getImages(html, pUrl)
        else:
            data = self.parse.getImages(html)
        if data == False:
            print("解析图片失败")
            return False

        dowImgs = data["images"]

        _errorIndex = 0
        for i in range(len(dowImgs)):
            src = dowImgs[i]
            # 获取图片后缀名
            try:
                finetype = re.search(r'\S+\.(\S+?)$', src).group(1)
            except:
                finetype = 'jpg'
            
            _index = 0
            while True:
                if self.downloader.dowF(src, self.dir + '/' + str(pId) + '_' + str(i) + '.' + finetype,  self.request.headers) == False:
                    _index += 1
                else:
                    break
                if _index > 3:
                    # 写进日志
                    print("下载" + str + " 失败， 写入日志")
                    f = open("downloader_error", "a")
                    f.write(src + "\n")
                    f.close()
                    _errorIndex += 1
                    break


        print(time.strftime("%H:%M:%S", time.localtime()) + " pid:" + str(pId) + " 爬取成功")
        txt = str(pId) + ' ' + str(data["ratedCount"]) + '\n'
        self.save(txt)
        return True

    def save(self, txt):
        f = open("item.txt", "a")
        f.seek(0, 2)
        f.write(txt)
        f.close()

    def setCookies(self, cookiesText):
        """
        用途 设置访问页面的cookies
        """
        _cookie = {}
        for row in cookiesText.split(';'):
            k, v = row.strip().split('=', 1)
            _cookie[k] = v
        self.cookies = _cookie
        return True

        
class Request(object):
    def __init__(self):
        self.cookie = http.cookiejar.MozillaCookieJar('pixivCookie.txt')
        self.header = request.HTTPCookieProcessor(self.cookie)
        self.opener = request.build_opener(self.header)
        self.headers = {
            "User-Agent" : r'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
            "Referer" : r'https://www.pixiv.net',
            "Origin" : r'https://www.pixiv.net'
        }


    def get(self, url, headers=None, timeout=5):
        """
        用途 发送http get 请求
        """
        try:
            if headers == None:
                html = request.urlopen(url, timeout=timeout).read()
            else:
                req = request.Request(url, headers=headers)
                html = request.urlopen(req, timeout=timeout).read()
        except URLError:
            return {
                "status" : "URLError"
            }
        except HTTPError as e:
            print(dir(HTTPError))
            return {
                "status" : "HTTPError",
                "code" : e.code
            }
        except socket.timeout:
            print("请求超时")
            return {
                "status" : "socket.timeout"
            }
        except:
            print("未知的错误")
            return {
                "status" : "error"
            }
        else:
            return {
                "status" : "OK",
                "data" : html
            }
    
    def login(self, id, pwd):
        """
        用途 登陆pixiv
        """
        loginUrl = "https://accounts.pixiv.net/login?lang=zh"
        apiUrl = "https://accounts.pixiv.net/api/login?lang=zh"
        self.opener.open(loginUrl)
        data = {
            "pixiv_id" : id,
            "password" : pwd,
            "post_key" : "869a622368d79e12bdcb34374ba4fec",
            "source" : "accounts",
            "return_to" : "https://www.pixiv.net/"
        }
        data = parse.urlencode(data).encode('utf-8')
        req = request.Request(apiUrl,headers=self.headers, data=data)
        html = request.urlopen(req)
        print(json.loads(html.read().decode('utf-8')))
        self.cookie.save(ignore_discard=True, ignore_expires=True)



class Downloader(object):
    def dowF(self, url, filename, headers=None, timeout=5):
        """
        用途 下载文件
        """
        req = Request()
        h = req.get(url, headers, timeout)
        if h["status"] == "OK":
            try:
                data = h["data"]
                f = open(filename, "wb")
                f.write(data)
                f.close()
                return True
            except FileNotFoundError:
                print("FileNotFoundError")
                return False
        elif h["status"] == "HTTPError":
            print("HTTPError, code " + h["code"])
        elif h["status"] == "URLError":
            print("URLError")


class Parse(object):
    def getItems(self, html):
        """
        用途 解析p html 页面
        """
        res = re.search(r'data-items="(.+?)"', html)
        if res != None:
            try:
                dataItems = res.group(1)
                dataItems = re.sub("&quot;", '"', dataItems)
                return json.loads(dataItems)
            except IndexError:
                return False


    def getImages(self, html, url=None):
        """
        用途 从页面中获取图片
        """
        data = {}


        view = re.findall(r'<span class="views">(\S+?)</span>', html)
        # 浏览量
        try:
            viewCount = view[0]
        except:
            viewCount = "None"
        # 赞！
        try:
            ratedCount = view[1]
        except:
            ratedCount = "None"

        data["viewCount"] = viewCount
        data["ratedCount"] = ratedCount


        if url == None:
            # 单张图片
            images = []
            try:
                images.append(re.search(r'data-title="registerImage"><img src="(\S+)"', html).group(1) )
            except:
                print("解析页面失败")
                return False

            data["images"] = images
        else:
            # 多张图片
            images = []
            pUrl = re.sub('medium', 'manga', url)
            request = Request()
            http = request.get(pUrl, request.headers)
            if not(http["status"] == "OK"):
                print("请求失败")
                return False
            phtml = http["data"].decode('utf-8')
            
            try:
                images = re.findall(r'data-filter="manga-image" data-src="(\S+?)"', phtml)
            except:
                return False
            data["images"] = images

        return data
    

    def getStatus(self, html):
        """
        用途 获取登陆状态
        """
        try:
            username = re.search(r'click-profile"data-click-label="">(\S+?)</a>', html).group(1)
        except:
            username = None
        
        if username == None:
            return False
        else:
            return username


    def getOver(self, html):
        """
        用途 判断是否爬取完成
        """
        try:
            items = re.search(r'data-items="\[\]"', html)
        except:
            print()
        
        if items == None:
            return False
        else:
            return True






if __name__ == '__main__':
    main = Main("https://www.pixiv.net/search.php?s_mode=s_tag&word=%E9%AA%8C%E5%AD%95%E6%A3%92")

    # 从浏览器复制
    cookiesText = "login_ever=yes; _tdim=8f3e76e2-357f-4599-efb6-0982a66fed17; is_sensei_service_user=1; p_ab_id=5; p_ab_id_2=6; __utmz=235335808.1518268144.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); login_bc=1; _ga=GA1.2.2058836629.1518268144; _gid=GA1.2.506767615.1518268171; PHPSESSID=27982114_e0d2c5b3f34e8f23e3ea2af981a7636c; device_token=3fcec64cd9b4ce40a4cad055f44361c9; c_type=20; a_type=0; b_type=2; module_orders_mypage=%5B%7B%22name%22%3A%22sketch_live%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22tag_follow%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22recommended_illusts%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22showcase%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22everyone_new_illusts%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22following_new_illusts%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22mypixiv_new_illusts%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22fanbox%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22featured_tags%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22contests%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22user_events%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22sensei_courses%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22spotlight%22%2C%22visible%22%3Atrue%7D%2C%7B%22name%22%3A%22booth_follow_items%22%2C%22visible%22%3Atrue%7D%5D; __utmv=235335808.|2=login%20ever=yes=1^3=plan=normal=1^5=gender=female=1^6=user_id=27982114=1^9=p_ab_id=5=1^10=p_ab_id_2=6=1^11=lang=zh=1; __utma=235335808.2058836629.1518268144.1518268144.1518328926.2; __utmc=235335808; __utmt=1; __utmb=235335808.1.10.1518328926; _td=6b937fc5-dc5b-49f9-b30d-61f88f1e53e5"
    
    main.setCookies(cookiesText)
    main.threadIndex = 4
    main.run()
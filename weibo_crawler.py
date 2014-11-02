#!/usr/bin/env python

from weibo_login import login as loginToWeibo, urllib2
import threading
import Queue
import getpass
import re

class CrawlerThread(threading.Thread):

	rFollowItem = re.compile(r"""
            (<li\ class=\\"follow_item.*? # beginning of a fan
                uid=(?P<uid>\d+)&   # uid
                fnick=(?P<nickname>[^&]+)& # nickname
                sex=(?P<gender>[^\\]+).*? # gender
                (?P<approved>微博个人认证)?.*? # approved person
                (?P<approved_co>微博机构认证)?.*?	# approved company
                关注\ <em[^>]+?><a[^>]+?>(?P<follwing>\d+).*? # following
                粉丝<em[^>]+?><a[^>]+?>(?P<fans>\d+).*? # fans number
                微博<em[^>]+?><a[^>]+?>(?P<weibo>\d+).*? # weibo number
                地址<\\/em><span>(?P<address>[^<]+).*? # weibo number
                info_intro\\"><span>(?P<introduction>[^<]+).*?
            <\\/li>)+ # end of a fan
        """, re.X)

	def __init__(self, taskQueue):
		threading.Thread.__init__()
		self.taskQueue = taskQueue

	def run(self):
		while True:
			uid = self.taskQueue.get()
			url = 'http://weibo.com/p/' + uid + '/follow?page='
			for i in range(1, 6):
				url += str(i)
				html = urllib2.urlopen(url).read()


class Crawler:
	def __init__(self, nThreads = 50, urlToStart = None):
		self.nThreads = nThreads
		self.urlToStart = urlToStart
		self.taskQueue = Queue.Queue()
		self.fileLock = threading.Lock()
	def start(self):
		if urlToStart != None:
			self.taskQueue.put()
			for i in range(0, self.nThreads):
				crawlerThread = CrawlerThread(taskQueue = self.taskQueue, fileLock = self.fileLock)
				crawlerThread.start()
			self.taskQueue.join()
		else:
			raise EOFError("No start url defined")

if __name__ == '__main__':
	username = '18817583755'
	password = getpass.getpass()
	cookieFile = 'cookies.txt'
	loginSuccess = loginToWeibo(username = username, pwd = password, cookie_file = cookieFile)
	if loginSuccess:
		urlToStart = 'http://weibo.com/blabla'
		crawler = Crawler(urlToStart = urlToStart)
		crawler.start()
	else:
		raise RuntimeError("Login to weibo failed")
#!/usr/bin/env python

from weibo_login import login as loginToWeibo
import threading
import Queue
import getpass

class CrawlerThread(threading.Thread):
	def __init__(self, taskQueue):
		threading.Thread.__init__()
		self.taskQueue = taskQueue
	def run(self):
		while True:
			pass

class Crawler:
	def __init__(self, nThreads = 50, urlToStart = None):
		self.nThreads = nThreads
		self.urlToStart = urlToStart
		self.taskQueue = Queue.Queue()
		self.fileLock = threading.Lock()
	def start(self):
		if urlToStart != None:
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
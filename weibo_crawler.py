#!/usr/bin/env python

from weibo_login import login
import threading
import Queue

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
			raise EOFError("No start url defined!")

if __name__ == '__main__':
	urlToStart = 'http://weibo.com/blabla'
	crawler = Crawler(urlToStart = urlToStart)
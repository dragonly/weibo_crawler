#!/usr/bin/env python
# -*- coding=utf8 -*-

from weibo_login import login as loginToWeibo, S
import threading
import Queue
import getpass
import re
import time
from math import floor
from random import random

__DEBUG__ = True

def debug(message):
	global __DEBUG__
	if __DEBUG__:
		print message

class GetUidThread(threading.Thread):

	rFollowItem = re.compile(r"""
			<li\ class=\\"follow_item[\s\S]*? # beginning of a fan
				uid=(?P<uid>\d+)&   # uid
				fnick=(?P<nickname>[^&]+)& # nickname
				sex=(?P<gender>[^\\]+)[\s\S]*? # gender
				(?:微博(?P<approved>个人|机构)认证[\s\S]*?)? # TODO
				关注\ <em[^>]+?><a[^>]+?>(?P<follwing>\d+)[\s\S]*? # following
				粉丝<em[^>]+?><a[^>]+?>(?P<fans>\d+)[\s\S]*? # fans number
				微博<em[^>]+?><a[^>]+?>(?P<weibo>\d+)[\s\S]*? # weibo number
				(?:地址<\\/em><span>(?P<address>[^<]+)[\s\S]*?)? # weibo number
				(?:info_intro\\">.*?<span[^>]*>(?P<introduction>[^<]+)[\s\S]*?)? # introduction
			<\\/li> # end of a fan # end of a fan
		""", re.X)
	

	def __init__(self, taskQueue, fileLock, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)
		self.taskQueue = taskQueue

	def _extractFromDict(self, target, fileds):
		ret = {}
		for filed in fileds:
			if target[filed] != None:
				ret[filed] = target[filed]
		return ret

	def _extract(self, url):
		html = S.get(url).text
		iter = self.__class__.rFollowItem.finditer(html)
		uids = []
		for i in iter:
			gDict = i.groupdict()
			if gDict['weibo'] > 1000 and gDict['fans'] > 10000:
				user = this._extractFromDict(gDict, ['uid', 'nickname', 'gender', 'introduction', 'address', 'approved', 'weibo', 'fans', 'following'])
				uids.append(user)
			# for (key, value) in gDict.items():
			# 	# sys.stdout.write(key + ': ' + value + ' | ')
			# 	print key, ': ', value
			# # print i.groups()
			# print '-' * 10

			# if random() < 0.1:
				# self.taskQueue.put(gDict['uid'])

	def run(self):
		while True:
			try: 
				uid = self.taskQueue.get(True)
			except Queue.Empty, e:
				print e, '\ntask done'
				return
				# continue
			url = 'http://weibo.com/' + str(uid) + '/follow?page='
			uids = []
			for i in range(1, 6):
				urlToRequest = url + str(i)
				print urlToRequest
				# retry = 3
				count = 0
				# reconnect if network error occurs
				while True:
					try:
						uids.extend(self._extract(urlToRequest))
						print threading.current_thread()
						break
					except Exception, e:
						count += 1
						print e, '-'*6, count

			# when task_done() called, count of unfinished tasks goes down,
			# so you call this every time you consume a very single item!!!

			self.taskQueue.task_done()
			# print self.taskQueue.queue


class Crawler:
	def __init__(self, numGetUidThread = 5, uidToStart = None, numGetPostsThread = 20):
		self.numGetUidThread = numGetUidThread
		self.uidToStart = uidToStart
		self.numGetPostsThread = numGetPostsThread
		self.taskQueue = Queue.Queue()
		self.fileLock = threading.Lock()
	def startGetUid(self):
		if self.uidToStart != None:
			if isinstance(self.uidToStart, list):
				for item in self.uidToStart:
					self.taskQueue.put(item)
			else:
				self.taskQueue.put(self.uidToStart)
			for i in range(0, self.numGetUidThread):
				getUidThread = GetUidThread(taskQueue = self.taskQueue, fileLock = self.fileLock)
				getUidThread.start()
			self.taskQueue.join()
		else:
			raise EOFError("No start uid defined")
	
	def startGetPosts(self):
		pass

	def start(self):
		getUidThread = threading.Thread(target=self.startGetUid)
		getUidThread.start()
		getUidThread.join()

if __name__ == '__main__':
	username = '18817583755'
	password = getpass.getpass()
	cookieFile = 'cookies.txt'
	if loginToWeibo(username = username, pwd = password, cookies_file = cookieFile):
		uidToStart = ['1826792401', '1826792402', '1826792403', '1826792404', '1826792405'] # sephirex
		crawler = Crawler(uidToStart = uidToStart, numGetUidThread = 2)
		crawler.start()
	else:
		raise RuntimeError("Login to weibo failed")
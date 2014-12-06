#!/usr/bin/env python
# -*- coding=utf8 -*-

import threading
import Queue
import getpass
import re
import time
import signal
import logging
import json
from math import floor
from random import random
from weibo_login import login as loginToWeibo, S
from bs4 import BeautifulSoup as BS

logging.basicConfig(level = logging.DEBUG,
					format='[%(levelname)s] '
							'%(filename)s '
							'[%(lineno)d] '
							'%(threadName)s '
							'%(message)s')
							# ' - %(asctime)s', datefmt='[%d/%b/%Y %H:%M:%S]')
					# filename

class LogFilter(logging.Filter):

	allowedFiles = ['weibo_crawler.py', 'weibo_login.py']

	def filter(self, record):
		return record.filename in LogFilter.allowedFiles

logging.getLogger('requests').setLevel(logging.WARNING)
# logFilter = LogFilter()
# log.addFilter(logFilter)

def csvGenerator(fd):
	data = ''
	while True:
		buff = fd.read(1024)
		if not buff:
			break
		data += buff
		if not ',' in buff:
			continue
		l = data.split(',')
		count = len(l)
		for i in xrange(count-1):
			yield l[i]
		data = l[count-1]
	yield data

class GetUidThread(threading.Thread):

	def __init__(self, uidsToVisit, uidsVisited, uidsToCrawl, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)
		self.uidsToVisit = uidsToVisit
		self.uidsVisited = uidsVisited
		self.uidsToCrawl = uidsToCrawl
		self.__terminated__ = False

	def get_follow_list(self, uid, page):

		url = 'http://weibo.com/' + str(uid) + '/follow?page=' + str(page)

		html = S.get(url).text

		pattern = r'html":"(<div class="WB_cardwrap S_bg2">[^}]*?)"\}'
		html = html.replace('\\t', '').replace('\\n', '').replace('\\r', '').replace('\\', '')
		# print html
		try:
			html_snippet = re.search(pattern, html).group(1)
		except AttributeError, e:
			print e
			return
		except Exception, e:
			logging.exception('Getting follow list failed')
			return
		
		soup = BS(html_snippet)

		followList = soup.find_all('li', class_='follow_item')
		# info = []
		for item in followList:
			try:
				d = {}
				kv = [pair.split('=') for pair in item.attrs['action-data'].split('&')]
				for pair in kv:
					d[pair[0]] = pair[1]
				
				mod_info = item.find('dd', class_='mod_info')

				# filter topics
				is_topic = mod_info.find('div', class_='info_name').find('span')
				if is_topic and is_topic.text == '#':
					continue

				nums = mod_info.find('div', class_='info_connect').find_all('span')
				# print nums
				d['following'] = nums[0].find('em').text
				d['follower'] = nums[1].find('em').text
				d['posts'] = nums[2].find('em').text

				address = mod_info.find('div', class_='info_add')
				if address:
					address = address.find('span').text
				introduction = mod_info.find('div', class_='info_intro')
				if introduction:
					introduction = introduction.find('span').text
				follow_from = mod_info.find('div', class_='info_from')
				if follow_from:
					follow_from = follow_from.find('a').text

				d['address'] = address
				d['introduction'] = introduction
				d['follow_from'] = follow_from

				# info.append(d)

				if self._qualified(d) and (d['uid'] not in self.uidsVisited) and (d['uid'] not in self.uidsToVisit):
					self.uidsToVisit.add(d['uid'])
					self.uidsToCrawl.add(d['uid'])

				with open('./data/html/%s.txt' % d['uid'], 'wt') as fd:
					json.dump(d, fd)

			except Exception, e:
				logging.exception('Parse follow list of %s [%s] error' % (uid, page))

	def _qualified(self, info):
		# return info['following']
		return True

	def run(self):
		while not self.__terminated__:
		# for i in range(1):
			while len(self.uidsToVisit) <= 0:
				pass

			try:
				uid = self.uidsToVisit.pop()
			except Exception, e:
				logging.exception('Getting uidsToVisit error')
				continue
			
			logging.info('Getting following list from uid[\'%s\']' % uid)
			for i in range(1, 6):
				self.get_follow_list(uid, i)

			self.uidsVisited.add(uid)

			logging.debug('Uids visited: %s' % len(self.uidsVisited))
			logging.debug('Uids to visit" %s' % len(self.uidsToVisit))

			# when task_done() called, count of unfinished tasks goes down,
			# so you call this every time you consume a very single item!!!

			# self.uidsToVisit.task_done()
			# print self.taskQueue.queue

class GetPostsThread(threading.Thread):
	def __init__(self, uidsToCrawl, uidsCrawled, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)
		self.uidsToCrawl = uidsToCrawl
		self.uidsCrawled = uidsCrawled
		self.__terminated__ = False

	def _escape_unicode(self, text):
		remove = ['\\n', '\\r', '\\t', '\\', '{"code":"100000","msg":"","data":"', '"}']

		pUnicodeReplace = re.compile(r'u(?=[0-9a-f]{4})')
		pUnicode = re.compile(r'u[0-9a-f]{4}')

		for i in remove:
			text = text.replace(i, '')
		for i in pUnicode.finditer(text):
			original = i.group(0)
			modified = ('\\' + original).decode('unicode-escape')
			text = text.replace(original, modified)
		return text

	def get_posts(self, uid):
		url_home = 'http://weibo.com/u/' + str(uid) + '?page='
		url_mbloglist = "http://weibo.com/p/aj/v6/mblog/mbloglist"
		params = {}
		params['pre_page'] = 1
		params['page'] = 1
		params['pagebar'] = 0
		for page in range(11)[1:]:
			if self.__terminated__:
				break
			try:
				logging.info('Getting posts from %s' % url_home)
				html = S.get(url_home + str(page)).text

				left = html.find('$CONFIG[\'domain\']=\'') + 19
				right = html.find('\'', left + 1)
				params['domain'] = html[left:right]

				left = html.find('$CONFIG[\'page_id\']=\'') + 20
				right = html.find('\'', left + 1)
				params['id'] = html[left:right]

				# first part is right in the home page of this page
				left = html.find('<!--feed内容-->') + 13
				right = html.find('"}', left + 1)
				html = html[left:right].replace('\\t', '').replace('\\n', '').replace('\\r', '').replace('\\', '')

				# then followed by 2 scroll to refresh parts on this page
				for j in range(2):
					html_snippet = S.get(url_mbloglist, params = params).text
					html += self._escape_unicode(html_snippet)
					params['pagebar'] += 1

				logging.info('Writing %s to file' % url_home)
				with open('./data/html/%s?page=%s.html' % (uid, str(page)), 'wt') as fd:
					fd.write(BS(html).prettify())

				params['pre_page'] += 1
				params['page'] += 1
				params['pagebar'] = 0

			except Exception, e:
				logging.exception('Getting posts from %s failed' % str(uid))

	def run(self):
		while not self.__terminated__:
			while len(self.uidsToCrawl) <= 0:
				pass
			try:
				uid = self.uidsToCrawl.pop()
			except Exception, e:
				logging.exception('Getting uidsToCrawl Error')
				continue

			logging.info('Getting posts from user %s' % uid)
			self.get_posts(uid)
			self.uidsCrawled.add(uid)

			logging.debug('Uids crawled: %s' % len(self.uidsCrawled))
			logging.debug('Uids to crawl" %s' % len(self.uidsToCrawl))

class Crawler:
	def __init__(self, numGetUidThread = 2, numGetPostsThread = 20, fileuidsToVisit = None, fileUidsVisited = None):
		self.numGetUidThread = numGetUidThread
		self.numGetPostsThread = numGetPostsThread

		self.uidsToVisit = set()
		self.uidsVisited = set()
		self.uidsToCrawl = set()
		self.uidsCrawled = set()

		self.fdUidsToVisit = open(fileuidsToVisit, 'r+t')
		self.fdUidsVisited = open(fileUidsVisited, 'r+t')
		self.fdUidsToCrawl = open(fileUidsToCrawl, 'r+t')
		self.fdUidsCrawled = open(fileUidsCrawled, 'r+t')

		self._loadUidsFromFile(self.fdUidsToVisit, self.uidsToVisit)
		self._loadUidsFromFile(self.fdUidsVisited, self.uidsVisited)
		self._loadUidsFromFile(self.fdUidsToCrawl, self.uidsToCrawl)
		self._loadUidsFromFile(self.fdUidsCrawled, self.uidsCrawled)

		self.getUidThreads = []
		self.getPostsThreads = []

	def _loadUidsFromFile(self, fd, uidSet):
		uidsIter = csvGenerator(fd)
		for uid in uidsIter:
			if uid != '':
				uidSet.add(uid)

	def startGetUid(self, q):
		for i in range(0, self.numGetUidThread):
			getUidThread = GetUidThread(uidsToVisit = self.uidsToVisit, uidsVisited = self.uidsVisited, uidsToCrawl = self.uidsToCrawl)
			getUidThread.daemon = True
			self.getUidThreads.append(getUidThread)
			getUidThread.start()

		for thread in self.getUidThreads:
			thread.join()

		# q.task_done()
	
	def startGetPosts(self, q):
		for i in range(0, self.numGetPostsThread):
			getPostsThread = GetPostsThread(uidsToCrawl = self.uidsToCrawl, uidsCrawled = self.uidsCrawled)
			getPostsThread.daemon = True
			self.getPostsThreads.append(getPostsThread)
			getPostsThread.start()

		for thread in self.getPostsThreads:
			thread.join()

		# q.task_done()

	def start(self):
		q = Queue.Queue()
		q.put(1)
		q.put(1)
		t = threading.Thread(target=self.startGetUid, args=(q, ))
		t.daemon = True
		t.start()
		t = threading.Thread(target=self.startGetPosts, args=(q, ))
		t.daemon = True
		t.start()
		# q.join()

	def _writeUidsToFile(self, fd, uidSet):
		fd.truncate()
		fd.seek(0)
		for uid in list(uidSet)[:-1]:
			fd.write(uid)
			fd.write(',')
		fd.write(list(uidSet)[-1])
		fd.close()

	def stop(self):
		for thread in self.getUidThreads:
			thread.__terminated__ = True
		for thread in self.getPostsThreads:
			thread.__terminated__ = True

		# wait until all thread finish current run
		for thread in self.getUidThreads:
			thread.join()
		for thread in self.getPostsThreads:
			thread.join()

		self._writeUidsToFile(self.fdUidsToVisit, self.uidsToVisit)
		self._writeUidsToFile(self.fdUidsVisited, self.uidsVisited)
		self._writeUidsToFile(self.fdUidsToCrawl, self.uidsToCrawl)
		self._writeUidsToFile(self.fdUidsCrawled, self.uidsCrawled)

def exitHandler(*args, **kwargs):
	global crawler
	crawler.stop()
	exit()

if __name__ == '__main__':
	username = '18817583755'
	# password = getpass.getpass()
	password = ''
	cookieFile = 'cookies.txt'
	if loginToWeibo(username = username, pwd = password, cookies_file = cookieFile):
		fileuidsToVisit = './data/uidsToVisit.txt'
		fileUidsVisited = './data/uidsVisited.txt'
		fileUidsToCrawl = './data/uidsToCrawl.txt'
		fileUidsCrawled = './data/uidsCrawled.txt'
		crawler = Crawler(numGetUidThread = 2, numGetPostsThread = 50, fileuidsToVisit = fileuidsToVisit, fileUidsVisited = fileUidsVisited)
		crawler.start()
 
		signal.signal(signal.SIGINT, exitHandler)

		while True:
			pass
	else:
		raise RuntimeError("Login to weibo failed")
#!/usr/bin/env python2
# -*- coding: utf8 -*-

class CXMPPLogger:
    def __init__(self, config):
	self.config = config
	self.ready = False

    def setBot(self, bot):
	self.bot = bot
	self.ready = True
	
    def log(self, text):
	if self.ready:
	    if self.config['manage']['log_to_admins'] == 'true':
		self.logToAdmins(text)
	    self.logToLoggers(text)

    def logToAdmins(self, text):
	for admin in self.config['manage']['admins']:
		self.bot.sendMessage(admin, text)

    def logToLoggers(self, text):
	for logger in self.config['manage']['loggers']:
	    self.bot.sendMessage(logger, text)

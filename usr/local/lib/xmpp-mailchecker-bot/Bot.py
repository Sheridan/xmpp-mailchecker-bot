#!/usr/bin/env python2
# -*- coding: utf8 -*-

import sys, string, xmpp, time, signal
from threading import Thread, Lock

class CCommandExecuter:

    def __init__(self, bot, storage, i18, mailcheckers, config):
	self.i18 = i18
	self.config = config
	self.storage = storage
	self.mailcheckers = mailcheckers
	self.bot = bot
	
    ########################### executors ###############################
    def addRecord(self, jid, mailbox, server, login, password):
	self.storage.storeRecord(jid, mailbox, server, login, password)
	self.mailcheckers.add(jid, mailbox)
	return self.i18['user_messages']['record_stored']%(mailbox, server, self.listRecords(jid, False))
	
    def editRecord(self, jid, mailbox, server, login, password):
	self.storage.editRecord(jid, mailbox, server, login, password)
	return self.i18['user_messages']['record_changed']%(mailbox, server, self.listRecords(jid, False))
	
    def removeRecord(self, jid, mailbox):
	self.storage.removeRecord(jid, mailbox)
	return self.i18['user_messages']['record_removed']%(mailbox, server, self.listRecords(jid, False))
    
    def resetRecord(self, jid, mailbox):
	self.storage.resetMessageHashes(jid, mailbox)
	return self.i18['user_messages']['record_cashe_reseted']%jid
	
    def resetRecords(self, jid):
	message = ''
	for record in self.storage.getRecords(jid):
	    message += '%s\n'%self.resetRecord(jid, mailbox)
	return message
	
    def checkRecords(self, jid):
	self.mailcheckers.checkNow(jid)
	return self.i18['user_messages']['record_check_started']%jid

    def listRecords(self, jid, unsequre):
        result=''
	for record in self.storage.getRecords(jid):
	    result += '%s %s'%(record['postbox'],record['server'])
	    if unsequre:
		result += ' %s %s'%(record['login'],record['password'])
	    result += '\n'
	return self.i18['user_messages']['records_list']%result;

    ########################### user handlers ##################################
    def cmd_help(self, user, args):
        msg  = self.i18['help']['header'] + ':\n'
        msg += '%s: %s\n'%(self.i18['help']['add']   , 'add postbox@domain.com server login password')
        msg += '%s: %s\n'%(self.i18['help']['remove'], 'remove postbox@domain.com')
        msg += '%s: %s\n'%(self.i18['help']['edit']  , 'edit postbox@domain.com server login password')
        msg += '%s: %s\n'%(self.i18['help']['list']  , 'list [unsequre]')
        msg += '%s: %s\n'%(self.i18['help']['check'] , 'check')
        msg += '%s: %s\n'%(self.i18['help']['reset'] , 'reset [postbox@domain.com]')
        if user.getStripped() in self.config['manage']['admins']:
	    msg += self.i18['help']['admin_header'] + ':\n'
	    msg += '%s: %s\n'%(self.i18['help']['a_add']   , 'a_add jid@domain.com postbox@domain.com server login password')
	    msg += '%s: %s\n'%(self.i18['help']['a_remove'], 'a_remove jid@domain.com postbox@domain.com')
	    msg += '%s: %s\n'%(self.i18['help']['a_edit']  , 'a_edit jid@domain.com postbox@domain.com server login password')
	    msg += '%s: %s\n'%(self.i18['help']['a_check'] , 'a_cheeck [jid@domain.com]')
	    msg += '%s: %s\n'%(self.i18['help']['a_list']  , 'a_list [jid@domain.com] [unsequre]')
	    msg += '%s: %s\n'%(self.i18['help']['a_reset'] , 'a_reset [jid@domain.com] [postbox@domain.com]')
	    msg += '%s: %s\n'%(self.i18['help']['a_status'], 'a_status')
	    msg += '%s: %s\n'%(self.i18['help']['a_stop']  , 'a_quit')
	return msg

    def cmd_add(self, user, args):
        data = args.split(' ')
        return self.addRecord(user.getStripped(), data[0], data[1], data[2], string.join(data[3:]))

    def cmd_edit(self, user, args):
        data = args.split(' ')
        return self.editRecord(user.getStripped(), data[0], data[1], data[2], string.join(data[3:]))

    def cmd_remove(self, user, args):
        return self.removeRecord(user.getStripped(), args)

    def cmd_list(self, user, args):
        return self.listRecords(user.getStripped(), args == 'unsequre')

    def cmd_reset(self, user, args):
        return self.resetRecord(user.getStripped(), args.strip())

    def cmd_check(self, user, args):
        return self.checkRecords(user.getStripped())

    ####################     admin #################################
    def cmd_a_add(self, user, args):
        if user.getStripped() in self.config['manage']['admins']:
	    data = args.split(' ')
	    return self.addRecord(data[0], data[1], data[2], data[3], string.join(data[4:]))
	else:
	    return self.i18['user_messages']['not_admin']%user.getStripped()

    def cmd_a_edit(self, user, args):
	if user.getStripped() in self.config['manage']['admins']:
	    data = args.split(' ')
	    return self.editRecord(data[0], data[1], data[2], data[3], string.join(data[4:]))
	else:
	    return i18['user_messages']['not_admin']%user.getStripped()

    def cmd_a_remove(self, user, args):
	if user.getStripped() in self.config['manage']['admins']:
	    data = args.split(' ')
	    return self.removeRecord(data[0], data[1])
	else:
	    return self.i18['user_messages']['not_admin']%user.getStripped()

    def cmd_a_list(self, user, args):
	if user.getStripped() in self.config['manage']['admins']:
	    data = args.split(' ')
	    if len(data) > 1:
		return self.listRecords(data[0], data[1] == 'unsequre')
	    else:
		if data[0] != '' and data[0].find('@'):
		    return self.listRecords(data[0], False)
		else:
		    message = ''
		    for jid in self.storage.getJids():
			message += "%s:%s\n"%(jid, self.listRecords(jid, data[0] == 'unsequre'))
		    return message
	else:
	    return self.i18['user_messages']['not_admin']%user.getStripped()

    def cmd_a_reset(self, user, args):
	if user.getStripped() in self.config['manage']['admins']:
	    data = args.split(' ')
	    if len(data) > 1:
	        return self.resetRecord(data[0], data[1])
	    else:
	        if len(data) > 0:
		    return self.resetRecords(data[0])
		else:
		    message = ''
		    for jid in self.storage.getJids():
			message += self.resetRecords(jid)
		    return message
	else:
	    return self.i18['user_messages']['not_admin']%user.getStripped()
    
    def cmd_a_check(self, user, args):
	if user.getStripped() in self.config['manage']['admins']:
	    if args != '' and args.find('@'):
		return self.checkRecords(args)
	    else:
		message = ''
		for jid in self.storage.getJids():
		    message += '%s\n'%self.checkRecords(jid)
		return message
	else:
	    return self.i18['user_messages']['not_admin']%user.getStripped()
    
    def cmd_a_status(self, user, args):
	if user.getStripped() in self.config['manage']['admins']:
	    return self.mailcheckers.statuses()
	else:
	    return self.i18['user_messages']['not_admin']%user.getStripped()

    def cmd_a_quit(self, user, args):
	if user.getStripped() in self.config['manage']['admins']:
	    self.bot.quit(self.i18['log']['bot_command_stopping']%(self.bot.jid.getStripped(), user.getStripped()))
	else:
	    return self.i18['user_messages']['not_admin']%user.getStripped()
	########################### admin handlers ###################################

    def execCommand(self, user, command, args):
	cmd = 'cmd_' + command
	if cmd in self.__class__.__dict__:
	    return getattr(self, cmd)(user, args)
	else:
	    return self.i18['user_messages']['unknown_command']%command

################################################  bot ####################################################################
class CBot:
    def __init__(self, i18, config, storage, mailcheckers, logger, jid, password, resource):
	self.terminate = False
	self.i18 = i18
	self.config = config
	self.logger = logger
	self.storage = storage
	self.mailcheckers = mailcheckers
	self.jid = xmpp.JID(jid)
	self.password = password
	self.resource = resource
	self.mutex = Lock()
	self.online_users = {}
	self.cexecuter = CCommandExecuter(self, self.storage, self.i18, self.mailcheckers, self.config)

    def presenceCB(self, client_connection, msg):
	prs_type = msg.getType()
	who = msg.getFrom()
	jid_stripped = who.getStripped()
	if jid_stripped not in self.online_users:
	    self.online_users[jid_stripped] = set()
	if prs_type == "unavailable":
	    del self.online_users[jid_stripped]
	if prs_type == "subscribe":
	    self.sendPresence(who, 'subscribed')
	    self.sendPresence(who, 'subscribe')

    def messageCB(self, client_connection, mess):
	if mess.getType() != 'chat': return
	text=mess.getBody()
	user=mess.getFrom()
	if text.find(' ')+1: 
	    command,args=text.split(' ',1)
	else: 
	    command,args=text,''
	self.sendMessage(mess.getFrom().getStripped(), self.cexecuter.execCommand(user, command.lower(), args))

    def sendMessage(self, jid_to, text):
	self.mutex.acquire()
	if jid_to in self.online_users                and self.config['manage']['send_to_offline_user']   == 'true' or \
	   jid_to in self.config['manage']['admins']  and self.config['manage']['send_to_offline_admin']  == 'true' or \
	   jid_to in self.config['manage']['loggers'] and self.config['manage']['send_to_offline_logger'] == 'true':
	    self.xmpp_connection.send(xmpp.Message(jid_to, text, 'chat'))
	self.mutex.release()
	
    def sendPresence(self, jid_to, p_type):
	self.mutex.acquire()
	self.xmpp_connection.send(xmpp.Presence(to=jid_to, typ=p_type))
	self.mutex.release()

    def GoOn(self):
        while not self.terminate: 
    	    self.xmpp_connection.Process(1)

    def stop(self):
	self.terminate = True
    
    def quit(self, why):
	self.logger.logToAdmins(why)
	self.mailcheckers.stop()
	self.logger.logToAdmins(self.i18['log']['bot_stopping']%self.jid.getStripped())
	self.stop()
	sys.exit(0)
    
    def run(self):
	self.xmpp_connection=xmpp.Client(self.jid.getDomain(),debug=[])
	conres=self.xmpp_connection.connect()
	if not conres:
	    print "Unable to connect to server %s!"%self.jid.getDomain()
	    sys.exit(1)
	if conres<>'tls':
	    print "Warning: unable to estabilish secure connection - TLS failed!"
	authres=self.xmpp_connection.auth(self.jid.getNode(), self.password, self.resource)
	if not authres:
	    print "Unable to authorize on %s - check login/password."%self.jid.getDomain()
	    sys.exit(1)
	if authres<>'sasl':
	    print "Warning: unable to perform SASL auth os %s. Old authentication method used!"%self.jid.getDomain()
	self.xmpp_connection.RegisterHandler('message' , self.messageCB )
	self.xmpp_connection.RegisterHandler('presence', self.presenceCB)
	self.xmpp_connection.sendInitPresence()
	self.logger.logToAdmins(self.i18['log']['bot_starting']%self.jid.getStripped())
	#self.runMailCheckers()
	self.logger.logToAdmins(self.i18['log']['bot_started']%self.jid.getStripped())
	self.GoOn();

    def runMailCheckers(self):
	for jid in self.storage.getJids():
	    for record in self.storage.getRecords(jid):
		self.mailcheckers.add(jid, record['postbox'])
		time.sleep(int(self.config['mailchecker_threads_start_interval']))
	pass
################################################  bot ####################################################################



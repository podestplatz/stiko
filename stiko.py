#!/usr/bin/python3

import time
import requests
import sys
import os
import argparse
from gi.repository import Gtk, GObject, GdkPixbuf
import threading


class STDetective(threading.Thread):
    def __init__(self, icon,iconDir,servers):
        super(STDetective, self).__init__()
        self.icon = icon
        self.isOver = False #flag for terminating when icon terminated

        self.server_names = servers
        self.server_ids =[]

        self.isDownloading = False
        self.isUploading = False
        self.isSTAvailable = False
        self.Busy = False   #for controllling animation only
        try:
            self.px_good = GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-ok.png'))
            self.px_noST = GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-notok.png'))
            self.px_noServer = GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-inactive.png'))
            self.px_sync = [GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-sync0.png')), 
                        GdkPixbuf.Pixbuf.new_from_file(os.path.join(iconDir,'stiko-sync1.png'))]
        except:
            #~ raise
            print("I coudn't open icon files.")
            sys.exit()            

        self.animation_counter = 1
        while True:
            try:
                c = requests.get('http://localhost:8384/rest/system/config')
                self.devices = c.json()["devices"]
                a,b,c,d= self.request_local_completion()
                self.isSTAvailable = True
                break
            except:
                #~ raise
                self.isSTAvailable = False
                GObject.idle_add(self.update_icon)
                time.sleep(3)
        self.id_dict = {}
        for a in self.devices:
            self.id_dict[a["deviceID"]] =  a['name']

        if any([not (a in self.id_dict.values()) for a in self.server_names]):
            print("Some provided server names are wrong.")
            sys.exit()
        if any([not (a in id_dict.keys()) for a in self.server_ids]):
            print("Some provided server ids are wrong.")
            sys.exit()

        if not self.server_names and not self.server_ids: 
            self.server_ids = self.id_dict.keys()
        else:  
            self.server_ids = [a for a in self.id_dict.keys() if (self.id_dict[a] in self.server_names or a in self.server_ids)]

        self.server_completion = {}

        try:
            c = requests.get('http://localhost:8384/rest/system/connections')
            self.connected_ids = list(c.json()["connections"].keys())
            self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]

            for s in self.connected_server_ids: self.server_completion[s] =  self.request_remote_completion(s)
            if self.connected_server_ids: self.isSTAvailable = True
        except:
            #~ raise
            self.isSTAvailable = False

        GObject.idle_add(self.update_icon)

        if not a is  b or not c is  d: self.isDownloading = True
        if all((not p == 100) for p in self.server_completion.values()): self.isUploading = True
        GObject.idle_add(self.update_icon)


    def update_icon(self):
        #~ print("update icon")
        self.icon.set_tooltip_text(str([len(self.connected_server_ids),self.isSTAvailable,self.isUploading, self.isDownloading])+'\nyep')
        if not self.isSTAvailable: 
            self.icon.set_tooltip_text("No contact with syncthing")
            icon.set_from_pixbuf(self.px_noST)
            self.Busy=False
            return False
        if not self.connected_server_ids:
            self.icon.set_tooltip_text("No servers")
            icon.set_from_pixbuf(self.px_noServer)
            self.Busy=False
            return False
        if self.isDownloading or self.isUploading:
            self.icon.set_tooltip_text(str(len(self.connected_server_ids))+" Server(s)"+
                "\nDownloading..." if self.isDownloading else ''+
                "\nUploading..." if self.isUploading else '')
            icon.set_from_pixbuf(self.px_sync[0])
            self.animation_counter = 1
            if not self.Busy: GObject.timeout_add(800, self.update_icon_animate)
            self.Busy=True
        else:
            self.icon.set_tooltip_text(str(len(self.connected_server_ids))+" Server(s)"+ "\nUp to Date")            
            icon.set_from_pixbuf(self.px_good)
            self.Busy=False
        return False
    
    def  update_icon_animate(self):
        #~ print("update icon animate")
        if (t.isDownloading or t.isUploading) and t.isSTAvailable and t.connected_server_ids:
            icon.set_from_pixbuf(self.px_sync[self.animation_counter])
            self.animation_counter = (self.animation_counter + 1) % 2
            return True
        else: 
            self.animation_counter = 1
            return False
        

    def request_local_completion(self):
        c = requests.get('http://localhost:8384/rest/db/status?folder=default')
        return c.json()["inSyncFiles"], c.json()["globalFiles"],  c.json()["inSyncBytes"], c.json()["globalBytes"]

    def request_remote_completion(self,devid):
        c = requests.get('http://localhost:8384/rest/db/completion?device='+devid+'&folder=default')
        return c.json()["completion"]   


    def run(self):
        next_event=1
        while not self.isOver:
            try:
                c = requests.get('http://localhost:8384/rest/system/connections')
                self.connected_ids = list(c.json()["connections"].keys())
                self.connected_server_ids = [s for s in self.server_ids if s in self.connected_ids]

                c = requests.get('http://localhost:8384/rest/events?since='+str(next_event))
                events = c.json()
                self.isSTAvailable = True
            except:
                #~ raise
                self.isSTAvailable = False
                GObject.idle_add(self.update_icon)
                time.sleep(3)
                continue
            for v in events:
                #~ print(v["type"])
                if v["type"] == "LocalIndexUpdated": 
                    self.isUploading = True

                elif v["type"] == "RemoteIndexUpdated": 
                    self.isDownloading = True
                elif str(v["type"]) == "FolderSummary": 
                    w = v["data"]["summary"]
                    a,b,c,d = w["inSyncFiles"], w["globalFiles"],  w["inSyncBytes"], w["globalBytes"]
                    if not a == b or not c == d: isDownloading = True
                    else: 
                        self.isDownloading = False
                GObject.idle_add(self.update_icon)

                if v["type"] == "FolderCompletion":
                    if v["data"]["device"] in self.connected_server_ids: 
                        self.server_completion[v["data"]["device"]] = v["data"]["completion"]
                    if all((not p == 100) for p in self.server_completion.values()): self.isUploading = True
                    else: self.isUploading = False
                GObject.idle_add(self.update_icon)

            next_event = events[len(events)-1]["id"]


def on_left_click(event, icon):
    icon.set_visible(False)
    Gtk.main_quit()


parser = argparse.ArgumentParser(description = 'This is stiko, an icon for syncthing.',epilog='', usage='stiko.py [options]')
parser.add_argument('--servers', nargs = '+', default ='',help = 'List of names of devices treated as servers, space separated. If empty then all connected devices will be treated as servers.',metavar='')
parser.add_argument('--icons',  default ='',help = 'Path to the directory with icons. If empty then use this script\'s directory ('+os.path.dirname(os.path.abspath(__file__))+')', action="store", metavar='')
args = parser.parse_args(sys.argv[1:])
iconDir = os.path.dirname(__file__) if not args.icons else args.icons[0]

GObject.threads_init()

icon = Gtk.StatusIcon()
t = STDetective(icon,iconDir, args.servers)

icon.set_from_pixbuf(t.px_noServer)
icon.connect('activate', on_left_click,icon)
icon.set_has_tooltip(True)

t.start()

Gtk.main()
t.isOver = True

#~ issues (why would it be better if syncthing did it): 
#~ -this depends on seeing all "LocalIndexUdated". 
#~ -at the beginning we might miss something
#~ -if webapp is part of st, why icon can't be - the same problems need to be solved.
#~ -if st config changed ping time then this might not work

#~ would be good if there was event "starting updating remote index", so that reactions are quicker?

#~ -would be nice to have st feature to allow stopping upload to servers if at least one server has it. Or simply a rule as to whom to speak (like: if platon is present don't talk to archimedes)

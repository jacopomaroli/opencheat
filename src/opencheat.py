import sys
import os
from os import listdir
from os.path import isfile, join
import pathlib
import json
import ctypes
from mem_edit import Process
from datetime import datetime
import threading
import wx
from pubsub import pub
import time
import logging

SHOULD_TERMINATE = False

curpath = os.path.dirname(os.path.abspath(__file__))
logging.getLogger("mem_edit").setLevel(logging.WARNING)
freeze_list = []
cheat_data = []
threads = []

str_ctype_map = {
    "binary":ctypes.c_bool,
    "byte": ctypes.c_byte,
    "float": ctypes.c_float,
    "double": ctypes.c_double
}

def ctype_type_from_string(size_str):
    return str_ctype_map[size_str]

class GameRecord(object):
    def __init__(self, name, cheats_count, enabled):
        self.name = name
        self.cheats_count = cheats_count
        self.enabled = enabled

class GamesPanel(wx.Panel):    
    def __init__(self, parent):
        global cheat_data
        super().__init__(parent)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.row_obj_dict = {}

        self.list_ctrl = wx.ListCtrl(
            self, size=(-1, 100), 
            style=wx.LC_REPORT | wx.BORDER_SUNKEN
        )
        self.list_ctrl.InsertColumn(0, 'Name', width=140)
        self.list_ctrl.InsertColumn(1, 'Cheats Count', width=140)
        self.list_ctrl.InsertColumn(2, 'Enabled', width=140)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_game_selected)
        main_sizer.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, 5)

        enable_button = wx.Button(self, label='Enable')
        enable_button.Bind(wx.EVT_BUTTON, self.on_enable_game)
        main_sizer.Add(enable_button, 0, wx.ALL | wx.CENTER, 5)

        self.SetSizer(main_sizer)

        self.cheat_files = load_cheat_list()
        index = 0
        for cheat_file in self.cheat_files:
            cheat_definition = load_cheat_definition(cheat_file)
            for cheat in cheat_definition["cheats"]:
                cheat["address"] = int(cheat["address"], 16)
            cheat_data.append(cheat_definition)
            index = self.list_ctrl.InsertItem(index, cheat_definition["name"])
            self.list_ctrl.SetItem(index, 1, str(len(cheat_definition["cheats"])))
            self.list_ctrl.SetItem(index, 2, "no")
            self.list_ctrl.SetItemData(index, index)

    def on_enable_game(self, event):
        print('in on_enable_game')

    def on_game_selected(self, event):
        game = cheat_data[event.Data]
        pub.sendMessage('on_game_selected', game=game)

class CheatsPanel(wx.Panel):    
    def __init__(self, parent):
        super().__init__(parent)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.game = {}
        self.name_to_idx = {}
        self.row_obj_dict = {}
        self.cheat_idx = -1

        self.list_ctrl = wx.ListCtrl(
            self, size=(-1, 100), 
            style=wx.LC_REPORT | wx.BORDER_SUNKEN
        )
        self.list_ctrl.InsertColumn(0, 'Name', width=100)
        self.list_ctrl.InsertColumn(1, 'Size', width=100)
        self.list_ctrl.InsertColumn(2, 'Address', width=100)
        self.list_ctrl.InsertColumn(3, 'Value', width=100)
        self.list_ctrl.InsertColumn(4, 'Enabled', width=100)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_cheat_selected)
        main_sizer.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, 5)

        enable_button = wx.Button(self, label='Enable')
        enable_button.Bind(wx.EVT_BUTTON, self.on_enable_cheat)
        main_sizer.Add(enable_button, 0, wx.ALL | wx.CENTER, 5)
        self.SetSizer(main_sizer)

        pub.subscribe(self.on_game_selected, 'on_game_selected')
        pub.subscribe(self.on_var_update, 'on_var_update')

    def on_enable_cheat(self, event):
        if self.cheat_idx == -1:
            return
        global freeze_list
        cheat = self.game["cheats"][self.cheat_idx]

        freeze_var = ProcVar()
        freeze_var.processName = self.game["processName"]
        freeze_var.address = cheat["address"]
        freeze_var.value = cheat["highRange"]
        freeze_var.size = cheat["size"]
        freeze_var.freeze_freq_ms = 100
        freeze_list.append(freeze_var)
    
    def on_var_update(self, event):
        index = self.name_to_idx.get(event["name"])
        if index is not None:
            self.list_ctrl.SetItem(index, 3, str(event["value"]))

    def on_game_selected(self, game):
        self.list_ctrl.DeleteAllItems()
        self.game = game
        self.name_to_idx = {}
        index = 0
        for cheat in self.game["cheats"]:
            index = self.list_ctrl.InsertItem(index, cheat["name"])
            self.name_to_idx[cheat["name"]] = index
            self.list_ctrl.SetItem(index, 1, cheat["size"])
            self.list_ctrl.SetItem(index, 2, '0x{:08x}'.format(cheat["address"]).upper())
            self.list_ctrl.SetItem(index, 3, "???")
            self.list_ctrl.SetItem(index, 4, "no")
            self.list_ctrl.SetItemData(index, index)

    def on_cheat_selected(self, event):
        self.cheat_idx = event.Data

class MainFrame(wx.Frame):    
    def __init__(self):
        super().__init__(parent=None, title='opencheat')
        self.SetSize(wx.DefaultCoord, wx.DefaultCoord, 640, 480, wx.SIZE_AUTO)
        panel = wx.Panel(self)

        games_panel = GamesPanel(panel)
        cheats_panel = CheatsPanel(panel)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(games_panel,0,wx.EXPAND|wx.ALL,border=10)
        sizer.Add(cheats_panel,0,wx.EXPAND|wx.ALL,border=10)
        panel.SetSizer(sizer)
        self.Show()

        pub.subscribe(self.on_game_selected, 'on_game_selected')
        self.Bind(wx.EVT_CLOSE,self.OnClose)

    def on_game_selected(self, game):
        print(game)
   
    def OnClose(self,evt):
        global threads
        global SHOULD_TERMINATE
        SHOULD_TERMINATE = True
        for thread in threads:
            thread.join()
        self.Destroy()

class ProcVar:
    def __init__(self):
        self.processName = ""
        self.process = None
        self.address = 0
        self.value = 0
        self.freeze_freq = 0

def write_memory(process, address, value, size):
    if process.process_handle == None:
        return
    ctype_type = ctype_type_from_string(size)
    process.write_memory(address, ctype_type(value))

def read_memory(process, address, size):
    if process.process_handle == None:
        return
    ctype_type = ctype_type_from_string(size)
    return process.read_memory(address, ctype_type())

def load_cheat_definition(file):
    file_path = os.path.join(curpath, "cheats", file)
    with open(file_path) as json_file:
        data = json.load(json_file)
        return data

def load_cheat_list():
    global curpath
    cheats_folder = os.path.join(curpath, "cheats")
    cheat_files = [f for f in listdir(cheats_folder) if isfile(join(cheats_folder, f)) and pathlib.Path(join(cheats_folder, f)).suffix == ".json" ]
    return cheat_files

def read_thread():
    while(True):
        if SHOULD_TERMINATE:
            return

        for cheat in cheat_data:
            if("process" not in cheat or cheat["process"] is None or cheat["process"].process_handle is None):
                continue
            for var in cheat["cheats"]:
                payload = {}
                payload["name"] = var["name"]

                value = read_memory(cheat["process"], var["address"], var["size"])
                payload["value"] = "???" if value is None else value.value
                pub.sendMessage('on_var_update', event=payload)
                
        time.sleep(0.5)

def freeze_thread():
    while(True):
        if SHOULD_TERMINATE:
            return

        for freeze_var in freeze_list:
            if freeze_var.process != None:
                write_memory(freeze_var.process, freeze_var.address, freeze_var.value, freeze_var.size)

        time.sleep(0.05)

def scan_processes_thread():
    global freeze_list
    global cheat_data
    while(True):
        if SHOULD_TERMINATE:
            return
        
        for cheat in cheat_data:
            if("process" not in cheat or cheat["process"] is None or cheat["process"].process_handle is None):
                pid = Process.get_pid_by_name(cheat["processName"])
                if pid is not None:
                    cheat["process"] = Process(pid)
        
            for freeze_var in freeze_list:
                if freeze_var.processName == cheat["processName"]:
                    freeze_var.process = cheat["process"]
            
        time.sleep(5)

def main():
    global threads

    t1 = threading.Thread(target=scan_processes_thread, args=())
    threads.append(t1)
    t1.start()

    t2 = threading.Thread(target=freeze_thread, args=())
    threads.append(t2)
    t2.start()

    t3 = threading.Thread(target=read_thread, args=())
    threads.append(t3)
    t3.start()

    app = wx.App()
    frame = MainFrame()
    app.MainLoop()

main()
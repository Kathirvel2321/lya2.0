"""Windows client for a linked LYA conversation. Only the device credential is durable."""
import http.client
import json
import os
from pathlib import Path
from queue import Empty, Queue
import re
import secrets
import socket
import threading
import time
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlsplit

import qrcode
import win32crypt

ROOT = Path(__file__).resolve().parents[1]
ENTROPY = b'LYA linked desktop credential v1'


def check_origin(origin):
    if not re.fullmatch(r'https://[a-z0-9-]{1,63}\.[a-z0-9-]{1,63}\.ts\.net', origin):
        raise ValueError('Use the private HTTPS address from LYA on your phone.')
    return origin


def request(origin, path, data, credential=None):
    host = urlsplit(check_origin(origin)).hostname
    https = http.client.HTTPSConnection(host, timeout=40)
    headers = {'Origin':origin, 'Content-Type':'application/json'}
    if credential is not None:
        headers['Authorization'] = 'Bearer '+credential
    try:
        https.request('POST', '/device/'+path, json.dumps(data), headers)
        with https.getresponse() as response:
            if response.status == 403:
                raise PermissionError('This device is waiting for approval or is unlinked.')
            if response.status != 200:
                raise ValueError('LYA could not complete the request. Refresh before resending.')
            raw = response.read(100001)
            if len(raw) > 100000:
                raise ValueError('Response too large.')
        return json.loads(raw)
    finally:
        https.close()


class CredentialFile:
    def __init__(self, checkout):
        self.folder = checkout / '.lya-linked'
        self.path = self.folder / 'device.dpapi'

    def check(self):
        if self.folder.resolve() != self.folder or self.path.is_symlink():
            raise PermissionError('The LYA device credential must stay in this checkout.')

    def read(self):
        self.check()
        try:
            with self.path.open('rb') as file:
                protected = file.read(4097)
        except FileNotFoundError:
            return None
        if len(protected) > 4096:
            raise ValueError('Invalid device credential.')
        _, raw = win32crypt.CryptUnprotectData(protected, ENTROPY, None, None, 1)
        data = json.loads(raw)
        if set(data) != {'origin','credential'} or not re.fullmatch(r'[A-Za-z0-9_-]{43}', data['credential']):
            raise ValueError('Invalid device credential.')
        check_origin(data['origin'])
        return data

    def save(self, origin, credential):
        self.check()
        self.folder.mkdir(exist_ok=True)
        raw = json.dumps(dict(origin=check_origin(origin),credential=credential)).encode()
        protected = win32crypt.CryptProtectData(raw, 'LYA linked device', ENTROPY, None, None, 1)
        temporary = self.folder / (secrets.token_hex(12)+'.tmp')
        try:
            with temporary.open('xb') as file:
                file.write(protected)
            os.rename(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


class LinkedWindow:
    def __init__(self, root):
        self.root, self.inbox = root, Queue()
        self.saved = CredentialFile(ROOT)
        self.link_deadline = 0
        self.busy = False
        self.device = None
        root.title('LYA')
        root.geometry('560x640')
        self.frame = ttk.Frame(root,padding=20)
        self.frame.pack(fill='both',expand=True)
        self.status = ttk.Label(self.frame,wraplength=470)
        self.status.pack(fill='x',pady=(0,10))
        self.body = ttk.Frame(self.frame)
        self.body.pack(fill='both',expand=True)
        self.root.after(100,self.receive)
        try:
            self.device = self.saved.read()
        except Exception:
            self.status.config(text='This Windows account cannot open the saved LYA link.')
            ttk.Button(self.body,text='Clear saved link',command=self.clear_link).pack()
            return
        if self.device:
            self.chat_screen()
        else:
            self.link_screen()

    def reset_body(self):
        for widget in self.body.winfo_children():
            widget.destroy()

    def run(self, operation, callback):
        if self.busy:
            return
        self.busy = True
        def work():
            try:
                self.inbox.put((callback, operation(), None))
            except Exception as exc:
                self.inbox.put((callback, None, exc))
        threading.Thread(target=work,daemon=True).start()

    def receive(self):
        try:
            callback, result, error = self.inbox.get_nowait()
        except Empty:
            pass
        else:
            self.busy=False
            callback(result,error)
        self.root.after(100,self.receive)

    def link_screen(self):
        self.reset_body()
        self.status.config(text='Connect to your existing LYA with one phone approval.')
        ttk.Label(self.body,text='Private LYA address').pack(anchor='w')
        origin=ttk.Entry(self.body)
        origin.pack(fill='x',pady=(4,12))
        ttk.Label(self.body,text='Name for this laptop').pack(anchor='w')
        name=ttk.Entry(self.body)
        name.insert(0,socket.gethostname()[:60] or 'Windows laptop')
        name.pack(fill='x',pady=(4,12))
        def start():
            selected=origin.get().strip()
            label=name.get().strip()
            self.run(lambda:request(selected,'start',{'name':label}),
                     lambda data,error:self.show_link(selected,data,error))
        ttk.Button(self.body,text='Connect to my LYA',command=start).pack(anchor='w')
        origin.focus_set()

    def show_link(self, origin, data, error):
        if error:
            self.status.config(text='Could not start a link. Check the private address and service setup.')
            return
        self.reset_body()
        qr=qrcode.QRCode()
        qr.add_data(origin+'/#link='+data['link'])
        matrix=qr.get_matrix()
        picture=tk.PhotoImage(width=len(matrix),height=len(matrix))
        for row, modules in enumerate(matrix):
            picture.put('{'+' '.join('black' if cell else 'white' for cell in modules)+'}',to=(0,row))
        self.qr=picture.zoom(4,4)
        ttk.Label(self.body,image=self.qr).pack(pady=12)
        self.status.config(text='Scan the QR with your phone and confirm code '+data['code']+'.')
        self.link_deadline=time.monotonic()+180
        candidate=dict(origin=origin,credential=data['credential'])
        def poll():
            if time.monotonic() >= self.link_deadline:
                self.link_screen()
                self.status.config(text='The link expired. Start again.')
                return
            self.run(lambda:request(origin,'history',{},candidate['credential']),done)
        def done(history, error):
            if error:
                self.root.after(2500,poll)
                return
            try:
                self.saved.save(**candidate)
            except Exception:
                self.link_screen()
                self.status.config(text='The phone approved this laptop, but LYA could not save its credential.')
                return
            self.device=candidate
            self.chat_screen(history['history'])
        poll()

    def chat_screen(self, history=None):
        self.reset_body()
        self.transcript=tk.Text(self.body,wrap='word',state='disabled',exportselection=False)
        self.transcript.pack(fill='both',expand=True)
        self.message=ttk.Entry(self.body,exportselection=False)
        self.message.pack(fill='x',pady=8)
        self.message.bind('<Return>',lambda _:self.send())
        actions=ttk.Frame(self.body)
        actions.pack(fill='x')
        ttk.Button(actions,text='Send',command=self.send).pack(side='left')
        ttk.Button(actions,text='Refresh',command=self.refresh).pack(side='left')
        ttk.Button(actions,text='Clear saved link',command=self.clear_link).pack(side='right')
        self.message.focus_set()
        if history is None:self.refresh()
        else:self.show_history({'history':history},None)

    def call(self, path, data, callback):
        device=self.device
        self.run(lambda:request(device['origin'],path,data,device['credential']),callback)

    def refresh(self):
        self.call('history',{},self.show_history)

    def show_history(self, result, error):
        if error:
            message=('This laptop is unlinked. Clear the saved link to connect again.'
                     if isinstance(error,PermissionError) else 'LYA could not complete the request. Refresh before resending.')
            self.status.config(text=message)
            return
        self.transcript.config(state='normal')
        self.transcript.delete('1.0','end')
        for message in result['history']:
            name='You' if message['role']=='user' else 'LYA'
            self.transcript.insert('end',name+'\n'+message['content']+'\n\n')
        self.transcript.config(state='disabled')
        self.transcript.see('end')
        self.status.config(text='Connected to your LYA.')

    def send(self):
        text=self.message.get().strip()
        if self.busy or not 1<=len(text)<=4000:
            return
        self.status.config(text='Waiting for LYA…')
        self.message.config(state='disabled')
        def done(_, error):
            self.message.config(state='normal')
            if error:
                self.show_history(None,error)
                return
            self.message.delete(0,'end')
            self.refresh()
        self.call('chat',{'id':secrets.token_hex(16),'text':text},done)

    def clear_link(self):
        if self.busy:
            return
        try:
            self.saved.check()
            self.saved.path.unlink(missing_ok=True)
        except OSError:
            self.status.config(text='Could not clear this laptop’s saved link.')
            return
        self.device=None
        self.link_screen()


if __name__=='__main__':
    root=tk.Tk()
    LinkedWindow(root)
    root.mainloop()

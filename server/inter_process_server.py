from multiprocessing.managers import SyncManager
from multiprocessing import shared_memory, Lock
import numpy as np
import sys
from time import sleep


class InterProcessInterface:
    def __init__(self):
        self.data = {'time': 0, 'value': None}

    def update_data(self, new_time, new_value):
        self.data['time'] = new_time
        self.data['value'] = new_value

    def get_data(self):
        return self.data


class EventManager(SyncManager): pass
lock = Lock()
data_share_api = InterProcessInterface()
EventManager.register('get_lock', callable=lambda: lock)
EventManager.register("get_api", callable=lambda: data_share_api)


class InterProcessServer:
    def __init__(self, ipc_address, shared_mem_name, shared_mem_template=None):
        # initiate connections and shared memory blocks
        self.manager = EventManager(address=ipc_address, authkey=b'secret password')

    def start(self):
        self.manager.start()
        self._lock = self.manager.get_lock()
        self._lock.acquire()
        self._api = self.manager.get_api()

    def test_data_alone(self):
        print(self._api.get_data())
        self._api.update_data(1, 1)
        first_msg = self._api.get_data()
        print(first_msg)
        return first_msg

    def test_data_with_node(self):
        return self._api.get_data()

    def test_lock(self):
        print('lock created')
        released = self._lock.acquire(block=False)
        print(f'lock {released=}')
        while not released:
            released = self._lock.acquire(block=False)
        print('client connected to lock')


address = ('localhost', 6000)
SHM_NAME = "NUMPY_SHMEM"
server = InterProcessServer(ipc_address=address, shared_mem_name=SHM_NAME)
server.start()
first_msg = server.test_data_alone()

while True:
    new_msg = server.test_data_with_node()
    if new_msg['time'] <= first_msg['time']:
        sleep(1)
        continue
    else:
        print(new_msg)
        break

server.test_lock()

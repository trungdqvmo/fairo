# deprecated

import sqlite3
import time
from .core import BaseHandler, not_implemented

import droidlet.lowlevel.rotation as rotation
from droidlet.memory.robot.loco_memory import LocoAgentMemory, DetectedObjectNode
from droidlet.memory.save_and_fetch_commands import *

def MemorizationHandler(BaseHandler):
    # TODO: this module should be handled in other function
    coordinate_transforms = rotation
    def __init__(self, db_file=":memory:", *args, **kwargs):
        self.dashboard_chat = None # using RAM for dashboard chatting
        self.memory = LocoAgentMemory(
            db_file=db_file,
            db_log_path=None,
            coordinate_transforms=self.coordinate_transforms,
        )
        self.dashboard_memory_dump_time = time.time()
        self.dashboard_memory = {
            "db": {},
            "objects": [],
            "humans": [],
            "chatResponse": {},
            "chats": [
                {"msg": "", "failed": False},
                {"msg": "", "failed": False},
                {"msg": "", "failed": False},
                {"msg": "", "failed": False},
                {"msg": "", "failed": False},
            ],
        }

    def add_chat(self, chat: str):
        self.logger.info("Sending chat: {}".format(chat))
        self.memory.add_chat(self.memory.self_memid, chat)

    def get_player_struct_by_name(self, speaker_name):
        p = self.memory.get_player_by_name(speaker_name)
        if p:
            return p.get_struct()
        else:
            return None

    def get_incoming_chats(self):
        all_chats = []
        speaker_name = "dashboard"
        if self.dashboard_chat is not None:
            # for now, only dashboard can speak
            # if not self.memory.get_player_by_name(speaker_name):
            #     PlayerNode.create(
            #         self.memory,
            #         to_player_struct((None, None, None), None, None, None, speaker_name),
            #     )
            all_chats.append(self.dashboard_chat)
            self.dashboard_chat = None
        return all_chats

    def objects_in_memory(self):
        objects = DetectedObjectNode.get_all(self.memory)
        for o in objects:
            del o["feature_repr"]  # pickling optimization
        self.dashboard_memory["objects"] = objects
        return self.dashboard_memory

    def get_previous_objects(self):
        return DetectedObjectNode.get_all(self.memory)

    def update_perception(self, perception_output):
        self.memory.update(perception_output)

    # TODO: this function should be called in other thread
    def maybe_dump_memory_to_dashboard(self):
        self.dashboard_memory_dump_time = time.time()
        memories_main = self.memory._db_read("SELECT * FROM Memories")
        triples = self.memory._db_read("SELECT * FROM Triples")
        reference_objects = self.memory._db_read("SELECT * FROM ReferenceObjects")
        named_abstractions = self.memory._db_read("SELECT * FROM NamedAbstractions")
        self.dashboard_memory["db"] = {
            "memories": memories_main,
            "triples": triples,
            "reference_objects": reference_objects,
            "named_abstractions": named_abstractions,
        }
        return self.dashboard_memory["db"]

    def save_and_fetch_commands(self, post_data):
        out = saveAndFetchCommands(self.conn, postData)
        if out == "DUPLICATE":
            self.logger.warning("Duplicate command not saved.")
        else:
            self.logger.info("Saved successfully")
        return out


    #def onlyFetchCommands(self, )


import gzip
import logging
import numpy as np
import os
import pickle
import sqlite3
import uuid
import datetime
from itertools import zip_longest
from typing import cast, Optional, List, Tuple, Sequence, Union
from droidlet.base_util import XYZ
from droidlet.shared_data_structs import Time
from droidlet.memory.memory_filters import MemorySearcher
from droidlet.event import dispatch
from droidlet.memory.memory_util import parse_sql, format_query

logger = logging.getLogger('memorydb')

class AgentSession(object):
    def __init__(self, db_file=":memory:"):
        self.db_file = db_file
        self._connector = sqlite3.connect(db_file, check_same_thread=False)
        self.on_delete_callback = on_delete_callback

    @property
    def connector

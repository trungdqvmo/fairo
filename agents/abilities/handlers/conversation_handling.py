"""
Copyright (c) Facebook, Inc. and its affiliates.
"""
# define a conversation skill:
# 1. can listen to chat or any command coming from client
# 2. can understand chat/command to certain level
# 3. can reply to client about any event
import logging
import random
import time
import numpy as np
import datetime
import os

from .core import BaseHandler
from agents.scheduler import EmptyScheduler
from droidlet.shared_data_structs import ErrorWithResponse
from droidlet.interpreter import InterpreterBase
from droidlet.event import sio, dispatch
# TODO: wrap all memory handling into module
from droidlet.memory.save_and_fetch_commands import *
# TODO: dashboard memory will be wrapped into ram_memory module

DATABASE_FILE_FOR_DASHBOARD = "dashboard_data.db"
DEFAULT_BEHAVIOUR_TIMEOUT = 20
MEMORY_DUMP_KEYFRAME_TIME = 0.5
# a BaseAgent with:
# 1: a controller that is (mostly) a scripted interpreter + neural semantic parser.
# 2: has a turnable head, can point, and has basic locomotion
# 3: can send and receive chats


class ConversationHandler(BaseHandler):
    def __init__(self, opts, name=None):
        logging.info("Initialize conversation skill")
        self.language_understanding = None # Not implemented
        self.conversation_memory = None
        self._logger = logging.getLogger("conversation_log")
        self.conn = create_connection(DATABASE_FILE_FOR_DASHBOARD)

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
        # Add optional hooks for timeline
        if opts.enable_timeline:
            dispatch.connect(self.log_to_dashboard, "perceive")
            dispatch.connect(self.log_to_dashboard, "memory")
            dispatch.connect(self.log_to_dashboard, "interpreter")
            dispatch.connect(self.log_to_dashboard, "dialogue")

    @sio.on("saveCommand")
    def save_command_to_db(sid, postData):
        self.logger.debug("in save_command_to_db, got postData: %r" % (postData))
        # save the command and fetch all
        out = saveAndFetchCommands(self.conn, postData)
        if out == "DUPLICATE":
            self.logger.warning("Duplicate command not saved.")
        else:
            self.logger.debug("Saved successfully")
        payload = {"commandList": out}
        sio.emit("updateSearchList", payload)

    @sio.on("fetchCommand")
    def get_cmds_from_db(sid, postData):
        self.logger.debug("in get_cmds_from_db, got postData: %r" % (postData))
        out = onlyFetchCommands(self.conn, postData["query"])
        payload = {"commandList": out}
        sio.emit("updateSearchList", payload)

    @sio.on("get_agent_type")
    def report_agent_type(sid):
        sio.emit("updateAgentType", {"agent_type": self.agent_type})

    @sio.on("saveErrorDetailsToDb")
    def save_error_details_to_db(sid, postData):
        self.logger.debug("in save_error_details_to_db, got PostData: %r" % (postData))
        # save the details to table
        saveAnnotatedErrorToDb(self.conn, postData)

    @sio.on("saveSurveyInfo")
    def save_survey_info_to_db(sid, postData):
        self.logger.debug("in save_survey_info_to_db, got PostData: %r" % (postData))
        # save details to survey table
        saveSurveyResultsToDb(self.conn, postData)

    @sio.on("saveObjectAnnotation")
    def save_object_annotation_to_db(sid, postData):
        self.logger.debug("in save_object_annotation_to_db, got postData: %r" % (postData))
        saveObjectAnnotationsToDb(self.conn, postData)

    @sio.on("sendCommandToAgent")
    def send_text_command_to_agent(sid, command):
        """Add the command to agent's incoming chats list and
        send back the parse.
        Args:
            command: The input text command from dashboard player
        Returns:
            return back a socket emit with parse of command and success status
        """
        self.logger.debug("in send_text_command_to_agent, got the command: %r" % (command))

        agent_chat = (
            "<dashboard> " + command
        )  # the chat is coming from a player called "dashboard"
        self.dashboard_chat = agent_chat
        logical_form = {}
        status = ""
        try:
            chat_parse = self.perception_modules["language_understanding"].get_logical_form(
                chat=command,
                parsing_model=self.perception_modules["language_understanding"].parsing_model,
            )
            logical_form = self.dialogue_manager.dialogue_object_mapper.postprocess_logical_form(
                speaker="dashboard", chat=command, logical_form=chat_parse
            )
            self.logger.debug("logical form is : %r" % (logical_form))
            status = "Sent successfully"
        except Exception as e:
            self.logger.error("error in sending chat", e)
            status = "Error in sending chat"
        # update server memory
        self.dashboard_memory["chatResponse"][command] = logical_form
        self.dashboard_memory["chats"].pop(0)
        self.dashboard_memory["chats"].append({"msg": command, "failed": False})
        payload = {
            "status": status,
            "chat": command,
            "chatResponse": self.dashboard_memory["chatResponse"][command],
            "allChats": self.dashboard_memory["chats"],
        }
        sio.emit("setChatResponse", payload)

    @sio.on("terminateAgent")
    def terminate_agent(sid, msg):
        self.logger.info("Terminating agent")
        turk_experiment_id = msg.get("turk_experiment_id", "null")
        mephisto_agent_id = msg.get("mephisto_agent_id", "null")
        turk_worker_id = msg.get("turk_worker_id", "null")
        if turk_experiment_id != "null":
            self.logger.info("turk worker ID: {}".format(turk_worker_id))
            self.logger.info("mephisto agent ID: {}".format(mephisto_agent_id))
            with open("turk_experiment_id.txt", "w+") as f:
                f.write(turk_experiment_id)
            # Write metadata associated with crowdsourced run such as the experiment ID
            # and worker identification
            job_metadata = {
                "turk_experiment_id": turk_experiment_id,
                "mephisto_agent_id": mephisto_agent_id,
                "turk_worker_id": turk_worker_id,
            }
            with open("job_metadata.json", "w+") as f:
                json.dump(job_metadata, f)
        os._exit(0)

    def handle_exception(self, e):
        if isinstance(e, ErrorWithResponse):
            self.send_chat("Oops! Ran into an exception.\n'{}''".format(e.chat))
            self.memory.task_stack_clear()
            self.dialogue_manager.dialogue_stack.clear()
            self.uncaught_error_count += 1
            if self.uncaught_error_count >= 100:
                raise e
        else:
            # if it's not a whitelisted exception, immediatelly raise upwards,
            # unless you are in some kind of a debug mode
            if self.opts.agent_debug_mode:
                return
            else:
                raise e

    def log_to_dashboard(self, **kwargs):
        """Emits the event to the dashboard and/or logs it in a file"""
        if self.opts.enable_timeline:
            result = kwargs["data"]
            # a sample filter for logging data from perceive and dialogue
            allowed = ["perceive", "dialogue", "interpreter"]
            if result["name"] in allowed:
                # JSONify the data, then send it to the dashboard and/or log it
                result = json.dumps(result, default=str)
                self.agent_emit(result)
                if self.opts.log_timeline:
                    self.timeline_log_file.flush()
                    print(result, file=self.timeline_log_file)

    def agent_emit(self, result):
        sio.emit("newTimelineEvent", result)

    def __del__(self):
        """Close the timeline log file"""
        if getattr(self, "timeline_log_file", None):
            self.timeline_log_file.close()


def default_agent_name():
    """Use a unique name based on timestamp"""
    return "bot.{}".format(str(time.time())[3:13])

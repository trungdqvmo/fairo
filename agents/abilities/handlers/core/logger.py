# basic logging for any ability of agent
# maybe add %(threadName)s for handle multi thread
import pytz
import datetime
import logging
import pathlib
from logging.handlers import TimedRotatingFileHandler

class Formatter(logging.Formatter):
    TIMEZONE_NAME = 'Asia/Ho_Chi_Minh'
    """override logging.Formatter to use an aware datetime object"""
    def converter(self, timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        tzinfo = pytz.timezone(Formatter.TIMEZONE_NAME)
        return tzinfo.localize(dt)

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec='milliseconds')
            except TypeError:
                s = dt.isoformat()
        return s

def create_ability_logger(logger_name, path, capables, logger_level=logging.DEBUG):
    logger = logging.getLogger(logger_name)
    handler = TimedRotatingFileHandler(path,
                                       when='midnight',
                                       backupCount=1)
    handler.suffix = "%Y-%m-%d"
    formatter = Formatter(u'%(asctime)s\t%(name)s%(levelname)s\t%(pathname)s\t%(module)s%(module)s:%(lineno)d\t%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info(f"Load an handler {logger_name} with capable in handle {capables}")
    logger.setLevel(logger_level)
    return logger

if __name__ == "__main__":
    # log all timezone to tmp.log file as sample log
    create_timed_rotating_log("sample","logs/tmp.log")
    for timezone_name in pytz.all_timezones:
        logger.info(pytz.timezone(timezone_name))

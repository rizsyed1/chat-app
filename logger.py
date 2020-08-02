import datetime
import logging
import os
import time


class Logger(object):
    def __init__(self, file, log_directory='Logs'):
        self.stream_handler = None
        self.file_handler = None
        self.log_directory = log_directory
        self.file = file
        self.logging_logger = logging.getLogger(__name__)
        self.logger = logging.getLogger(self.file)

    def create_new_file(self):
        """Creates a new log file from the current date time stamp and places it inside log directory"""
        current_date_time = datetime.datetime.now().strftime("%I:%M%p on %d-%B-%Y")
        file_name = fr'{self.file} {current_date_time}.log'
        file_path = os.path.join('Logs', file_name)

        """if logs directory does not exist make new directory"""
        if not os.path.isdir(self.log_directory):
            self.logging_logger.info('detected no log directory')
            os.mkdir(self.log_directory)
            file = open(file_path, 'w+')
            file.close()

        """create new log file if it does exist"""
        if not os.path.exists(file_path):
            self.logging_logger.info('created new log file')
            file = open(file_path, 'w+')
            file.close()

        """remove any files that are older than 30 days"""
        now = time.time()
        for log in os.listdir(self.log_directory):
            log = os.path.join(self.log_directory, log)
            if os.stat(log).st_mtime < now - 30 * 86400:
                self.logging_logger.info(f'Deleted log {log} because it is more than 30 days old')
                os.remove(log)

        return file_path

    def initialise_logging(self):
        self.logger.setLevel(logging.DEBUG)

        self.file_handler = logging.FileHandler(self.create_new_file())
        self.file_handler.setLevel(logging.DEBUG)
        self.stream_handler = logging.StreamHandler()
        self.stream_handler.setLevel(logging.INFO)

        self.stream_handler.setFormatter(logging.Formatter('| {levelname:<5} | {module}: {message}', style='{'))
        self.file_handler.setFormatter(logging.Formatter(
            '{asctime} | {levelname:<5} | {module:20}: {funcName:30}: {message}', style='{'
        ))

        self.logger.addHandler(self.stream_handler)
        self.logger.addHandler(self.file_handler)

    def toggle_stream_debug(self):
        logger = logging.getLogger(self.file)

        if self.stream_handler.level == logging.INFO:
            self.stream_handler.setLevel(logging.DEBUG)

            console_formatter = logging.Formatter(
                '| {levelname:<5} | {module:20}: {funcName:30}: {message}', style='{'
            )

            self.stream_handler.setFormatter(console_formatter)

            self.logging_logger.info('stream logger set to DEBUG')

        elif self.stream_handler.level == logging.DEBUG:
            self.stream_handler.setLevel(logging.INFO)

            console_formatter = logging.Formatter(
                '| {levelname} | {module}: {message}', style='{'
            )

            self.stream_handler.setFormatter(console_formatter)

            self.logging_logger.info('stream logger set to INFO')
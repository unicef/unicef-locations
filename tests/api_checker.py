import datetime

from drf_api_checker.recorder import Recorder
from rest_framework.response import Response


class LastModifiedRecorder(Recorder):

    def assert_modified(self, response: Response, stored: Response, path: str):
        value = response['modified']
        assert datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')

    def assert_created(self, response: Response, stored: Response, path: str):
        value = response['created']
        assert datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')

from unittest import TestCase
from unittest.mock import Mock, patch

from lighthouse.lighthouse import RESTAPITarget, RESTAction


class LighthouseTest(TestCase):
    @patch("readerwriterlock.rwlock.RWLockRead.gen_rlock")
    def test_rest_api_target(self, mock_gen_rlock):
        t = RESTAPITarget("test_target")
        t.get_data()

        t.rw_lock.gen_rlock.assert_called_once()


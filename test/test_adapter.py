from unittest import TestCase
from unittest.mock import Mock
from binascii import unhexlify

from lighthouse.adapter import Adapter, Source, Target


class AdapterTest(TestCase):

    @staticmethod
    def test_adapter_update():
        """
        Create and adapter with mock source and target, check that call to update functions properly
        """
        source = Mock(spec=Source)
        target = Mock(spec=Target)
        msg = {"test_keu": "test_value"}
        source.get_message.return_value = msg
        adapter = Adapter(name="test_adapter", source=source, target=target)
        adapter.update()

        adapter.source.get_message.assert_called_once()
        adapter.target.feed.assert_called_with(msg)

    @staticmethod
    def test_adapter_update_msg_none():
        """
        Create and adapter with mock source and target, check that call to update functions properly
        """
        source = Mock(spec=Source)
        target = Mock(spec=Target)

        source.get_message.return_value = None
        adapter = Adapter(name="test_adapter", source=source, target=target)
        adapter.update()

        adapter.source.get_message.assert_called_once()
        # feed shouldn't be called when None is obtained from source
        adapter.target.feed.assert_not_called()

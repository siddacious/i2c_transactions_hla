from register_decoder import RegisterDecoder
from collections import namedtuple

MockTrans = namedtuple("MockTrans", "register_address data write")

def test_testing_tests():
    decoder = RegisterDecoder()
    transaction = MockTrans(0x22, [0x60], True)
    trans_string = decoder.decode_transaction(transaction)
    assert trans_string == 'Reg: INTERFACE FORMAT, Data:0x60'

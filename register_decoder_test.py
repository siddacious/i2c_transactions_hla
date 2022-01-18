from register_decoder import RegisterDecoder
from collections import namedtuple

MockTrans = namedtuple("MockTrans", "register_address data write")



# Current register: {
# 'address': 29, 
# 'name': 'CLOCK RATIO NI MSB', 
# 'last_read_value': None, 
# 'reset_string': 0, 
# 'raw_string': '—\tNI[14:8]\t'}
# EXPANDED:
# ['', 'NI[14:8]']


def test_testing_tests():
    decoder = RegisterDecoder()
    transaction = MockTrans(0x1D, [0x60], True)
    trans_string = decoder.decode_transaction(transaction)
    assert trans_string == 'Reg: INTERFACE FORMAT, Data:0x60'

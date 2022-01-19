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
    assert trans_string == 'WRITE|   Clock Ratio Ni Msb  --  NI: 48, '

def test_cv():
    # not so obviously, the CV filling should be an additional _potential_ source for info, not mando

    # given a register thing with a cv, it should be used
    # given a byte of data
    # given a previous value for that data

    # when
    decoder = RegisterDecoder()
#!/usr/bin/env bash
clear
# self._map = {0: {}, 1: {}, 2: {}, 3: {}, -1:
# {
#     127:{
#         'name': 'REG_BANK_SEL',
#         'address': 127, 
#         0: '',
#         1: '', 
#         2: '',
#         3: '', 
#         4: 'USER_BANK[1:0]', 
#         5: 'USER_BANK[1:0]', 
#         6: '', 
#         7: '', 
#         'last_read_value': None}}}
python register_decoder/decoder.py test.csv maps/bank0.csv maps/bank1.csv maps/bank2.csv maps/bank3.csv


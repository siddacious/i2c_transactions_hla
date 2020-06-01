# The MIT License (MIT)
#
# Copyright (c) 2020 Bryan Siepert
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""

This module decodes register read/write statements into state changes using a map of the register structures, bitfields, and bitfield controlled vocabularies (CVs)/enums

"""
import sys

# import _bleio

# from .services import Service
# from .advertising import Advertisement

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/siddacious/i2c_transactions_hla.git"

# class RegisterDecoder:
#     """
#     Represents a connection to a peer BLE device.
#     It acts as a map from a `Service` type to a `Service` instance for the connection.

#     :param bleio_connection _bleio.Connection: the native `_bleio.Connection` object to wrap

#     """

#     def __init__(self, bleio_connection):
#         self._bleio_connection = bleio_connection
#         # _bleio.Service objects representing services found during discovery.
#         self._discovered_bleio_services = {}
#         # Service objects that wrap remote services.
#         self._constructed_services = {}

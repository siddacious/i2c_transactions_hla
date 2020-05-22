# I2C Address Regs

A simple HLA for Saleae Logic 2.0 that packages raw I2C analyzer frames into read/write transactions between a master and a slave that uses address-based registers

## Status

**Only tested with repeated starts**

The code that packages the I2C frames into transactions is currently tangled with register name mapping code. I'm hoping to extract into a higher-level HLA if possible, bbut for now my plans are:

* Test support for arbitrary register maps
* Add higher-level register mapper with support for bitwise operation tracking

Possible additions:
* Write to file
* User provided format strings?

## Attribution
Derived from the [Example Gyroscope HLA](https://github.com/saleae/logic2-extensions/tree/master/hla_gyroscope) by [Ryan Huffman](https://github.com/huffman)

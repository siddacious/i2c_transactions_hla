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

## Usage/Docs
Basic installation instructions from the code this was ripped off from:

https://github.com/saleae/logic2-extensions/tree/master/hla_gyroscope#try-it-for-yourself

I'll update this section later as I polish things up

Here's Saleae's docs on how High Level Analyzers can be written:

https://github.com/saleae/logic2-extensions#high-level-protocol-analyzers
## Attribution
Derived from the [Example Gyroscope HLA](https://github.com/saleae/logic2-extensions/tree/master/hla_gyroscope) by [Ryan Huffman](https://github.com/huffman)

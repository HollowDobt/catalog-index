"""
# src/infrastructure/io

Input and output devices, which allow receiving and
sending through the server and direct input and output from the terminal

输入输出器, 允许通过服务端接收发送和终端直接输入输出的方式
"""


from base_io_stream import IOInStream, IOOutStream, IOStream


__all__ = ["IOInStream", "IOOutStream", "IOStream"]
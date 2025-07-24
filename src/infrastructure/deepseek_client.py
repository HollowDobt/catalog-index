"""
-------------------------------------
src/infrastructure/deepseek_client.py
-------------------------------------

Simple encapsulation of requests to deepseek servers, implemented as DeepSeekClient class

Each time the DeepSeekClient class is instantiated, it will first send a request to the determined server address using the corresponding API to test whether it works properly. If the test fails, the error type is returned and output to the log

Encapsulates some common functions of the OpenAI library to facilitate calls and modularization of other parts
"""

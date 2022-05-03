"""
Retrieval for v1_dynamicParsingRules
"""
import sys
import json
sys.dont_write_bytecode = 1
def get_and_format_output(self):
    """
    wrapper for HTTP get for: /v1/dynamicParsingRules
    """
    urlpath="/v1/dynamicParsingRules"
    body = self.get(urlpath).text
    results = json.loads(body)
    return results
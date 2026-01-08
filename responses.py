import random
import re
from languages import text_all

quotes = text_all("quotes")

def get_response(message):
    p_message = message.lower()

    if p_message == 'roll':
        return str(random.randint(1, 6))
    
    # elif re.search(r'\test\b', p_message) or re.search(r'\test\b', p_message):
        # return "test"
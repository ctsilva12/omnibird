import random
import math
from languages import text

def generate_arithmetic_problem():
    operators = ['+', '-', 'x', '/', "factorial", "sqrt"]
    operator = random.choice(operators)
    question = None
    answer = None

    if operator == '+':
        num1 = random.randint(1, 100)
        num2 = random.randint(1, 100)
        question = f"{text("math", "what_is")} {num1}{operator}{num2}?"
        answer = num1 + num2

    elif operator == '-':
        num1 = random.randint(1, 100)
        num2 = random.randint(1, 100)
        question = f"{text("math", "what_is")} {num1}{operator}{num2}?"
        answer = num1 - num2

    elif operator == 'x':
        num1 = random.randint(1, 12)
        num2 = random.randint(1, 10)
        question = f"{text("math", "what_is")} {num1}{operator}{num2}?"
        answer = num1 * num2

    elif operator == '/':
        divisor = random.randint(2, 10)
        dividend = random.randint(1, 10) * divisor
        question = f"{text("math", "what_is")} {dividend}{operator}{divisor}?"
        answer = dividend // divisor

    elif operator == 'factorial':
        num = random.randint(2, 6)
        question = f"{text("math", "what_is")} {num}!?"
        answer = math.factorial(num)

    elif operator == "sqrt":
        answer = random.randint(1, 20)
        question = f"{text("math", "what_is")} {text("the")} {text("math", "square_root")} {text("of")} {answer**2}?"

    return question, answer

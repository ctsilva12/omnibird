import random
import math
from languages import l

def generate_arithmetic_problem():
    operators = ['+', '-', 'x', '/', "factorial", "sqrt", "log"]
    operator = random.choice(operators)
    question = None
    answer = None

    if operator == '+':
        num1 = random.randint(1, 100)
        num2 = random.randint(1, 100)
        question = f"{l.text("math", "what_is")} {num1}{operator}{num2}?"
        answer = num1 + num2

    elif operator == '-':
        num1 = random.randint(1, 100)
        num2 = random.randint(1, 100)
        question = f"{l.text("math", "what_is")} {num1}{operator}{num2}?"
        answer = num1 - num2

    elif operator == 'x':
        num1 = random.randint(1, 12)
        num2 = random.randint(1, 10)
        question = f"{l.text("math", "what_is")} {num1}{operator}{num2}?"
        answer = num1 * num2

    elif operator == '/':
        divisor = random.randint(2, 10)
        dividend = random.randint(1, 10) * divisor
        question = f"{l.text("math", "what_is")} {dividend}{operator}{divisor}?"
        answer = dividend // divisor

    elif operator == 'factorial':
        num = random.randint(2, 6)
        question = f"{l.text("math", "what_is")} {num}!?"
        answer = math.factorial(num)

    elif operator == "sqrt":
        answer = random.randint(1, 20)
        question = f"{l.text("math", "what_is")} {l.text("the")} {l.text("math", "square_root")} {l.text("of")} {answer**2}?"

    elif operator == "log":
        bases : list[float] = [2, 3, 5, 10, math.e]
        base = random.choice(bases)
        if base == 2: exponent = random.randint(-3, 12)
        else: exponent = random.randint(-1, 4)
        if math.isclose(base, math.e): operator = "ln"
        else: operator = f"log{base}"
        question = f"{l.text("math", "what_is")} {operator}({round(base**exponent, 4)})?"
        answer = exponent


    return question, answer

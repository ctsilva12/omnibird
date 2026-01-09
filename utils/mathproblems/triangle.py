from typing import Union
import random
from languages import l

def generate_triangle_problem():
    timeout = 40
    PYTHAGOREAN_TRIPLES : list[list[Union[int, str]]] = [
        [3, 4, 5],
        [5, 12, 13],
        [8, 15, 17]
    ]
    multiply_by = [1, 1, 1, 1, 2, 3, 4, 5]
    multiply = random.choice(multiply_by)
    preprocessed_triple = random.choice(PYTHAGOREAN_TRIPLES)
    pythagorean_triple = [num * multiply for num in preprocessed_triple]
    index = random.randrange(len(pythagorean_triple))
    answer = pythagorean_triple[index];
    pythagorean_triple[index] = "x";
    if random.choice([True, False]):
        adjacent, opposite = pythagorean_triple[0], pythagorean_triple[1]
    else: adjacent, opposite = pythagorean_triple[1], pythagorean_triple[0]
    question = f"{l.text("math", "pyth", "question")}\n{l.text("math", "pyth", "adjacent")}: {adjacent}\n{l.text("math", "pyth", "opposite")}: {opposite}\n{l.text("math", "pyth", "hypotenuse")}: {pythagorean_triple[2]}"
    tip = l.text("math", "pyth", "tip", preprocessed_triple=preprocessed_triple, multiply=multiply)

    return question, answer, tip, timeout;
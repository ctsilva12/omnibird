import random
from .arithmetic import generate_arithmetic_problem
from .geometry import generate_geometry_problem
from .triangle import generate_triangle_problem
from .trigonometry import generate_trigonometry_problem

def generate_problem():
    problem_type = random.randint(1, 4)
    timeout = 20
    tip = None
    if problem_type == 1:
        question, answer = generate_arithmetic_problem()
    elif problem_type == 2:
        question, answer, timeout = generate_geometry_problem()
    elif problem_type == 3:
        question, answer, tip, timeout = generate_triangle_problem()
    else: 
        question, answer = generate_trigonometry_problem()

    return question, answer, tip, timeout

import math
import random
from languages import l
circle =  """
    elif shape == 'circle':
        timeout = 30
        radius = random.randint(1, 10)
        question = f"What is the {operation} of a circle with radius {radius}?"
        if (operation == 'area'): answer = math.pi * (radius ** 2)
        elif (operation == 'perimeter'): answer = 2 * math.pi * radius
    """

def generate_geometry_problem():
    timeout = 20
    shapes = ['square', 'rectangle', 'triangle', 'pentagon', 'trapezoid']
    operations = ['perimeter', 'area']
    shape = random.choice(shapes)
    operation = random.choice(operations)
    question = None
    answer = 0

    if shape == 'square':
        side = random.randint(1, 20)
        question = l.text("math", "square_question", operation=l.text("math", operation), side=side)
        if (operation == 'area'): answer = side ** 2
        elif (operation == 'perimeter'): answer = side * 4

    elif shape == 'rectangle':
        length = random.randint(1, 12)
        width = random.randint(1, 12)
        question = l.text("math", "rectangle_question", operation=l.text("math", operation), length=length, width=width)
        if (operation == 'area'): answer = length * width
        elif (operation == 'perimeter'): answer = (length*2) + (width*2)
   
    elif shape == 'triangle':
        base = random.randint(1, 20)
        height = random.randint(1, 20)
        question = l.text("math", "triangle_question", base=base, height=height)
        answer = 0.5 * base * height
    
    elif shape == 'pentagon':
        length = random.randint(1, 100)
        question = l.text("math", "pentagon_question", length=length)
        answer = length*5

    elif shape == 'trapezoid':
        timeout = 30
        base = random.randint(1, 10)
        base2 = random.randint(1, 10)
        height = random.randint(1, 20)
        question = l.text("math", "trapezoid_question", base=base, base2=base2, height=height)
        answer = ((base+base2)/2)*height

    return question, round(answer, 2), timeout
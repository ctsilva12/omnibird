import math
import random
from fractions import Fraction
from languages import l

def display_in_radians(degrees: float, max_denominator: int = 24) -> str:
    degrees = round(degrees)
    frac = Fraction(degrees, 180).limit_denominator(max_denominator)
    n, d = frac.numerator, frac.denominator

    if n == 0:
        return "0"

    sign = "-" if n < 0 else ""
    n = abs(n)
    if d == 1:
        if n == 1:
            return f"{sign}π"
        else: return f"{sign}{n}π"

    return f"{sign}{n if n != 1 else ""}π/{d}"

def sign(x, tol=1e-12) -> str:
    if math.isnan(x):
        return l.text("undefined")
    if x > tol:
        return "+"
    elif x < -tol: return "-"
    else: return "0"

def tan_sign(angle_deg: float) -> str:
    a = round(angle_deg) % 360

    if a == 0:
        return "0"
    if a % 180 == 90:
        return l.text("undefined")
    
    if a % 180 == 0:
        return "0"

    if 0 < a < 90 or 180 < a < 270:
        return "+"
    else:
        return "-"

def generate_trigonometry_problem():
    ANGLES_TO_CHOOSE = [0, 30, 45, 60, 90]
    QUADRANTS = [0, 90, 180, 270, 360]
    OPERATIONS = ["sin", "cos", "tan"]
    display = ""
    answer = ""
    
    quadrant = random.choice(QUADRANTS)
    operation = random.choice(OPERATIONS)
    angle = random.choice(ANGLES_TO_CHOOSE) + quadrant
    radians = bool(random.randint(0, 1))
    if operation == "tan":
        answer = tan_sign(angle) if angle % 180 != 90 else l.text("undefined")
    elif operation == "cos":
        answer = sign(math.cos(math.radians(angle)))
    elif operation == "sin":
        answer = sign(math.sin(math.radians(angle)))
    print(f"Angle: {angle}º, Answer: {answer}")

    display = display_in_radians(angle) if radians else f"{angle}º"
    question = f"{l.text("math", "what_is")} {l.text("the")} {l.text("math", "sign_of")} {operation}({display})? (+, -, 0 or {l.text("undefined")})"
    return question, answer
    
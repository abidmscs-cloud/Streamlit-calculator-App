"""
Streamlit Calculator (safe expression evaluator)

Features:
- Safe evaluation of arithmetic and common math functions using AST (no eval()).
- On-screen keypad + text input.
- Calculation history stored in st.session_state.
- Error handling with friendly messages.
- Supports: + - * / % // **, parentheses, unary +/-, and math functions:
  sin, cos, tan, asin, acos, atan, sqrt, log, log10, exp, pow, abs, floor, ceil, factorial, radians, degrees
- Constants: pi, e

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

import ast
import math
import operator as op
import streamlit as st

# ---------- SAFE EVALUATOR ----------
# Allowed binary operators mapping
_allowed_binops = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

# Allowed unary operators mapping
_allowed_unaryops = {
    ast.UAdd: lambda x: x,
    ast.USub: lambda x: -x,
}

# Allowed math functions mapping (whitelist)
_math_funcs = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "log": math.log,       # natural log; log(x, base) allowed via two args
    "log10": math.log10,
    "exp": math.exp,
    "pow": math.pow,
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    "radians": math.radians,
    "degrees": math.degrees,
}

# Allowed constants
_constants = {
    "pi": math.pi,
    "e": math.e,
}

class EvalError(Exception):
    pass

def _eval_node(node):
    """Recursively evaluate an AST node in a safe manner."""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    # Numbers (int, float)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        else:
            raise EvalError("Only numeric constants are allowed.")

    # Python 3.7 and older used Num; some AST versions may present nums differently
    if isinstance(node, ast.Num):
        return node.n

    # Binary operations: + - * / ** // %
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op_type = type(node.op)
        if op_type in _allowed_binops:
            func = _allowed_binops[op_type]
            try:
                return func(left, right)
            except Exception as e:
                raise EvalError(f"Error in operation: {e}")
        else:
            raise EvalError(f"Operator {op_type} not supported.")

    # Unary ops: +, -
    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        op_type = type(node.op)
        if op_type in _allowed_unaryops:
            return _allowed_unaryops[op_type](operand)
        else:
            raise EvalError(f"Unary operator {op_type} not supported.")

    # Function calls from whitelist: sin(x), log(x, base)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in _math_funcs:
                func = _math_funcs[func_name]
                args = [_eval_node(arg) for arg in node.args]
                try:
                    return func(*args)
                except TypeError as e:
                    raise EvalError(f"Bad arguments for {func_name}: {e}")
                except Exception as e:
                    raise EvalError(f"Error calling {func_name}: {e}")
            else:
                raise EvalError(f"Function '{func_name}' is not allowed.")
        else:
            raise EvalError("Only direct function names are allowed.")

    # Names (variables/constants)
    if isinstance(node, ast.Name):
        if node.id in _constants:
            return _constants[node.id]
        else:
            raise EvalError(f"Unknown identifier: {node.id}")

    # Parentheses are handled by the structure of AST (no explicit node)
    raise EvalError(f"Unsupported expression: {ast.dump(node)}")

def safe_eval(expr: str):
    """Safely evaluate a math expression using AST parsing."""
    try:
        parsed = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise EvalError(f"Syntax error: {e}")

    # Walk AST to ensure there are no disallowed nodes quickly
    for node in ast.walk(parsed):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Lambda, ast.Global, ast.Nonlocal, ast.ClassDef, ast.FunctionDef)):
            raise EvalError("Disallowed Python construct in expression.")
    return _eval_node(parsed)

# ---------- STREAMLIT UI ----------
st.set_page_config(page_title="Calculator (Streamlit)", layout="centered")

st.title("🧮 Streamlit Calculator — Safe & Simple")
st.markdown(
    """
Enter a numeric expression (examples):
- `2 + 3*4`
- `sqrt(16) + sin(pi/6)`
- `log(100, 10)`  (log with base)
- `factorial(5)`
Constants available: `pi`, `e`
"""
)

# Initialize history in session_state
if "history" not in st.session_state:
    st.session_state.history = []

# Input area
col1, col2 = st.columns([3, 1])
with col1:
    expr = st.text_input("Expression", value="", placeholder="e.g. 2+2 or sqrt(2)*pi")
with col2:
    if st.button("Calculate"):
        # will be handled below after validation
        pass

# On-screen keypad (small)
st.markdown("**Keypad**")
kp_cols = st.columns(4)
buttons = [
    ("7", kp_cols[0]), ("8", kp_cols[1]), ("9", kp_cols[2]), ("/", kp_cols[3]),
    ("4", kp_cols[0]), ("5", kp_cols[1]), ("6", kp_cols[2]), ("*", kp_cols[3]),
    ("1", kp_cols[0]), ("2", kp_cols[1]), ("3", kp_cols[2]), ("-", kp_cols[3]),
    ("0", kp_cols[0]), (".", kp_cols[1]), ("(", kp_cols[2]), (")", kp_cols[3]),
]
# Display buttons and allow appending to expression
for label, column in buttons:
    if column.button(label):
        # append to expression (update via session_state hack)
        # Use a key in session_state to remember unsaved expr between reruns
        if "expr_buffer" not in st.session_state:
            st.session_state.expr_buffer = expr
        st.session_state.expr_buffer = (st.session_state.get("expr_buffer", "") or "") + label
        # Rerun: set expr local var to buffer so user sees it
        expr = st.session_state.expr_buffer

# Scientific function buttons
func_cols = st.columns(4)
func_buttons = ["sin(", "cos(", "tan(", "sqrt("]
for label, col in zip(func_buttons, func_cols):
    if col.button(label):
        if "expr_buffer" not in st.session_state:
            st.session_state.expr_buffer = expr
        st.session_state.expr_buffer = (st.session_state.get("expr_buffer", "") or "") + label
        expr = st.session_state.expr_buffer

# If session buffer exists, show it in the input box by re-rendering
if "expr_buffer" in st.session_state and st.session_state.expr_buffer != expr:
    # Show the buffered expression (streamlit input does not accept dynamic set easily),
    # we reassign expr variable so that next calculation uses it.
    expr = st.session_state.expr_buffer

# Perform calculation if user clicked button or pressed Enter in text_input
# Streamlit can't directly detect Enter reliably, so use a separate button as main trigger
if st.button("Compute"):
    if not expr or expr.strip() == "":
        st.error("Please enter an expression.")
    else:
        try:
            result = safe_eval(expr)
            # Format result (float vs int)
            if isinstance(result, float):
                # show a concise float (avoid long repr)
                result_display = float(f"{result:.12g}")
            else:
                result_display = result
            st.success(f"Result: `{result_display}`")
            # Save to history
            st.session_state.history.insert(0, (expr, result_display))
            # Clear expr buffer (but keep text_input content until user changes)
            st.session_state.expr_buffer = ""
        except EvalError as e:
            st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

# Quick action buttons
clear_col1, clear_col2 = st.columns([1, 3])
with clear_col1:
    if st.button("Clear"):
        st.session_state.expr_buffer = ""
        st.experimental_rerun()

with clear_col2:
    if st.button("Clear History"):
        st.session_state.history = []

# History display
st.markdown("### History")
if st.session_state.history:
    for idx, (expression, res) in enumerate(st.session_state.history[:20], start=1):
        st.write(f"{idx}. `{expression}`  =  **{res}**")
else:
    st.info("No calculations yet. Use the input above and press Compute.")

# Footer: allowed functions and constants
st.markdown("---")
st.markdown("**Allowed functions:** " + ", ".join(sorted(_math_funcs.keys())))
st.markdown("**Constants:** " + ", ".join(sorted(_constants.keys())))
st.caption("This evaluator uses a safe AST-based parser — it does NOT use Python's eval().")

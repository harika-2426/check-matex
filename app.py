from flask import Flask, render_template, request, jsonify, redirect, session
import chess
import database
import random

app = Flask(__name__)
app.secret_key = "super_secret_key"

database.init_db()

board = chess.Board()
mode = "pvp"
level = 1

piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}

# ---------------- AI EVAL ---------------- #

def evaluate(board):
    score = 0
    for piece in board.piece_map().values():
        value = piece_values[piece.piece_type]
        if piece.color == chess.WHITE:
            score += value
        else:
            score -= value
    return score

# ---------------- MINIMAX ---------------- #

def minimax(board, depth, alpha, beta, maximizing):
    if depth == 0 or board.is_game_over():
        return evaluate(board)

    if maximizing:
        max_eval = -9999
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = 9999
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

# ---------------- AI MOVE ---------------- #

def ai_move():
    global level

    moves = list(board.legal_moves)

    if level <= 2:
        return random.choice(moves)

    depth = 2 if level <= 4 else 3 if level <= 6 else 4 if level <= 8 else 5

    best_move = None
    best_value = -9999

    for move in moves:
        board.push(move)
        value = minimax(board, depth - 1, -9999, 9999, False)
        board.pop()

        if value > best_value:
            best_value = value
            best_move = move

    return best_move

# ================= AUTH ================= #

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if database.create_user(username, password):
            return redirect("/login")
        return "User already exists"

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = database.get_user(username, password)

        if user:
            session["user"] = username
            return redirect("/mode")

        return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/mode")
def mode_page():
    if "user" not in session:
        return redirect("/login")
    return render_template("mode.html")

@app.route("/levels")
def levels_page():
    if "user" not in session:
        return redirect("/login")

    unlocked = database.get_level(session["user"]) or 1
    return render_template("levels.html", unlocked=unlocked)

@app.route("/game/<game_mode>/<lvl>")
def game(game_mode, lvl):
    global board, mode, level

    if "user" not in session:
        return redirect("/login")

    board = chess.Board()
    mode = game_mode
    level = int(lvl)

    return render_template("game.html", mode=mode, level=level)

# ================= RESULT PAGE ================= #

@app.route("/result/<res>")
def result(res):
    global mode, level

    if "user" not in session:
        return redirect("/login")

    winner = None
    theme = "default"

    if mode == "pvp":
        if res == "checkmate":
            winner = "White" if board.turn == chess.BLACK else "Black"
            theme = "pvp_win"
        elif res == "draw":
            winner = "Draw"
            theme = "pvp_draw"

    elif mode == "ai":
        if res == "win":
            winner = "Player"
            theme = "ai_win"

            current = database.get_level(session["user"]) or 1
            if level + 1 > current:
                database.unlock_level(session["user"], level + 1)

        elif res == "lose":
            winner = "AI"
            theme = "ai_lose"

        elif res == "draw":
            winner = "Draw"
            theme = "ai_draw"

    return render_template("result.html",
                           result=res,
                           winner=winner,
                           mode=mode,
                           theme=theme)

# ================= GAME RESET ================= #

@app.route("/play_again")
def play_again():
    global board

    board = chess.Board()

    if mode == "ai":
        return redirect(f"/game/ai/{level}")
    return redirect("/game/pvp/1")

# ================= API ================= #

@app.route("/new_game")
def new_game():
    global board
    board = chess.Board()

    return jsonify({
        "fen": board.fen(),
        "timer": 600
    })

@app.route("/legal_moves/<square>")
def legal_moves(square):
    moves = [
        chess.square_name(m.to_square)
        for m in board.legal_moves
        if chess.square_name(m.from_square) == square
    ]

    return jsonify({"moves": moves})

# ================= MOVE ================= #

@app.route("/move", methods=["POST"])
def move():
    global board, mode

    data = request.json
    move_str = data["move"]

    try:
        move = chess.Move.from_uci(move_str)
    except:
        return jsonify({"error": "invalid move format"})

    if move not in board.legal_moves:
        return jsonify({"error": "illegal"})

    board.push(move)

    result = None

    # 🔥 FIXED CHECKMATE LOGIC
    if board.is_checkmate():
        if mode == "ai":
            result = "win" if board.turn == chess.BLACK else "lose"
        else:
            result = "checkmate"

    elif board.is_stalemate() or board.is_insufficient_material():
        result = "draw"

    return jsonify({
        "fen": board.fen(),
        "result": result,
        "check": board.is_check(),
        "check_square": None
    })

# ================= AI MOVE ================= #

@app.route("/ai_move")
def ai_move_route():
    global board

    if not board.is_game_over():
        move = ai_move()
        if move:
            board.push(move)

    result = None

    if board.is_checkmate():
        result = "lose"
    elif board.is_stalemate() or board.is_insufficient_material():
        result = "draw"

    return jsonify({
        "fen": board.fen(),
        "result": result,
        "check": board.is_check(),
        "check_square": None
    })

# ================= RUN ================= #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
from flask import Flask, render_template, request, jsonify, redirect, session
import chess
import database
import random

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------------- INIT DB ---------------- #
database.init_db()

# ---------------- GAME STATE ---------------- #

board = chess.Board()
mode = "pvp"
level = 1

# ---------------- PIECE VALUES ---------------- #

piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}

# ---------------- EVALUATION ---------------- #

def evaluate(board):
    score = 0
    for piece in board.piece_map().values():
        value = piece_values[piece.piece_type]
        score += value if piece.color == chess.WHITE else -value
    return score

# ---------------- MINIMAX ---------------- #

def minimax(board, depth, alpha, beta, maximizing):
    if depth == 0 or board.is_game_over():
        return evaluate(board)

    if maximizing:
        best = -9999
        for move in board.legal_moves:
            board.push(move)
            best = max(best, minimax(board, depth - 1, alpha, beta, False))
            board.pop()
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = 9999
        for move in board.legal_moves:
            board.push(move)
            best = min(best, minimax(board, depth - 1, alpha, beta, True))
            board.pop()
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best

# ---------------- AI MOVE ---------------- #

def ai_best_move():
    global level

    moves = list(board.legal_moves)
    if not moves:
        return None

    if level <= 2:
        return random.choice(moves)

    depth = 2 if level <= 4 else 3 if level <= 6 else 4

    best_move = None
    best_value = -99999

    for move in moves:
        board.push(move)
        value = minimax(board, depth - 1, -99999, 99999, False)
        board.pop()

        if value > best_value:
            best_value = value
            best_move = move

    return best_move

# =================== ROUTES =================== #

@app.route("/")
def home():
    return render_template("home.html")


# ---------------- REGISTER ---------------- #
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if database.create_user(username, password):
            return redirect("/login")
        else:
            return render_template("register.html", error="User already exists")

    return render_template("register.html")


# ---------------- LOGIN ---------------- #
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = database.get_user(username, password)

        if user:
            session["user"] = username
            return redirect("/mode")
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# ---------------- LOGOUT ---------------- #
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


# ---------------- MODE PAGE ---------------- #
@app.route("/mode")
def mode_page():
    if "user" not in session:
        return redirect("/login")

    return render_template("mode.html", user=session["user"])


# ---------------- LEVELS ---------------- #
@app.route("/levels")
def levels():
    if "user" not in session:
        return redirect("/login")

    unlocked = database.get_level(session["user"]) or 1
    return render_template("levels.html", unlocked=unlocked)


# ---------------- GAME ---------------- #
@app.route("/game/<game_mode>/<lvl>")
def game(game_mode, lvl):
    global board, mode, level

    if "user" not in session:
        return redirect("/login")

    board = chess.Board()
    mode = game_mode
    level = int(lvl)

    return render_template("game.html", mode=mode, level=level)


# ---------------- PLAY AGAIN ---------------- #
@app.route("/play_again")
def play_again():
    global board

    board = chess.Board()
    return redirect(f"/game/{mode}/1")


# =================== NEW GAME =================== #

@app.route("/new_game")
def new_game():
    global board
    board = chess.Board()

    return jsonify({
        "fen": board.fen(),
        "timer": 600
    })


# =================== LEGAL MOVES =================== #

@app.route("/legal_moves/<square>")
def legal_moves(square):
    moves = []

    for move in board.legal_moves:
        if chess.square_name(move.from_square) == square:
            moves.append(chess.square_name(move.to_square))

    return jsonify({"moves": moves})


# =================== MOVE PLAYER =================== #

@app.route("/move", methods=["POST"])
def move():
    global board, mode

    if board.is_game_over():
        return jsonify({"error": "game over"})

    data = request.json
    move_str = data.get("move")

    try:
        move = chess.Move.from_uci(move_str)
    except:
        return jsonify({"error": "bad format"})

    if move not in board.legal_moves:
        return jsonify({"error": "illegal move"})

    board.push(move)

    result = None

    if board.is_checkmate():
        result = "win" if mode == "ai" else "checkmate"

    elif board.is_stalemate() or board.is_insufficient_material():
        result = "draw"

    return jsonify({
        "fen": board.fen(),
        "result": result,
        "check": board.is_check()
    })


# =================== AI MOVE =================== #

@app.route("/ai_move")
def ai_move_route():
    global board

    if board.is_game_over():
        return jsonify({
            "fen": board.fen(),
            "result": None,
            "check": board.is_check()
        })

    move = ai_best_move()

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
        "check": board.is_check()
    })


# =================== RUN =================== #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
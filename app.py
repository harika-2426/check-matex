from flask import Flask, render_template, request, jsonify, redirect, session
import chess
import database
import random

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------------- INIT DB ---------------- #
database.init_db()

# ---------------- Game Variables ---------------- #

board = chess.Board()
mode = "pvp"
level = 1

# ---------------- Piece Values ---------------- #

piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}

# ---------------- AI Evaluation ---------------- #

def evaluate(board):
    score = 0
    for piece in board.piece_map().values():
        value = piece_values[piece.piece_type]
        if piece.color == chess.WHITE:
            score += value
        else:
            score -= value
    return score

# ---------------- Minimax ---------------- #

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

# ---------------- AI Move ---------------- #

def ai_move():
    global level
    moves = list(board.legal_moves)

    if level <= 2:
        return random.choice(moves)

    best_move = None
    best_value = -9999

    if level <= 4:
        depth = 2
    elif level <= 6:
        depth = 3
    elif level <= 8:
        depth = 4
    else:
        depth = 5

    for move in moves:
        board.push(move)
        value = minimax(board, depth - 1, -9999, 9999, False)
        board.pop()

        if value > best_value:
            best_value = value
            best_move = move

    return best_move

# =================== PAGES =================== #

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if database.create_user(username, password):
            return redirect("/login")
        else:
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
        else:
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


@app.route("/result/<res>")
def result(res):
    global mode, level

    if "user" not in session:
        return redirect("/login")

    winner = None
    theme = "default"

    # ---------------- PVP ---------------- #
    if mode == "pvp":
        if res == "checkmate":
            winner = "White" if board.turn == chess.BLACK else "Black"
            theme = "pvp_win"
        elif res == "draw":
            winner = "Draw"
            theme = "pvp_draw"

    # ---------------- AI ---------------- #
    if mode == "ai":
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

    return render_template(
        "result.html",
        result=res,
        winner=winner,
        mode=mode,
        theme=theme
    )

# =================== PLAY AGAIN =================== #

@app.route("/play_again")
def play_again():
    global board

    board = chess.Board()

    if mode == "ai":
        return redirect(f"/game/ai/{level}")
    else:
        return redirect("/game/pvp/1")

# =================== GAME API =================== #

@app.route("/new_game")
def new_game():
    global board

    board = chess.Board()

    return jsonify({
        "fen": board.fen(),
        "timer": 600
    })

# ---------------- LEGAL MOVES ---------------- #

@app.route("/legal_moves/<square>")
def legal_moves(square):
    moves = []

    for move in board.legal_moves:
        if chess.square_name(move.from_square) == square:
            moves.append(chess.square_name(move.to_square))

    return jsonify({"moves": moves})

# ---------------- PLAYER MOVE ---------------- #

@app.route("/move", methods=["POST"])
def move():
    global board, mode

    data = request.json
    move_str = data["move"]

    try:
        move = chess.Move.from_uci(move_str)
    except:
        return jsonify({"error": "invalid move format"})

    piece = board.piece_at(move.from_square)

    if not piece:
        return jsonify({"error": "no piece"})

    if piece.piece_type == chess.PAWN:
        to_rank = chess.square_rank(move.to_square)
        if to_rank in [0, 7] and move.promotion is None:
            return jsonify({"error": "promotion required"})

    if move in board.legal_moves:
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

    return jsonify({"error": "illegal"})

# ---------------- AI MOVE ---------------- #

@app.route("/ai_move")
def ai_move_route():
    global board, level

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
        "check": board.is_check()
    })

# =================== RUN =================== #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
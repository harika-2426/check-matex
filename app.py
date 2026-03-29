from flask import Flask, render_template, request, jsonify, redirect, session, url_for
import chess
import database
import random
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

# ---------------- INIT DB ---------------- #
database.init_db()

# ---------------- SESSION BOARD ---------------- #

def get_board():
    if "board_fen" not in session:
        board = chess.Board()
        session["board_fen"] = board.fen()
    return chess.Board(session["board_fen"])


def save_board(board):
    session["board_fen"] = board.fen()


def reset_board():
    board = chess.Board()
    save_board(board)
    return board


# ---------------- AI CONFIG ---------------- #

piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}


def evaluate(board):
    score = 0
    for piece in board.piece_map().values():
        value = piece_values[piece.piece_type]
        score += value if piece.color == chess.WHITE else -value
    return score


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


def ai_best_move(board, level):
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


# ================= ROUTES ================= #

@app.route("/")
def home():
    return render_template("home.html")


# ---------------- AUTH ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if database.create_user(username, password):
            return redirect("/login")
        else:
            return render_template("register.html", error="User exists")

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
            return render_template("login.html", error="Invalid login")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- MODE ---------------- #

@app.route("/mode")
def mode_page():
    if "user" not in session:
        return redirect("/login")

    return render_template("mode.html", user=session["user"])


@app.route("/levels")
def levels():
    if "user" not in session:
        return redirect("/login")

    unlocked = database.get_level(session["user"]) or 1
    return render_template("levels.html", unlocked=unlocked)


# ---------------- GAME ---------------- #

@app.route("/game/<game_mode>/<lvl>")
def game(game_mode, lvl):
    if "user" not in session:
        return redirect("/login")

    reset_board()

    session["mode"] = game_mode
    session["level"] = int(lvl)

    return render_template("game.html", mode=game_mode, level=lvl)


# ---------------- RESET ---------------- #

@app.route("/reset", methods=["POST"])
def reset():
    board = reset_board()
    return jsonify({"fen": board.fen()})


# ---------------- STATE ---------------- #

@app.route("/state")
def state():
    board = get_board()
    return jsonify({
        "fen": board.fen(),
        "game_over": board.is_game_over()
    })


# ---------------- LEGAL MOVES ---------------- #

@app.route("/legal_moves/<square>")
def legal_moves(square):
    board = get_board()
    moves = []

    for move in board.legal_moves:
        if chess.square_name(move.from_square) == square:
            moves.append(chess.square_name(move.to_square))

    return jsonify({"moves": moves})


# ---------------- PLAYER MOVE ---------------- #

@app.route("/move", methods=["POST"])
def move():
    board = get_board()

    if board.is_game_over():
        return jsonify({"status": "error", "message": "game over"})

    data = request.json
    move_str = data.get("move")

    try:
        move = chess.Move.from_uci(move_str)
    except:
        return jsonify({"status": "error", "message": "bad format"})

    if move not in board.legal_moves:
        return jsonify({"status": "error", "message": "illegal move"})

    board.push(move)
    save_board(board)

    return jsonify({
        "status": "success",
        "fen": board.fen(),
        "game_over": board.is_game_over()
    })


# ---------------- AI MOVE ---------------- #

@app.route("/ai-move", methods=["POST"])
def ai_move():
    board = get_board()

    if board.is_game_over():
        return jsonify({"status": "game_over"})

    level = session.get("level", 1)

    move = ai_best_move(board, level)

    if move:
        board.push(move)
        save_board(board)

    return jsonify({
        "status": "success",
        "move": move.uci() if move else None,
        "fen": board.fen(),
        "game_over": board.is_game_over()
    })


# ================= RUN ================= #

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, render_template, request, jsonify
import chess
import database

app = Flask(__name__)

# ---------------- Game Variables ---------------- #

board = chess.Board()

mode = "pvp"
level = 1
unlocked_level = 1


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

def minimax(board, depth, maximizing):

    if depth == 0 or board.is_game_over():
        return evaluate(board)

    if maximizing:

        best = -9999

        for move in board.legal_moves:

            board.push(move)

            value = minimax(board, depth - 1, False)

            board.pop()

            best = max(best, value)

        return best

    else:

        best = 9999

        for move in board.legal_moves:

            board.push(move)

            value = minimax(board, depth - 1, True)

            board.pop()

            best = min(best, value)

        return best


# ---------------- AI Move ---------------- #

def ai_move():

    global level

    best_move = None
    best_value = -9999

    depth = min(level + 1, 3)

    for move in board.legal_moves:

        board.push(move)

        value = minimax(board, depth - 1, False)

        board.pop()

        if value > best_value:

            best_value = value
            best_move = move

    return best_move


# =================== PAGES =================== #

# ---------------- Home Page ---------------- #

@app.route("/")
def home():
    return render_template("home.html")


# ---------------- Mode Selection ---------------- #

@app.route("/mode")
def mode_page():
    return render_template("mode.html")


# ---------------- Levels Page ---------------- #

@app.route("/levels")
def levels_page():
    global unlocked_level
    return render_template("levels.html", unlocked=unlocked_level)


# ---------------- Game Page ---------------- #

@app.route("/game/<game_mode>/<lvl>")
def game(game_mode, lvl):

    global board, mode, level

    board = chess.Board()

    mode = game_mode
    level = int(lvl)

    return render_template(
        "game.html",
        mode=mode,
        level=level
    )


# ---------------- Result Page ---------------- #

@app.route("/result/<res>")
def result(res):

    global mode, level, unlocked_level
    if res == "win":
        if level >= unlocked_level:
            unlocked_level = level + 1

    next_level = level + 1

    return render_template(
        "result.html",
        result=res,
        mode=mode,
        level=level,
        unlocked=unlocked_level,
        next_level=next_level
    )


# =================== GAME API =================== #

# ---------------- New Game ---------------- #

@app.route("/new_game")
def new_game():

    global board

    board = chess.Board()

    return jsonify({
        "fen": board.fen(),
        "timer": 600
    })


# ---------------- Player Move ---------------- #

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

    # ❌ If no piece
    if not piece:
        return jsonify({"error": "no piece"})

    # ---------------- FIX: PROMOTION HANDLING ---------------- #

    # If pawn reaching last rank → ensure promotion is included
    if piece.piece_type == chess.PAWN:
        to_rank = chess.square_rank(move.to_square)

        if to_rank in [0, 7]:
            # ❌ If promotion not specified → reject
            if move.promotion is None:
                return jsonify({"error": "promotion required"})

    # ---------------- LEGAL MOVE CHECK ---------------- #

    if move in board.legal_moves:

        board.push(move)

        result = None

        if board.is_checkmate():

            if mode == "ai":
                result = "win"
            else:
                result = "checkmate"

        elif board.is_stalemate():
            result = "draw"

        elif board.is_insufficient_material():
            result = "draw"

        return jsonify({
            "fen": board.fen(),
            "result": result
        })

    return jsonify({"error": "illegal"})

# ---------------- AI Move ---------------- #

@app.route("/ai_move")
def ai_move_route():

    global board, unlocked_level, level

    if not board.is_game_over():

        move = ai_move()

        if move:
            board.push(move)

    result = None

    if board.is_checkmate():

        result = "lose"

    elif board.is_stalemate():
        result = "draw"

    elif board.is_insufficient_material():
        result = "draw"

    # Unlock next level when player wins
    if result == "lose":

        if level >= unlocked_level:
            unlocked_level = level + 1

    return jsonify({
        "fen": board.fen(),
        "result": result,
        "next_level": unlocked_level
    })


# =================== RUN SERVER =================== #

if __name__ == "__main__":

    database.init_db()

    app.run(debug=True)
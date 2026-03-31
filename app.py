from flask import Flask, render_template, request, jsonify
import chess
import database
import random

app = Flask(__name__)

# ---------------- Game Variables ---------------- #
board = chess.Board()
mode = "pvp"
level = 1
unlocked_level = 1

# ---------------- Piece Values ---------------- #
piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# ---------------- AI Evaluation ---------------- #
def evaluate(board):
   
    if board.is_checkmate():
        return -9999 if board.turn else 9999

    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

   
    for piece in board.piece_map().values():
        value = piece_values[piece.piece_type]
        if piece.color == chess.WHITE:
            score += value
        else:
            score -= value

  
    center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
    for sq in center_squares:
        piece = board.piece_at(sq)
        if piece:
            if piece.color == chess.WHITE:
                score += 30
            else:
                score -= 30

  
    score += 5 * len(list(board.legal_moves))

    return score

# ---------------- Minimax ---------------- #
def minimax(board, depth, alpha, beta, maximizing):
    if depth == 0 or board.is_game_over():
        return evaluate(board)

    if maximizing:
        max_eval = -999999
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
        min_eval = 999999
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

    if level <= 3:
        return random.choice(moves)

   
    moves.sort(key=lambda move: board.is_capture(move), reverse=True)

    best_move = None
    best_value = -999999

    
    if level == 4:
        depth = 2
    elif level == 5:
        depth = 2
    elif level == 6:
        depth = 3
    elif level == 7:
        depth = 3
    elif level == 8:
        depth = 4
    elif level == 9:
        depth = 4
    else:  
        depth = 5

    for move in moves:
        board.push(move)
        value = minimax(board, depth - 1, -999999, 999999, False)
        board.pop()

        if value > best_value:
            best_value = value
            best_move = move

    return best_move

# =================== PAGES =================== #
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/mode")
def mode_page():
    return render_template("mode.html")

@app.route("/levels")
def levels_page():
    global unlocked_level
    return render_template("levels.html", unlocked=unlocked_level)

@app.route("/game/<game_mode>/<lvl>")
def game(game_mode, lvl):
    global board, mode, level
    board = chess.Board()
    mode = game_mode
    level = int(lvl)
    return render_template("game.html", mode=mode, level=level)

@app.route("/result/<res>")
def result(res):
    global mode, level, unlocked_level
    winner = None

    if mode == "pvp":
        winner = request.args.get("winner", None)

    if mode == "ai":
        if res == "win" and level >= unlocked_level and level < 10:
            unlocked_level = level + 1

    return render_template("result.html", result=res, winner=winner, mode=mode)

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
        winner = None

        if board.is_checkmate():
            if mode == "ai":
                result = "win"
            else:
                result = "checkmate"
                winner = "White" if board.turn == chess.BLACK else "Black"

        elif board.is_stalemate() or board.is_insufficient_material():
            result = "draw"
            winner = "Draw"

        check_color = None
        check_square = None
        if board.is_check():
            king_square = board.king(board.turn)
            check_color = "white" if board.turn == chess.WHITE else "black"
            check_square = chess.square_name(king_square)

        return jsonify({
            "fen": board.fen(),
            "result": result,
            "winner": winner,
            "check": board.is_check(),
            "check_color": check_color,
            "check_square": check_square
        })

    return jsonify({"error": "illegal"})

# ---------------- AI MOVE ---------------- #
@app.route("/ai_move")
def ai_move_route():
    global board, unlocked_level, level

    if not board.is_game_over():
        move = ai_move()
        if move:
            board.push(move)

    result = None
    winner = None

    if board.is_checkmate():
        result = "lose"
        winner = "AI"
    elif board.is_stalemate() or board.is_insufficient_material():
        result = "draw"
        winner = "Draw"

    if result == "lose":
        if level >= unlocked_level and level < 10:
            unlocked_level = level + 1

    check_color = None
    check_square = None
    if board.is_check():
        king_square = board.king(board.turn)
        check_color = "white" if board.turn == chess.WHITE else "black"
        check_square = chess.square_name(king_square)

    return jsonify({
        "fen": board.fen(),
        "result": result,
        "winner": winner,
        "check": board.is_check(),
        "check_color": check_color,
        "check_square": check_square,
        "next_level": unlocked_level
    })

# =================== RUN =================== #
if __name__ == "__main__":
    database.init_db()
    app.run(debug=True)
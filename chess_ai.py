import chess
import random

piece_value = {
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
        value = piece_value[piece.piece_type]
        if piece.color == chess.WHITE:
            score += value
        else:
            score -= value
    return score


def minimax(board, depth, maximizing):

    if depth == 0 or board.is_game_over():
        return evaluate(board)

    if maximizing:
        max_eval = -9999
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth-1, False)
            board.pop()
            max_eval = max(max_eval, eval)
        return max_eval

    else:
        min_eval = 9999
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth-1, True)
            board.pop()
            min_eval = min(min_eval, eval)
        return min_eval


def get_ai_move(board, level):

    if level == 1:
        return random.choice(list(board.legal_moves))

    depth = level

    best_move = None
    best_value = -9999

    for move in board.legal_moves:
        board.push(move)
        board_value = minimax(board, depth, False)
        board.pop()

        if board_value > best_value:
            best_value = board_value
            best_move = move

    return best_move
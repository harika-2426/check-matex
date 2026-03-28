let boardDiv = document.getElementById("board")
let selected = null
let files = "abcdefgh"
let historyList = document.getElementById("history")

let time = 1800
let timerInterval

let moveSound = new Audio("/static/sounds/move_sound.wav")

let gameMode = window.location.pathname.includes("ai") ? "ai" : "pvp"

let pendingPromotion = null

let currentTheme = parseInt(localStorage.getItem("boardTheme")) || 1

/* ---------------- TIMER ---------------- */

function startTimer() {
    clearInterval(timerInterval)
    time = 1800

    timerInterval = setInterval(() => {
        time--

        let minutes = Math.floor(time / 60)
        let seconds = time % 60

        let timer = document.getElementById("timer")

        if (timer) {
            timer.innerText = minutes + ":" + (seconds < 10 ? "0" : "") + seconds
        }

        if (time <= 0) {
            clearInterval(timerInterval)
            alert("Time Over")
            window.location.href = "/result/draw"
        }

    }, 1000)
}

/* ---------------- PIECES ---------------- */

let pieces = {
    "r": "br.png", "n": "bn.png", "b": "bb.png", "q": "bq.png", "k": "bk.png", "p": "bp.png",
    "R": "wr.png", "N": "wn.png", "B": "wb.png", "Q": "wq.png", "K": "wk.png", "P": "wp.png"
}

/* ---------------- DRAW BOARD ---------------- */

function drawBoard(fen) {
    boardDiv.innerHTML = ""
    clearCheckHighlight()

    let rows = fen.split(" ")[0].split("/")

    for (let r = 0; r < 8; r++) {
        let col = 0
        for (let char of rows[r]) {
            if (!isNaN(char)) {
                for (let i = 0; i < char; i++) {
                    createSquare(r, col, null)
                    col++
                }
            } else {
                createSquare(r, col, char)
                col++
            }
        }
    }
}

/* ---------------- CREATE SQUARE ---------------- */

function createSquare(r, c, piece) {
    let square = document.createElement("div")
    square.classList.add("square")

    let baseColor = (r + c) % 2 == 0 ? "white" : "black"
    square.classList.add(baseColor)

    if (currentTheme === 2) square.classList.add("theme2")
    if (currentTheme === 3) square.classList.add("theme3")
    if (currentTheme === 4) square.classList.add("theme4")

    square.dataset.row = r
    square.dataset.col = c
    square.onclick = selectSquare

    if (piece) {
        let img = document.createElement("img")
        img.src = "/static/pieces/" + pieces[piece]
        img.classList.add("piece")
        square.appendChild(img)
    }

    boardDiv.appendChild(square)
}

/* ---------------- THEME ---------------- */

function changeBoardTheme() {
    currentTheme++
    if (currentTheme > 4) currentTheme = 1
    localStorage.setItem("boardTheme", currentTheme)
}

/* ---------------- DOT SYSTEM ---------------- */

function clearDots() {
    document.querySelectorAll(".moveDot").forEach(dot => dot.remove())
}

/* ---------------- SELECT ---------------- */

function selectSquare() {
    clearHighlights()
    clearDots()

    let piece = this.querySelector("img")

    if (selected == null) {
        if (!piece) return
        selected = this
        this.classList.add("highlight")

        let squareName = convertToSquare(this.dataset.row, this.dataset.col)

        fetch("/legal_moves/" + squareName)
            .then(res => res.json())
            .then(data => {
                if (!data || !data.moves) return

                data.moves.forEach(move => {
                    let sq = convertFromSquare(move)
                    let target = document.querySelector(
                        `[data-row='${sq.row}'][data-col='${sq.col}']`
                    )

                    if (target) {
                        let dot = document.createElement("div")
                        dot.classList.add("moveDot")
                        target.appendChild(dot)
                    }
                })
            })

    } else {
        let from = selected.dataset.row + selected.dataset.col
        let to = this.dataset.row + this.dataset.col

        selected.classList.remove("highlight")
        selected = null

        movePiece(from, to)
    }
}

/* ---------------- CLEAR ---------------- */

function clearHighlights() {
    document.querySelectorAll(".highlight").forEach(s => s.classList.remove("highlight"))
}

function clearCheckHighlight() {
    document.querySelectorAll(".check").forEach(s => s.classList.remove("check"))
}

/* ---------------- CHECK ---------------- */

function highlightCheck(square) {

    clearCheckHighlight()

    if (!square) return   // 🔥 FIX CRASH

    try {
        let sq = convertFromSquare(square)

        let target = document.querySelector(
            `[data-row='${sq.row}'][data-col='${sq.col}']`
        )

        if (target) {
            target.classList.add("check")
        }
    } catch (e) {
        console.log("Check highlight error:", e)
    }
}

/* ---------------- MOVE ---------------- */

function convertMove(from, to) {
    return files[from[1]] + (8 - from[0]) + files[to[1]] + (8 - to[0])
}

function movePiece(from, to) {
    sendMove(from, to, null)
}

/* ---------------- SEND MOVE ---------------- */

function sendMove(from, to, promotion) {
    let move = convertMove(from, to)
    if (promotion) move += promotion

    fetch("/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ move })
    })
    .then(res => res.json())
    .then(data => {

        if (data.error) return

        if (data.fen) {
            drawBoard(data.fen)
            moveSound.play()
            addMoveToHistory(move)
        }

        if (data.check && data.check_square) {
            highlightCheck(data.check_square)
        }

        if (data.result) {
            clearInterval(timerInterval)
            changeBoardTheme()

            setTimeout(() => {
                window.location.href = "/result/" + data.result
            }, 500)

            return
        }

        if (gameMode === "ai") {
            setTimeout(() => {
                fetch("/ai_move")
                .then(res => res.json())
                .then(aiData => {

                    if (aiData.fen) {
                        drawBoard(aiData.fen)
                        moveSound.play()
                        addMoveToHistory("AI move")
                    }

                    if (aiData.check && aiData.check_square) {
                        highlightCheck(aiData.check_square)
                    }

                    if (aiData.result) {
                        clearInterval(timerInterval)
                        changeBoardTheme()

                        setTimeout(() => {
                            window.location.href = "/result/" + aiData.result
                        }, 500)
                    }
                })
            }, 1200)
        }
    })
}

/* ---------------- HISTORY ---------------- */

function addMoveToHistory(move) {
    if (!historyList) return
    let item = document.createElement("li")
    item.innerText = move
    historyList.appendChild(item)
}

/* ---------------- CONVERTERS ---------------- */

function convertToSquare(r, c) {
    return files[c] + (8 - r)
}

function convertFromSquare(square) {
    if (!square || square.length < 2) return { row: 0, col: 0 }

    return {
        row: 8 - parseInt(square[1]),
        col: files.indexOf(square[0])
    }
}

/* ---------------- NEW GAME ---------------- */

function newGame() {
    fetch("/new_game")
    .then(res => res.json())
    .then(data => {
        drawBoard(data.fen)
        startTimer()
    })
}

/* ---------------- INIT ---------------- */

if (boardDiv) {
    newGame()
}
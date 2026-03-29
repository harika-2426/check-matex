let boardDiv = document.getElementById("board")
let selected = null
let files = "abcdefgh"
let historyList = document.getElementById("history")

let time = 1800
let timerInterval

let moveSound = new Audio("/static/sounds/move_sound.wav")

let gameMode = window.location.pathname.includes("ai") ? "ai" : "pvp"
localStorage.setItem("mode", gameMode)

let pendingPromotion = null
let gameOver = false   // 🔥 IMPORTANT FIX

const MAX_LEVEL = 10

let currentTheme = parseInt(localStorage.getItem("boardTheme")) || 1

if (!localStorage.getItem("unlockedLevel")) {
    localStorage.setItem("unlockedLevel", "1")
}
if (!localStorage.getItem("currentLevel")) {
    localStorage.setItem("currentLevel", "1")
}

/* ---------------- LEVEL SYSTEM ---------------- */

function getCurrentLevel() {
    return parseInt(localStorage.getItem("currentLevel")) || 1
}

function getUnlockedLevel() {
    return parseInt(localStorage.getItem("unlockedLevel")) || 1
}

function unlockNextLevel() {
    let current = getCurrentLevel()
    let unlocked = getUnlockedLevel()

    if (current === unlocked && unlocked < MAX_LEVEL) {
        localStorage.setItem("unlockedLevel", unlocked + 1)
    }
}

/* ---------------- TIMER ---------------- */

function startTimer() {
    clearInterval(timerInterval)
    time = 1800

    timerInterval = setInterval(() => {
        if (gameOver) return   // 🔥 STOP TIMER LOGIC

        time--

        let minutes = Math.floor(time / 60)
        let seconds = time % 60

        let timer = document.getElementById("timer")

        if (timer) {
            timer.innerText = minutes + ":" + (seconds < 10 ? "0" : "") + seconds
        }

        if (time <= 0) {
            clearInterval(timerInterval)
            gameOver = true
            window.location.href = "/result/draw"
        }

    }, 1000)
}

/* ---------------- PIECES ---------------- */

let pieces = {
    r: "br.png", n: "bn.png", b: "bb.png", q: "bq.png", k: "bk.png", p: "bp.png",
    R: "wr.png", N: "wn.png", B: "wb.png", Q: "wq.png", K: "wk.png", P: "wp.png"
}

/* ---------------- BOARD ---------------- */

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

/* ---------------- SQUARE ---------------- */

function createSquare(r, c, piece) {
    let square = document.createElement("div")
    square.classList.add("square")

    let baseColor = (r + c) % 2 === 0 ? "white" : "black"
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

/* ---------------- SELECT ---------------- */

function selectSquare() {
    if (gameOver) return   // 🔥 BLOCK AFTER WIN

    clearHighlights()
    clearDots()

    let piece = this.querySelector("img")

    if (!selected) {
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

/* ---------------- MOVE ---------------- */

function movePiece(from, to) {
    if (gameOver) return

    if (checkPromotion(from, to)) {
        pendingPromotion = { from, to }
        document.getElementById("promotionBox").style.display = "flex"
        return
    }

    sendMove(from, to, null)
}

/* ---------------- SEND MOVE ---------------- */

function sendMove(from, to, promotion) {

    if (gameOver) return

    let move = convertMove(from, to)
    if (promotion) move += promotion

    fetch("/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ move })
    })
    .then(res => res.json())
    .then(data => {

        if (gameOver) return

        if (data.error) return

        if (data.fen) {
            drawBoard(data.fen)
            moveSound.play()
            addMoveToHistory(move)
        }

        if (data.check && data.check_square) {
            highlightCheck(data.check_square)
        }

        /* ---------------- GAME OVER ---------------- */

        if (data.result && !gameOver) {
            gameOver = true
            clearInterval(timerInterval)

            if (gameMode === "ai" && data.result === "win") {
                unlockNextLevel()
            }

            setTimeout(() => {
                window.location.href = "/result/" + data.result
            }, 600)

            return
        }

        /* ---------------- AI MOVE ---------------- */

        if (gameMode === "ai") {

            if (gameOver) return

            setTimeout(() => {

                fetch("/ai_move")
                .then(res => res.json())
                .then(aiData => {

                    if (gameOver) return

                    if (aiData.fen) {
                        drawBoard(aiData.fen)
                        moveSound.play()
                        addMoveToHistory("AI move")
                    }

                    if (aiData.check && aiData.check_square) {
                        highlightCheck(aiData.check_square)
                    }

                    if (aiData.result && !gameOver) {
                        gameOver = true
                        clearInterval(timerInterval)

                        setTimeout(() => {
                            window.location.href = "/result/" + aiData.result
                        }, 600)
                    }
                })

            }, 900)
        }
    })
}

/* ---------------- PROMOTE ---------------- */

function promote(piece) {
    document.getElementById("promotionBox").style.display = "none"
    sendMove(pendingPromotion.from, pendingPromotion.to, piece)
    pendingPromotion = null
}

/* ---------------- CHECK ---------------- */

function highlightCheck(square) {
    clearCheckHighlight()

    if (!square) return

    let sq = convertFromSquare(square)

    let target = document.querySelector(
        `[data-row='${sq.row}'][data-col='${sq.col}']`
    )

    if (target) target.classList.add("check")
}

/* ---------------- HELPERS ---------------- */

function clearHighlights() {
    document.querySelectorAll(".highlight").forEach(e => e.classList.remove("highlight"))
}

function clearCheckHighlight() {
    document.querySelectorAll(".check").forEach(e => e.classList.remove("check"))
}

function clearDots() {
    document.querySelectorAll(".moveDot").forEach(e => e.remove())
}

function addMoveToHistory(move) {
    if (!historyList) return
    let li = document.createElement("li")
    li.innerText = move
    historyList.appendChild(li)
}

/* ---------------- CONVERT ---------------- */

function convertToSquare(r, c) {
    return files[c] + (8 - r)
}

function convertFromSquare(square) {
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
            gameOver = false
            drawBoard(data.fen)
            startTimer()
        })
}

/* ---------------- INIT ---------------- */

if (boardDiv) {
    newGame()
}
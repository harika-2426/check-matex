let boardDiv = document.getElementById("board")
let selected = null
let files = "abcdefgh"
let historyList = document.getElementById("history")

let time = 600
let timerInterval

let moveSound = new Audio("/static/sounds/move_sound.wav")
let hitSound = new Audio("/static/sounds/hit_sound.wav")
let winSound = new Audio("/static/sounds/win_sound.wav")

let gameMode = window.location.pathname.includes("ai") ? "ai" : "pvp"

// ✅ ALWAYS SAVE MODE (IMPORTANT FIX)
localStorage.setItem("mode", gameMode)

let pendingPromotion = null

/* ---------------- LEVEL SYSTEM ---------------- */

const MAX_LEVEL = 10

// initialize safely
if (!localStorage.getItem("unlockedLevel")) {
    localStorage.setItem("unlockedLevel", "1")
}

if (!localStorage.getItem("currentLevel")) {
    localStorage.setItem("currentLevel", "1")
}

// helper functions
function getCurrentLevel() {
    return parseInt(localStorage.getItem("currentLevel")) || 1
}

function getUnlockedLevel() {
    return parseInt(localStorage.getItem("unlockedLevel")) || 1
}

function unlockNextLevel() {
    let current = getCurrentLevel()
    let unlocked = getUnlockedLevel()

    // unlock only next level
    if (current === unlocked && unlocked < MAX_LEVEL) {
        localStorage.setItem("unlockedLevel", unlocked + 1)
        console.log("✅ Level Unlocked:", unlocked + 1)
    }
}

/* ---------------- TIMER ---------------- */

function startTimer() {
    clearInterval(timerInterval)
    time = 600

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

    square.classList.add((r + c) % 2 == 0 ? "white" : "black")

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

/* ---------------- SELECT PIECE ---------------- */

function selectSquare() {
    clearHighlights()
    let piece = this.querySelector("img")

    if (selected == null) {
        if (!piece) return
        selected = this
        this.classList.add("highlight")

        let squareName = convertToSquare(this.dataset.row, this.dataset.col)

        fetch("/legal_moves/" + squareName)
            .then(res => res.json())
            .then(data => {
                data.moves.forEach(move => {
                    let sq = convertFromSquare(move)
                    let target = document.querySelector(
                        `[data-row='${sq.row}'][data-col='${sq.col}']`
                    )
                    if (target) target.classList.add("highlightMove")
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

/* ---------------- CLEAR HIGHLIGHTS ---------------- */

function clearHighlights() {
    document.querySelectorAll(".highlightMove").forEach(s => s.classList.remove("highlightMove"))
    document.querySelectorAll(".highlight").forEach(s => s.classList.remove("highlight"))
}

/* ---------------- PROMOTION ---------------- */

function checkPromotion(from, to) {

    let fromRow = parseInt(from[0])
    let fromCol = from[1]

    let piece = document.querySelector(`[data-row='${fromRow}'][data-col='${fromCol}'] img`)
    if (!piece) return false

    let src = piece.src
    let toRow = parseInt(to[0])
    let toCol = to[1]

    let targetSquare = document.querySelector(`[data-row='${toRow}'][data-col='${toCol}'] img`)

    // ---------------- WHITE PAWN ----------------
    if (src.includes("wp.png")) {

        // Must reach last row
        if (toRow !== 0) return false

        // Same column (forward move) → must be empty
        if (fromCol === toCol) {
            if (targetSquare) return false
        }

        // Diagonal move → must capture
        else {
            if (!targetSquare) return false
        }

        return true
    }

    // ---------------- BLACK PAWN ----------------
    if (src.includes("bp.png")) {

        if (toRow !== 7) return false

        if (fromCol === toCol) {
            if (targetSquare) return false
        } else {
            if (!targetSquare) return false
        }

        return true
    }

    return false
}

/* ---------------- MOVE ---------------- */

function convertMove(from, to) {
    return files[from[1]] + (8 - from[0]) + files[to[1]] + (8 - to[0])
}

function movePiece(from, to) {
    if (checkPromotion(from, to)) {
        pendingPromotion = { from, to }
        document.getElementById("promotionBox").style.display = "flex"
        return
    }
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

        if (data.check) highlightKing()

        // ✅ FIXED LEVEL UNLOCK HERE ONLY
        if (data.result) {
            clearInterval(timerInterval)

            if (gameMode === "ai" && data.result === "win") {
                unlockNextLevel()
            }

            window.location.href = "/result/" + data.result
            return
        }

        if (gameMode === "ai") {
            setTimeout(() => {
                fetch("/ai_move")
                .then(res => res.json())
                .then(aiData => {
                    drawBoard(aiData.fen)
                    moveSound.play()
                    addMoveToHistory("AI move")

                    if (aiData.check) highlightKing()

                    if (aiData.result) {
                        clearInterval(timerInterval)
                        window.location.href = "/result/" + aiData.result
                    }
                })
            }, 1200)
        }
    })
}

/* ---------------- PROMOTION SELECT ---------------- */

function promote(piece) {
    document.getElementById("promotionBox").style.display = "none"
    sendMove(pendingPromotion.from, pendingPromotion.to, piece)
    pendingPromotion = null
}

/* ---------------- HISTORY ---------------- */

function addMoveToHistory(move) {
    if (!historyList) return
    let item = document.createElement("li")
    item.innerText = move
    historyList.appendChild(item)
    historyList.scrollTop = historyList.scrollHeight
}

/* ---------------- CHECK ---------------- */

function highlightKing() {
    document.querySelectorAll(".check").forEach(s => s.classList.remove("check"))
    document.querySelectorAll("img[src*='k.png']").forEach(k => {
        k.parentElement.classList.add("check")
    })
}

/* ---------------- CONVERTERS ---------------- */

function convertToSquare(r, c) {
    return files[c] + (8 - r)
}

function convertFromSquare(square) {
    return {
        row: 8 - square[1],
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
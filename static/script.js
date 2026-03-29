/* ================= AUTH + NAVIGATION (NEW) ================= */

// Navigation
function goToLogin() {
    window.location.href = "/login";
}

function goToRegister() {
    window.location.href = "/register";
}

// Register
function registerUser(e) {
    e.preventDefault();

    let username = document.getElementById("regUsername").value;
    let password = document.getElementById("regPassword").value;

    localStorage.setItem("user", JSON.stringify({ username, password }));

    alert("Registered successfully! Now login.");
    window.location.href = "/login";
}

// Login
function loginUser(e) {
    e.preventDefault();

    let username = document.getElementById("loginUsername").value;
    let password = document.getElementById("loginPassword").value;

    let storedUser = JSON.parse(localStorage.getItem("user"));

    if (storedUser && username === storedUser.username && password === storedUser.password) {
        alert("Login successful!");
        window.location.href = "/mode";
    } else {
        alert("Invalid credentials!");
    }
}

/* ================= EXISTING GAME CODE ================= */

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
let gameOver = false

const MAX_LEVEL = 10

let currentTheme = parseInt(localStorage.getItem("boardTheme")) || 1

/* ---------------- RESET SAFE STATE ---------------- */

function resetUI() {
    selected = null
    clearHighlights()
    clearDots()
    clearCheckHighlight()
}

/* ---------------- TIMER ---------------- */

function startTimer() {
    clearInterval(timerInterval)
    time = 1800

    timerInterval = setInterval(() => {
        if (gameOver) return

        time--

        let m = Math.floor(time / 60)
        let s = time % 60

        let timer = document.getElementById("timer")
        if (timer) timer.innerText = m + ":" + (s < 10 ? "0" : "") + s

        if (time <= 0) {
            gameOver = true
            clearInterval(timerInterval)
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
    if (!boardDiv) return

    boardDiv.innerHTML = ""
    resetUI()

    let rows = fen.split(" ")[0].split("/")

    for (let r = 0; r < 8; r++) {
        let col = 0

        for (let ch of rows[r]) {
            if (!isNaN(ch)) {
                for (let i = 0; i < ch; i++) {
                    createSquare(r, col, null)
                    col++
                }
            } else {
                createSquare(r, col, ch)
                col++
            }
        }
    }
}

/* ---------------- SQUARE ---------------- */

function createSquare(r, c, piece) {
    let square = document.createElement("div")
    square.classList.add("square")

    square.classList.add((r + c) % 2 === 0 ? "white" : "black")

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
    if (gameOver) return

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
                if (!data.moves) return

                data.moves.forEach(m => {
                    let sq = convertFromSquare(m)

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

        if (data.error) return

        if (data.fen) {
            drawBoard(data.fen)
            moveSound.play()
            addMoveToHistory(move)
        }

        if (data.result && !gameOver) {
            gameOver = true
            clearInterval(timerInterval)

            setTimeout(() => {
                window.location.href = "/result/" + data.result
            }, 500)

            return
        }

        /* ---------------- AI MOVE ---------------- */

        if (gameMode === "ai") {
            if (gameOver) return

            setTimeout(() => {
                fetch("/ai_move")
                    .then(res => res.json())
                    .then(aiData => {

                        if (aiData.fen) {
                            drawBoard(aiData.fen)
                            moveSound.play()
                            addMoveToHistory("AI")
                        }

                        if (aiData.result && !gameOver) {
                            gameOver = true
                            clearInterval(timerInterval)

                            setTimeout(() => {
                                window.location.href = "/result/" + aiData.result
                            }, 500)
                        }
                    })
            }, 600)
        }
    })
}

/* ---------------- PROMOTION ---------------- */

function promote(piece) {
    document.getElementById("promotionBox").style.display = "none"
    sendMove(pendingPromotion.from, pendingPromotion.to, piece)
    pendingPromotion = null
}

/* ---------------- HISTORY ---------------- */

function addMoveToHistory(move) {
    if (!historyList) return
    let li = document.createElement("li")
    li.innerText = move
    historyList.appendChild(li)
}

/* ---------------- HELPERS ---------------- */

function clearHighlights() {
    document.querySelectorAll(".highlight").forEach(e => e.classList.remove("highlight"))
}

function clearDots() {
    document.querySelectorAll(".moveDot").forEach(e => e.remove())
}

function clearCheckHighlight() {
    document.querySelectorAll(".check").forEach(e => e.classList.remove("check"))
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
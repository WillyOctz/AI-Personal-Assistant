const form = document.getElementById("chat-form")
const input = document.getElementById("message-input")
const messages = document.getElementById("messages")
const sendButton = document.getElementById("send-button")
const status = document.getElementById("connection-status")
const confirmationActions = document.getElementById("confirmation-actions")
const confirmButton = document.getElementById("confirm-button")
const cancelButton = document.getElementById("cancel-button")

function addMessage(role, text) {
    const message = document.createElement("article")
    const label = document.createElement("p")
    const content = document.createElement("p")

    message.classList.add("message")
    message.classList.add(
        role === "user" ? "user-message" : "assistant-message"
    )

    label.classList.add("message-label")
    label.textContent = role === "user" ? "You" : "Nebula"

    content.textContent = text

    message.append(label, content)
    messages.appendChild(message)
    messages.scrollTop = messages.scrollHeight
}

function needsConfirmation(res) {
    return res.toLowerCase().includes("reply yes")
}

function setChatBusy(isBusy) {
    sendButton.disabled = isBusy
    confirmButton.disabled = isBusy
    cancelButton.disabled = isBusy
}

function sendConfirmation(answer) {
    input.value = answer
    form.requestSubmit()
}

async function sendMessage(message) {
    const res = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            message: message,
        })
    })

    const data = await res.json()

    if (!res.ok) {
        throw new Error(data.detail || "Request failed.")
    }

    return data.response
}

async function loadConversation() {
    try {
        const res = await fetch("/conversation?limit=20")

        if (!res.ok) {
            throw new Error("Conversation request failed.")
        }

        const data = await res.json()
        const turns = data.turns

        if (turns.length === 0) {
            addMessage("assistant", "Hello. What can I help you with?")
            return
        }

        for (const turn of turns) {
            addMessage("user", turn.user)
            addMessage("assistant", turn.assistant)
        }

        const latestTurn = turns[turns.length - 1]
        confirmationActions.hidden = !needsConfirmation(
            latestTurn.assistant
        )
    } catch (err) {
        addMessage("assistant", "I could not load our recent conversation.")
        status.textContent = "Connection error"
    }
}

async function loadStartupMessage() {
    try {
        const res = await fetch("/startup")

        if (!res.ok) {
            throw new Error("Startup request failed.")
        }

        const data = await res.json()

        if (data.message) {
            addMessage("assistant", data.message)
        }
    } catch (err) {
        status.textContent = "Connection error"
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = input.value.trim()

    if (!message) {
        return
    }

    addMessage("user", message)
    confirmationActions.hidden = true

    input.value = ""
    input.focus()
    setChatBusy(true)
    status.textContent = "Contemplating..."

    try {
        const res = await sendMessage(message);
        addMessage("assistant", res)
        confirmationActions.hidden = !needsConfirmation(res)
        status.textContent = "Local API"
    } catch (err) {
        addMessage("assistant", `Error: ${err.message}`)
        status.textContent = "Connection error"
    } finally {
        setChatBusy(false)
    }
})

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault()
        form.requestSubmit()
    }
})

confirmButton.addEventListener("click", () => {
    sendConfirmation("yes")
})

cancelButton.addEventListener("click", () => {
    sendConfirmation("no")
})

async function initializeChat() {
    await loadConversation()
    await loadStartupMessage()
}

initializeChat()
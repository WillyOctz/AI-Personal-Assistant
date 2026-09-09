const form = document.getElementById("chat-form")
const input = document.getElementById("message-input")
const messages = document.getElementById("messages")
const sendButton = document.getElementById("send-button")
const status = document.getElementById("connection-status")

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

    input.value = ""
    input.focus()
    sendButton.disabled = true
    status.textContent = "Contemplating..."

    try {
        const res = await sendMessage(message);
        addMessage("assistant", res)
        status.textContent = "Local API"
    } catch (err) {
        addMessage("assistant", `Error: ${err.message}`)
        status.textContent = "Connection error"
    } finally {
        sendButton.disabled = false
    }
})

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault()
        form.requestSubmit()
    }
})

loadStartupMessage()
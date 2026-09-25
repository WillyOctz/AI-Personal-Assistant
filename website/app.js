// ID Element get from HTML
const form = document.getElementById("chat-form")
const input = document.getElementById("message-input")
const messages = document.getElementById("messages")
const sendButton = document.getElementById("send-button")
const status = document.getElementById("connection-status")
const confirmationActions = document.getElementById("confirmation-actions")
const confirmButton = document.getElementById("confirm-button")
const cancelButton = document.getElementById("cancel-button")
const reminderList = document.getElementById("reminder-list")
const reminderCount = document.getElementById("reminder-count")
const reminderForm = document.getElementById("reminder-form")
const reminderTextInput = document.getElementById("reminder-text-input")
const reminderDueInput = document.getElementById("reminder-due-input")
const addReminderButton = document.getElementById("add-reminder-button")

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

function renderReminders(reminders) {
    reminderList.replaceChildren()
    reminderCount.textContent = String(reminders.length)

    if (reminders.length === 0) {
        const empty = document.createElement("p")
        empty.classList.add("reminder-empty")
        empty.textContent = "No reminders yet."
        reminderList.appendChild(empty)
        return
    }

    for (const reminder of reminders) {
        const item = document.createElement("li")
        const text = document.createElement("p")
        const due = document.createElement("p")
        const completeButton = document.createElement("button")

        item.classList.add("reminder-item")
        text.classList.add("reminder-text")
        due.classList.add("reminder-due")
        completeButton.classList.add("complete-reminder")
        completeButton.type = "button"
        completeButton.textContent = "Done"

        text.textContent = reminder.text
        due.textContent = reminder.due ? `Due: ${reminder.due}` : "No due date"
        completeButton.addEventListener("click", async() => {
            completeButton.disabled = true

            try {
                await completeReminder(reminder.position)
                await loadReminders()
            } catch (err) {
                addMessage(
                    "assistant",
                    `I could not complete that reminder: ${err.message}`
                )
                completeButton.disabled = false
            }
        })

        item.append(text, due, completeButton)
        reminderList.appendChild(item)
    }
}

async function createReminder(text, due) {
    const res = await fetch("/reminders", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            text: text,
            due: due || null,
        }),
    })

    const data = await res.json()

    if (!res.ok) {
        throw new Error(data.detail || "Reminder could not be created.")
    }

    return data
}

async function completeReminder(position) {
    const res = await fetch(`/reminders/${position}/complete`, {
        method: "POST",
    })

    const data = await res.json()

    if (!res.ok) {
        throw new Error(data.detail || "Reminder could not be completed.")
    }

    return data
}

async function loadReminders() {
    try {
        if (!reminderList || !reminderCount) {
            console.error("Reminder panel elements are missing from index.html.")
            return
        }

        const res = await fetch("/reminders")

        if (!res.ok) {
            throw new Error("Reminder request failed.")
        }

        const data = await res.json()

        if (!Array.isArray(data.reminders)) {
            throw new Error("Invalid reminder response.")
        }

        renderReminders(data.reminders)
    } catch (err) {
        reminderList.replaceChildren()
        reminderCount.textContent = "-"

        const unavailable = document.createElement("p")
        unavailable.classList.add("reminder-empty")
        unavailable.textContent = "Reminders are unavailable."
        reminderList.appendChild(unavailable)
    }
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

async function loadHealth() {
    try {
        const res = await fetch("/health")

        if (!res.ok) {
            throw new Error("Health check failed.")
        }

        const data = await res.json()

        if (!data.ok || !data.database.ok) {
            throw new Error("Nebula is unavailable.")
        }

        status.textContent = "Connected"
    } catch (err) {
        status.textContent = "Connection error"
    }
}

reminderForm.addEventListener("submit", async (event) => {
    event.preventDefault()

    const text = reminderTextInput.value.trim()
    const due = reminderDueInput.value

    if (!text) {
        return
    }

    addReminderButton.disabled = true

    try {
        await createReminder(text, due)

        reminderTextInput.value = ""
        reminderDueInput.value = ""

        await loadReminders()
    } catch (err) {
        addMessage(
            "assistant",
            `I could not add that reminder: ${err.message}`
        )
    } finally {
        addReminderButton.disabled = false
    }
})

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
        await loadReminders()
        status.textContent = "Connected"
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
    await loadHealth()
    await loadConversation()
    await loadStartupMessage()
    await loadReminders()
}

initializeChat()
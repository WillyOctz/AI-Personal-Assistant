"use strict"

const $ = (id) => document.getElementById(id)

const messagesEl = $("messages")
const form = $("chat-form")
const input = $("message-input")
const sendButton = $("send-button")
const statusEl = $("status")
const orb = $("orb")
const todayPanel = $("today")
const todayToggle = $("today-toggle")
const todaySummary = $("today-summary")
const focusLine = $("focus-line")
const goalLine = $("goal-line")
const goalProgress = $("goal-progress")
const goalFill = $("goal-fill")
const focusStart = $("focus-start")
const focusStop = $("focus-stop")
const noteForm = $("note-form")
const noteInput = $("note-input")
const reminderListEl = $("reminder-list")
const reminderForm = $("reminder-form")
const reminderText = $("reminder-text")
const reminderDue = $("reminder-due")
const launchBlock = $("launch-block")
const launchChips = $("launch-chips")

const CONFIRM_ACTIONS = [
    { label: "Yes", type: "command", command: "yes", style: "primary" },
    { label: "No", type: "command", command: "no", style: "ghost" },
]

let busy = false
const sent = []
let sentIndex = 0

/* -----------------------Helper------------------------ */
function el(tag, className, text) {
    const node = document.createElement(tag)
    if (className) node.className = className
    if (text !== undefined && text !== null) node.textContent = text
    return node
}

async function api(path, options = {}) {
    const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
    })

    let data = null
    try { data = await res.json() } catch (_) {}

    if (!res.ok) {
        const detail = data && data.detail
        throw new Error(typeof detail === "string" ? detail : "Request failed.")
    }

    return data
}

function setStatus(text, state) {
    statusEl.textContent = text
    if (state) orb.dataset.state = state
}

function resizeComposer() {
    input.style.height = "auto"
    input.style.height = `${Math.min(input.scrollHeight, 140)}px`
}

function scrollDown() {
    messagesEl.scrollTop = messagesEl.scrollHeight
}

function flash(button, text) {
    const old = button.textContent
    button.textContent = text
    setTimeout(() => { button.textContent = old }, 1200)
}


/* --------------------------------MESSAGES--------------------------*/
function addUser(text) {
    const m = el("article", "msg user")
    m.appendChild(el("p", "bubble", text))
    messagesEl.appendChild(m)
    scrollDown()
    return m
}

function addAssistantText(text) {
    const m = el("article", "msg assistant")
    m.appendChild(el("p", "bubble", text))
    messagesEl.appendChild(m)
    scrollDown()
    return m
}

function addTyping() {
    const m = el("article", "msg assistant typing")
    const bubble = el("p", "bubble")
    for (let i = 0; i < 3; i++) bubble.appendChild(el("span", "dot"))
    m.appendChild(bubble)
    messagesEl.appendChild(m)
    scrollDown()
    return m
}


/* -----------------------------------ACTION BUTTONS------------------------------- */
function renderActions(actions) {
    const row = el("div", "actions")

    for (const a of actions) {
        const b = el("button", `btn ${a.style || "default"}`, a.label)
        b.type = "button"
        b.addEventListener("click", () => runAction(a, b, row))
        row.appendChild(b)
    }

    return row
}

async function runAction(a, button, row) {
    if (a.type === "copy") {
        try {
            await navigator.clipboard.writeText(a.value || "")
            flash(button, "Copied")
        } catch (_) {
            flash(button, "Can't copy")
        }
        return
    }

    if (busy) return

    if (a.command === "yes" || a.command === "no") {
        row.classList.add("answered")
        row.querySelectorAll("button").forEach((b) => { b.disabled = true })
    }

    send(a.command)
}

/* -------------------------------------CARD RENDERERS---------------------------- */
function progressBar(percent) {
    const bar = el("div", "progress")
    const fill = document.createElement("span")
    fill.style.width = `${Math.max(0, Math.min(100, percent))}%`
    bar.appendChild(fill)
    return bar
}

function addSection(card, title, items, warn) {
    if (!items || !items.length) return

    card.appendChild(el("h4", warn ? "card-title warn" : "card-title", `${title} (${items.length})`))

    const ul = el("ul", "card-list")

    for (const item of items) {
        const li = el("li")
        li.appendChild(el("span", "", item.text))
        if (item.due) li.appendChild(el("small", "muted", item.due))
        ul.appendChild(li)
    }

    card.appendChild(ul)
}

function renderBriefing(d) {
    const card = el("div", "card")

    if (d.goal) card.appendChild(el("p", "card-line", `Goal: ${d.goal}`))

    addSection(card, "Overdue", d.overdue, true)
    addSection(card, "Today", d.today, false)

    if (d.focus && d.focus.goal) {
        const hasProgress = typeof d.focus.progress === "number"
        card.appendChild(el("p", "card-line",
            hasProgress
                ? `Focus goal: ${d.focus.goal} · ${d.focus.today_focus} (${d.focus.progress}%)`
                : `Focus goal: ${d.focus.goal}`))
        if (hasProgress) card.appendChild(progressBar(d.focus.progress))
    }

    if (d.suggested) card.appendChild(el("p", "card-line", `Suggested: ${d.suggested}`))

    return card
}

function renderFileList(d) {
    const card = el("div", "card")

    for (const item of d.items || []) {
        const row = el("div", "file-row")
        const icon = item.type === "folder" ? "📁" : "📄"

        row.appendChild(el("span", "file-name", `${icon} ${item.name}`))

        const path = el("p", "file-path", item.rel)
        path.title = item.path
        row.appendChild(path)

        if (item.actions && item.actions.length) row.appendChild(renderActions(item.actions))

        card.appendChild(row)
    }

    return card
}

function renderReminderList(d) {
    const card = el("div", "card")
    const ul = el("ul", "card-list")

    for (const item of d.items || []) {
        const li = el("li")
        li.className = item.overdue ? "overdue" : ""

        const text = el("span", "", item.text)
        li.appendChild(text)
        li.appendChild(el("small", "muted", item.due || "no date"))
        ul.appendChild(li)

        if (item.actions && item.actions.length) {
            const wrap = el("li")
            wrap.appendChild(renderActions(item.actions))
            ul.appendChild(wrap)
        }
    }

    card.appendChild(ul)
    return card
}

function renderFocus(d) {
    const card = el("div", "card")
    card.appendChild(el("p", "card-line strong", `Focusing on: ${d.task}`))
    if (d.started_at) card.appendChild(el("p", "muted", `since ${String(d.started_at).slice(11, 16)}`))
    return card
}

function renderFocusSummary(d) {
    const card = el("div", "card")
    card.appendChild(el("p", "card-line strong", d.task))
    card.appendChild(el("p", "card-line", `Duration: ${d.duration}`))

    if (d.notes && d.notes.length) {
        const ul = el("ul", "card-list")
        for (const note of d.notes) ul.appendChild(el("li", "", `• ${note}`))
        card.appendChild(ul)
    }

    return card
}

function renderConfirm(d) {
    const card = el("div", "card")
    card.appendChild(el("p", "card-line strong", d.title || "Please confirm"))
    if (d.subtitle) card.appendChild(el("p", "muted", d.subtitle))
    return card
}

const RENDERERS = {
    briefing: renderBriefing,
    file_list: renderFileList,
    reminder_list: renderReminderList,
    focus: renderFocus,
    focus_summary: renderFocusSummary,
    confirm: renderConfirm,
}

function renderReply(reply) {
    const m = el("article", "msg assistant")
    const renderer = RENDERERS[reply.kind]

    m.appendChild(el("p", "bubble", reply.say || reply.response))

    if (renderer) {
        m.appendChild(renderer(reply.data || {}))
    } else if (reply.detail && !reply.needs_confirmation) {
        m.appendChild(el("p", "detail", reply.detail))
    }

    if (reply.actions && reply.actions.length) {
        m.appendChild(renderActions(reply.actions))
    }

    messagesEl.appendChild(m)
    scrollDown()
}

/* -------------------------SENDING---------------------------- */
function setBusy(value) {
    busy = value
    sendButton.disabled = value
    orb.dataset.busy = value ? "1" : "0"
    if (value) statusEl.textContent = "Contemplating…"
}

async function send(text, { echo = true} = {}) {
    const message = text.trim()
    if (!message || busy) return 

    setBusy(true)
    if (echo) addUser(message)
    const typing = addTyping()

    try {
        const reply = await api("/chat", { method: "POST", body: JSON.stringify({ message }) })
        typing.remove()
        renderReply(reply)
        setStatus("Connected")
    } catch (err) {
        typing.remove()
        addAssistantText(`Error: ${err.message}`)
        setStatus("Connection error", "offline")
    } finally {
        setBusy(false)
        refreshToday()
        input.focus()
    }
}

/* -------------------------TODAY DRAWER--------------------------- */
function renderFocusBlock(focus, goal) {
    const active = Boolean(focus && focus.active)

    focusLine.textContent = active
        ? `Focusing on: ${focus.task || "untitled task"}`
        : "Not focusing."
    focusStart.hidden = active
    focusStop.hidden = !active
    noteForm.hidden = !active

    if (goal && goal.goal) {
        const hasProgress = typeof goal.progress === "number"
        goalLine.hidden = false
        goalLine.textContent = hasProgress
            ? `Goal: ${goal.goal} · today ${goal.today_focus} (${goal.progress}%)`
            : `Goal: ${goal.goal}`
        goalProgress.hidden = !hasProgress
        if (hasProgress) goalFill.style.width = `${Math.max(0, Math.min(100, goal.progress))}%`
    } else {
        goalLine.hidden = true
        goalProgress.hidden = true
    }
}

function renderReminderBlock(reminders) {
    reminderListEl.replaceChildren()

    if (!reminders.length) {
        reminderListEl.appendChild(el("li", "muted", "Nothing waiting on you."))
        return
    }

    for (const r of reminders) {
        const li = el("li", r.overdue ? "rem-item overdue" : "rem-item")
        const main = el("div", "rem-main")
        main.appendChild(el("span", "rem-text", r.text))
        main.appendChild(el("small", "muted", r.due ? `Due ${r.due}` : "No due date"))

        const done = el("button", "btn primary", "Done")
        done.type = "button"
        done.addEventListener("click", async () => {
            done.disabled = true
            try {
                await api(`/reminders/${r.position}/complete`, { method: "POST" })
            } catch (err) {
                addAssistantText(`I could not complete that reminder: ${err.message}`)
            }
            refreshToday()
        })

        li.append(main, done)
        reminderListEl.appendChild(li)
    }
}

function chip(label, command) {
    const b = el("button", "chip", label)
    b.type = "button"
    b.addEventListener("click", () => send(command))
    return b
}

function renderLaunchBlock(apps, websites) {
    launchChips.replaceChildren()

    for (const a of apps) launchChips.appendChild(chip(a.name, `open ${a.name}`))
    for (const w of websites) launchChips.appendChild(chip(`🌐 ${w.name}`, `open website ${w.name}`))

    launchBlock.hidden = launchChips.children.length === 0
}

function renderToday(t) {
    const reminders = t.reminders || []
    const overdue = reminders.filter((r) => r.overdue).length
    const active = Boolean(t.focus && t.focus.active)

    const parts = [`${reminders.length} reminder${reminders.length === 1 ? "" : "s"}`]
    if (overdue) parts.push(`${overdue} overdue`)
    parts.push(active ? "focusing" : "idle")
    todaySummary.textContent = parts.join(" . ")

    orb.dataset.state = active ? "focus" : overdue ? "alert" : "idle"

    renderFocusBlock(t.focus, t.goal)
    renderReminderBlock(reminders)
    renderLaunchBlock(t.apps || [], t.websites || [])
}

async function refreshToday() {
    try {
        renderToday(await api("/today"))
        if (!busy) setStatus("Connected")
    } catch (_) {
        setStatus("Connection error", "offline")
    }
}


/* --------------------------------HISTORY + PUSH EVENTS--------------------------------- */
async function loadHistory() {
    try {
        const data = await api("/conversation?limit=10")
        const turns = data.turns || []

        if (!turns.length) {
            addAssistantText("Hi! What can i help you with?")
            return
        }

        for (const turn of turns) {
            addUser(turn.user)
            if (turn.assistant) addAssistantText(turn.assistant)
        }

        const last = turns[turns.length - 1]

        if (last.assistant && last.assistant.toLowerCase().includes("reply yes")) {
            messagesEl.lastElementChild.appendChild(renderActions(CONFIRM_ACTIONS))
        }
    } catch (_) {
        addAssistantText("I could not load our recent conversation.")
    }
}

function connectEvents() {
    const source = new EventSource("/events")

    source.addEventListener("notify", (event) => {
        const data = JSON.parse(event.data)
        addAssistantText(data.text).classList.add("notice")
        refreshToday()
    })

    source.addEventListener("reminders_changed", refreshToday)
    source.addEventListener("today_changed", refreshToday)
}


/* -----------------------------WIRING----------------------------- */
form.addEventListener("submit", (event) => {
    event.preventDefault()

    const text = input.value.trim()
    if (!text || busy) return

    sent.push(text)
    sentIndex = sent.length
    input.value = ""
    resizeComposer()
    send(text)
})

function recall(step) {
    const next = sentIndex + step
    if (!sent.length || next < 0 || next > sent.length) return false

    sentIndex = next
    input.value = sent[sentIndex] || ""
    resizeComposer()
    return true
}

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault()
        form.requestSubmit()
    } else if (event.key === "ArrowUp" && (input.value === "" || input.value === sent[sentIndex])) {
        if (recall(-1)) event.preventDefault()
    } else if (event.key === "ArrowDown" && input.value === sent[sentIndex]) {
        if (recall(1)) event.preventDefault()
    }
})

input.addEventListener("input", resizeComposer)

todayToggle.addEventListener("click", () => {
    const opening = todayPanel.hidden
    todayPanel.hidden = !opening
    todayToggle.setAttribute("aria-expanded", String(opening))
})

focusStart.addEventListener("click", () => send("start focus"))
focusStop.addEventListener("click", () => send("stop focus"))

noteForm.addEventListener("submit", (event) => {
    event.preventDefault()
    const note = noteInput.value.trim()
    if (!note) return
    noteInput.value = ""
    send(`focus note ${note}`)
})

reminderForm.addEventListener("submit", async (event) => {
    event.preventDefault()

    const text = reminderText.value.trim()
    if(!text) return

    try {
        await api("/reminders", {
            method: "POST",
            body: JSON.stringify({ text, due: reminderDue.value || null }),
        })
        reminderText.value = ""
        reminderDue.value = ""
        refreshToday()
    } catch (err) {
        addAssistantText(`I could not add that reminder: ${err.message}`)
    }
})

document.querySelectorAll("[data-cmd]").forEach((button) => {
    button.addEventListener("click", () => send(button.dataset.cmd))
})

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && window.pywebview) window.pywebview.api.hide()
})

window.addEventListener("focus", refreshToday)
document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshToday() })

async function init() {
    resizeComposer()
    await refreshToday()
    await loadHistory()
    connectEvents()
    input.focus()
}

init()
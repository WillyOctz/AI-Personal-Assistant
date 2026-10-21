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
const focusSessionList = document.getElementById("focus-session-list")
const focusStatus = document.getElementById("focus-status")
const focusTask = document.getElementById("focus-task")
const focusNoteCount = document.getElementById("focus-note-count")
const startFocusButton = document.getElementById("start-focus-button")
const stopFocusButton = document.getElementById("stop-focus-button")
const focusNoteForm = document.getElementById("focus-note-form")
const focusNoteInput = document.getElementById("focus-note-input")
const addFocusNoteButton = document.getElementById("add-focus-note-button")
const focusGoalText = document.getElementById("focus-goal-text")
const focusProgressTrack = document.getElementById("focus-progress-track")
const focusProgressFill = document.getElementById("focus-progress-fill")
const focusGoalMeta = document.getElementById("focus-goal-meta")
const appList = document.getElementById("app-list")
const appCount = document.getElementById("app-count")
const websiteList = document.getElementById("website-list")
const websiteCount = document.getElementById("website-count")
const profileFactList = document.getElementById("profile-fact-list")
const automationStatusList = document.getElementById("automation-status-list")
const runLLMEvaluationButton = document.getElementById(
    "run-llm-evaluation-button"
)
const llmEvaluationStatus = document.getElementById(
    "llm-evaluation-status"
)
const llmEvaluationFailures = document.getElementById(
    "llm-evaluation-failures"
)
const llmStatusList = document.getElementById("llm-status-list")
const feedbackSourceList = document.getElementById(
    "feedback-source-list"
)
const feedbackCandidateList = document.getElementById("feedback-candidate-list")
let isPollingReminderNotifications = false
const feedbackCandidateStatus = document.getElementById(
    "feedback-candidate-status"
)
const enableBrowserNotificationsButton = document.getElementById(
    "enable-browser-notifications-button"
)
const browserNotificationStatus = document.getElementById(
    "browser-notification-status"
)

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

function resizeComposer() {
    input.style.height = "auto"
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`
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

async function runFocusCommand(command) {
    addMessage("user", command)
    confirmationActions.hidden = true

    setChatBusy(true)
    startFocusButton.disabled = true
    stopFocusButton.disabled = true
    status.textContent = "Contemplating..."

    try {
        const response = await sendMessage(command)

        addMessage("assistant", response)
        confirmationActions.hidden = !needsConfirmation(response)

        await loadReminders()
        await loadFocusStatus()
        await loadFocusGoalProgress()
        await loadFocusSessions()

        status.textContent = "Connected"
    } catch (err) {
        addMessage("assistant", `Error: ${err.message}`)
        await loadFocusStatus()
        status.textContent = "Connection error"
    } finally {
        setChatBusy(false)
    }
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

function formatProfileKey(key) {
    return key.replaceAll("_", " ")
}

function renderProfile(facts) {
    profileFactList.replaceChildren()

    const entries = Object.entries(facts).sort(
        ([firstKey], [secondKey]) => firstKey.localeCompare(secondKey)
    )

    if (entries.length === 0) {
        const empty = document.createElement("p")
        empty.classList.add("profile-empty")
        empty.textContent = "No profile facts saved."
        profileFactList.appendChild(empty)
        return
    }

    for (const [key, value] of entries) {
        const row = document.createElement("div")
        const label = document.createElement("dt")
        const detail = document.createElement("dd")

        row.classList.add("profile-fact")
        label.classList.add("profile-key")
        detail.classList.add("profile-value")

        label.textContent = formatProfileKey(key)
        detail.textContent = value

        row.append(label, detail)
        profileFactList.appendChild(row)
    }
}

async function loadProfile() {
    try {
        const res = await fetch("/profile")

        if (!res.ok) {
            throw new Error("Profile request failed.")
        }

        const data = await res.json()

        if (!data.facts || typeof data.facts !== "object") {
            throw new Error("Invalid profile response.")
        }

        renderProfile(data.facts)
    } catch (err) {
        profileFactList.replaceChildren()

        const unavailable = document.createElement("p")
        unavailable.classList.add("profile-empty")
        unavailable.textContent = "Profile is unavailable."
        profileFactList.appendChild(unavailable)
    }
}

function addAutomationStatusRow(labelText, valueText) {
    const row = document.createElement("div")
    const label = document.createElement("dt")
    const value = document.createElement("dd")

    row.classList.add("automation-status-row")
    label.classList.add("automation-status-label")
    value.classList.add("automation-status-value")

    label.textContent = labelText
    value.textContent = valueText

    row.append(label, value)
    automationStatusList.appendChild(row)
}

function renderAutomationStatus(statusData) {
    automationStatusList.replaceChildren()

    const apps = statusData.apps
    const websites = statusData.websites

    addAutomationStatusRow(
        "Apps",
        `${apps.launching_enabled ? "Enabled" : "Disabled"} | ` +
        `${apps.allowed_apps}/${apps.registered_apps} allowed | ` +
        `${apps.confirmation_enabled ? "confirmation on" : "confirmation off"}`
    )

    addAutomationStatusRow(
        "Websites",
        `${websites.opening_enabled ? "Enabled" : "Disabled"} | ` +
        `${websites.allowed_websites}/${websites.registered_websites} allowed`
    )

    if (websites.pending_website) {
        addAutomationStatusRow(
            "Pending Website",
            websites.pending_website
        )
    }
}

async function loadAutomationStatus() {
    try {
        const response = await fetch("/automation/status")

        if (!response.ok) {
            throw new Error("Could not load automation status.")
        }

        const data = await response.json()

        if (!data.apps || !data.websites) {
            throw new Error("Automation status response is incomplete.")
        }

        renderAutomationStatus(data)
    } catch (err) {
        automationStatusList.replaceChildren()

        const message = document.createElement("p")
        message.classList.add("automation-status-empty")
        message.textContent = "Automation status unavailable."

        automationStatusList.appendChild(message)
    }
}

function renderWebsites(websites) {
    websiteList.replaceChildren()
    websiteCount.textContent = String(websites.length)

    if (websites.length === 0) {
        const empty = document.createElement("p")
        empty.classList.add("website-empty")
        empty.textContent = "No registered websites."
        websiteList.appendChild(empty)
        return
    }

    for (const website of websites) {
        const item = document.createElement("li")
        const name = document.createElement("p")
        const url = document.createElement("p")
        const permission = document.createElement("p")
        const openButton = document.createElement("button")

        item.classList.add("website-item")
        name.classList.add("website-name")
        url.classList.add("website-url")
        permission.classList.add("website-permission")
        openButton.classList.add("open-website-button")

        name.textContent = website.name
        url.textContent = website.url
        permission.textContent = website.allowed ? "Opening allowed" : "Opening not allowed"

        openButton.type = "button"
        openButton.textContent = "Open"
        openButton.disabled = !website.allowed
        openButton.title = website.allowed
            ? `Ask Nebula to open ${website.name}`
            : "This website is not allowed for opening"

        openButton.addEventListener("click", () => {
            input.value = `open website ${website.name}`
            form.requestSubmit()
        })

        item.append(name, url, permission, openButton)
        websiteList.appendChild(item)
    }
}

async function loadWebsites() {
    try {
        const res = await fetch("/websites")

        if (!res.ok) {
            throw new Error("Website registry request failed.")
        }

        const data = await res.json()

        if (!Array.isArray(data.websites)) {
            throw new Error("Invalid website registry response.")
        }

        renderWebsites(data.websites)
    } catch (err) {
        websiteList.replaceChildren()
        websiteCount.textContent = "-"

        const unavailable = document.createElement("p")
        unavailable.classList.add("website-empty")
        unavailable.textContent = "Registered websites are unavailable."
        websiteList.appendChild(unavailable)
    }
}

function renderFocusStatus(focus) {
    focusStatus.classList.toggle("is-active", focus.active)
    focusStatus.textContent = focus.active ? "Active" : "Idle"

    startFocusButton.disabled = focus.active
    stopFocusButton.disabled = !focus.active

    focusTask.hidden = !focus.active
    focusNoteCount.hidden = !focus.active

    focusNoteForm.hidden = !focus.active

    if (!focus.active) {
        focusTask.textContent = ""
        focusNoteCount.textContent = ""
        focusNoteInput.value = ""
        return
    }

    focusTask.textContent = focus.task || "Untitled focus task"

    const noteCount = Array.isArray(focus.notes) ? focus.notes.length : 0

    focusNoteCount.textContent = `Current notes: ${noteCount}`
}

function renderApps(apps) {
    appList.replaceChildren()
    appCount.textContent = String(apps.length)

    if (apps.length === 0) {
        const empty = document.createElement("p")
        empty.classList.add("app-empty")
        empty.textContent = "No registered apps."
        appList.appendChild(empty)
        return
    }

    for (const app of apps) {
        const item = document.createElement("li")
        const name = document.createElement("p")
        const permission = document.createElement("p")
        const openButton = document.createElement("button")

        item.classList.add("app-item")
        name.classList.add("app-name")
        permission.classList.add("app-permission")
        openButton.classList.add("open-app-button")
        openButton.type = "button"
        openButton.textContent = "Open"
        openButton.disabled = !app.allowed
        openButton.title = app.allowed ? `Ask Nebula to open ${app.name}` : "This app is not allowed for launching"

        name.textContent = app.name
        permission.textContent = app.allowed ? "Launch allowed" : "Launch not allowed"
        openButton.addEventListener("click", () => {
            input.value = `open ${app.name}`
            form.requestSubmit()
        })

        item.append(name, permission, openButton)
        appList.appendChild(item)
    }
}

async function loadApps() {
    try {
        const res = await fetch("/apps")

        if (!res.ok) {
            throw new Error("App registry request failed.")
        }

        const data = await res.json()

        if (!Array.isArray(data.apps)) {
            throw new Error("Invalid app registry response.")
        }

        renderApps(data.apps)
    } catch (err) {
        appList.replaceChildren()
        appCount.textContent = "-"

        const unavailable = document.createElement("p")
        unavailable.classList.add("app-empty")
        unavailable.textContent = "Registered apps are unavailable."
        appList.appendChild(unavailable)
    }
}

async function loadFocusStatus() {
    try {
        const res = await fetch("/focus/status")

        if (!res.ok) {
            throw new Error("Focus status request failed.")
        }

        const data = await res.json()

        if (typeof data.active !== "boolean") {
            throw new Error("Invalid focus status response.")
        }

        renderFocusStatus(data)
    } catch (err) {
        focusStatus.classList.remove("is-active")
        focusStatus.textContent = "Unavailable"
        focusTask.hidden = true
        focusNoteCount.hidden = true
        startFocusButton.disabled = true
        stopFocusButton.disabled = true
        focusNoteForm.hidden = true
    }
}

function renderFocusGoalProgress(goalProgress) {
    const { goal, progress, today_focus: todayFocus } = goalProgress

    if (!goal) {
        focusGoalText.textContent = "No focus goal set."
        focusGoalMeta.textContent = ""
        focusProgressTrack.hidden = true
        return
    }

    focusGoalText.textContent = `Goal: ${goal}`

    if (
        typeof progress !== "number"
        || typeof todayFocus !== "string" 
    ) {
        focusGoalMeta.textContent =
            "Use a duration goal, such as 30 minutes."
        focusProgressTrack.hidden = true
        return
    }

    const safeProgress = Math.max(0, Math.min(progress, 100))

    focusProgressTrack.hidden = false
    focusProgressFill.style.width = `${safeProgress}%`
    focusProgressFill.setAttribute("aria-valuenow", String(safeProgress))
    focusGoalMeta.textContent =
        `Today: ${todayFocus} (${safeProgress}%)`
}

async function loadFocusGoalProgress() {
    try {
        const res = await fetch("/focus/goal-progress")

        if (!res.ok) {
            throw new Error("Focus goal request failed.")
        }

        const data = await res.json()
        renderFocusGoalProgress(data)
    } catch (err) {
        focusGoalText.textContent = "Focus goal is unavailable."
        focusGoalMeta.textContent = ""
        focusProgressTrack.hidden = true
    }
}

function renderFocusSessions(sessions) {
    focusSessionList.replaceChildren()

    if (sessions.length === 0) {
        const empty = document.createElement("p")
        empty.classList.add("focus-session-empty")
        empty.textContent = "No completed focus sessions yet."
        focusSessionList.appendChild(empty)
        return
    }

    for (const session of sessions) {
        const item = document.createElement("li")
        const task = document.createElement("p")
        const duration = document.createElement("p")
        const notes = document.createElement("p")

        item.classList.add("focus-session-item")
        task.classList.add("focus-session-task")
        duration.classList.add("focus-session-meta")
        notes.classList.add("focus-session-meta")

        task.textContent = session.task
        duration.textContent = `Duration: ${session.duration}`

        const noteCount = Array.isArray(session.notes) ? session.notes.length : 0
        notes.textContent = `Notes: ${noteCount}`

        item.append(task, duration, notes)
        focusSessionList.appendChild(item)

    }
}

async function loadFocusSessions() {
    try {
        const res = await fetch("/focus/sessions?limit=5")

        if (!res.ok) {
            throw new Error("Focus session request failed.")
        }

        const data = await res.json()

        if (!Array.isArray(data.sessions)) {
            throw new Error("Invalid focus session response.")
        }

        renderFocusSessions(data.sessions)
    } catch (err) {
        focusSessionList.replaceChildren()

        const unavailable = document.createElement("p")
        unavailable.classList.add("focus-session-empty")
        unavailable.textContent = "Focus sessions are unavailable."
        focusSessionList.appendChild(unavailable)
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

function formatReminderNotification(data) {
    const lines = [`Reminder notification: ${data.today}`]

    if (data.overdue.length > 0) {
        lines.push("", "Overdue:")

        for (const reminder of data.overdue) {
            lines.push(
                `- ${reminder.index}. ${reminder.text} | ` +
                `due: ${reminder.due}`
            )
        }
    }

    if (data.due.length > 0) {
        lines.push("", "Due today:")

        for (const reminder of data.due) {
            lines.push(
                `- ${reminder.index}. ${reminder.text} | ` +
                `due: ${reminder.due}`
            )
        }
    }

    return lines.join("\n")
}

function updateBrowserNotificationStatus() {
    if (!("Notification" in window)) {
        enableBrowserNotificationsButton.disabled = true
        browserNotificationStatus.textContent = 
            "Browser notifications are unavailable."
        return
    }

    if (Notification.permission === "granted") {
        enableBrowserNotificationsButton.disabled = true
        browserNotificationStatus.textContent = 
            "Browser notifications are enabled."
        return
    }

    if (Notification.permission === "denied") {
        enableBrowserNotificationsButton.disabled = true
        browserNotificationStatus.textContent =
            "Browser notifications were blocked."
        return
    }

    enableBrowserNotificationsButton.disabled = false
    browserNotificationStatus.textContent = 
        "Browser notifications are not enabled."
}

async function enableBrowserNotifications() {
    if (!("Notification" in window)) {
        updateBrowserNotificationStatus()
        return
    }

    enableBrowserNotificationsButton.disabled = true
    
    try {
        await Notification.requestPermission()
    } finally {
        updateBrowserNotificationStatus()
    }
}

function showBrowserReminderNotification(data) {
    if (
       !("Notification" in window) ||
        Notification.permission !== "granted" 
    ) {
        return
    }

    const reminders = [...data.overdue, ...data.due]

    if (reminders.length === 0) {
        return
    }

    const body = reminders.map((reminder) => `${reminder.text} (${reminder.due})`)
        .join("\n")

    new Notification("Nebula reminder", {
        body: body,
    })
}

async function pollReminderNotifications() {
    if (isPollingReminderNotifications) {
        return
    }

    isPollingReminderNotifications = true

    try {
        const res = await fetch("/notifications/pending", {
            method: "POST",
        })

        if (!res.ok) {
            throw new Error("Reminder notification request failed.")
        }

        const data = await res.json()

        if (
            !Array.isArray(data.due) ||
            !Array.isArray(data.overdue)
        ) {
            throw new Error("Invalid reminder notification response.")
        }

        if (data.due.length === 0 && data.overdue.length === 0) {
            return
        }

        addMessage("assistant", formatReminderNotification(data))
        showBrowserReminderNotification(data)
        await loadReminders()
    } catch (err) {

    } finally {
        isPollingReminderNotifications = false
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

function addFeedbackSourceRow(labelText, valueText) {
    const row = document.createElement("div")
    const label = document.createElement("dt")
    const value = document.createElement("dd")

    row.classList.add("feedback-source-row")
    label.classList.add("feedback-source-label")
    value.classList.add("feedback-source-value")

    label.textContent = labelText
    value.textContent = valueText

    row.append(label, value)
    feedbackSourceList.appendChild(row)
}

function renderFeedbackSources(sources) {
    feedbackSourceList.replaceChildren()

    if (sources.length === 0) {
        const empty = document.createElement("p")
        empty.classList.add("feedback-source-empty")
        empty.textContent = "No response feedback yet."
        feedbackSourceList.appendChild(empty)
        return
    }

    for (const source of sources) {
        const helpfulPercent = Math.round(
            source.helpful_rate * 100
        )

        addFeedbackSourceRow(
            source.source,
            `${source.helpful}/${source.total} helpful ` +
            `(${helpfulPercent}%) | ` +
            `${source.not_helpful} not helpful`
        )
    }
}

async function loadFeedbackSources() {
    try {
        const res = await fetch("/feedback/response-sources")

        if (!res.ok) {
            throw new Error("Feedback source request failed.")
        }

        const data = await res.json()

        if (!Array.isArray(data.sources)) {
            throw new Error("Invalid feedback source response.")
        }

        renderFeedbackSources(data.sources)
    } catch (err) {
        feedbackSourceList.replaceChildren()

        const unavailable = document.createElement("p")
        unavailable.classList.add("feedback-source-empty")
        unavailable.textContent = "Response quality is unavailable."

        feedbackSourceList.appendChild(unavailable)
    }
}

async function saveFeedbackCandidate(
    candidateNumber,
    expectedCommand,
    commandPrefix,
) {
    const res = await fetch(
        `/feedback/llm-review-candidates/${candidateNumber}/save`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                expected_command: expectedCommand,
                command_prefix: commandPrefix,
            }),
        }
    )

    const data = await res.json()

    if (!res.ok) {
        throw new Error(data.detail || "Could not save evaluation case.")
    }

    return data
}

function renderFeedbackCandidates(candidates) {
    feedbackCandidateList.replaceChildren()

    if (candidates.length === 0) {
        const empty = document.createElement("p")
        empty.classList.add("feedback-candidate-empty")
        empty.textContent = "No LLM responses need review yet."
        feedbackCandidateList.appendChild(empty)
        return
    }

    for (const [index, candidate] of candidates.entries()) {
        const item = document.createElement("li")
        const meta = document.createElement("p")
        const prompt = document.createElement("p")
        const reply = document.createElement("p")

        item.classList.add("feedback-candidate-item")
        meta.classList.add("feedback-candidate-meta")
        prompt.classList.add("feedback-candidate-prompt")
        reply.classList.add("feedback-candidate-reply")

        meta.textContent =
            `${candidate.source} | ${candidate.intent} | ` +
            `${candidate.timestamp || "No timestamp"}`

        prompt.textContent = `User: ${candidate.user_input}`
        reply.textContent = `Reply: ${candidate.response_text}`

        const controls = document.createElement("div")
        const decision = document.createElement("select")
        const noCommandOption = document.createElement("option")
        const commandOption = document.createElement("option")
        const prefixInput = document.createElement("input")
        const saveButton = document.createElement("button")

        controls.classList.add("feedback-candidate-controls")
        decision.classList.add("feedback-candidate-decision")
        prefixInput.classList.add("feedback-candidate-prefix")
        saveButton.classList.add("feedback-candidate-save")

        noCommandOption.value = "no_command"
        noCommandOption.textContent = "No command"

        commandOption.value = "command"
        commandOption.textContent = "Command expected"

        decision.append(noCommandOption, commandOption)

        prefixInput.type = "text"
        prefixInput.placeholder = "Command prefix"
        prefixInput.setAttribute(
            "aria-label",
            "Expected command prefix"
        )
        prefixInput.hidden = true

        saveButton.type = "button"
        saveButton.textContent = "Save"

        decision.addEventListener("change", () => {
            const needsPrefix = decision.value === "command"


            prefixInput.hidden = !needsPrefix

            if (!needsPrefix) {
                prefixInput.value = ""
            }
        })

        saveButton.addEventListener("click", async () => {
            const expectedCommand = decision.value === "command"
            const commandPrefix = prefixInput.value.trim()

            if (expectedCommand && !commandPrefix) {
                feedbackCandidateStatus.textContent =
                    "A command case needs a command prefix."
                prefixInput.focus()
                return
            }

            saveButton.disabled = true
            feedbackCandidateStatus.textContent = "Saving review decision..."

            try {
                const result = await saveFeedbackCandidate(
                    index + 1,
                    expectedCommand,
                    commandPrefix,
                )

                feedbackCandidateStatus.textContent = result.message
                await loadFeedbackCandidates()
            } catch (err) {
                feedbackCandidateStatus.textContent = err.message
            } finally {
                saveButton.disabled = false
            }
        })

        controls.append(decision, prefixInput, saveButton)

        item.append(meta, prompt, reply, controls)
        feedbackCandidateList.appendChild(item)
    }
}

async function loadFeedbackCandidates() {
    try {
        const res = await fetch(
            "/feedback/llm-review-candidates?limit=5"
        )

        if (!res.ok) {
            throw new Error("Feedback candidate request failed.")
        }

        const data = await res.json()

        if (!Array.isArray(data.candidates)) {
            throw new Error("Invalid feedback candidate response.")
        }

        renderFeedbackCandidates(data.candidates)
    } catch (err) {
        feedbackCandidateList.replaceChildren()

        const unavailable = document.createElement("p")
        unavailable.classList.add("feedback-candidate-empty")
        unavailable.textContent = "Review candidates are unavailable."

        feedbackCandidateList.appendChild(unavailable)
    }
}

focusNoteForm.addEventListener("submit", async (event) => {
    event.preventDefault()

    const note = focusNoteInput.value.trim()

    if (!note) {
        return
    }

    addFocusNoteButton.disabled = true

    try {
        await runFocusCommand(`focus note ${note}`)
        focusNoteInput.value = ""
    } finally {
        addFocusNoteButton.disabled = false
    }
})

enableBrowserNotificationsButton.addEventListener("click", () => {
    enableBrowserNotifications()
})

startFocusButton.addEventListener("click", () => {
    runFocusCommand("start focus")
})

stopFocusButton.addEventListener("click", () => {
    runFocusCommand("stop focus")
})

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

function renderLLMEvaluation(evaluation) {
    const { total, passed, failed, results } = evaluation

    llmEvaluationStatus.textContent = 
        `${passed}/${total} cases passed. ${failed} failed.`

    llmEvaluationFailures.replaceChildren()

    const failures = results.filter((result) => !result.passed)

    if (failures.length === 0) {
        llmEvaluationFailures.hidden = true
        return
    }

    for (const failure of failures) {
        const item = document.createElement("li")
        const message = document.createElement("p")
        const reason = document.createElement("p")

        item.classList.add("llm-evaluation-failure")
        message.classList.add("llm-evaluation-failure-message")
        reason.classList.add("llm-evaluation-failure-reason")

        message.textContent = failure.message
        reason.textContent = failure.reason

        item.append(message, reason)
        llmEvaluationFailures.appendChild(item)
    }

    llmEvaluationFailures.hidden = false
}

async function runLLMEvaluation() {
    runLLMEvaluationButton.disabled = true
    llmEvaluationStatus.textContent = "Running evaluation..."
    llmEvaluationFailures.hidden = true
    status.textContent = "Evaluating..."

    try {
        const res = await fetch(
            "/evaluations/llm-command-proposals",
            {
                method: "POST",
            }
        )

        const data = await res.json()

        if (!res.ok) {
            throw new Error(
                data.detail || "LLM evaluation could not run."
            )
        }

        if (!Array.isArray(data.results)) {
            throw new Error("Invalid LLM evaluation response.")
        }

        renderLLMEvaluation(data)
        status.textContent = "Connected"
    } catch (err) {
        llmEvaluationStatus.textContent =
            `Evaluation unavailable: ${err.message}`
        llmEvaluationFailures.replaceChildren()
        llmEvaluationFailures.hidden = true
        status.textContent = "Connection error"
    } finally {
        runLLMEvaluationButton.disabled = false
    }
}

function addLLMStatusRow(labelText, valueText) {
    const row = document.createElement("div")
    const label = document.createElement("dt")
    const value = document.createElement("dd")

    row.classList.add("llm-status-row")
    label.classList.add("llm-status-label")
    value.classList.add("llm-status-value")

    label.textContent = labelText
    value.textContent = valueText

    row.append(label, value)
    llmStatusList.appendChild(row)
}

function renderLLMStatus(statusData) {
    llmStatusList.replaceChildren()

    addLLMStatusRow(
        "Gemini",
        statusData.gemini.configured
            ? `Configured | ${statusData.gemini.model}`
            : "Not configured"
    )

    addLLMStatusRow(
        "Groq",
        statusData.groq.configured
            ? `Configured | ${statusData.groq.model}`
            : "Not configured"
    )

    addLLMStatusRow(
        "Chat",
        statusData.chat_available ? "Available" : "Unavailable"
    )

    addLLMStatusRow(
        "Embeddings",
        statusData.embeddings_available ? "Available" : "Unavailable"
    )
}

async function loadLLMStatus() {
    try {
        const res = await fetch("/llm/status")

        if (!res.ok) {
            throw new Error("LLM status request failed.")
        }

        const data = await res.json()

        if (!data.gemini || !data.groq) {
            throw new Error("Invalid LLM status response.")
        }

        renderLLMStatus(data)
    } catch (err) {
        llmStatusList.replaceChildren()

        const unavailable = document.createElement("p")
        unavailable.classList.add("llm-status-empty")
        unavailable.textContent = "LLM status unavailable."

        llmStatusList.appendChild(unavailable)
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
    resizeComposer()
    input.focus()
    setChatBusy(true)
    status.textContent = "Contemplating..."

    try {
        const res = await sendMessage(message);
        addMessage("assistant", res)
        confirmationActions.hidden = !needsConfirmation(res)
        await loadReminders()
        await loadApps()
        await loadWebsites()
        await loadProfile()
        await loadAutomationStatus()
        await loadFocusStatus()
        await loadFocusGoalProgress()
        await loadFocusSessions()
        await loadLLMStatus()
        await loadFeedbackSources()
        await loadFeedbackCandidates()
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

input.addEventListener("input", resizeComposer)

runLLMEvaluationButton.addEventListener("click", () => {
    runLLMEvaluation()
})

confirmButton.addEventListener("click", () => {
    sendConfirmation("yes")
})

cancelButton.addEventListener("click", () => {
    sendConfirmation("no")
})

async function initializeChat() {
    updateBrowserNotificationStatus()

    await loadHealth()
    await loadConversation()
    await loadStartupMessage()
    await loadReminders()
    await loadApps()
    await loadWebsites()
    await loadProfile()
    await loadAutomationStatus()
    await loadFocusStatus()
    await loadFocusGoalProgress()
    await loadFocusSessions()
    await loadLLMStatus()
    await loadFeedbackSources()
    await loadFeedbackCandidates()
    window.setInterval(pollReminderNotifications, 60_000)
}

initializeChat()

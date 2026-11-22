
document.addEventListener("DOMContentLoaded", function () {

    // --------------------------------------------------
    // AUTO-DISMISS FLASH MESSAGES
    // --------------------------------------------------

    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(function (alert) {
        setTimeout(function () {
            if (typeof bootstrap !== "undefined") {
                const instance = bootstrap.Alert.getOrCreateInstance(alert);
                instance.close();
            } else {
                alert.remove();
            }
        }, 5000);
    });


    // --------------------------------------------------
    // CONFIRM BEFORE CANCELLING TOKENS
    // --------------------------------------------------

    const cancelForms = document.querySelectorAll(".cancel-form");

    cancelForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const confirmed = confirm(
                "Are you sure you want to cancel this token?"
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });


    // --------------------------------------------------
    // HELPER FUNCTIONS
    // --------------------------------------------------

    function createElement(tag, className, text) {
        const element = document.createElement(tag);

        if (className) {
            element.className = className;
        }

        if (text !== undefined && text !== null) {
            element.textContent = text;
        }

        return element;
    }

    function createActionForm(action, buttonText, buttonClass, confirmation) {
        const form = document.createElement("form");

        form.method = "POST";
        form.action = action;

        if (confirmation) {
            form.addEventListener("submit", function (event) {
                if (!confirm(confirmation)) {
                    event.preventDefault();
                }
            });
        }

        const button = createElement(
            "button",
            buttonClass,
            buttonText
        );

        button.type = "submit";
        form.appendChild(button);

        return form;
    }


    // --------------------------------------------------
    // ADMIN DASHBOARD LIVE UPDATES
    // --------------------------------------------------

    const adminDashboard = document.getElementById("admin-dashboard");

    if (adminDashboard) {

        const apiUrl = adminDashboard.dataset.apiUrl;

        const updateStatus = document.getElementById(
            "dashboard-update-status"
        );

        const counterContainer = document.getElementById(
            "counter-container"
        );

        const waitingQueueBody = document.getElementById(
            "waiting-queue-body"
        );

        const waitingQueueCount = document.getElementById(
            "waiting-queue-count"
        );

        const recentActivityBody = document.getElementById(
            "recent-activity-body"
        );


        // Update statistics

        function updateStatistics(stats) {
            document.getElementById("stat-total").textContent = stats.total;
            document.getElementById("stat-waiting").textContent = stats.waiting;
            document.getElementById("stat-serving").textContent = stats.serving;
            document.getElementById("stat-completed").textContent = stats.completed;
        }


        // Render active counters

        function renderCounters(counters) {

            counterContainer.replaceChildren();

            if (!counters.length) {
                const column = createElement("div", "col-12");
                const card = createElement("div", "custom-card text-center");

                const heading = createElement("h5", "mt-3", "No counters available");
                const message = createElement(
                    "p",
                    "text-muted",
                    "Create a service and add your first counter."
                );

                const link = createElement(
                    "a",
                    "btn btn-primary",
                    "Create Counter"
                );

                link.href = "/admin/services";

                card.append(heading, message, link);
                column.appendChild(card);
                counterContainer.appendChild(column);

                return;
            }

            counters.forEach(function (counter) {

                const column = createElement("div", "col-md-6 col-lg-4");
                const card = createElement("div", "dashboard-card h-100");

                const header = createElement(
                    "div",
                    "d-flex justify-content-between align-items-center mb-3"
                );

                const heading = createElement(
                    "h5",
                    "fw-bold mb-0",
                    counter.name
                );

                const activeBadge = createElement(
                    "span",
                    "badge bg-success",
                    "Active"
                );

                header.append(heading, activeBadge);

                const service = createElement(
                    "p",
                    "text-muted small mb-2",
                    "Service: " + counter.service_name
                );

                card.append(header, service, createElement("hr"));

                if (counter.serving_token_id !== null) {

                    card.appendChild(
                        createElement("p", "text-muted mb-1", "Currently Serving")
                    );

                    card.appendChild(
                        createElement(
                            "h2",
                            "text-primary fw-bold",
                            "#" + counter.serving_token_number
                        )
                    );

                    card.appendChild(
                        createElement(
                            "p",
                            "small text-muted",
                            "Customer: " + counter.customer_name
                        )
                    );

                    card.appendChild(
                        createActionForm(
                            "/admin/complete/" + counter.serving_token_id,
                            "Complete Token",
                            "btn btn-success w-100 mb-2"
                        )
                    );

                    card.appendChild(
                        createActionForm(
                            "/admin/skip/" + counter.serving_token_id,
                            "Skip Token",
                            "btn btn-outline-danger w-100",
                            "Skip this serving token?"
                        )
                    );

                } else {

                    const emptyArea = createElement(
                        "div",
                        "text-center py-3"
                    );

                    emptyArea.appendChild(
                        createElement(
                            "i",
                            "bi bi-inbox display-5 text-muted"
                        )
                    );

                    emptyArea.appendChild(
                        createElement(
                            "p",
                            "text-muted mt-2",
                            "No active token"
                        )
                    );

                    card.appendChild(emptyArea);

                    card.appendChild(
                        createActionForm(
                            "/admin/call-next/" + counter.id,
                            "Call Next Token",
                            "btn btn-primary w-100"
                        )
                    );
                }

                column.appendChild(card);
                counterContainer.appendChild(column);
            });
        }


        // Render waiting queue

        function renderWaitingQueue(tokens) {

            waitingQueueBody.replaceChildren();

            waitingQueueCount.textContent = tokens.length + " shown";

            if (!tokens.length) {
                const row = createElement("tr");
                const cell = createElement(
                    "td",
                    "text-center text-muted py-3",
                    "No waiting tokens."
                );

                cell.colSpan = 4;
                row.appendChild(cell);
                waitingQueueBody.appendChild(row);

                return;
            }

            tokens.forEach(function (token) {

                const row = createElement("tr");

                row.appendChild(
                    createElement(
                        "td",
                        "fw-bold text-primary",
                        "#" + token.token_number
                    )
                );

                row.appendChild(createElement("td", "", token.customer_name));
                row.appendChild(createElement("td", "", token.service_name));
                row.appendChild(createElement("td", "", token.created_at));

                waitingQueueBody.appendChild(row);
            });
        }


        // Render recent queue activity

        function renderRecentActivity(tokens) {

            recentActivityBody.replaceChildren();

            if (!tokens.length) {
                const row = createElement("tr");
                const cell = createElement(
                    "td",
                    "text-center text-muted py-4",
                    "No queue activity yet."
                );

                cell.colSpan = 7;
                row.appendChild(cell);
                recentActivityBody.appendChild(row);

                return;
            }

            tokens.forEach(function (token) {

                const row = createElement("tr");

                row.appendChild(
                    createElement(
                        "td",
                        "fw-bold text-primary",
                        "#" + token.token_number
                    )
                );

                row.appendChild(createElement("td", "", token.customer_name));
                row.appendChild(createElement("td", "", token.service_name));
                row.appendChild(createElement("td", "", token.counter_name));
                row.appendChild(createElement("td", "", token.created_at));

                const statusCell = createElement("td");
                let badgeClass = "badge bg-secondary";

                if (token.status === "Waiting") {
                    badgeClass = "badge bg-warning text-dark";
                } else if (token.status === "Serving") {
                    badgeClass = "badge bg-primary";
                } else if (token.status === "Completed") {
                    badgeClass = "badge bg-success";
                }

                statusCell.appendChild(
                    createElement("span", badgeClass, token.status)
                );

                row.appendChild(statusCell);

                const actionCell = createElement("td");

                if (
                    token.status === "Waiting" ||
                    token.status === "Serving"
                ) {
                    actionCell.appendChild(
                        createActionForm(
                            "/admin/skip/" + token.id,
                            "Skip",
                            "btn btn-sm btn-outline-danger",
                            "Cancel this token?"
                        )
                    );
                } else {
                    actionCell.appendChild(
                        createElement("span", "text-muted small", "-")
                    );
                }

                row.appendChild(actionCell);
                recentActivityBody.appendChild(row);
            });
        }


        // Fetch latest dashboard data

        let adminPollingInProgress = false;

        async function refreshAdminDashboard() {

            if (adminPollingInProgress) {
                return;
            }

            adminPollingInProgress = true;

            try {

                const response = await fetch(apiUrl, {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    },
                    cache: "no-store"
                });

                if (!response.ok) {
                    throw new Error("Server error: " + response.status);
                }

                const data = await response.json();

                updateStatistics(data.stats);
                renderCounters(data.counters);
                renderWaitingQueue(data.waiting_queue);
                renderRecentActivity(data.recent_activity);

                if (updateStatus) {
                    updateStatus.textContent =
                        "Live updates enabled. Last checked just now.";
                }

            } catch (error) {

                console.error("Admin dashboard update failed:", error);

                if (updateStatus) {
                    updateStatus.textContent =
                        "Unable to refresh dashboard. Retrying automatically...";
                }

            } finally {
                adminPollingInProgress = false;
            }
        }

        // Update immediately and every five seconds

        refreshAdminDashboard();
        setInterval(refreshAdminDashboard, 5000);
    }


    // --------------------------------------------------
    // USER TOKEN DETAILS LIVE UPDATES
    // --------------------------------------------------

    const tokenPage = document.getElementById("live-token-page");

    if (tokenPage) {

        const tokenId = tokenPage.dataset.tokenId;

        const statusElement = document.getElementById("token-status");
        const peopleAheadElement = document.getElementById("people-ahead");
        const estimatedWaitElement = document.getElementById("estimated-wait");
        const currentServingElement = document.getElementById("current-serving");
        const counterElement = document.getElementById("token-counter");
        const cancelForm = document.getElementById("cancel-token-form");
        const updateNote = document.getElementById("live-update-note");

        const statusStyles = {
            Waiting: {
                text: "Waiting",
                classes: "status-badge bg-warning text-dark"
            },
            Serving: {
                text: "Now Serving You",
                classes: "status-badge bg-primary text-white"
            },
            Completed: {
                text: "Completed",
                classes: "status-badge bg-success text-white"
            },
            Cancelled: {
                text: "Cancelled",
                classes: "status-badge bg-secondary text-white"
            }
        };

        let pollingStopped = false;
        let tokenPollingInProgress = false;
        let pollingTimer;

        async function refreshTokenStatus() {

            if (pollingStopped || tokenPollingInProgress) {
                return;
            }

            tokenPollingInProgress = true;

            try {

                const response = await fetch(
                    `/api/token/${encodeURIComponent(tokenId)}`,
                    {
                        method: "GET",
                        headers: {
                            "Accept": "application/json"
                        },
                        cache: "no-store"
                    }
                );

                if (!response.ok) {
                    throw new Error("Server error: " + response.status);
                }

                const data = await response.json();
                const statusInfo = statusStyles[data.status];

                if (!statusInfo) {
                    throw new Error("Unknown token status received.");
                }

                statusElement.textContent = statusInfo.text;
                statusElement.className = statusInfo.classes;

                if (peopleAheadElement) {
                    peopleAheadElement.textContent =
                        data.status === "Waiting" ? data.waiting_ahead : 0;
                }

                if (estimatedWaitElement) {
                    estimatedWaitElement.textContent =
                        data.status === "Waiting" ? data.estimated_wait : 0;
                }

                if (currentServingElement) {
                    currentServingElement.textContent =
                        data.current_serving !== null
                            ? "#" + data.current_serving
                            : "No token currently serving";
                }

                if (counterElement) {
                    counterElement.textContent =
                        data.counter_name || "Not assigned yet";
                }

                if (cancelForm) {
                    cancelForm.hidden = data.status !== "Waiting";
                }

                if (updateNote) {
                    updateNote.textContent =
                        "Live updates enabled. Last checked just now.";
                }

                if (
                    data.status === "Completed" ||
                    data.status === "Cancelled"
                ) {

                    pollingStopped = true;
                    clearInterval(pollingTimer);

                    if (updateNote) {
                        updateNote.textContent =
                            "Your token is " + data.status.toLowerCase() + ".";
                    }
                }

            } catch (error) {

                console.error("Live queue update failed:", error);

                if (updateNote) {
                    updateNote.textContent =
                        "Unable to refresh. Retrying automatically...";
                }

            } finally {
                tokenPollingInProgress = false;
            }
        }

        refreshTokenStatus();
        pollingTimer = setInterval(refreshTokenStatus, 5000);
    }

});

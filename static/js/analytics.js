const chartColors = [
    "#2563eb",
    "#7c3aed",
    "#0891b2",
    "#059669",
    "#d97706",
    "#dc2626",
    "#4f46e5",
    "#0d9488",
];

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
}

function formatCurrency(value) {
    return `$${Number(value).toFixed(2)}`;
}

document.addEventListener("DOMContentLoaded", async function () {
    const departmentCanvas = document.getElementById("departmentChart");
    const categoryCanvas = document.getElementById("categoryChart");
    const trendCanvas = document.getElementById("trendChart");

    if (!departmentCanvas || !categoryCanvas || !trendCanvas) {
        return;
    }

    try {
        const [summary, departments, categories, trend] = await Promise.all([
            fetchJson("/admin/api/analytics/summary"),
            fetchJson("/admin/api/analytics/by-department"),
            fetchJson("/admin/api/analytics/by-category"),
            fetchJson("/admin/api/analytics/trend"),
        ]);

        const currentEl = document.getElementById("currentMonthTotal");
        const previousEl = document.getElementById("previousMonthTotal");
        if (currentEl) currentEl.textContent = formatCurrency(summary.current_month);
        if (previousEl) previousEl.textContent = formatCurrency(summary.previous_month);

        if (!Array.isArray(departments) || departments.length === 0) {
            departmentCanvas.parentElement.innerHTML = "<p class=\"text-muted mb-0\">No approved department data yet.</p>";
        } else {
        new Chart(departmentCanvas, {
            type: "bar",
            data: {
                labels: departments.map((item) => item.department),
                datasets: [{
                    label: "Approved Expenses",
                    data: departments.map((item) => item.total),
                    backgroundColor: chartColors[0],
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => formatCurrency(ctx.raw),
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => `$${value}`,
                        },
                    },
                },
            },
        });
        }

        if (!Array.isArray(categories) || categories.length === 0) {
            categoryCanvas.parentElement.innerHTML = "<p class=\"text-muted mb-0\">No approved category data yet.</p>";
        } else {
        new Chart(categoryCanvas, {
            type: "pie",
            data: {
                labels: categories.map((item) => item.category),
                datasets: [{
                    data: categories.map((item) => item.total),
                    backgroundColor: chartColors,
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.label}: ${formatCurrency(ctx.raw)}`,
                        },
                    },
                },
            },
        });
        }

        if (!Array.isArray(trend) || trend.length === 0) {
            trendCanvas.parentElement.innerHTML = "<p class=\"text-muted mb-0\">No approved trend data yet.</p>";
        } else {
        new Chart(trendCanvas, {
            type: "line",
            data: {
                labels: trend.map((item) => item.month),
                datasets: [{
                    label: "Monthly Approved Expenses",
                    data: trend.map((item) => item.total),
                    borderColor: chartColors[0],
                    backgroundColor: "rgba(37, 99, 235, 0.15)",
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (ctx) => formatCurrency(ctx.raw),
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => `$${value}`,
                        },
                    },
                },
            },
        });
        }
    } catch (error) {
        console.error("Failed to load analytics charts:", error);
    }
});

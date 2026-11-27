let rawData = null;
let roleChart = null;
let memberChart = null;
let weekChart = null;

const plannedHoursForWeek = (roleCfg, weekNum) => {
    if (!weekNum || weekNum < 1) return 0;
    const blockIdx = Math.min(Math.floor((weekNum - 1) / 4), roleCfg.weekly_plan_by_block.length - 1);
    return roleCfg.weekly_plan_by_block[blockIdx];
};

const populateFilters = (entries) => {
    const sprintSel = document.getElementById("sprint-filter");
    const weekSel = document.getElementById("week-filter");

    const sprints = [...new Set(entries.map((e) => e.sprint))].sort();
    const weeks = [...new Set(entries.map((e) => e.week))].sort((a, b) => {
        const na = parseInt((a.match(/\d+/) || [999])[0], 10);
        const nb = parseInt((b.match(/\d+/) || [999])[0], 10);
        return na - nb;
    });

    sprintSel.innerHTML = `<option value="ALL">Tutti gli sprint</option>` +
        sprints.map((s) => `<option value="${s}">${s}</option>`).join("");
    weekSel.innerHTML = `<option value="ALL">Tutte le settimane</option>` +
        weeks.map((w) => `<option value="${w}">${w}</option>`).join("");
};

const render = () => {
    const sprintFilter = document.getElementById("sprint-filter").value;
    const weekFilter = document.getElementById("week-filter").value;
    const { roles, target_hours_per_member: targetMember, total_budget_eur: totalBudget } = rawData.budget;
    const roleKeys = Object.keys(roles);

    const filtered = rawData.entries.filter((e) =>
        (sprintFilter === "ALL" || e.sprint === sprintFilter) &&
        (weekFilter === "ALL" || e.week === weekFilter)
    );

    const activeWeekNums = [...new Set(filtered.map((e) => e.week_number).filter(Boolean))];
    const isFullProject = sprintFilter === "ALL" && weekFilter === "ALL";

    const plannedByRole = {};
    roleKeys.forEach((rk) => {
        plannedByRole[rk] = isFullProject
            ? roles[rk].total_hours
            : activeWeekNums.reduce((acc, wn) => acc + plannedHoursForWeek(roles[rk], wn), 0);
    });

    const actualByRole = {};
    const membersByRole = {};
    let unassignedHours = 0;

    roleKeys.forEach((rk) => {
        actualByRole[rk] = 0;
        membersByRole[rk] = {};
    });

    filtered.forEach((e) => {
        if (roles[e.role]) {
            actualByRole[e.role] += e.hours;
            membersByRole[e.role][e.member_name] = (membersByRole[e.role][e.member_name] || 0) + e.hours;
        } else {
            unassignedHours += e.hours;
        }
    });

    const totalPlannedHours = Object.values(plannedByRole).reduce((a, b) => a + b, 0);
    const totalActualHours = filtered.reduce((a, e) => a + e.hours, 0);
    const totalActualCost = roleKeys.reduce((acc, rk) => acc + actualByRole[rk] * roles[rk].hourly_rate, 0);
    const periodBudgetEur = roleKeys.reduce((acc, rk) => acc + plannedByRole[rk] * roles[rk].hourly_rate, 0);
    const memberCount = Object.keys(rawData.members).length || 7;

    document.getElementById("kpi-hours").textContent = `${totalActualHours.toFixed(1)} h`;
    document.getElementById("kpi-hours-sub").textContent =
        `su ${totalPlannedHours.toFixed(0)} h preventivate (${totalPlannedHours ? ((totalActualHours / totalPlannedHours) * 100).toFixed(1) : 0}%)`;

    document.getElementById("kpi-cost").textContent = `€ ${totalActualCost.toFixed(0)}`;
    document.getElementById("kpi-cost-sub").textContent =
        `su € ${(isFullProject ? totalBudget : periodBudgetEur).toFixed(0)} preventivati`;

    document.getElementById("kpi-avg").textContent = `${(totalActualHours / memberCount).toFixed(1)} h`;
    document.getElementById("kpi-avg-sub").textContent = `Target fine progetto: ${targetMember} h / membro`;

    document.getElementById("kpi-unassigned").textContent = `${unassignedHours.toFixed(1)} h`;

    document.getElementById("role-chart-desc").textContent = isFullProject
        ? "Confronto ore totali sull'intero progetto (20 settimane)"
        : `Preventivo scalato sulle ${activeWeekNums.length} settimane del filtro selezionato`;

    if (roleChart) roleChart.destroy();
    roleChart = new Chart(document.getElementById("roleChart"), {
        type: "bar",
        data: {
            labels: roleKeys.map((rk) => roles[rk].label),
            datasets: [
                {
                    label: "Preventivo (h)",
                    data: roleKeys.map((rk) => plannedByRole[rk]),
                    backgroundColor: "rgba(93, 58, 155, 0.25)",
                    borderColor: "#5d3a9b",
                    borderWidth: 1.5
                },
                {
                    label: "Consuntivo (h)",
                    data: roleKeys.map((rk) => Number(actualByRole[rk].toFixed(2))),
                    backgroundColor: "#5d3a9b"
                }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
    });

    const allMembers = [...new Set([
        ...Object.values(rawData.members),
        ...filtered.map((e) => e.member_name)
    ])].sort();

    const roleDatasets = [
        ...roleKeys.map((rk) => ({
            label: roles[rk].label,
            backgroundColor: roles[rk].color,
            data: allMembers.map((m) =>
                Number(filtered.filter((e) => e.member_name === m && e.role === rk).reduce((s, e) => s + e.hours, 0).toFixed(2))
            )
        })),
        ...(unassignedHours > 0 ? [{
            label: "Senza ruolo",
            backgroundColor: "#94a3b8",
            data: allMembers.map((m) =>
                Number(filtered.filter((e) => e.member_name === m && !roles[e.role]).reduce((s, e) => s + e.hours, 0).toFixed(2))
            )
        }] : [])
    ];

    if (memberChart) memberChart.destroy();
    memberChart = new Chart(document.getElementById("memberChart"), {
        type: "bar",
        data: { labels: allMembers, datasets: roleDatasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
        }
    });

    const maxWeek = Math.max(4, ...rawData.entries.map((e) => e.week_number || 0));
    const weekNums = Array.from({ length: maxWeek }, (_, i) => i + 1);
    const weekActuals = weekNums.map((wn) =>
        Number(rawData.entries.filter((e) => e.week_number === wn && (sprintFilter === "ALL" || e.sprint === sprintFilter)).reduce((s, e) => s + e.hours, 0).toFixed(2))
    );
    const weekPlans = weekNums.map((wn) =>
        roleKeys.reduce((acc, rk) => acc + plannedHoursForWeek(roles[rk], wn), 0)
    );

    if (weekChart) weekChart.destroy();
    weekChart = new Chart(document.getElementById("weekChart"), {
        type: "bar",
        data: {
            labels: weekNums.map((wn) => `Settimana ${wn}`),
            datasets: [
                {
                    type: "line",
                    label: "Preventivo settimanale (h)",
                    data: weekPlans,
                    borderColor: "#dc2626",
                    backgroundColor: "#dc2626",
                    borderDash: [6, 4],
                    tension: 0.2
                },
                {
                    type: "bar",
                    label: "Ore rendicontate (h)",
                    data: weekActuals,
                    backgroundColor: "#5d3a9b"
                }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
    });

    const tbody = document.getElementById("role-table-body");
    tbody.innerHTML = roleKeys.map((rk) => {
        const cfg = roles[rk];
        const planned = plannedByRole[rk];
        const actual = actualByRole[rk];
        const remaining = planned - actual;
        const cost = actual * cfg.hourly_rate;
        const membersList = Object.entries(membersByRole[rk])
            .map(([name, h]) => `${name} (${h.toFixed(1)} h)`)
            .join(", ") || "—";

        let pill = `<span class="status-pill status-ok">In linea</span>`;
        if (remaining < 0) pill = `<span class="status-pill status-over">Sforato</span>`;
        else if (planned > 0 && actual / planned >= 0.85) pill = `<span class="status-pill status-warn">In esaurimento</span>`;

        return `
            <tr>
                <td><strong>${cfg.label}</strong></td>
                <td>${membersList}</td>
                <td class="num">${planned.toFixed(1)}</td>
                <td class="num">${actual.toFixed(1)}</td>
                <td class="num">${remaining.toFixed(1)}</td>
                <td class="num">€ ${cost.toFixed(0)}</td>
                <td>${pill}</td>
            </tr>
        `;
    }).join("");
};

const init = async () => {
    const resp = await fetch("./data.json");
    rawData = await resp.json();

    const dt = new Date(rawData.generated_at).toLocaleString("it-IT");
    document.getElementById("meta-info").textContent = `${rawData.project_title} · Aggiornato il ${dt}`;
    if (rawData.is_mock) {
        document.getElementById("mock-banner").hidden = false;
    }

    populateFilters(rawData.entries);
    document.getElementById("sprint-filter").addEventListener("change", render);
    document.getElementById("week-filter").addEventListener("change", render);
    render();
};

document.addEventListener("DOMContentLoaded", () => {
    init().catch((err) => {
        document.getElementById("meta-info").textContent = `Errore caricamento data.json: ${err.message}`;
    });
});
